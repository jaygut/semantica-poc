"""Graph validation queries - verify population integrity."""

from datetime import datetime

from maris.graph.connection import get_driver, get_config

VALIDATION_QUERIES = {
    "node_counts": {
        "cypher": "MATCH (n) RETURN labels(n)[0] AS type, count(n) AS count ORDER BY count DESC",
        "description": "Node counts by label",
    },
    "edge_counts": {
        "cypher": "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY count DESC",
        "description": "Edge counts by type",
    },
    "cabo_pulmo_provenance": {
        "cypher": """
            MATCH (m:MPA {name: "Cabo Pulmo National Park"})
            OPTIONAL MATCH path = (m)-[*1..4]->(d:Document)
            WITH m, count(DISTINCT d) AS doc_count
            RETURN m.name AS site, doc_count
        """,
        "description": "Cabo Pulmo provenance chain completeness",
    },
    "axiom_evidence": {
        "cypher": """
            MATCH (a:BridgeAxiom)-[:EVIDENCED_BY]->(d:Document)
            RETURN a.axiom_id AS axiom, count(d) AS evidence_sources
            ORDER BY a.axiom_id
        """,
        "description": "Bridge axiom evidence coverage",
    },
    "orphan_nodes": {
        "cypher": "MATCH (n) WHERE NOT (n)--() RETURN labels(n)[0] AS type, count(n) AS orphan_count",
        "description": "Orphan nodes (no relationships)",
    },
    "esv_trace": {
        "cypher": """
            MATCH (m:MPA {name: "Cabo Pulmo National Park"})-[:GENERATES]->(es:EcosystemService)
            RETURN es.service_name AS service, es.annual_value_usd AS value_usd
            ORDER BY es.annual_value_usd DESC
        """,
        "description": "ESV trace from Cabo Pulmo to services",
    },
    "total_esv": {
        "cypher": """
            MATCH (m:MPA {name: "Cabo Pulmo National Park"})-[:GENERATES]->(es:EcosystemService)
            RETURN sum(es.annual_value_usd) AS total_esv_usd
        """,
        "description": "Total ESV for Cabo Pulmo",
    },
    "data_freshness": {
        "cypher": """
            MATCH (m:MPA)
            RETURN m.name AS site,
                   m.biomass_measurement_year AS measurement_year,
                   m.data_freshness_status AS freshness_status,
                   m.last_validated_date AS last_validated
            ORDER BY m.name
        """,
        "description": "MPA data freshness status",
    },
    "obis_enrichment": {
        "cypher": """
            MATCH (m:MPA)
            WHERE m.characterization_tier = 'gold'
            RETURN
                count(m) AS total_gold,
                count(m.obis_species_richness) AS with_obis_data
        """,
        "description": "OBIS enrichment coverage for gold-tier MPAs",
    },
}


def _check_data_age(results: dict, current_year: int | None = None) -> dict:
    """Check data age for all MPA nodes. Returns warnings and errors."""
    if current_year is None:
        current_year = datetime.now().year

    warnings = []
    errors = []

    freshness_records = results.get("data_freshness", [])
    for rec in freshness_records:
        site = rec.get("site", "Unknown")
        meas_year = rec.get("measurement_year")

        if meas_year is None:
            warnings.append(f"{site}: no measurement_year recorded")
            continue

        age = current_year - meas_year
        if age > 10:
            errors.append(
                f"{site}: biomass data is {age} years old (from {meas_year}) - "
                f"exceeds 10-year threshold. Update required."
            )
        elif age > 5:
            warnings.append(
                f"{site}: biomass data is {age} years old (from {meas_year}) - "
                f"exceeds 5-year freshness threshold."
            )

    return {"warnings": warnings, "errors": errors}


def validate_graph(verbose: bool = True) -> dict:
    """Run all validation queries and return results dict."""
    driver = get_driver()
    cfg = get_config()
    results = {}
    all_pass = True

    with driver.session(database=cfg.neo4j_database) as session:
        for name, q in VALIDATION_QUERIES.items():
            records = [r.data() for r in session.run(q["cypher"])]
            results[name] = records
            if verbose:
                print(f"\n--- {q['description']} ---")
                for rec in records:
                    print(f"  {rec}")

    # Basic assertions
    node_counts = {r["type"]: r["count"] for r in results.get("node_counts", [])}
    checks = {
        "has_documents": node_counts.get("Document", 0) > 0,
        "has_mpas": node_counts.get("MPA", 0) > 0,
        "has_axioms": node_counts.get("BridgeAxiom", 0) >= 12,
        "has_species": node_counts.get("Species", 0) > 0,
        "has_services": node_counts.get("EcosystemService", 0) > 0,
        "cabo_pulmo_has_docs": any(
            r.get("doc_count", 0) > 0 for r in results.get("cabo_pulmo_provenance", [])
        ),
        "all_axioms_have_evidence": all(
            r.get("evidence_sources", 0) >= 1 for r in results.get("axiom_evidence", [])
        ),
    }

    # Check total ESV is in acceptable range
    esv_records = results.get("total_esv", [])
    if esv_records:
        total = esv_records[0].get("total_esv_usd", 0) or 0
        checks["esv_in_range"] = 21_000_000 <= total <= 39_000_000

    # Data age checks
    age_results = _check_data_age(results)
    checks["no_data_age_errors"] = len(age_results["errors"]) == 0

    if verbose:
        print("\n" + "=" * 60)
        print("VALIDATION CHECKS:")
        for check, passed in checks.items():
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {check}")
            if not passed:
                all_pass = False

        # Print data age warnings and errors
        if age_results["warnings"]:
            print("\nDATA AGE WARNINGS:")
            for w in age_results["warnings"]:
                print(f"  [WARN] {w}")
        if age_results["errors"]:
            print("\nDATA AGE ERRORS:")
            for e in age_results["errors"]:
                print(f"  [ERROR] {e}")

        # OBIS enrichment info
        obis_records = results.get("obis_enrichment", [{}])
        if obis_records:
            total_gold = obis_records[0].get("total_gold", 0)
            with_obis = obis_records[0].get("with_obis_data", 0)
            if with_obis == 0 and total_gold > 0:
                print(
                    f"\nOBIS ENRICHMENT WARNING:"
                    f"\n  [WARN] No gold-tier MPAs have OBIS data "
                    f"({total_gold} gold sites). Run: python scripts/enrich_obis.py"
                )
            else:
                print(
                    f"\nOBIS ENRICHMENT:"
                    f"\n  [INFO] {with_obis}/{total_gold} gold-tier MPAs enriched with OBIS data"
                )

        print("=" * 60)
        print(f"Overall: {'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")

    return {
        "checks": checks,
        "results": results,
        "all_pass": all_pass,
        "data_age": age_results,
    }
