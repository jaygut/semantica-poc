"""LLM-enhanced pattern detection for axiom discovery.

Uses the LLMAdapter to extract cross-domain quantitative relationships
with higher accuracy than regex alone. Falls back to the regex-based
PatternDetector when no LLM adapter is provided.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from maris.discovery.pattern_detector import (
    CandidatePattern,
    PatternDetector,
    _classify_domain,
    _detect_habitat,
)
from maris.llm.prompts import AXIOM_DISCOVERY_PROMPT

logger = logging.getLogger(__name__)

# Confidence string -> numeric mapping
_CONFIDENCE_MAP = {"high": 0.9, "medium": 0.7, "low": 0.4}

# Maximum LLM extraction attempts per paper before falling back to regex
_MAX_LLM_ATTEMPTS = 2


def _resolve_confidence(raw_value: Any) -> float:
    """Convert a confidence value from LLM output to a float in [0, 1].

    Handles both string labels ("high", "medium", "low") and numeric
    values (0.0-1.0 floats or ints).
    """
    if isinstance(raw_value, (int, float)):
        return max(0.0, min(1.0, float(raw_value)))
    label = str(raw_value).strip().lower()
    return _CONFIDENCE_MAP.get(label, 0.5)


def _parse_json_array(text: str) -> list[dict[str, Any]]:
    """Extract a JSON array from LLM output, handling markdown fences.

    Returns a list of dicts on success (may be empty for ``[]``).
    Returns ``None`` when no valid JSON array can be extracted at all,
    which callers can use to distinguish "parsed but empty" from
    "unparseable output".
    """
    text = text.strip()

    # Strip markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        result = json.loads(text[start : end + 1])
        if not isinstance(result, list):
            return None
        # Filter out non-dict entries that an LLM might accidentally include
        return [item for item in result if isinstance(item, dict)]
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM JSON response for axiom discovery")
        return None


class LLMPatternDetector:
    """LLM-enhanced pattern detection for axiom discovery.

    Uses the existing LLMAdapter from maris.llm to extract cross-domain
    quantitative relationships with higher accuracy than regex alone.
    Falls back to regex PatternDetector when LLM is unavailable.
    """

    def __init__(
        self,
        llm_adapter: Any | None = None,
        min_confidence: float = 0.3,
    ) -> None:
        self._llm = llm_adapter
        self._regex_fallback = PatternDetector(min_confidence=min_confidence)
        self._min_confidence = min_confidence

    def detect_patterns(self, papers: list[dict[str, Any]]) -> list[CandidatePattern]:
        """Detect patterns using LLM extraction with regex fallback.

        Args:
            papers: List of paper dicts with keys: paper_id, doi, title,
                    abstract, source_tier, domain_tags.

        Returns:
            List of CandidatePattern objects found.
        """
        if self._llm is None:
            return self._regex_fallback.detect_patterns(papers)

        all_patterns: list[CandidatePattern] = []

        for paper in papers:
            abstract = paper.get("abstract", "")
            if not abstract:
                continue

            llm_patterns = self._extract_via_llm(paper)
            regex_patterns = self._regex_fallback._detect_in_text(
                text=abstract,
                paper_id=paper.get("paper_id", ""),
                doi=paper.get("doi", ""),
                source_tier=paper.get("source_tier", "T1"),
            )

            merged = self._merge_patterns(llm_patterns, regex_patterns)
            all_patterns.extend(merged)

        logger.info(
            "LLM detector found %d patterns from %d papers",
            len(all_patterns),
            len(papers),
        )
        return all_patterns

    def _extract_via_llm(self, paper: dict[str, Any]) -> list[CandidatePattern]:
        """Use LLM to extract cross-domain relationships from a paper abstract.

        Retries once with explicit JSON instructions if the first attempt
        returns unparseable output.
        """
        abstract = paper.get("abstract", "")
        doi = paper.get("doi", "")
        paper_id = paper.get("paper_id", "")
        source_tier = paper.get("source_tier", "T1")

        prompt = AXIOM_DISCOVERY_PROMPT.format(
            doi=doi,
            abstract=abstract,
        )

        items: list[dict[str, Any]] | None = None
        for attempt in range(1, _MAX_LLM_ATTEMPTS + 1):
            try:
                raw = self._llm.complete(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                )
            except Exception as e:
                logger.warning(
                    "LLM extraction failed for %s (attempt %d): %s",
                    paper_id, attempt, e,
                )
                break

            items = _parse_json_array(raw)
            if items is not None:
                # Parsing succeeded (even if the list is empty - that's valid)
                break

            if attempt < _MAX_LLM_ATTEMPTS:
                logger.warning(
                    "Unparseable LLM output for %s (attempt %d), retrying",
                    paper_id, attempt,
                )
                prompt = (
                    "Your previous response was not valid JSON. "
                    "Return ONLY a JSON array of objects. No explanation.\n\n"
                    + prompt
                )

        if items is None:
            items = []

        patterns: list[CandidatePattern] = []

        for item in items:
            coefficient = item.get("coefficient")
            if coefficient is None:
                continue
            try:
                coefficient = float(coefficient)
            except (ValueError, TypeError):
                continue

            confidence = _resolve_confidence(item.get("confidence", "medium"))

            # Boost confidence for T1 sources
            tier_boost = {"T1": 0.05, "T2": 0.0, "T3": -0.05, "T4": -0.1}
            confidence += tier_boost.get(source_tier, 0.0)
            confidence = max(0.0, min(1.0, confidence))

            if confidence < self._min_confidence:
                continue

            eco_metric = item.get("ecological_metric", "")
            fin_metric = item.get("financial_metric", "")
            unit = item.get("unit", "")
            quote = str(item.get("quote", "") or "")[:200]

            # Classify domains from the metric descriptions
            domain_from = _classify_domain(eco_metric) if eco_metric else "ecological"
            domain_to = _classify_domain(fin_metric) if fin_metric else "financial"

            # Default to ecological->service if classification is ambiguous
            if domain_from == "unknown":
                domain_from = "ecological"
            if domain_to == "unknown":
                domain_to = "service"

            # Skip same-domain patterns
            if domain_from == domain_to:
                continue

            habitat = _detect_habitat(f"{abstract} {eco_metric}")

            rel_type = f"{domain_from}_to_{domain_to}"

            patterns.append(CandidatePattern(
                relationship_type=rel_type,
                coefficient_value=coefficient,
                coefficient_unit=unit,
                source_doi=doi,
                source_quote=quote,
                confidence=confidence,
                domain_from=domain_from,
                domain_to=domain_to,
                habitat=habitat,
                paper_id=paper_id,
            ))

        return patterns

    def _merge_patterns(
        self,
        llm_patterns: list[CandidatePattern],
        regex_patterns: list[CandidatePattern],
    ) -> list[CandidatePattern]:
        """Merge LLM and regex patterns, preferring LLM when they overlap.

        Two patterns are considered overlapping if they share the same DOI
        and a similar coefficient value (within 10%).
        """
        if not llm_patterns:
            return regex_patterns
        if not regex_patterns:
            return llm_patterns

        merged = list(llm_patterns)

        for rp in regex_patterns:
            is_duplicate = False
            for lp in llm_patterns:
                if rp.source_doi and rp.source_doi == lp.source_doi:
                    # Check if coefficients are similar (within 10%)
                    if lp.coefficient_value != 0:
                        ratio = abs(rp.coefficient_value - lp.coefficient_value) / abs(
                            lp.coefficient_value
                        )
                        if ratio < 0.1:
                            is_duplicate = True
                            break
            if not is_duplicate:
                merged.append(rp)

        return merged
