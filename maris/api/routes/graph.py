"""Graph exploration and structured data endpoints."""

import json
import logging

from fastapi import APIRouter, HTTPException

from maris.api.models import (
    AxiomResponse,
    CompareRequest,
    CompareResponse,
    EvidenceItem,
    SiteResponse,
    TraverseRequest,
)
from maris.query.executor import QueryExecutor
from maris.axioms.engine import BridgeAxiomEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["graph"])

_executor: QueryExecutor | None = None
_axiom_engine: BridgeAxiomEngine | None = None


def _init():
    global _executor, _axiom_engine
    if _executor is None:
        _executor = QueryExecutor()
        _axiom_engine = BridgeAxiomEngine()


@router.get("/graph/node/{node_id}")
def get_node(node_id: str):
    """Retrieve a single node with its relationships by element ID."""
    _init()
    assert _executor

    result = _executor.execute("node_detail", {"node_id": node_id})
    if not result["results"]:
        raise HTTPException(status_code=404, detail="Node not found")
    return result["results"][0]


@router.post("/graph/traverse")
def traverse(request: TraverseRequest):
    """Multi-hop graph traversal from a named node."""
    _init()
    assert _executor

    result = _executor.execute("graph_traverse", {
        "start_name": request.start_name,
        "max_hops": request.max_hops,
        "result_limit": request.result_limit,
    })
    return {"paths": result["results"], "count": result["record_count"]}


@router.get("/axiom/{axiom_id}", response_model=AxiomResponse)
def get_axiom(axiom_id: str):
    """Return bridge axiom details from the template file and graph evidence."""
    _init()
    assert _executor and _axiom_engine

    # Get template data
    template = _axiom_engine.get_axiom(axiom_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Axiom {axiom_id} not found")

    # Get graph evidence
    graph_result = _executor.execute("axiom_explanation", {"axiom_id": axiom_id})
    graph_data = graph_result["results"][0] if graph_result["results"] else {}

    evidence = []
    for src in template.get("sources", []):
        evidence.append(EvidenceItem(
            doi=src.get("doi"),
            doi_url=f"https://doi.org/{src['doi']}" if src.get("doi") else None,
            title=src.get("citation", ""),
            quote=src.get("finding", ""),
        ))

    coefficients = template.get("coefficients", {})

    return AxiomResponse(
        axiom_id=axiom_id,
        name=template.get("name", ""),
        category=template.get("category", ""),
        description=template.get("description", ""),
        coefficients=coefficients,
        evidence=evidence,
        applicable_sites=graph_data.get("applicable_sites", []),
        translated_services=graph_data.get("translated_services", []),
    )


@router.get("/site/{site_name}", response_model=SiteResponse)
def get_site(site_name: str):
    """Return full site valuation with provenance."""
    _init()
    assert _executor

    result = _executor.execute("site_valuation", {"site_name": site_name})
    if not result["results"]:
        raise HTTPException(status_code=404, detail=f"Site '{site_name}' not found")

    row = result["results"][0]

    evidence = []
    for e in row.get("evidence", []):
        if e.get("doi"):
            evidence.append(EvidenceItem(
                doi=e["doi"],
                doi_url=f"https://doi.org/{e['doi']}",
                title=e.get("title", ""),
                year=e.get("year"),
                tier=e.get("tier", ""),
            ))

    return SiteResponse(
        site=row.get("site", site_name),
        total_esv_usd=row.get("total_esv"),
        biomass_ratio=row.get("biomass_ratio"),
        neoli_score=row.get("neoli_score"),
        asset_rating=row.get("asset_rating"),
        services=row.get("services", []),
        evidence=evidence,
    )


@router.post("/compare", response_model=CompareResponse)
def compare_sites(request: CompareRequest):
    """Compare multiple sites on NEOLI, ESV, and biomass."""
    _init()
    assert _executor

    result = _executor.execute("comparison", {"site_names": request.site_names})
    return CompareResponse(sites=result["results"])
