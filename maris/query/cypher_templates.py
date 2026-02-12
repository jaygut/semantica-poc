"""Parameterized Cypher query templates for MARIS graph queries.

All templates include a LIMIT clause to prevent unbounded result sets.
Detail queries default to 100 rows; traversal queries default to 1000.
The limit is configurable via the ``result_limit`` parameter (max 1000).
"""

# Default limits
_DETAIL_LIMIT = 100
_TRAVERSAL_LIMIT = 1000
_MAX_LIMIT = 1000

TEMPLATES: dict[str, dict] = {
    # ------------------------------------------------------------------
    # Core query templates (mapped to classifier categories)
    # ------------------------------------------------------------------
    "site_valuation": {
        "name": "site_valuation",
        "category": "site_valuation",
        "default_limit": _DETAIL_LIMIT,
        "cypher": """
            MATCH (m:MPA {name: $site_name})
            OPTIONAL MATCH (m)-[:GENERATES]->(es:EcosystemService)
            OPTIONAL MATCH (es)<-[:TRANSLATES]-(ba:BridgeAxiom)-[:EVIDENCED_BY]->(d:Document)
            RETURN m.name AS site, m.total_esv_usd AS total_esv,
                   m.biomass_ratio AS biomass_ratio, m.neoli_score AS neoli_score,
                   m.asset_rating AS asset_rating,
                   collect(DISTINCT {
                       service: es.service_name,
                       value_usd: es.annual_value_usd,
                       method: es.valuation_method,
                       ci_low: es.ci_low,
                       ci_high: es.ci_high
                   }) AS services,
                   collect(DISTINCT {
                       axiom_id: ba.axiom_id,
                       axiom_name: ba.name,
                       doi: d.doi,
                       title: d.title,
                       year: d.year,
                       tier: d.source_tier
                   }) AS evidence
            LIMIT $result_limit
        """,
        "parameters": ["site_name"],
    },
    "provenance_drilldown": {
        "name": "provenance_drilldown",
        "category": "provenance_drilldown",
        "default_limit": _DETAIL_LIMIT,
        "cypher": """
            MATCH (m:MPA {name: $site_name})
            OPTIONAL MATCH path = (m)-[*1..4]->(d:Document)
            WITH m, d, [r IN relationships(path) | type(r)] AS rel_types
            RETURN m.name AS site,
                   d.doi AS doi, d.title AS title, d.year AS year,
                   d.source_tier AS tier, d.citation AS citation,
                   rel_types AS provenance_path
            ORDER BY d.year DESC
            LIMIT $result_limit
        """,
        "parameters": ["site_name"],
    },
    "axiom_explanation": {
        "name": "axiom_explanation",
        "category": "axiom_explanation",
        "default_limit": _DETAIL_LIMIT,
        "cypher": """
            MATCH (ba:BridgeAxiom {axiom_id: $axiom_id})
            OPTIONAL MATCH (ba)-[:EVIDENCED_BY]->(d:Document)
            OPTIONAL MATCH (ba)-[:APPLIES_TO]->(m:MPA)
            OPTIONAL MATCH (ba)-[:TRANSLATES]->(es:EcosystemService)
            RETURN ba.axiom_id AS axiom_id, ba.name AS axiom_name,
                   ba.category AS category, ba.description AS description,
                   ba.coefficients_json AS coefficients,
                   collect(DISTINCT {doi: d.doi, title: d.title, year: d.year, tier: d.source_tier}) AS evidence,
                   collect(DISTINCT m.name) AS applicable_sites,
                   collect(DISTINCT es.service_name) AS translated_services
            LIMIT $result_limit
        """,
        "parameters": ["axiom_id"],
    },
    "comparison": {
        "name": "comparison",
        "category": "comparison",
        "default_limit": _DETAIL_LIMIT,
        "cypher": """
            MATCH (m:MPA)
            WHERE m.name IN $site_names
            OPTIONAL MATCH (m)-[:GENERATES]->(es:EcosystemService)
            RETURN m.name AS site, m.total_esv_usd AS total_esv,
                   m.biomass_ratio AS biomass_ratio, m.neoli_score AS neoli_score,
                   m.asset_rating AS asset_rating,
                   collect({service: es.service_name, value_usd: es.annual_value_usd}) AS services
            ORDER BY m.total_esv_usd DESC
            LIMIT $result_limit
        """,
        "parameters": ["site_names"],
    },
    "risk_assessment": {
        "name": "risk_assessment",
        "category": "risk_assessment",
        "default_limit": _DETAIL_LIMIT,
        "cypher": """
            MATCH (m:MPA {name: $site_name})
            OPTIONAL MATCH (m)-[:GENERATES]->(es:EcosystemService)
            OPTIONAL MATCH (ba:BridgeAxiom)-[:APPLIES_TO]->(m)
            WHERE ba.category IN ['ecological_to_service', 'ecological_to_ecological']
            OPTIONAL MATCH (ba)-[:EVIDENCED_BY]->(d:Document)
            RETURN m.name AS site, m.total_esv_usd AS total_esv,
                   m.biomass_ratio AS biomass_ratio,
                   collect(DISTINCT {
                       service: es.service_name,
                       value_usd: es.annual_value_usd,
                       ci_low: es.ci_low,
                       ci_high: es.ci_high
                   }) AS services,
                   collect(DISTINCT {
                       axiom_id: ba.axiom_id,
                       axiom_name: ba.name,
                       coefficients: ba.coefficients_json,
                       doi: d.doi,
                       title: d.title
                   }) AS risk_axioms
            LIMIT $result_limit
        """,
        "parameters": ["site_name"],
    },

    # ------------------------------------------------------------------
    # Utility templates
    # ------------------------------------------------------------------
    "node_detail": {
        "name": "node_detail",
        "category": "utility",
        "default_limit": _DETAIL_LIMIT,
        "cypher": """
            MATCH (n)
            WHERE elementId(n) = $node_id
            OPTIONAL MATCH (n)-[r]-(m)
            RETURN labels(n) AS labels, properties(n) AS props,
                   collect({type: type(r), direction: CASE WHEN startNode(r) = n THEN 'out' ELSE 'in' END,
                            neighbor_labels: labels(m), neighbor_name: m.name}) AS relationships
            LIMIT $result_limit
        """,
        "parameters": ["node_id"],
    },
    "graph_traverse": {
        "name": "graph_traverse",
        "category": "utility",
        "default_limit": _TRAVERSAL_LIMIT,
        # NOTE: max_hops is substituted via str.replace in executor (Neo4j
        # does not allow parameters in variable-length path bounds).
        "cypher": """
            MATCH (start)
            WHERE start.name = $start_name
            MATCH path = (start)-[*1..MAX_HOPS_PLACEHOLDER]-(end)
            WHERE NOT end:Document
            WITH path, end, [n IN nodes(path) | {labels: labels(n), name: n.name}] AS node_list,
                 [r IN relationships(path) | type(r)] AS rel_list
            RETURN node_list, rel_list
            LIMIT $result_limit
        """,
        "parameters": ["start_name", "max_hops", "result_limit"],
    },
    "graph_stats": {
        "name": "graph_stats",
        "category": "utility",
        "default_limit": _DETAIL_LIMIT,
        "cypher": """
            CALL {
                MATCH (n) RETURN count(n) AS total_nodes
            }
            CALL {
                MATCH ()-[r]->() RETURN count(r) AS total_edges
            }
            CALL {
                MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt
                ORDER BY cnt DESC
            }
            RETURN total_nodes, total_edges, collect({label: label, count: cnt}) AS node_breakdown
            LIMIT $result_limit
        """,
        "parameters": [],
    },
}


def get_template(name: str) -> dict | None:
    """Return a Cypher template by name, or None if not found."""
    return TEMPLATES.get(name)


def templates_for_category(category: str) -> list[dict]:
    """Return all templates matching a query category."""
    return [t for t in TEMPLATES.values() if t["category"] == category]
