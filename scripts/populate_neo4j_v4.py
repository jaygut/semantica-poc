#!/usr/bin/env python3
"""Populate Neo4j v4 database with all discovered case study sites.

This script targets a SEPARATE v4 Neo4j database and auto-discovers all
case study JSON files from examples/*_case_study.json. It runs the full
9-stage population pipeline from maris.graph.population (documents,
entities, bridge axioms, relationships, cross-domain links, comparison
sites, provenance) and additionally populates ALL discovered case study
sites using a generic case study populator.

IMPORTANT: This script does NOT run against the production v2/v3 database.
It uses MARIS_NEO4J_URI_V4 (default: bolt://localhost:7688) or
MARIS_NEO4J_DATABASE_V4 to isolate v4 data.

Usage:
    python scripts/populate_neo4j_v4.py
    python scripts/populate_neo4j_v4.py --dry-run
    python scripts/populate_neo4j_v4.py --validate

Idempotent - safe to run multiple times (all operations use MERGE).
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from maris.config_v4 import (
    discover_case_study_paths,
    discover_site_names,
    get_config_v4,
)


# ---------------------------------------------------------------------------
# Habitat ID mapping for linking sites to Habitat nodes
# ---------------------------------------------------------------------------
_HABITAT_IDS = {
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


def _load_json(path: Path) -> dict:
    """Load and return a JSON file."""
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Generic case study populator (works with any site)
# ---------------------------------------------------------------------------
def _populate_case_study_site(session, case_path: Path) -> int:
    """Populate a single case study site into the graph.

    Handles both Cabo Pulmo-style (ecological_recovery) and Shark Bay-style
    (ecological_status) case study structures. Creates:
    - MPA node with full metadata
    - EcosystemService nodes + GENERATES edges
    - Species nodes + LOCATED_IN edges
    - Habitat links (HAS_HABITAT)
    - Provenance edges (DERIVED_FROM)
    """
    cs = _load_json(case_path)
    count = 0

    site = cs.get("site", {})
    site_name = site.get("name", "")
    if not site_name:
        print(f"  WARNING: No site name in {case_path.name}, skipping.")
        return 0

    coords = site.get("coordinates", {})
    neoli = cs.get("neoli_assessment", {})
    rating = cs.get("asset_quality_rating", {})

    # Support both ecological_recovery (Cabo Pulmo) and ecological_status (Shark Bay)
    eco_recovery = cs.get("ecological_recovery", {})
    eco_status = cs.get("ecological_status", {})

    # Determine assessment year and freshness
    import datetime as _dt

    measurement_year = (
        eco_recovery.get("assessment_year")
        or eco_status.get("assessment_year")
        or site.get("designation_year")
        or 2020
    )
    _current_year = _dt.datetime.now().year
    _data_age = _current_year - measurement_year
    if _data_age <= 5:
        data_freshness = "current"
    elif _data_age <= 10:
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
    session.run(
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

    # Create EcosystemService nodes and GENERATES edges
    services = cs.get("ecosystem_services", {}).get("services", [])
    site_prefix = site_name.lower().replace(" ", "_")
    for svc in services:
        svc_type = svc.get("service_type", "")
        service_id = f"{site_prefix}_{svc_type}"
        session.run(
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
        session.run(
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

    # Create Species nodes and LOCATED_IN edges
    for sp in cs.get("key_species", []):
        worms_id = sp.get("worms_aphia_id", 0)
        if worms_id:
            session.run(
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
            session.run(
                """
                MATCH (s:Species {worms_id: $worms_id})
                MATCH (m:MPA {name: $mpa_name})
                MERGE (s)-[:LOCATED_IN]->(m)
                """,
                {"worms_id": worms_id, "mpa_name": site_name},
            )
            count += 1

    # Link site to habitats
    habitats_linked = set()
    # From primary_habitat
    if primary_habitat:
        hab_id = _HABITAT_IDS.get(primary_habitat)
        if hab_id:
            session.run(
                """
                MERGE (h:Habitat {habitat_id: $hab_id})
                ON CREATE SET h.name = $name
                WITH h
                MATCH (m:MPA {name: $mpa_name})
                MERGE (m)-[:HAS_HABITAT]->(h)
                """,
                {
                    "hab_id": hab_id,
                    "name": primary_habitat.replace("_", " ").title(),
                    "mpa_name": site_name,
                },
            )
            habitats_linked.add(hab_id)
            count += 1

    # From habitats list in case study
    for hab in cs.get("habitats", []):
        hab_raw = hab if isinstance(hab, str) else hab.get("habitat_id", "")
        hab_id = _HABITAT_IDS.get(hab_raw, hab_raw)
        if hab_id and hab_id not in habitats_linked:
            session.run(
                """
                MERGE (h:Habitat {habitat_id: $hab_id})
                ON CREATE SET h.name = $name
                WITH h
                MATCH (m:MPA {name: $mpa_name})
                MERGE (m)-[:HAS_HABITAT]->(h)
                """,
                {
                    "hab_id": hab_id,
                    "name": hab_raw.replace("_", " ").title(),
                    "mpa_name": site_name,
                },
            )
            habitats_linked.add(hab_id)
            count += 1

    # From ecological_status.secondary_habitats
    for hab in eco_status.get("secondary_habitats", []):
        hab_id = _HABITAT_IDS.get(hab)
        if hab_id and hab_id not in habitats_linked:
            session.run(
                """
                MERGE (h:Habitat {habitat_id: $hab_id})
                ON CREATE SET h.name = $name
                WITH h
                MATCH (m:MPA {name: $mpa_name})
                MERGE (m)-[:HAS_HABITAT]->(h)
                """,
                {
                    "hab_id": hab_id,
                    "name": hab.replace("_", " ").title(),
                    "mpa_name": site_name,
                },
            )
            habitats_linked.add(hab_id)
            count += 1

    # Ecological recovery habitat (coral reef for Cabo Pulmo style)
    if eco_recovery and "coral_reef" not in habitats_linked:
        session.run(
            """
            MATCH (h:Habitat {habitat_id: "coral_reef"})
            MATCH (m:MPA {name: $mpa_name})
            MERGE (m)-[:HAS_HABITAT]->(h)
            """,
            {"mpa_name": site_name},
        )
        habitats_linked.add("coral_reef")
        count += 1

    # Provenance edges (DERIVED_FROM)
    for src in cs.get("provenance", {}).get("data_sources", []):
        doi = src.get("doi", "")
        if not doi or "xxxx" in doi:
            continue
        session.run(
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

    # NEOLI provenance
    neoli_doi = neoli.get("source", {}).get("doi", "")
    if neoli_doi:
        session.run(
            """
            MATCH (m:MPA {name: $mpa_name})
            MERGE (d:Document {doi: $doi})
            MERGE (m)-[r:DERIVED_FROM]->(d)
            SET r.data_type = "NEOLI assessment"
            """,
            {"mpa_name": site_name, "doi": neoli_doi},
        )
        count += 1

    # Link applicable bridge axioms based on habitat types
    _link_axioms_to_site(session, site_name, habitats_linked)

    print(f"  {site_name}: {count} nodes/edges merged.")
    return count


def _link_axioms_to_site(session, site_name: str, habitats: set[str]) -> None:
    """Link bridge axioms to a site based on its habitat types."""
    # Coral reef axioms
    if "coral_reef" in habitats:
        for aid in ("BA-001", "BA-002", "BA-004", "BA-011", "BA-012"):
            session.run(
                """
                MATCH (a:BridgeAxiom {axiom_id: $aid})
                MATCH (m:MPA {name: $name})
                MERGE (a)-[:APPLIES_TO]->(m)
                """,
                {"aid": aid, "name": site_name},
            )

    # Seagrass axioms
    if "seagrass_meadow" in habitats:
        for aid in ("BA-008", "BA-013"):
            session.run(
                """
                MATCH (a:BridgeAxiom {axiom_id: $aid})
                MATCH (m:MPA {name: $name})
                MERGE (a)-[:APPLIES_TO]->(m)
                """,
                {"aid": aid, "name": site_name},
            )

    # Mangrove axioms
    if "mangrove_forest" in habitats:
        for aid in ("BA-005", "BA-006", "BA-007"):
            session.run(
                """
                MATCH (a:BridgeAxiom {axiom_id: $aid})
                MATCH (m:MPA {name: $name})
                MERGE (a)-[:APPLIES_TO]->(m)
                """,
                {"aid": aid, "name": site_name},
            )

    # Kelp axioms
    if "kelp_forest" in habitats:
        for aid in ("BA-003", "BA-010"):
            session.run(
                """
                MATCH (a:BridgeAxiom {axiom_id: $aid})
                MATCH (m:MPA {name: $name})
                MERGE (a)-[:APPLIES_TO]->(m)
                """,
                {"aid": aid, "name": site_name},
            )

    # Carbon axioms (apply to any site with carbon-relevant habitats)
    carbon_habitats = {"seagrass_meadow", "mangrove_forest", "kelp_forest"}
    if habitats & carbon_habitats:
        for aid in ("BA-014", "BA-015", "BA-016"):
            session.run(
                """
                MATCH (a:BridgeAxiom {axiom_id: $aid})
                MATCH (m:MPA {name: $name})
                MERGE (a)-[:APPLIES_TO]->(m)
                """,
                {"aid": aid, "name": site_name},
            )


# ---------------------------------------------------------------------------
# Dry-run report
# ---------------------------------------------------------------------------
def _dry_run(case_paths: list[Path], sites: list[tuple[str, Path]]) -> None:
    """Print what would be populated without connecting to Neo4j."""
    print("=" * 60)
    print("DRY RUN - No database operations will be performed")
    print("=" * 60)
    print()

    cfg = get_config_v4()
    print(f"Target Neo4j URI:      {cfg.neo4j_uri}")
    print(f"Target Neo4j database: {cfg.neo4j_database}")
    print()

    print(f"Case study files discovered: {len(case_paths)}")
    for p in case_paths:
        print(f"  {p.name}")
    print()

    print(f"Sites to populate: {len(sites)}")
    for name, path in sites:
        cs = _load_json(path)
        esv = cs.get("ecosystem_services", {}).get("total_annual_value_usd", 0)
        n_services = len(cs.get("ecosystem_services", {}).get("services", []))
        n_species = len(cs.get("key_species", []))
        site = cs.get("site", {})
        country = site.get("country", "?")
        area = site.get("area_km2", "?")

        # Determine habitats
        habitats = set()
        eco = cs.get("ecological_status", {})
        ph = eco.get("primary_habitat", "")
        if ph:
            hab_id = _HABITAT_IDS.get(ph)
            if hab_id:
                habitats.add(hab_id)
        for h in cs.get("habitats", []):
            h_raw = h if isinstance(h, str) else h.get("habitat_id", "")
            h_id = _HABITAT_IDS.get(h_raw, h_raw)
            if h_id:
                habitats.add(h_id)
        for h in eco.get("secondary_habitats", []):
            h_id = _HABITAT_IDS.get(h)
            if h_id:
                habitats.add(h_id)
        if cs.get("ecological_recovery"):
            habitats.add("coral_reef")

        hab_str = ", ".join(sorted(habitats)) if habitats else "unknown"
        print(
            f"  {name} ({country})\n"
            f"    Area: {area} km2 | Habitats: {hab_str}\n"
            f"    ESV: ${esv:,.0f} | Services: {n_services} | Species: {n_species}"
        )
    print()

    # Pipeline stages
    print("Population pipeline stages:")
    stages = [
        "1. Documents (from registry)",
        "2. Entities (from entities.jsonld)",
        "3. Cabo Pulmo enrichment (legacy, via population.py)",
        "4. Shark Bay enrichment (legacy, via population.py)",
        "5. Bridge Axioms (16 axioms with evidence links)",
        "6. Comparison sites (GBR, Papahanaumokuakea)",
        "7. Curated relationships (15 cross-domain edges)",
        "8. Cross-domain links (habitat-MPA, framework-MPA)",
        "9. Provenance edges (Cabo Pulmo sources)",
        "10. ALL case study sites (generic populator - new in v4)",
        "11. Dynamic site registration (query classifier)",
    ]
    for stage in stages:
        print(f"  {stage}")

    print()
    print("Estimated operations: ~{} merges".format(
        200  # documents
        + 14  # entities
        + len(sites) * 25  # ~25 ops per site (MPA + services + species + edges)
        + 16  # axioms
        + 2  # comparison sites
        + 15  # relationships
        + 15  # cross-domain links
    ))
    print()
    print("To run for real, remove --dry-run.")


# ---------------------------------------------------------------------------
# Full population pipeline
# ---------------------------------------------------------------------------
def populate_v4(validate: bool = False) -> int:
    """Run the full v4 population pipeline.

    1. Runs the existing 9-stage pipeline from maris.graph.population
    2. Populates ALL discovered case study sites via the generic populator
    3. Registers all site names with the query classifier
    4. Optionally validates the graph
    """
    # Import here to avoid import-time Neo4j connection
    from maris.graph.population import (
        _populate_bridge_axioms,
        _populate_comparison_sites,
        _populate_cross_domain_links,
        _populate_documents,
        _populate_entities,
        _populate_provenance,
        _populate_relationships,
    )
    from maris.graph.schema import SCHEMA_STATEMENTS
    from maris.query.classifier import register_dynamic_sites

    cfg = get_config_v4()
    case_paths = discover_case_study_paths(Path(cfg.project_root))
    sites = discover_site_names(case_paths)

    print(f"Neo4j v4: {cfg.neo4j_uri} (database: {cfg.neo4j_database})")
    print(f"Discovered {len(case_paths)} case study files, {len(sites)} sites")
    print()

    # Safety check: warn if targeting default port
    if "7687" in cfg.neo4j_uri:
        print("WARNING: Targeting port 7687 (default production port).")
        print("Set MARIS_NEO4J_URI_V4 to use a different port for v4.")
        print()

    # Connect to v4 database
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        cfg.neo4j_uri,
        auth=(cfg.neo4j_user, cfg.neo4j_password),
    )
    driver.verify_connectivity()

    print("Populating v4 graph from curated data assets...")
    print("=" * 60)

    total = 0

    with driver.session(database=cfg.neo4j_database) as session:
        # Apply schema
        print("Step 1: Applying schema...")
        for stmt in SCHEMA_STATEMENTS:
            try:
                session.run(stmt)
            except Exception as e:
                if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                    continue
                raise
        print(f"  Schema: {len(SCHEMA_STATEMENTS)} statements applied.")
        print()

        # Run existing pipeline stages
        print("Step 2: Core population pipeline...")
        total += _populate_documents(session, cfg)
        total += _populate_entities(session, cfg)
        total += _populate_bridge_axioms(session, cfg)
        total += _populate_comparison_sites(session)
        total += _populate_relationships(session, cfg)
        total += _populate_cross_domain_links(session)
        total += _populate_provenance(session, cfg)
        print()

        # Populate ALL discovered case study sites
        print("Step 3: Populating all case study sites...")
        for _name, path in sites:
            total += _populate_case_study_site(session, path)
        print()

    # Register all sites with the query classifier
    print("Step 4: Registering sites for query classification...")
    site_names = [name for name, _ in sites]
    n_registered = register_dynamic_sites(site_names)
    print(f"  Registered {n_registered} dynamic site patterns.")
    print()

    # Summary
    print("=" * 60)
    _print_summary(driver, cfg)
    print(f"Population complete. ~{total} operations executed.")

    if validate:
        print()
        print("Step 5: Validating graph...")
        _validate_v4(driver, cfg)

    driver.close()
    return total


def _print_summary(driver, cfg) -> None:
    """Print node and edge count summary."""
    with driver.session(database=cfg.neo4j_database) as session:
        # Node counts
        result = session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count "
            "ORDER BY count DESC"
        )
        print("Node counts:")
        total_nodes = 0
        for rec in result:
            label = rec["label"]
            count = rec["count"]
            total_nodes += count
            print(f"  {label}: {count}")
        print(f"  TOTAL: {total_nodes}")
        print()

        # Edge counts
        result = session.run(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count "
            "ORDER BY count DESC"
        )
        print("Edge counts:")
        total_edges = 0
        for rec in result:
            rtype = rec["type"]
            count = rec["count"]
            total_edges += count
            print(f"  {rtype}: {count}")
        print(f"  TOTAL: {total_edges}")
        print()

        # MPA sites with ESV
        result = session.run(
            "MATCH (m:MPA) "
            "RETURN m.name AS name, m.total_esv_usd AS esv, "
            "       m.asset_rating AS rating, m.characterization_tier AS tier "
            "ORDER BY m.total_esv_usd DESC"
        )
        print("MPA sites:")
        for rec in result:
            name = rec["name"]
            esv = rec["esv"]
            rating = rec["rating"] or "N/A"
            tier = rec["tier"] or "legacy"
            esv_str = f"${esv:,.0f}" if esv else "N/A"
            print(f"  {name}: ESV={esv_str}, Rating={rating}, Tier={tier}")
        print()


def _validate_v4(driver, cfg) -> None:
    """Run basic validation checks against the v4 graph."""
    with driver.session(database=cfg.neo4j_database) as session:
        checks = {}

        # Node counts
        result = session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count"
        )
        node_counts = {rec["label"]: rec["count"] for rec in result}

        checks["has_documents"] = node_counts.get("Document", 0) > 0
        checks["has_mpas"] = node_counts.get("MPA", 0) >= 4
        checks["has_axioms"] = node_counts.get("BridgeAxiom", 0) >= 12
        checks["has_services"] = node_counts.get("EcosystemService", 0) > 0

        # All axioms have evidence
        result = session.run(
            "MATCH (a:BridgeAxiom) "
            "OPTIONAL MATCH (a)-[:EVIDENCED_BY]->(d:Document) "
            "WITH a, count(d) AS docs "
            "WHERE docs = 0 "
            "RETURN count(a) AS unevidenced"
        )
        rec = result.single()
        checks["all_axioms_have_evidence"] = (rec["unevidenced"] == 0) if rec else True

        # All Gold-tier MPAs have GENERATES edges
        result = session.run(
            "MATCH (m:MPA) WHERE m.total_esv_usd > 0 "
            "OPTIONAL MATCH (m)-[:GENERATES]->(es:EcosystemService) "
            "WITH m, count(es) AS svc_count "
            "WHERE svc_count = 0 "
            "RETURN count(m) AS orphan_mpas"
        )
        rec = result.single()
        checks["gold_mpas_have_services"] = (rec["orphan_mpas"] == 0) if rec else True

        print()
        print("VALIDATION CHECKS:")
        all_pass = True
        for check, passed in checks.items():
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {check}")
            if not passed:
                all_pass = False

        print("=" * 60)
        print(f"Overall: {'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Populate MARIS v4 Neo4j graph (separate database)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be populated without connecting to Neo4j",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation after population",
    )
    args = parser.parse_args()

    cfg = get_config_v4()
    case_paths = discover_case_study_paths(Path(cfg.project_root))
    sites = discover_site_names(case_paths)

    if args.dry_run:
        _dry_run(case_paths, sites)
        return

    try:
        populate_v4(validate=args.validate)
    except Exception as e:
        print(f"\nERROR: {e}")
        print("Make sure the v4 Neo4j instance is running and accessible.")
        print(f"Expected URI: {cfg.neo4j_uri}")
        sys.exit(1)


if __name__ == "__main__":
    main()
