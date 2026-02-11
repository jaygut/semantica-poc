"""Graph validation queries - verify population integrity."""

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
}


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

    if verbose:
        print("\n" + "=" * 60)
        print("VALIDATION CHECKS:")
        for check, passed in checks.items():
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {check}")
            if not passed:
                all_pass = False
        print("=" * 60)
        print(f"Overall: {'ALL CHECKS PASSED' if all_pass else 'SOME CHECKS FAILED'}")

    return {"checks": checks, "results": results, "all_pass": all_pass}
