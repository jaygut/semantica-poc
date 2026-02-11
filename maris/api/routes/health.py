"""Health check endpoint."""

import logging

from fastapi import APIRouter

from maris.api.models import HealthResponse
from maris.config import get_config
from maris.graph.connection import run_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health():
    """Check Neo4j connectivity, LLM availability, and return graph stats."""
    status = "healthy"
    neo4j_ok = False
    llm_ok = False
    graph_stats: dict = {}

    # Neo4j check
    try:
        rows = run_query("RETURN 1 AS ok")
        neo4j_ok = bool(rows)
    except Exception:
        logger.warning("Neo4j health check failed")
        status = "degraded"

    # Graph stats (only if Neo4j is up)
    if neo4j_ok:
        try:
            node_rows = run_query("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC")
            edge_rows = run_query("MATCH ()-[r]->() RETURN count(r) AS total")
            graph_stats = {
                "total_nodes": sum(r["cnt"] for r in node_rows),
                "total_edges": edge_rows[0]["total"] if edge_rows else 0,
                "node_breakdown": {r["label"]: r["cnt"] for r in node_rows},
            }
        except Exception:
            logger.warning("Graph stats query failed")

    # LLM check (lightweight - just verify the client can be created)
    try:
        config = get_config()
        llm_ok = bool(config.llm_api_key or config.llm_provider == "ollama")
    except Exception:
        logger.warning("LLM availability check failed")

    if not neo4j_ok:
        status = "degraded"
    if not neo4j_ok and not llm_ok:
        status = "offline"

    return HealthResponse(
        status=status,
        neo4j_connected=neo4j_ok,
        llm_available=llm_ok,
        graph_stats=graph_stats,
    )
