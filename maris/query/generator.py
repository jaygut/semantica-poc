"""Graph-constrained response generation using LLM."""

import json
import logging
import re

from maris.axioms.confidence import calculate_response_confidence
from maris.llm.adapter import LLMAdapter
from maris.llm.prompts import RESPONSE_SYNTHESIS_PROMPT
from maris.query.validators import (
    build_provenance_summary,
    empty_result_response,
    extract_numerical_claims,
    is_graph_context_empty,
    validate_llm_response,
)

# Matches real DOIs: 10.NNNN/anything  (NNNN = 4+ digits)
_REAL_DOI_RE = re.compile(r"^10\.\d{4,}/\S+")


def _has_real_doi(item: dict) -> bool:
    """Return True only if the evidence item contains a properly formatted DOI."""
    doi = str(item.get("doi") or "").strip()
    return bool(_REAL_DOI_RE.match(doi))

logger = logging.getLogger(__name__)

# Map query category to inference hop count for confidence scoring
_CATEGORY_HOPS = {
    "site_valuation": 1,
    "provenance_drilldown": 2,
    "axiom_explanation": 2,
    "concept_explanation": 2,
    "comparison": 1,
    "risk_assessment": 3,
    "open_domain": 3,
}


class ResponseGenerator:
    """Generate provenance-grounded answers from graph query results."""

    def __init__(self, llm: LLMAdapter):
        self._llm = llm

    def generate(
        self,
        question: str,
        graph_context: dict,
        category: str,
        explanation_chain: str | None = None,
    ) -> dict:
        """Synthesize a response from graph results.

        Returns dict with keys: answer, confidence, evidence, axioms_used,
        graph_path, caveats, verified_claims, unverified_claims.

        If explanation_chain is provided (from inference engine), it is
        appended to the LLM prompt to ground the response in the reasoning.
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

        # Append inference explanation if available
        if explanation_chain:
            prompt += (
                "\n\nInference chain (use this to structure your answer):\n"
                + explanation_chain
            )

        try:
            result = self._llm.complete_json([{"role": "user", "content": prompt}])
        except Exception:
            logger.exception("LLM complete_json failed for category=%s", category)
            return empty_result_response()

        llm_evidence = result.get("evidence", [])
        if not isinstance(llm_evidence, list):
            llm_evidence = []

        # Filter out fabricated/placeholder DOI strings (e.g. "source DOI unavailable").
        # Only keep items whose doi matches the standard 10.NNNN/... format.
        llm_evidence = [e for e in llm_evidence if _has_real_doi(e)]

        # When the LLM returned insufficient real evidence, supplement from the
        # graph context (which always carries T1-backed DOIs after the recent
        # population fix).  We merge: LLM evidence first, then graph items whose
        # DOI is not already present, capped at 10 total to keep responses concise.
        if len(llm_evidence) < 3:
            graph_evidence = _materialize_graph_evidence(graph_context)
            if graph_evidence:
                existing_dois = {e.get("doi") for e in llm_evidence if e.get("doi")}
                supplemental = [
                    e for e in graph_evidence if e.get("doi") not in existing_dois
                ]
                llm_evidence = (llm_evidence + supplemental)[:10]

        # Normalise into expected shape
        raw = {
            "answer": result.get("answer", result.get("raw", "")),
            "confidence": result.get("confidence", 0.0),
            "evidence": llm_evidence,
            "axioms_used": result.get("axioms_used", []),
            "graph_path": result.get("graph_path", []),
            "caveats": result.get("caveats", []),
        }

        # Validate response against graph context
        strict_deterministic = category != "open_domain"
        validated = validate_llm_response(
            raw,
            graph_context,
            category=category,
            strict_deterministic=strict_deterministic,
        )

        # Preserve axioms_used and graph_path through validation
        validated.setdefault("axioms_used", raw["axioms_used"])
        validated.setdefault("graph_path", raw["graph_path"])

        # Replace LLM self-stated confidence with composite grounded score
        try:
            evidence_nodes = validated.get("evidence", [])
            if not isinstance(evidence_nodes, list):
                evidence_nodes = []
            provenance_summary = build_provenance_summary(
                validated.get("evidence", []),
                validated.get("answer", ""),
            )
            provenance_summary["has_numeric_claims"] = bool(
                extract_numerical_claims(validated.get("answer", ""))
            )
            n_hops = _CATEGORY_HOPS.get(category, 1)
            breakdown = calculate_response_confidence(
                evidence_nodes,
                n_hops=n_hops,
                provenance_summary=provenance_summary,
            )
            validated["confidence"] = breakdown["composite"]
            validated["confidence_breakdown"] = breakdown
            validated.update({
                "evidence_count": provenance_summary["evidence_count"],
                "doi_citation_count": provenance_summary["doi_citation_count"],
                "evidence_completeness_score": provenance_summary["evidence_completeness_score"],
                "provenance_warnings": provenance_summary["provenance_warnings"],
                "provenance_risk": provenance_summary["provenance_risk"],
            })
        except Exception:
            logger.warning(
                "Composite confidence scoring failed, keeping LLM confidence",
                exc_info=True,
            )

        return validated


def _extract_evidence_nodes(graph_context: dict) -> list[dict]:
    """Extract evidence-like dicts from graph_context results.

    Looks for items with source_tier, doi, year, or confidence properties
    in the top-level results list and in nested evidence lists.
    """
    nodes: list[dict] = []
    results = graph_context.get("results", [])
    if not isinstance(results, list):
        return nodes

    _EVIDENCE_KEYS = {"source_tier", "tier", "doi", "year", "confidence"}

    for item in results:
        if not isinstance(item, dict):
            continue
        # Check the item itself
        if _EVIDENCE_KEYS & item.keys():
            nodes.append(item)
        # Check nested evidence lists
        for val in item.values():
            if isinstance(val, list):
                for sub in val:
                    if isinstance(sub, dict) and (_EVIDENCE_KEYS & sub.keys()):
                        nodes.append(sub)

    return nodes


def _materialize_graph_evidence(graph_context: dict) -> list[dict]:
    """Build fallback evidence entries from graph context records.

    This is used when the LLM omits the evidence list despite graph records
    containing citation-like fields.
    """
    fallback: list[dict] = []
    for node in _extract_evidence_nodes(graph_context):
        doi = node.get("doi")
        title = node.get("title") or node.get("axiom_name") or ""
        year = node.get("year") or node.get("measurement_year")
        tier = node.get("tier") or node.get("source_tier")
        finding = node.get("finding") or node.get("quote") or node.get("evidence") or ""

        if not any((doi, title, year, tier, finding)):
            continue

        fallback.append({
            "doi": doi,
            "title": title,
            "year": year,
            "tier": tier,
            "finding": finding,
        })

    # Deduplicate by DOI/title/year tuple while preserving order.
    seen: set[tuple[str, str, int | None]] = set()
    deduped: list[dict] = []
    for item in fallback:
        key = (str(item.get("doi") or ""), str(item.get("title") or ""), item.get("year"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
