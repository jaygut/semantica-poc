#!/usr/bin/env python3
"""Populate Neo4j v4 database with all discovered case study sites.

This script targets a SEPARATE v4 Neo4j database and auto-discovers all
case study JSON files from examples/*_case_study.json. It runs the full
population pipeline using modular services from maris.services.ingestion.

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
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from maris.config_v4 import get_config_v4
from maris.services.ingestion.discovery import (
    discover_case_study_paths,
    discover_site_names,
)
from maris.services.ingestion.case_study_loader import CaseStudyLoader, HABITAT_IDS
from maris.services.ingestion.concepts_loader import ConceptsLoader


def _load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _populate_concepts(session) -> int:
    """Populate Concept nodes and INVOLVES_AXIOM edges from concepts.json."""
    loader = ConceptsLoader(session)
    return loader.load_concepts()


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
            hab_id = HABITAT_IDS.get(ph)
            if hab_id:
                habitats.add(hab_id)
        for h in cs.get("habitats", []):
            h_raw = h if isinstance(h, str) else h.get("habitat_id", "")
            h_id = HABITAT_IDS.get(h_raw, h_raw)
            if h_id:
                habitats.add(h_id)
        for h in eco.get("secondary_habitats", []):
            h_id = HABITAT_IDS.get(h)
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
    print("To run for real, remove --dry-run.")


def populate_v4(validate: bool = False) -> int:
    """Run the full v4 population pipeline."""
    # Import legacy pipeline stages (kept for now)
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
    from neo4j import GraphDatabase

    cfg = get_config_v4()
    case_paths = discover_case_study_paths(Path(cfg.project_root))
    sites = discover_site_names(case_paths)

    print(f"Neo4j v4: {cfg.neo4j_uri} (database: {cfg.neo4j_database})")
    print(f"Discovered {len(case_paths)} case study files, {len(sites)} sites")
    print()

    if "7687" in cfg.neo4j_uri:
        print("WARNING: Targeting port 7687 (possible production port).")

    driver = GraphDatabase.driver(
        cfg.neo4j_uri,
        auth=(cfg.neo4j_user, cfg.neo4j_password),
    )
    driver.verify_connectivity()

    print("Populating v4 graph...")
    print("=" * 60)

    total = 0

    with driver.session(database=cfg.neo4j_database) as session:
        # Step 1: Schema
        print("Step 1: Applying schema...")
        for stmt in SCHEMA_STATEMENTS:
            try:
                session.run(stmt)
            except Exception as e:
                # Ignore index already exists errors
                if "already exists" not in str(e).lower():
                    raise
        print(f"  Schema applied.")
        print()

        # Step 2: Core pipeline (legacy)
        print("Step 2: Core population pipeline...")
        # Note: These functions take 'cfg' which is now compliant thanks to our wrapper
        total += _populate_documents(session, cfg)
        total += _populate_entities(session, cfg)
        total += _populate_bridge_axioms(session, cfg)
        total += _populate_comparison_sites(session)
        total += _populate_relationships(session, cfg)
        total += _populate_cross_domain_links(session)
        total += _populate_provenance(session, cfg)
        print()

        # Step 3: Case Studies (New Service)
        print("Step 3: Populating all case study sites (CaseStudyLoader)...")
        loader = CaseStudyLoader(session)
        for _name, path in sites:
            total += loader.load_site(path)
        print()

        # Step 4: Concepts (New Service)
        print("Step 4: Populating concept nodes (ConceptsLoader)...")
        total += _populate_concepts(session)
        print()

    # Step 5: Dynamic Registration
    print("Step 5: Registering sites...")
    site_names = [name for name, _ in sites]
    n_registered = register_dynamic_sites(site_names)
    print(f"  Registered {n_registered} dynamic sites.")
    print()

    # Summary
    print("=" * 60)
    print(f"Population complete. ~{total} operations executed.")

    if validate:
        print()
        print("Step 6: Validating graph...")
        _validate_v4(driver, cfg)

    driver.close()
    return total


def _validate_v4(driver, cfg) -> None:
    """Run basic validation checks against the v4 graph."""
    with driver.session(database=cfg.neo4j_database) as session:
        result = session.run("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count")
        print("Node counts:")
        for rec in result:
            print(f"  {rec['label']}: {rec['count']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Populate Neo4j v4 database")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be populated")
    parser.add_argument("--validate", action="store_true", help="Run validation checks after population")
    args = parser.parse_args()

    if args.dry_run:
        cfg = get_config_v4()
        paths = discover_case_study_paths(Path(cfg.project_root))
        sites = discover_site_names(paths)
        _dry_run(paths, sites)
    else:
        populate_v4(validate=args.validate)
