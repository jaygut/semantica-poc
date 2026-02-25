"""Service for loading Case Study JSONs into Neo4j."""

import json
import datetime
from pathlib import Path
from typing import Any

from neo4j import Session



# Habitat ID mapping for normalization
HABITAT_IDS = {
    "coral_reef": "coral_reef",
    "coral reef": "coral_reef",
    "seagrass_meadow": "seagrass_meadow",
    "seagrass meadow": "seagrass_meadow",
    "seagrass": "seagrass_meadow",
    "mangrove_forest": "mangrove_forest",
    "mangrove forest": "mangrove_forest",
    "mangrove": "mangrove_forest",
    "kelp_forest": "kelp_forest",
    "kelp forest": "kelp_forest",
    "kelp": "kelp_forest",
}


class CaseStudyLoader:
    """Service to load case study JSON data into the Graph."""

    def __init__(self, session: Session):
        self.session = session

    def load_site(self, case_path: Path) -> int:
        """Populate a single case study site into the graph.

        Args:
            case_path: Path to the case study JSON file.

        Returns:
            Number of operations/nodes merged.
        """
        try:
            with open(case_path) as f:
                cs = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error loading {case_path}: {e}")
            return 0

        count = 0
        site = cs.get("site", {})
        site_name = site.get("name", "")
        
        if not site_name:
            # Fallback to name inside file or filename if missing
            from maris.services.ingestion.discovery import _name_from_filename
            site_name = _name_from_filename(case_path)
            
        if not site_name:
             print(f"  WARNING: No site name in {case_path.name}, skipping.")
             return 0

        coords = site.get("coordinates", {})
        neoli = cs.get("neoli_assessment", {})
        rating = cs.get("asset_quality_rating", {})

        # Support both ecological_recovery and ecological_status structures
        eco_recovery = cs.get("ecological_recovery", {})
        eco_status = cs.get("ecological_status", {})

        # Determine assessment year and freshness
        measurement_year = (
            eco_recovery.get("assessment_year")
            or eco_status.get("assessment_year")
            or site.get("designation_year")
            or 2020
        )
        current_year = datetime.datetime.now().year
        data_age = current_year - measurement_year
        if data_age <= 5:
            data_freshness = "current"
        elif data_age <= 10:
            data_freshness = "aging"
        else:
            data_freshness = "stale"

        # Total ESV
        total_esv = cs.get("ecosystem_services", {}).get("total_annual_value_usd", 0)

        # Primary habitat
        primary_habitat = eco_status.get("primary_habitat", "")

        # Biomass recovery (Cabo Pulmo style)
        biomass = eco_recovery.get("metrics", {}).get("fish_biomass", {})
        biomass_ratio = biomass.get("recovery_ratio")
        ci_low = None
        ci_high = None
        ci = biomass.get("confidence_interval_95", [])
        if len(ci) >= 2:
            ci_low = ci[0]
            ci_high = ci[1]

        # Merge MPA node
        self.session.run(
            """
            MERGE (m:MPA {name: $name})
            SET m.country          = $country,
                m.lat              = $lat,
                m.lon              = $lon,
                m.area_km2         = $area_km2,
                m.designation_year = $designation_year,
                m.neoli_score      = $neoli_score,
                m.neoli_no_take    = $no_take,
                m.neoli_enforced   = $enforced,
                m.neoli_old        = $old,
                m.neoli_large      = $large,
                m.neoli_isolated   = $isolated,
                m.primary_habitat  = $primary_habitat,
                m.biomass_ratio    = $biomass_ratio,
                m.biomass_ci_low   = $ci_low,
                m.biomass_ci_high  = $ci_high,
                m.biomass_measurement_year = $measurement_year,
                m.asset_rating     = $asset_rating,
                m.asset_score      = $asset_score,
                m.total_esv_usd    = $total_esv,
                m.data_freshness_status = $freshness,
                m.characterization_tier = "gold"
            """,
            {
                "name": site_name,
                "country": site.get("country", ""),
                "lat": coords.get("latitude"),
                "lon": coords.get("longitude"),
                "area_km2": site.get("area_km2"),
                "designation_year": site.get("designation_year"),
                "neoli_score": neoli.get("neoli_score"),
                "no_take": neoli.get("criteria", {}).get("no_take", {}).get("value"),
                "enforced": neoli.get("criteria", {}).get("enforced", {}).get("value"),
                "old": neoli.get("criteria", {}).get("old", {}).get("value"),
                "large": neoli.get("criteria", {}).get("large", {}).get("value"),
                "isolated": neoli.get("criteria", {}).get("isolated", {}).get("value"),
                "primary_habitat": primary_habitat,
                "biomass_ratio": biomass_ratio,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "measurement_year": measurement_year,
                "asset_rating": rating.get("rating", ""),
                "asset_score": rating.get("composite_score"),
                "total_esv": total_esv,
                "freshness": data_freshness,
            },
        )
        count += 1

        # Create EcosystemService nodes
        services = cs.get("ecosystem_services", {}).get("services", [])
        site_prefix = site_name.lower().replace(" ", "_")
        for svc in services:
            svc_type = svc.get("service_type", "")
            service_id = f"{site_prefix}_{svc_type}"
            self.session.run(
                """
                MERGE (es:EcosystemService {service_id: $service_id})
                SET es.service_name     = $name,
                    es.service_type     = $svc_type,
                    es.category         = $category,
                    es.annual_value_usd = $value,
                    es.valuation_method = $method
                """,
                {
                    "service_id": service_id,
                    "name": svc_type.replace("_", " ").title(),
                    "svc_type": svc_type,
                    "category": svc.get("service_category", ""),
                    "value": svc.get("annual_value_usd"),
                    "method": svc.get("valuation_method", ""),
                },
            )
            self.session.run(
                """
                MATCH (m:MPA {name: $mpa_name})
                MATCH (es:EcosystemService {service_id: $service_id})
                MERGE (m)-[g:GENERATES]->(es)
                SET g.total_usd_yr = $value,
                    g.method       = $method
                """,
                {
                    "mpa_name": site_name,
                    "service_id": service_id,
                    "value": svc.get("annual_value_usd"),
                    "method": svc.get("valuation_method", ""),
                },
            )
            count += 1

        # Key Species
        for sp in cs.get("key_species", []):
            worms_id = sp.get("worms_aphia_id", 0)
            if worms_id:
                self.session.run(
                    """
                    MERGE (s:Species {worms_id: $worms_id})
                    SET s.scientific_name      = $scientific_name,
                        s.common_name          = $common_name,
                        s.functional_group     = $functional_group,
                        s.conservation_status  = $conservation_status,
                        s.role_in_ecosystem    = $role
                    """,
                    {
                        "worms_id": worms_id,
                        "scientific_name": sp.get("scientific_name", ""),
                        "common_name": sp.get("common_name", ""),
                        "functional_group": sp.get("functional_group", ""),
                        "conservation_status": sp.get("conservation_status", ""),
                        "role": sp.get("role_in_ecosystem", ""),
                    },
                )
                self.session.run(
                    """
                    MATCH (s:Species {worms_id: $worms_id})
                    MATCH (m:MPA {name: $mpa_name})
                    MERGE (s)-[:LOCATED_IN]->(m)
                    """,
                    {"worms_id": worms_id, "mpa_name": site_name},
                )
                count += 1

        # Habitats
        habitats_linked = set()
        if primary_habitat:
            hab_id = HABITAT_IDS.get(primary_habitat)
            if hab_id:
                self._link_habitat(site_name, hab_id, primary_habitat, habitats_linked)
                count += 1

        for hab in cs.get("habitats", []):
            hab_raw = hab if isinstance(hab, str) else hab.get("habitat_id", "")
            hab_id = HABITAT_IDS.get(hab_raw, hab_raw)
            if hab_id and hab_id not in habitats_linked:
                self._link_habitat(site_name, hab_id, hab_raw, habitats_linked)
                count += 1

        for hab in eco_status.get("secondary_habitats", []):
            hab_id = HABITAT_IDS.get(hab)
            if hab_id and hab_id not in habitats_linked:
                self._link_habitat(site_name, hab_id, hab, habitats_linked)
                count += 1

        if eco_recovery and "coral_reef" not in habitats_linked:
            self.session.run(
                """
                MATCH (h:Habitat {habitat_id: "coral_reef"})
                MATCH (m:MPA {name: $mpa_name})
                MERGE (m)-[:HAS_HABITAT]->(h)
                """,
                {"mpa_name": site_name},
            )
            habitats_linked.add("coral_reef")
            count += 1

        # Provenance
        for src in cs.get("provenance", {}).get("data_sources", []):
            doi = src.get("doi", "")
            if not doi or "xxxx" in doi:
                continue
            self.session.run(
                """
                MATCH (m:MPA {name: $mpa_name})
                MERGE (d:Document {doi: $doi})
                MERGE (m)-[r:DERIVED_FROM]->(d)
                SET r.data_type   = $data_type,
                    r.access_date = $access_date
                """,
                {
                    "mpa_name": site_name,
                    "doi": doi,
                    "data_type": src.get("data_type", ""),
                    "access_date": src.get("access_date", ""),
                },
            )
            count += 1

        neoli_doi = neoli.get("source", {}).get("doi", "")
        if neoli_doi:
            self.session.run(
                """
                MATCH (m:MPA {name: $mpa_name})
                MERGE (d:Document {doi: $doi})
                MERGE (m)-[r:DERIVED_FROM]->(d)
                SET r.data_type = "NEOLI assessment"
                """,
                {"mpa_name": site_name, "doi": neoli_doi},
            )
            count += 1

        # Trophic Network & Cascades
        self._load_trophic_network(site_name, cs.get("trophic_network", {}))

        # Financial Mechanisms (Debt Swaps, Blue Bonds)
        self._load_financial_mechanisms(site_name, cs.get("financial_mechanisms", []))

        # Risks (Climate, biological, anthropogenic)
        self._load_risks(site_name, cs.get("risk_assessment", {}))

        # Link Axioms
        self._link_axioms_to_site(site_name, habitats_linked)

        # OBIS enrichment properties (no-op if keys absent in case study)
        self._load_obis_properties(site_name, cs)

        print(f"  {site_name}: {count} nodes/edges merged.")
        return count

    def _load_risks(self, site_name: str, risk_data: dict[str, Any]) -> None:
        """Create structured nodes for risk factors."""
        if not risk_data:
            return

        risks = risk_data.get("risk_factors", [])
        for risk in risks:
            self.session.run(
                """
                MERGE (r:Risk {name: $risk_type})
                WITH r
                MATCH (m:MPA {name: $site_name})
                MERGE (m)-[rel:FACES_RISK]->(r)
                SET rel.severity   = $severity,
                    rel.likelihood = $likelihood,
                    rel.evidence   = $evidence
                """,
                {
                    "risk_type": risk.get("risk_type", "").replace("_", " ").title(),
                    "severity": risk.get("severity", ""),
                    "likelihood": risk.get("likelihood", ""),
                    "evidence": risk.get("evidence", ""),
                    "site_name": site_name
                }
            )

    def _load_trophic_network(self, site_name: str, network: dict[str, Any]) -> None:
        """Create structured nodes for ecological cascades and pathways."""
        if not network:
            return

        # 1. Trophic Cascades (High-level processes)
        for cascade in network.get("cascade_pathways", []):
            desc = cascade.get("description", "")
            effect = cascade.get("effect", "")
            chain_str = " ".join(cascade.get("chain", []))
            
            # Create process node
            self.session.run(
                """
                MERGE (p:EcologicalProcess {name: $name})
                SET p.description = $desc,
                    p.effect      = $effect,
                    p.chain       = $chain
                WITH p
                MATCH (m:MPA {name: $site_name})
                MERGE (m)-[:HAS_ECOLOGICAL_PROCESS]->(p)
                """,
                {
                    "name": desc,
                    "desc": desc,
                    "effect": effect,
                    "chain": chain_str,
                    "site_name": site_name
                }
            )

        # 2. Food Web Structure (Optional detail)
        # We can link key species to functional groups if needed later
        pass

    def _load_financial_mechanisms(self, site_name: str, mechanisms: list[dict[str, Any]]) -> None:
        """Create structured nodes for financial instruments (swaps, bonds, credits)."""
        if not mechanisms:
            return

        for mech in mechanisms:
            self.session.run(
                """
                MERGE (f:FinancialMechanism {name: $name})
                SET f.type        = $mech_type,
                    f.year        = $year,
                    f.amount_usd  = $amount,
                    f.description = $desc,
                    f.status      = $status
                WITH f
                MATCH (m:MPA {name: $site_name})
                MERGE (m)-[:USING_MECHANISM]->(f)
                """,
                {
                    "name": mech.get("name", ""),
                    "mech_type": mech.get("mechanism_type", ""),
                    "year": mech.get("year"),
                    "amount": mech.get("amount_usd"),
                    "desc": mech.get("description", ""),
                    "status": mech.get("status", "active"),
                    "site_name": site_name
                }
            )

    def _link_habitat(self, site_name: str, hab_id: str, raw_name: str, linked_set: set) -> None:
        """Helper to merge habitat link."""
        self.session.run(
            """
            MERGE (h:Habitat {habitat_id: $hab_id})
            ON CREATE SET h.name = $name
            WITH h
            MATCH (m:MPA {name: $mpa_name})
            MERGE (m)-[:HAS_HABITAT]->(h)
            """,
            {
                "hab_id": hab_id,
                "name": raw_name.replace("_", " ").title(),
                "mpa_name": site_name,
            },
        )
        linked_set.add(hab_id)

    def _load_obis_properties(self, site_name: str, cs: dict) -> None:
        """Write OBIS-derived properties onto the MPA node (no-op if keys absent)."""
        bio = cs.get("biodiversity_metrics") or {}
        qual = cs.get("observation_quality") or {}
        env = (cs.get("environmental_baselines") or {}).get("sst") or {}

        if not any([bio, qual, env]):
            return

        year_range = bio.get("year_range")
        self.session.run(
            """
            MATCH (m:MPA {name: $name})
            SET m.obis_species_richness          = $species_richness,
                m.obis_iucn_threatened_count     = $iucn_threatened,
                m.obis_total_records             = $total_records,
                m.obis_observation_quality_score = $quality_score,
                m.obis_median_sst_c              = $median_sst,
                m.obis_bleaching_proximity_c     = $bleaching_proximity,
                m.obis_data_year_min             = $year_min,
                m.obis_data_year_max             = $year_max,
                m.obis_fetched_at                = $fetched_at
            """,
            {
                "name": site_name,
                "species_richness": bio.get("species_richness"),
                "iucn_threatened": bio.get("iucn_threatened_count"),
                "total_records": bio.get("total_records"),
                "quality_score": qual.get("composite_quality_score"),
                "median_sst": env.get("median_sst_c"),
                "bleaching_proximity": env.get("bleaching_proximity_c"),
                "year_min": year_range[0] if year_range else None,
                "year_max": year_range[1] if year_range else None,
                "fetched_at": bio.get("obis_fetched_at"),
            },
        )

    def _link_axioms_to_site(self, site_name: str, habitats: set[str]) -> None:
        """Link bridge axioms to a site based on its habitat types."""
        # Mapping of habitat to axiom IDs
        mappings = {
            "coral_reef": ["BA-001", "BA-002", "BA-004", "BA-011", "BA-012", 
                           "BA-023", "BA-026", "BA-028", "BA-029"],
            "seagrass_meadow": ["BA-008", "BA-013", "BA-025"],
            "mangrove_forest": ["BA-005", "BA-006", "BA-007", "BA-017"],
            "kelp_forest": ["BA-003", "BA-010", "BA-018"],
        }

        # Specific habitats
        for habitat, axioms in mappings.items():
            if habitat in habitats:
                for aid in axioms:
                    self._merge_applies_to(site_name, aid)

        # Carbon
        carbon_habitats = {"seagrass_meadow", "mangrove_forest", "kelp_forest"}
        if habitats & carbon_habitats:
            for aid in ("BA-014", "BA-015", "BA-016", "BA-020", "BA-021", "BA-022"):
                self._merge_applies_to(site_name, aid)

        # Cross-cutting
        for aid in ("BA-027", "BA-034", "BA-035"):
            self._merge_applies_to(site_name, aid)

    def _merge_applies_to(self, site_name: str, axiom_id: str) -> None:
        self.session.run(
            """
            MATCH (a:BridgeAxiom {axiom_id: $aid})
            MATCH (m:MPA {name: $name})
            MERGE (a)-[:APPLIES_TO]->(m)
            """,
            {"aid": axiom_id, "name": site_name},
        )
