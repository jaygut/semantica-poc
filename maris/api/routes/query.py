"""Query endpoint - full NL-to-answer pipeline."""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException

from maris.api.auth import rate_limit_query
from maris.api.models import QueryRequest, QueryResponse, QueryMetadata, EvidenceItem
from maris.config import get_config
from maris.llm.adapter import LLMAdapter
from maris.query.classifier import QueryClassifier
from maris.query.executor import QueryExecutor
from maris.query.generator import ResponseGenerator
from maris.query.formatter import format_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])

# Lazy singletons initialised on first request
_llm: LLMAdapter | None = None
_classifier: QueryClassifier | None = None
_executor: QueryExecutor | None = None
_generator: ResponseGenerator | None = None


def _init_components():
    global _llm, _classifier, _executor, _generator
    if _llm is None:
        _llm = LLMAdapter(get_config())
        _classifier = QueryClassifier(llm=_llm)
        _executor = QueryExecutor()
        _generator = ResponseGenerator(llm=_llm)


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(rate_limit_query)])
def query(request: QueryRequest):
    """Classify a natural-language question, run Cypher, and return a grounded answer."""
    _init_components()
    assert _classifier and _executor and _generator  # narrowing for type checker

    start = time.monotonic()

    # 1. Classify
    classification = _classifier.classify(request.question)
    category = classification["category"]
    site = request.site or classification.get("site")

    # 2. Build parameters for the Cypher template
    params: dict = {}
    if category in ("site_valuation", "provenance_drilldown", "risk_assessment"):
        if not site:
            raise HTTPException(status_code=400, detail="Site name required for this query type. Provide 'site' or mention a site in your question.")
        params["site_name"] = site
    elif category == "axiom_explanation":
        # Try to extract axiom ID from question
        import re
        m = re.search(r"BA-\d{3}", request.question)
        if m:
            params["axiom_id"] = m.group(0)
        else:
            # No axiom ID found - fall back to provenance_drilldown with site context
            category = "provenance_drilldown"
            if not site:
                site = "Cabo Pulmo National Park"
            params["site_name"] = site
    elif category == "comparison":
        if site:
            params["site_names"] = [site]
        else:
            params["site_names"] = ["Cabo Pulmo National Park"]

    # 3. Execute Cypher
    graph_result = _executor.execute(category, params)
    if graph_result.get("error"):
        raise HTTPException(status_code=500, detail=graph_result["error"])

    # 4. Generate response via LLM
    raw = _generator.generate(
        question=request.question,
        graph_context=graph_result,
        category=category,
    )

    # 5. Format
    formatted = format_response(raw)

    # 6. Build structured graph_path from actual Neo4j traversal (not LLM text)
    graph_path = []
    if request.include_graph_path:
        graph_path = _executor.get_provenance_edges(category, params)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    evidence = [EvidenceItem(**e) for e in formatted["evidence"][:request.max_evidence_sources]]

    return QueryResponse(
        answer=formatted["answer"],
        confidence=formatted["confidence"],
        evidence=evidence,
        axioms_used=formatted["axioms_used"],
        graph_path=graph_path,
        caveats=formatted["caveats"],
        verified_claims=formatted.get("verified_claims", []),
        unverified_claims=formatted.get("unverified_claims", []),
        confidence_breakdown=formatted.get("confidence_breakdown"),
        query_metadata=QueryMetadata(
            category=category,
            classification_confidence=classification.get("confidence", 0.0),
            template_used=category,
            response_time_ms=elapsed_ms,
        ),
    )
