"""Execute Cypher queries against Neo4j."""

import logging

from maris.graph.connection import run_query
from maris.query.cypher_templates import get_template

logger = logging.getLogger(__name__)


class QueryExecutor:
    """Run parameterized Cypher templates or raw queries against Neo4j."""

    def execute(self, template_name: str, parameters: dict) -> dict:
        """Execute a named Cypher template with parameters.

        Returns dict with keys: template, parameters, results, record_count.
        """
        template = get_template(template_name)
        if template is None:
            return {"error": f"Unknown template: {template_name}", "results": []}

        cypher = template["cypher"]

        # Neo4j does not allow parameters in variable-length path bounds,
        # so we substitute max_hops directly (already validated by Pydantic).
        if "MAX_HOPS_PLACEHOLDER" in cypher and "max_hops" in parameters:
            hops = int(parameters.pop("max_hops"))
            cypher = cypher.replace("MAX_HOPS_PLACEHOLDER", str(hops))

        try:
            records = run_query(cypher, parameters)
            return {
                "template": template_name,
                "parameters": parameters,
                "results": records,
                "record_count": len(records),
            }
        except Exception:
            logger.exception("Cypher execution failed for template=%s", template_name)
            return {"template": template_name, "error": "Query execution failed", "results": []}

    def execute_raw(self, cypher: str, parameters: dict | None = None) -> list[dict]:
        """Execute arbitrary Cypher and return result dicts."""
        try:
            return run_query(cypher, parameters)
        except Exception:
            logger.exception("Raw Cypher execution failed")
            return []

    def get_provenance_edges(self, category: str, params: dict) -> list[dict]:
        """Return structured provenance edges for the graph explorer visualization.

        Each edge is a dict with from_node, from_type, relationship, to_node, to_type.
        """
        site_name = params.get("site_name")
        axiom_id = params.get("axiom_id")

        if category in ("site_valuation", "provenance_drilldown", "risk_assessment") and site_name:
            return self._site_provenance(site_name)
        elif category == "axiom_explanation" and axiom_id:
            return self._axiom_provenance(axiom_id)
        elif category == "comparison":
            edges = []
            for name in params.get("site_names", []):
                edges.extend(self._site_provenance(name))
            return edges
        return []

    def _site_provenance(self, site_name: str) -> list[dict]:
        """Get provenance chain edges for a site."""
        cypher = """
            // MPA -> EcosystemService
            MATCH (m:MPA {name: $site_name})-[:GENERATES]->(es:EcosystemService)
            RETURN m.name AS from_node, labels(m)[0] AS from_type,
                   'GENERATES' AS relationship,
                   es.service_name AS to_node, labels(es)[0] AS to_type
            UNION ALL
            // BridgeAxiom -> MPA
            MATCH (ba:BridgeAxiom)-[:APPLIES_TO]->(m:MPA {name: $site_name})
            RETURN ba.axiom_id AS from_node, 'BridgeAxiom' AS from_type,
                   'APPLIES_TO' AS relationship,
                   m.name AS to_node, 'MPA' AS to_type
            UNION ALL
            // BridgeAxiom -> EcosystemService (for axioms that apply to this site)
            MATCH (ba:BridgeAxiom)-[:APPLIES_TO]->(:MPA {name: $site_name})
            MATCH (ba)-[:TRANSLATES]->(es:EcosystemService)
            RETURN ba.axiom_id AS from_node, 'BridgeAxiom' AS from_type,
                   'TRANSLATES' AS relationship,
                   es.service_name AS to_node, 'EcosystemService' AS to_type
            UNION ALL
            // BridgeAxiom -> Document (for axioms that apply to this site)
            MATCH (ba:BridgeAxiom)-[:APPLIES_TO]->(:MPA {name: $site_name})
            MATCH (ba)-[:EVIDENCED_BY]->(d:Document)
            RETURN ba.axiom_id AS from_node, 'BridgeAxiom' AS from_type,
                   'EVIDENCED_BY' AS relationship,
                   COALESCE(d.title, d.doi) AS to_node, 'Document' AS to_type
            UNION ALL
            // MPA -> Habitat
            MATCH (m:MPA {name: $site_name})-[:HAS_HABITAT]->(h:Habitat)
            RETURN m.name AS from_node, 'MPA' AS from_type,
                   'HAS_HABITAT' AS relationship,
                   h.name AS to_node, 'Habitat' AS to_type
        """
        try:
            return run_query(cypher, {"site_name": site_name})
        except Exception:
            logger.exception("Provenance edge query failed for site=%s", site_name)
            return []

    def _axiom_provenance(self, axiom_id: str) -> list[dict]:
        """Get provenance chain edges for an axiom."""
        cypher = """
            // Axiom -> MPA
            MATCH (ba:BridgeAxiom {axiom_id: $axiom_id})-[:APPLIES_TO]->(m:MPA)
            RETURN ba.axiom_id AS from_node, 'BridgeAxiom' AS from_type,
                   'APPLIES_TO' AS relationship,
                   m.name AS to_node, 'MPA' AS to_type
            UNION ALL
            // Axiom -> EcosystemService
            MATCH (ba:BridgeAxiom {axiom_id: $axiom_id})-[:TRANSLATES]->(es:EcosystemService)
            RETURN ba.axiom_id AS from_node, 'BridgeAxiom' AS from_type,
                   'TRANSLATES' AS relationship,
                   es.service_name AS to_node, 'EcosystemService' AS to_type
            UNION ALL
            // Axiom -> Document
            MATCH (ba:BridgeAxiom {axiom_id: $axiom_id})-[:EVIDENCED_BY]->(d:Document)
            RETURN ba.axiom_id AS from_node, 'BridgeAxiom' AS from_type,
                   'EVIDENCED_BY' AS relationship,
                   COALESCE(d.title, d.doi) AS to_node, 'Document' AS to_type
        """
        try:
            return run_query(cypher, {"axiom_id": axiom_id})
        except Exception:
            logger.exception("Provenance edge query failed for axiom=%s", axiom_id)
            return []
