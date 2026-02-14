"""Auto-characterization pipeline for new MPA sites.

Implements a 5-step pipeline:
  1. LOCATE - Fetch MPA metadata from Marine Regions
  2. POPULATE SPECIES - Query OBIS checklist, cross-ref WoRMS for taxonomy and attributes
  3. CHARACTERIZE HABITAT - Score habitat types from taxonomic hierarchy and functional groups
  4. ESTIMATE SERVICES - Apply relevant bridge axioms based on habitat
  5. SCORE & RATE - Calculate NEOLI score, assign provisional rating

Each step records provenance through P0's MARISProvenanceManager.
"""

from __future__ import annotations

import logging
from typing import Any

from maris.sites.api_clients import (
    MarineRegionsClient,
    OBISClient,
    WoRMSClient,
    flatten_classification,
)
from maris.sites.esv_estimator import estimate_esv
from maris.sites.models import (
    CharacterizationTier,
    CoordinatePair,
    EcosystemServiceEstimate,
    HabitatInfo,
    SiteCharacterization,
    SpeciesRecord,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Habitat inference configuration
# ---------------------------------------------------------------------------

# Keyword matches on species scientific names (genus, order, common name)
_HABITAT_KEYWORDS: dict[str, list[str]] = {
    "coral_reef": ["Acropora", "Porites", "Pocillopora", "Scleractinia", "coral",
                    "Montipora", "Stylophora", "Fungia", "Millepora"],
    "seagrass_meadow": ["Posidonia", "Zostera", "Halophila", "Thalassia", "seagrass",
                         "Cymodocea", "Halodule", "Syringodium", "Enhalus"],
    "mangrove_forest": ["Rhizophora", "Avicennia", "Sonneratia", "mangrove",
                         "Bruguiera", "Ceriops", "Laguncularia"],
    "kelp_forest": ["Macrocystis", "Ecklonia", "Laminaria", "Nereocystis", "kelp",
                     "Saccharina", "Undaria", "Lessonia"],
}

# Taxonomic indicators: order/family names that strongly indicate habitat
_TAXONOMIC_INDICATORS: dict[str, dict[str, list[str]]] = {
    "coral_reef": {
        "Order": ["Scleractinia", "Alcyonacea"],
        "Family": ["Acroporidae", "Poritidae", "Pocilloporidae", "Faviidae",
                    "Fungiidae", "Merulinidae", "Milleporidae"],
    },
    "seagrass_meadow": {
        "Order": ["Alismatales"],
        "Family": ["Posidoniaceae", "Zosteraceae", "Hydrocharitaceae",
                    "Cymodoceaceae"],
    },
    "mangrove_forest": {
        "Order": ["Malpighiales", "Lamiales"],
        "Family": ["Rhizophoraceae", "Acanthaceae", "Combretaceae"],
    },
    "kelp_forest": {
        "Order": ["Laminariales"],
        "Family": ["Laminariaceae", "Lessoniaceae", "Alariaceae"],
    },
}

# WoRMS functional group keywords that map to habitats
_FUNCTIONAL_GROUP_HABITAT: dict[str, list[str]] = {
    "coral_reef": ["reef-associated", "coral", "coral reef"],
    "seagrass_meadow": ["seagrass", "seagrass-associated"],
    "mangrove_forest": ["mangrove", "mangrove-associated"],
    "kelp_forest": ["kelp", "macroalgae"],
}


class SiteCharacterizer:
    """Orchestrates the multi-step characterization of a new MPA site."""

    def __init__(
        self,
        obis_client: OBISClient | None = None,
        worms_client: WoRMSClient | None = None,
        marine_regions_client: MarineRegionsClient | None = None,
        provenance_manager: Any | None = None,
    ) -> None:
        self._obis = obis_client or OBISClient()
        self._worms = worms_client or WoRMSClient()
        self._mr = marine_regions_client or MarineRegionsClient()
        self._provenance = provenance_manager

    def characterize(
        self,
        name: str,
        tier: CharacterizationTier = CharacterizationTier.bronze,
        country: str = "",
        coordinates: CoordinatePair | None = None,
        area_km2: float | None = None,
        designation_year: int | None = None,
    ) -> SiteCharacterization:
        """Run the full characterization pipeline for a site.

        Parameters
        ----------
        name : Human-readable MPA name.
        tier : Desired characterization depth.
        country : Country if known (skips lookup).
        coordinates : Lat/lon if known (skips lookup).
        area_km2 : Area if known.
        designation_year : Year of designation if known.
        """
        # Step 1: LOCATE - resolve metadata from Marine Regions
        site = self._step_locate(
            name, country=country, coordinates=coordinates,
            area_km2=area_km2, designation_year=designation_year,
        )
        self._track_provenance("locate", site.canonical_name, {"step": "locate"})

        if tier == CharacterizationTier.bronze:
            site.tier = CharacterizationTier.bronze
            return site

        # Step 2: POPULATE SPECIES
        species = self._step_populate_species(site)
        site.species = species
        self._track_provenance("populate_species", site.canonical_name, {
            "step": "species", "count": len(species),
        })

        # Step 3: CHARACTERIZE HABITAT
        habitats = self._step_characterize_habitat(site, species)
        site.habitats = habitats
        self._track_provenance("characterize_habitat", site.canonical_name, {
            "step": "habitat", "habitats": [h.habitat_id for h in habitats],
        })

        # Step 4: ESTIMATE SERVICES
        services, total_esv, esv_confidence = self._step_estimate_services(site, habitats)
        site.ecosystem_services = services
        site.estimated_esv_usd = total_esv
        site.esv_confidence = esv_confidence
        self._track_provenance("estimate_services", site.canonical_name, {
            "step": "esv", "total_esv_usd": total_esv,
        })

        # Step 5: SCORE & RATE
        neoli_score, asset_rating = self._step_score_and_rate(site)
        site.neoli_score = neoli_score
        site.asset_rating = asset_rating
        self._track_provenance("score_rate", site.canonical_name, {
            "step": "scoring", "neoli": neoli_score, "rating": asset_rating,
        })

        site.tier = tier
        return site

    # -- Step implementations --------------------------------------------------

    def _step_locate(
        self,
        name: str,
        country: str = "",
        coordinates: CoordinatePair | None = None,
        area_km2: float | None = None,
        designation_year: int | None = None,
    ) -> SiteCharacterization:
        """Step 1: Resolve MPA metadata from Marine Regions or supplied data."""
        mrgid: int | None = None
        boundary_wkt: str | None = None

        if not country or not coordinates:
            try:
                records = self._mr.search_by_name(name)
                if records:
                    rec = records[0]
                    country = country or rec.get("country", "")
                    if not coordinates:
                        lat = rec.get("latitude")
                        lon = rec.get("longitude")
                        if lat is not None and lon is not None:
                            coordinates = CoordinatePair(latitude=lat, longitude=lon)
                    area_km2 = area_km2 or rec.get("area_km2")
                    designation_year = designation_year or rec.get("year")
                    mrgid = rec.get("MRGID")
            except ConnectionError:
                logger.warning("Marine Regions lookup failed for %s", name)

        # Fetch boundary geometry for spatial queries if MRGID available
        if mrgid:
            try:
                geom = self._mr.get_geometry(mrgid)
                boundary_wkt = geom.get("the_geom") or geom.get("geometry")
            except ConnectionError:
                logger.warning("Marine Regions geometry lookup failed for MRGID %d", mrgid)

        site = SiteCharacterization(
            canonical_name=name,
            country=country,
            coordinates=coordinates,
            area_km2=area_km2,
            designation_year=designation_year,
            mrgid=mrgid,
        )
        # Store boundary WKT for use in OBIS spatial queries (not persisted in model)
        site._boundary_wkt = boundary_wkt  # type: ignore[attr-defined]
        return site

    def _step_populate_species(
        self, site: SiteCharacterization
    ) -> list[SpeciesRecord]:
        """Step 2: Query OBIS for species, cross-reference WoRMS.

        Uses the OBIS checklist endpoint first (more efficient - deduplicated
        server-side). Falls back to raw occurrences if checklist fails.
        Enriches each species with WoRMS record, taxonomic classification,
        and biological attributes (functional group, trophic level).
        """
        species: list[SpeciesRecord] = []

        # Try checklist endpoint first (more efficient, deduplicated).
        # If boundary WKT is available from Marine Regions, use spatial query.
        # Fall back to name-based occurrence query as last resort.
        boundary_wkt: str | None = getattr(site, "_boundary_wkt", None)
        obis_records: list[dict[str, Any]] = []

        try:
            obis_records = self._obis.get_checklist(
                geometry=boundary_wkt,
                mpa_name=site.canonical_name if not boundary_wkt else None,
                limit=100,
            )
        except ConnectionError:
            logger.warning("OBIS checklist failed for %s", site.canonical_name)

        if not obis_records:
            try:
                obis_records = self._obis.get_occurrences(
                    geometry=boundary_wkt,
                    mpa_name=site.canonical_name if not boundary_wkt else None,
                    limit=100,
                )
            except ConnectionError:
                logger.warning("OBIS occurrence fallback failed for %s", site.canonical_name)
                return species

        seen_ids: set[int] = set()
        for occ in obis_records:
            aphia_id = occ.get("aphiaID") or occ.get("taxonID")
            if not aphia_id or aphia_id in seen_ids:
                continue
            seen_ids.add(aphia_id)

            record = SpeciesRecord(
                scientific_name=occ.get("scientificName", ""),
                common_name=occ.get("vernacularName", ""),
                worms_aphia_id=aphia_id,
            )

            # Enrich from WoRMS record (basic info + IUCN status)
            try:
                worms_rec = self._worms.get_record(aphia_id)
                if worms_rec:
                    record.scientific_name = worms_rec.get(
                        "scientificname", record.scientific_name
                    )
                    record.conservation_status = worms_rec.get("iucn_status", "")
            except ConnectionError:
                logger.warning("WoRMS record lookup failed for AphiaID %d", aphia_id)

            # Enrich with taxonomic classification
            try:
                classification = self._worms.get_classification(aphia_id)
                if classification:
                    flat = flatten_classification(classification)
                    record._classification = flat  # type: ignore[attr-defined]
            except ConnectionError:
                logger.warning("WoRMS classification failed for AphiaID %d", aphia_id)

            # Enrich with biological attributes (functional group, trophic level)
            try:
                attrs = self._worms.get_attributes(aphia_id)
                for attr in attrs:
                    mtype = (attr.get("measurementType") or "").lower()
                    mvalue = attr.get("measurementValue", "")
                    if "functional group" in mtype or "functional_group" in mtype:
                        record.functional_group = str(mvalue)
                    elif "trophic" in mtype and mvalue:
                        try:
                            record.trophic_level = float(mvalue)
                        except (ValueError, TypeError):
                            pass
            except ConnectionError:
                logger.warning("WoRMS attributes failed for AphiaID %d", aphia_id)

            species.append(record)

        return species

    def _step_characterize_habitat(
        self,
        site: SiteCharacterization,
        species: list[SpeciesRecord],
    ) -> list[HabitatInfo]:
        """Step 3: Infer habitat types from species composition.

        Uses a multi-signal scoring system:
          1. Keyword matches on scientific names (1 pt each)
          2. Taxonomic hierarchy indicators at order/family level (3 pts each)
          3. WoRMS functional group keywords (2 pts each)

        Only habitats with score >= 1 are included. Confidence is derived
        from the proportion of indicator species found.
        """
        habitat_scores: dict[str, float] = {}
        habitat_indicator_count: dict[str, int] = {}

        for hab_id in _HABITAT_KEYWORDS:
            habitat_scores[hab_id] = 0.0
            habitat_indicator_count[hab_id] = 0

        for sp in species:
            name_lower = sp.scientific_name.lower()
            classification: dict[str, str] = getattr(sp, "_classification", {})
            func_group_lower = sp.functional_group.lower()

            for hab_id, keywords in _HABITAT_KEYWORDS.items():
                # Signal 1: keyword match on scientific name
                for kw in keywords:
                    if kw.lower() in name_lower:
                        habitat_scores[hab_id] += 1.0
                        habitat_indicator_count[hab_id] += 1
                        break

                # Signal 2: taxonomic hierarchy (order / family level)
                if classification:
                    tax_indicators = _TAXONOMIC_INDICATORS.get(hab_id, {})
                    for rank, indicator_names in tax_indicators.items():
                        sp_rank_value = classification.get(rank, "")
                        if sp_rank_value in indicator_names:
                            habitat_scores[hab_id] += 3.0
                            habitat_indicator_count[hab_id] += 1
                            break

                # Signal 3: WoRMS functional group
                if func_group_lower:
                    fg_keywords = _FUNCTIONAL_GROUP_HABITAT.get(hab_id, [])
                    for fg_kw in fg_keywords:
                        if fg_kw in func_group_lower:
                            habitat_scores[hab_id] += 2.0
                            habitat_indicator_count[hab_id] += 1
                            break

        habitats: list[HabitatInfo] = []
        total_species = max(len(species), 1)
        for hab_id in sorted(habitat_scores, key=habitat_scores.get, reverse=True):  # type: ignore[arg-type]
            score = habitat_scores[hab_id]
            if score < 1.0:
                continue
            indicator_frac = habitat_indicator_count[hab_id] / total_species
            habitats.append(HabitatInfo(
                habitat_id=hab_id,
                name=hab_id.replace("_", " ").title(),
                extent_km2=site.area_km2,
                confidence=min(indicator_frac, 1.0),
            ))

        return habitats

    def _step_estimate_services(
        self,
        site: SiteCharacterization,
        habitats: list[HabitatInfo],
    ) -> tuple[list[EcosystemServiceEstimate], float, dict[str, Any]]:
        """Step 4: Apply bridge axioms to estimate ESV."""
        return estimate_esv(habitats, area_km2=site.area_km2)

    def _step_score_and_rate(
        self, site: SiteCharacterization
    ) -> tuple[int, str]:
        """Step 5: Calculate provisional NEOLI score and asset rating.

        NEOLI criteria:
          N - No-take: assumed if designation_year is set
          E - Enforced: assumed True for designated MPAs
          O - Old: >10 years since designation
          L - Large: >100 km2
          I - Isolated: cannot infer, defaults to False
        """
        import datetime

        criteria: dict[str, bool] = {}
        criteria["no_take"] = site.designation_year is not None
        criteria["enforced"] = site.designation_year is not None
        current_year = datetime.datetime.now().year
        if site.designation_year:
            criteria["old"] = (current_year - site.designation_year) > 10
        else:
            criteria["old"] = False
        criteria["large"] = (site.area_km2 or 0) > 100
        criteria["isolated"] = False  # Cannot infer from metadata alone

        site.neoli_criteria = criteria
        score = sum(1 for v in criteria.values() if v)

        # Rating scale based on NEOLI + ESV availability
        if score >= 4 and site.estimated_esv_usd and site.estimated_esv_usd > 0:
            rating = "AA"
        elif score >= 3:
            rating = "A"
        elif score >= 2:
            rating = "BBB"
        else:
            rating = "BB"

        return score, rating

    # -- Provenance helper -----------------------------------------------------

    def _track_provenance(
        self, activity_type: str, entity_id: str, attributes: dict[str, Any]
    ) -> None:
        """Record a provenance activity if manager is available."""
        if self._provenance is None:
            return
        try:
            self._provenance.provenance.record_activity(
                activity_type=f"characterization:{activity_type}",
                used=[],
                generated=[entity_id],
                associated_with="maris:system",
                attributes=attributes,
            )
        except Exception:
            logger.warning("Provenance tracking failed for %s", activity_type)
