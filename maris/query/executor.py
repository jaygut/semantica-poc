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
