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
            OPTIONAL MATCH (m)-[:HAS_ECOLOGICAL_PROCESS]->(p:EcologicalProcess)
            OPTIONAL MATCH (m)-[:USING_MECHANISM]->(fm:FinancialMechanism)
            OPTIONAL MATCH (m)-[rel:FACES_RISK]->(r:Risk)
            RETURN m.name AS site, m.total_esv_usd AS total_esv,
                   m.biomass_ratio AS biomass_ratio, m.neoli_score AS neoli_score,
                   m.asset_rating AS asset_rating,
                   collect(DISTINCT {
                       service: es.service_name,
                       value_usd: es.annual_value_usd,
                       method: es.valuation_method,
                       ci_low: properties(es)['ci_low'],
                       ci_high: properties(es)['ci_high']
                   }) AS services,
                   collect(DISTINCT {
                       name: fm.name,
                       type: fm.type,
                       amount_usd: fm.amount_usd,
                       description: fm.description
                   }) AS financial_mechanisms,
                   collect(DISTINCT {
                       process: p.name,
                       description: p.description,
                       effect: p.effect,
                       chain: p.chain
                   }) AS ecological_processes,
                   collect(DISTINCT {
                       risk: r.name,
                       severity: rel.severity,
                       likelihood: rel.likelihood,
                       evidence: rel.evidence
                   }) AS risks,
                   collect(DISTINCT {
                       axiom_id: ba.axiom_id,
                       axiom_name: ba.name,
                       doi: d.doi,
                       title: d.title,
                       year: d.year,
                       tier: d.source_tier
                   }) AS evidence
            LIMIT $result_limit        """,
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
                   d.source_tier AS tier, properties(d)['citation'] AS citation,
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
    "axiom_by_concept": {
        "name": "axiom_by_concept",
        "category": "axiom_explanation",
        "default_limit": _DETAIL_LIMIT,
        "cypher": """
            MATCH (ba:BridgeAxiom)
            WHERE ba.name CONTAINS $concept_term
               OR ba.description CONTAINS $concept_term
               OR ba.axiom_id IN $axiom_ids
            OPTIONAL MATCH (ba)-[:EVIDENCED_BY]->(d:Document)
            OPTIONAL MATCH (ba)-[:APPLIES_TO]->(m:MPA)
            OPTIONAL MATCH (ba)-[:TRANSLATES]->(es:EcosystemService)
            OPTIONAL MATCH (ba)-[:APPLIES_TO_HABITAT]->(h:Habitat)
            RETURN ba.axiom_id AS axiom_id, ba.name AS axiom_name,
                   ba.description AS description, ba.coefficient AS coefficient,
                   ba.category AS category,
                   collect(DISTINCT {doi: d.doi, title: d.title, year: d.year, tier: d.source_tier}) AS evidence,
                   collect(DISTINCT m.name) AS applicable_sites,
                   collect(DISTINCT es.service_name) AS services,
                   collect(DISTINCT h.habitat_id) AS habitats
            LIMIT $result_limit
        """,
        "parameters": ["concept_term", "axiom_ids"],
    },
    "comparison": {
        "name": "comparison",
        "category": "comparison",
        "default_limit": _DETAIL_LIMIT,
        "cypher": """
            MATCH (m:MPA)
            WHERE m.name IN $site_names
            OPTIONAL MATCH (m)-[:GENERATES]->(es:EcosystemService)
            OPTIONAL MATCH (es)<-[:TRANSLATES]-(ba:BridgeAxiom)-[:EVIDENCED_BY]->(d:Document)
            RETURN m.name AS site, m.total_esv_usd AS total_esv,
                   m.biomass_ratio AS biomass_ratio, m.neoli_score AS neoli_score,
                   m.asset_rating AS asset_rating,
                   collect(DISTINCT {service: es.service_name, value_usd: es.annual_value_usd}) AS services,
                   collect(DISTINCT {doi: d.doi, title: d.title, year: d.year, tier: d.source_tier}) AS evidence
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
            OPTIONAL MATCH (m)-[:FACES_RISK]->(r:Risk)
            OPTIONAL MATCH (ba:BridgeAxiom)-[:APPLIES_TO]->(m)
            WHERE ba.category IN ['ecological_to_service', 'ecological_to_ecological']
            OPTIONAL MATCH (ba)-[:EVIDENCED_BY]->(d:Document)
            RETURN m.name AS site, m.total_esv_usd AS total_esv,
                   m.biomass_ratio AS biomass_ratio,
                   collect(DISTINCT {
                       service: es.service_name,
                       value_usd: es.annual_value_usd,
                       ci_low: properties(es)['ci_low'],
                       ci_high: properties(es)['ci_high']
                   }) AS services,
                   collect(DISTINCT {
                       risk: r.name,
                       severity: r.severity,
                       likelihood: r.likelihood,
                       evidence: r.evidence
                   }) AS risks,
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
    # Concept-aware query templates (Phase II)
    # ------------------------------------------------------------------
    "mechanism_chain": {
        "name": "mechanism_chain",
        "category": "concept_explanation",
        "default_limit": _DETAIL_LIMIT,
        "cypher": """
            MATCH (c:Concept {concept_id: $concept_id})
            MATCH (c)-[:INVOLVES_AXIOM]->(ba:BridgeAxiom)
            OPTIONAL MATCH (ba)-[:EVIDENCED_BY]->(d:Document)
            OPTIONAL MATCH (ba)-[:TRANSLATES]->(es:EcosystemService)
            OPTIONAL MATCH (ba)-[:APPLIES_TO_HABITAT]->(h:Habitat)
            WITH ba, collect(DISTINCT d) AS docs, collect(DISTINCT es) AS services,
                 collect(DISTINCT h.habitat_id) AS habitats
            ORDER BY ba.axiom_id
            RETURN ba.axiom_id AS axiom_id, ba.name AS name,
                   ba.description AS description, ba.category AS category,
                   ba.coefficient AS coefficient,
                   [d IN docs | {doi: d.doi, title: d.title, tier: d.source_tier}] AS evidence,
                   [s IN services | s.service_name] AS services,
                   habitats
            LIMIT $result_limit
        """,
        "parameters": ["concept_id"],
    },
    "concept_overview": {
        "name": "concept_overview",
        "category": "concept_explanation",
        "default_limit": _DETAIL_LIMIT,
        "cypher": """
            MATCH (c:Concept)
            WHERE c.name CONTAINS $search_term OR c.concept_id = $concept_id
            OPTIONAL MATCH (c)-[:INVOLVES_AXIOM]->(ba:BridgeAxiom)
            OPTIONAL MATCH (c)-[:DOCUMENTED_BY]->(d:Document)
            OPTIONAL MATCH (c)-[:RELEVANT_TO]->(h:Habitat)
            RETURN c.concept_id AS concept_id, c.name AS name,
                   c.description AS description, c.domain AS domain,
                   collect(DISTINCT ba.axiom_id) AS axiom_ids,
                   collect(DISTINCT {doi: d.doi, title: d.title}) AS key_papers,
                   collect(DISTINCT h.habitat_id) AS habitats
            LIMIT $result_limit
        """,
        "parameters": ["search_term", "concept_id"],
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

    # ------------------------------------------------------------------
    # Open-domain retrieval templates (P2)
    # ------------------------------------------------------------------
    "graph_neighborhood": {
        "name": "graph_neighborhood",
        "category": "open_domain",
        "default_limit": _TRAVERSAL_LIMIT,
        "cypher": """
            MATCH (start)
            WHERE start.name = $start_name
            MATCH path = (start)-[*1..MAX_HOPS_PLACEHOLDER]-(neighbor)
            WITH start, neighbor, path,
                 [n IN nodes(path) | {labels: labels(n), name: n.name, props: properties(n)}] AS node_list,
                 [r IN relationships(path) | {type: type(r), start: startNode(r).name, end: endNode(r).name}] AS rel_list
            RETURN start.name AS start_node,
                   neighbor.name AS neighbor_name,
                   labels(neighbor)[0] AS neighbor_label,
                   properties(neighbor) AS neighbor_props,
                   node_list, rel_list
            LIMIT $result_limit
        """,
        "parameters": ["start_name", "max_hops", "result_limit"],
    },
    "semantic_search": {
        "name": "semantic_search",
        "category": "open_domain",
        "default_limit": _DETAIL_LIMIT,
        "cypher": """
            MATCH (n)
            WHERE n.name CONTAINS $search_term
               OR n.description CONTAINS $search_term
               OR n.service_name CONTAINS $search_term
               OR n.axiom_id CONTAINS $search_term
            RETURN labels(n)[0] AS label, n.name AS name,
                   properties(n) AS props
            LIMIT $result_limit
        """,
        "parameters": ["search_term"],
    },
}


def get_template(name: str) -> dict | None:
    """Return a Cypher template by name, or None if not found."""
    return TEMPLATES.get(name)


def templates_for_category(category: str) -> list[dict]:
    """Return all templates matching a query category."""
    return [t for t in TEMPLATES.values() if t["category"] == category]
