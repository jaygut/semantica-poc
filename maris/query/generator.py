"""Graph-constrained response generation using LLM."""

import json
import logging

from maris.llm.adapter import LLMAdapter
from maris.llm.prompts import RESPONSE_SYNTHESIS_PROMPT
from maris.query.validators import (
    empty_result_response,
    is_graph_context_empty,
    validate_llm_response,
)

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generate provenance-grounded answers from graph query results."""

    def __init__(self, llm: LLMAdapter):
        self._llm = llm

    def generate(self, question: str, graph_context: dict, category: str) -> dict:
        """Synthesize a response from graph results.

        Returns dict with keys: answer, confidence, evidence, axioms_used,
        graph_path, caveats, verified_claims, unverified_claims.
        """
        # Empty result protection: do not call LLM if graph has no data
        if is_graph_context_empty(graph_context):
            logger.info("Empty graph context for question: %s", question[:80])
            return empty_result_response()

        context_str = json.dumps(graph_context, indent=2, default=str)

        prompt = RESPONSE_SYNTHESIS_PROMPT.format(
            question=question,
            category=category,
            graph_context=context_str,
        )

        result = self._llm.complete_json([{"role": "user", "content": prompt}])

        # Normalise into expected shape
        raw = {
            "answer": result.get("answer", result.get("raw", "")),
            "confidence": result.get("confidence", 0.0),
            "evidence": result.get("evidence", []),
            "axioms_used": result.get("axioms_used", []),
            "graph_path": result.get("graph_path", []),
            "caveats": result.get("caveats", []),
        }

        # Validate response against graph context
        validated = validate_llm_response(raw, graph_context)

        # Preserve axioms_used and graph_path through validation
        validated.setdefault("axioms_used", raw["axioms_used"])
        validated.setdefault("graph_path", raw["graph_path"])

        return validated
