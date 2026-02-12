"""Query classification - keyword-first with LLM fallback.

Classifies natural-language questions into five query categories using a
two-tier approach: fast keyword/regex matching, then LLM fallback for
ambiguous queries. Includes Unicode normalization, acronym support, fuzzy
site matching, multi-site detection, and negation handling.
"""

import difflib
import logging
import re
import unicodedata

from maris.llm.adapter import LLMAdapter
from maris.llm.prompts import QUERY_CLASSIFICATION_PROMPT

logger = logging.getLogger(__name__)

_MAX_QUESTION_LENGTH = 500

# Keyword patterns for fast classification without LLM round-trip.
# provenance_drilldown rules merged from former duplicate entries.
_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    ("site_valuation", [
        r"\b(?:value|valuation|esv|worth|asset.?rating|total.?value)\b",
        r"\bhow much\b.*\bworth\b",
    ]),
    ("provenance_drilldown", [
        r"\b(?:evidence|provenance|doi|source|paper|citation|backed|supporting)\b",
        r"\bwhat.+(?:evidence|research|study|studies)\b",
        r"\bhow does.+(?:translat|lead to|convert|become)",
        r"\b(?:mechanism|translat)",
    ]),
    ("axiom_explanation", [
        r"\b(?:bridge.?axiom|axiom|coefficient)\b",
        r"\b(?:BA-\d{3})\b",
        r"\b(?:seagrass|blue.?carbon).*(?:sequester|carbon|mechanism|how)\b",
        r"\bhow\b.*\b(?:seagrass|mangrove)\b.*\b(?:sequester|carbon|store)\b",
    ]),
    ("comparison", [
        r"\b(?:compar|versus|vs\.?|differ|rank|benchmark)\b",
    ]),
    ("risk_assessment", [
        r"\b(?:risk|degrad|scenario|climate|threat|loss|lost|decline|vulnerab)\b",
        r"\bwhat\b.*\bif\b",
        r"\bwhat\s+happens\b",
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

# Common site name patterns -> canonical Neo4j node names.
# Includes acronyms (GBR, CP, PMNM) and full-name patterns.
_SITE_PATTERNS: list[tuple[str, str]] = [
    (r"\b(?:cabo\s+pulmo|CP)\b", "Cabo Pulmo National Park"),
    (r"\b(?:great\s+barrier\s+reef|GBR)\b", "Great Barrier Reef Marine Park"),
    (r"\b(?:galapagos)\b", "Galapagos Marine Reserve"),
    (r"\b(?:papah[aā]naumoku[aā]kea|PMNM)\b",
     "Papah\u0101naumoku\u0101kea Marine National Monument"),
    (r"\b(?:shark\s+bay|SB)\b", "Shark Bay World Heritage Area"),
]

# Canonical names list for fuzzy matching fallback
_CANONICAL_SITES = [s[1] for s in _SITE_PATTERNS]

# Negation markers
_NEGATION_PATTERN = re.compile(
    r"\b(?:not|without|no\s+|never|exclude|excluding|lacks?|missing)\b",
    re.IGNORECASE,
)


class QueryClassifier:
    """Classify user questions into query categories.

    Uses fast keyword matching first; falls back to LLM for ambiguous queries.
    Supports Unicode normalization, acronyms, fuzzy site matching, multi-site
    detection, and negation handling.
    """

    def __init__(self, llm: LLMAdapter | None = None):
        self._llm = llm

    def classify(self, question: str) -> dict:
        """Classify a question and extract metadata.

        Returns dict with keys: category, site (or sites), metrics, confidence,
        and optionally caveats.
        """
        if not question or not question.strip():
            return {
                "category": "site_valuation",
                "site": None,
                "metrics": [],
                "confidence": 0.0,
                "caveats": ["Empty question provided"],
            }

        caveats: list[str] = []

        # Truncate overly long questions
        if len(question) > _MAX_QUESTION_LENGTH:
            question = question[:_MAX_QUESTION_LENGTH]
            caveats.append(
                f"Question truncated to {_MAX_QUESTION_LENGTH} characters"
            )

        # Unicode normalization (NFKD) then strip combining marks for
        # consistent matching (e.g., ā -> a)
        normalized = unicodedata.normalize("NFKD", question)
        q_lower = "".join(
            c for c in normalized if not unicodedata.combining(c)
        ).lower()

        # Extract sites (supports multi-site)
        sites = self._extract_sites(q_lower)

        # Multi-site detection -> force comparison category
        if len(sites) >= 2:
            metrics = self._extract_metrics(q_lower)
            return {
                "category": "comparison",
                "site": sites[0],
                "sites": sites,
                "metrics": metrics,
                "confidence": 0.85,
                "caveats": caveats or [],
            }

        site = sites[0] if sites else None

        # Extract metrics
        metrics = self._extract_metrics(q_lower)

        # Negation detection
        if _NEGATION_PATTERN.search(q_lower):
            caveats.append("Negation detected - verify classification")

        # Keyword-based classification
        scores: dict[str, int] = {}
        for category, patterns in _KEYWORD_RULES:
            hits = sum(1 for p in patterns if re.search(p, q_lower))
            if hits:
                scores[category] = scores.get(category, 0) + hits

        if scores:
            best = max(scores, key=scores.get)  # type: ignore[arg-type]
            confidence = min(0.6 + 0.15 * scores[best], 0.95)
            return {
                "category": best,
                "site": site,
                "metrics": metrics,
                "confidence": confidence,
                "caveats": caveats or [],
            }

        # LLM fallback for ambiguous queries
        if self._llm:
            result = self._classify_with_llm(question, site, metrics)
            if caveats:
                result["caveats"] = result.get("caveats", []) + caveats
            return result

        # Default fallback
        return {
            "category": "site_valuation",
            "site": site,
            "metrics": metrics,
            "confidence": 0.3,
            "caveats": caveats or [],
        }

    def _extract_metrics(self, text: str) -> list[str]:
        return [
            name for name, pat in _METRIC_KEYWORDS.items()
            if re.search(pat, text)
        ]

    def _extract_sites(self, text: str) -> list[str]:
        """Extract all mentioned sites, with fuzzy fallback."""
        found: list[str] = []
        for pat, canonical in _SITE_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                if canonical not in found:
                    found.append(canonical)

        if not found:
            # Fuzzy matching fallback: extract multi-word tokens and try
            # matching against canonical site names
            fuzzy_match = self._fuzzy_site_match(text)
            if fuzzy_match:
                found.append(fuzzy_match)

        return found

    def _extract_site(self, text: str) -> str | None:
        """Extract a single site (backwards compatible)."""
        sites = self._extract_sites(text)
        return sites[0] if sites else None

    def _fuzzy_site_match(self, text: str, cutoff: float = 0.6) -> str | None:
        """Try fuzzy matching against canonical site names."""
        # Build candidate words from the text (2-5 word windows)
        words = text.split()
        candidates: list[str] = []
        for window in range(5, 1, -1):
            for i in range(len(words) - window + 1):
                candidates.append(" ".join(words[i:i + window]))
        candidates.extend(words)

        # Try each candidate against canonical names
        for candidate in candidates:
            matches = difflib.get_close_matches(
                candidate,
                [name.lower() for name in _CANONICAL_SITES],
                n=1,
                cutoff=cutoff,
            )
            if matches:
                # Map back to properly cased canonical name
                idx = [name.lower() for name in _CANONICAL_SITES].index(
                    matches[0]
                )
                return _CANONICAL_SITES[idx]

        return None

    def _classify_with_llm(
        self, question: str, site: str | None, metrics: list[str]
    ) -> dict:
        prompt = QUERY_CLASSIFICATION_PROMPT.format(question=question)
        try:
            result = self._llm.complete_json(
                [{"role": "user", "content": prompt}]
            )
            return {
                "category": result.get("category", "site_valuation"),
                "site": result.get("site") or site,
                "metrics": result.get("metrics", metrics),
                "confidence": result.get("confidence", 0.5),
                "caveats": [],
            }
        except Exception:
            logger.exception("LLM classification failed, using default")
            return {
                "category": "site_valuation",
                "site": site,
                "metrics": metrics,
                "confidence": 0.3,
                "caveats": [],
            }
