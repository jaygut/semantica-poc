"""Auto-characterization pipeline for new MPA sites.

Implements a 5-step pipeline:
  1. LOCATE - Fetch MPA metadata from Marine Regions
  2. POPULATE SPECIES - Query OBIS for occurrences, cross-ref WoRMS
  3. CHARACTERIZE HABITAT - Infer habitat types from species + metadata
  4. ESTIMATE SERVICES - Apply relevant bridge axioms based on habitat
  5. SCORE & RATE - Calculate NEOLI score, assign provisional rating

Each step records provenance through P0's MARISProvenanceManager.
"""

from __future__ import annotations

import logging
from typing import Any

from maris.sites.api_clients import MarineRegionsClient, OBISClient, WoRMSClient
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

# Habitat inference rules based on dominant species families / keywords
_HABITAT_INFERENCE: dict[str, list[str]] = {
    "coral_reef": ["Acropora", "Porites", "Pocillopora", "Scleractinia", "coral"],
    "seagrass_meadow": ["Posidonia", "Zostera", "Halophila", "Thalassia", "seagrass"],
    "mangrove_forest": ["Rhizophora", "Avicennia", "Sonneratia", "mangrove"],
    "kelp_forest": ["Macrocystis", "Ecklonia", "Laminaria", "Nereocystis", "kelp"],
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

        return SiteCharacterization(
            canonical_name=name,
            country=country,
            coordinates=coordinates,
            area_km2=area_km2,
            designation_year=designation_year,
            mrgid=mrgid,
        )

    def _step_populate_species(
        self, site: SiteCharacterization
    ) -> list[SpeciesRecord]:
        """Step 2: Query OBIS for species, cross-reference WoRMS."""
        species: list[SpeciesRecord] = []

        try:
            occurrences = self._obis.get_occurrences(
                mpa_name=site.canonical_name, limit=50,
            )
        except ConnectionError:
            logger.warning("OBIS lookup failed for %s", site.canonical_name)
            return species

        seen_ids: set[int] = set()
        for occ in occurrences:
            aphia_id = occ.get("aphiaID") or occ.get("taxonID")
            if not aphia_id or aphia_id in seen_ids:
                continue
            seen_ids.add(aphia_id)

            record = SpeciesRecord(
                scientific_name=occ.get("scientificName", ""),
                common_name=occ.get("vernacularName", ""),
                worms_aphia_id=aphia_id,
            )

            # Enrich from WoRMS
            try:
                worms_rec = self._worms.get_record(aphia_id)
                if worms_rec:
                    record.scientific_name = worms_rec.get(
                        "scientificname", record.scientific_name
                    )
                    record.conservation_status = worms_rec.get("iucn_status", "")
            except ConnectionError:
                logger.warning("WoRMS lookup failed for AphiaID %d", aphia_id)

            species.append(record)

        return species

    def _step_characterize_habitat(
        self,
        site: SiteCharacterization,
        species: list[SpeciesRecord],
    ) -> list[HabitatInfo]:
        """Step 3: Infer habitat types from species composition."""
        habitat_scores: dict[str, int] = {}
        all_names = " ".join(s.scientific_name for s in species).lower()

        for habitat_id, keywords in _HABITAT_INFERENCE.items():
            score = sum(1 for kw in keywords if kw.lower() in all_names)
            if score > 0:
                habitat_scores[habitat_id] = score

        habitats: list[HabitatInfo] = []
        for hab_id in sorted(habitat_scores, key=habitat_scores.get, reverse=True):  # type: ignore[arg-type]
            habitats.append(HabitatInfo(
                habitat_id=hab_id,
                name=hab_id.replace("_", " ").title(),
                extent_km2=site.area_km2,
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
