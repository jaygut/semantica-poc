"""Query classification - keyword-first with LLM fallback."""

import logging
import re

from maris.llm.adapter import LLMAdapter
from maris.llm.prompts import QUERY_CLASSIFICATION_PROMPT

logger = logging.getLogger(__name__)

# Keyword patterns for fast classification without LLM round-trip
_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    ("site_valuation", [
        r"\b(?:value|valuation|esv|worth|asset.?rating|total.?value)\b",
        r"\bhow much\b.*\bworth\b",
    ]),
    ("provenance_drilldown", [
        r"\b(?:evidence|provenance|doi|source|paper|citation|backed|supporting)\b",
        r"\bwhat.+(?:evidence|research|study|studies)\b",
    ]),
    ("axiom_explanation", [
        r"\b(?:bridge.?axiom|axiom|coefficient)\b",
        r"\b(?:BA-\d{3})\b",
    ]),
    ("provenance_drilldown", [
        r"\bhow does.+(?:translat|lead to|convert|become)\b",
        r"\b(?:mechanism|translat)\b",
    ]),
    ("comparison", [
        r"\b(?:compar|versus|vs\.?|differ|rank|benchmark)\b",
    ]),
    ("risk_assessment", [
        r"\b(?:risk|degrad|scenario|what.?if|climate|threat|loss|decline|vulnerab)\b",
    ]),
]

# Metric keywords to extract from the question
_METRIC_KEYWORDS = {
    "biomass": r"\bbiomass\b",
    "esv": r"\b(?:esv|ecosystem.?service.?value)\b",
    "neoli": r"\bneoli\b",
    "tourism": r"\btourism\b",
    "carbon": r"\bcarbon\b",
    "fisheries": r"\bfisher(?:y|ies)\b",
    "protection": r"\b(?:flood.?protect|coastal.?protect)\b",
}

# Common site name patterns -> canonical Neo4j node names
_SITE_PATTERNS: list[tuple[str, str]] = [
    (r"\b(cabo\s+pulmo)\b", "Cabo Pulmo National Park"),
    (r"\b(great\s+barrier\s+reef)\b", "Great Barrier Reef Marine Park"),
    (r"\b(galapagos)\b", "Galapagos Marine Reserve"),
    (r"\b(papah[aā]naumoku[aā]kea)\b", "Papah\u0101naumoku\u0101kea Marine National Monument"),
]


class QueryClassifier:
    """Classify user questions into query categories.

    Uses fast keyword matching first; falls back to LLM for ambiguous queries.
    """

    def __init__(self, llm: LLMAdapter | None = None):
        self._llm = llm

    def classify(self, question: str) -> dict:
        """Classify a question and extract metadata.

        Returns dict with keys: category, site, metrics, confidence.
        """
        q_lower = question.lower()

        # Extract site
        site = self._extract_site(q_lower)

        # Extract metrics
        metrics = [name for name, pat in _METRIC_KEYWORDS.items() if re.search(pat, q_lower)]

        # Keyword-based classification
        scores: dict[str, int] = {}
        for category, patterns in _KEYWORD_RULES:
            hits = sum(1 for p in patterns if re.search(p, q_lower))
            if hits:
                scores[category] = hits

        if scores:
            best = max(scores, key=scores.get)  # type: ignore[arg-type]
            confidence = min(0.6 + 0.15 * scores[best], 0.95)
            return {"category": best, "site": site, "metrics": metrics, "confidence": confidence}

        # LLM fallback for ambiguous queries
        if self._llm:
            return self._classify_with_llm(question, site, metrics)

        # Default fallback
        return {"category": "site_valuation", "site": site, "metrics": metrics, "confidence": 0.3}

    def _extract_site(self, text: str) -> str | None:
        for pat, canonical in _SITE_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return canonical
        return None

    def _classify_with_llm(self, question: str, site: str | None, metrics: list[str]) -> dict:
        prompt = QUERY_CLASSIFICATION_PROMPT.format(question=question)
        try:
            result = self._llm.complete_json([{"role": "user", "content": prompt}])
            return {
                "category": result.get("category", "site_valuation"),
                "site": result.get("site") or site,
                "metrics": result.get("metrics", metrics),
                "confidence": result.get("confidence", 0.5),
            }
        except Exception:
            logger.exception("LLM classification failed, using default")
            return {"category": "site_valuation", "site": site, "metrics": metrics, "confidence": 0.3}
