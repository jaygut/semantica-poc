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
        r"\b(?:recover\w*|biomass|drive|cause|increase|change|restor\w*)\b",
        r"\b(?:debt|swap|finance|bond|fund|invest|mechanism)\b",
    ]),
    ("provenance_drilldown", [
        r"\b(?:evidence|provenance|dois?|source|paper|citation|backed|support(?:s|ing|ed)?)\b",
        r"\bwhat.+(?:evidence|research|study|studies)\b",
        r"\bhow does.+(?:translat|lead to|convert|become)",
        r"\b(?:mechanism|translat)",
        r"\b(?:methodolog\w*|verification|verra|vcs|issuance|accounting)\b",
    ]),
    ("concept_explanation", [
        r"\bwhat\s+(?:is|are)\b.*\b(?:blue.?carbon|carbon.?credit|coastal.?protect|blue.?bonds?|nature.?based|tnfd|ecosystem.?service)\b",
        r"\bhow\b.*\b(?:blue.?carbon|carbon|coastal|ecosystem|nature)\b.*\b(?:work|function|operate)\b",
        r"\bexplain\b.*\b(?:blue.?carbon|carbon|protection|restoration|resilience|trophic|biodiversity)\b",
        r"\bwhat\s+(?:is|are)\b.*\b(?:debt.?for.?nature|reef.?insurance|parametric|mpa.?network|trophic.?cascade)\b",
        r"\b(?:how\s+(?:does|do|can)|explain)\b.*\b(?:debt.?for.?nature|blue.?bonds?|reef.?insurance|parametric.?insurance|nature.?bonds?|mpa.?bonds?)\b",
    ]),
    ("axiom_explanation", [
        r"\b(?:bridge.?axiom|axiom|coefficient)\b",
        r"\b(?:[Bb][Aa]-\d{3})\b",
        r"\b(?:seagrass|blue.?carbon|mangrove|kelp).*(?:sequest\w*|carbon|mechanism)\b",
        r"\bhow\b.*\b(?:seagrass|mangrove|kelp|coral|blue.?carbon)\b.*\b(?:sequest\w*|work|store|accumulate|protect|value)\b",
        r"\bhow\b.*\b(?:carbon|biomass|tourism|fisheries|coastal)\b.*\b(?:translat\w*|convert|valued?|work)\b",
        r"\bwhat\s+(?:is|are)\b.*\b(?:bridge.?axiom|blue.?carbon|carbon.?credit|carbon.?sequest\w*)\b",
    ]),
    ("comparison", [
        r"\b(?:compar|versus|vs\.?|differ|rank|benchmark)\b",
    ]),
    ("scenario_analysis", [
        r"\bwhat\s+if\b",
        r"\bwhat\s+happens?\s+(?:if|when|under)\b",
        r"\b(?:scenario|counterfactual)\b",
        r"\bssp[125][-\s]",
        r"\bwithout\s+protection\b",
        r"\brestore|restoration\b",
        r"\bcarbon\s+price.{0,20}(?:at|\$|\d)",
        r"\bblue\s+carbon\s+revenue\b",
        r"\bcarbon\s+revenue.{0,30}(?:\$|\d)",
        r"\btipping\s+point\b",
        r"\bstress\s+test\b",
        r"\bnature\s+var\b",
        r"\binvest\s+\$?\d",
        r"\bhow\s+(?:much|close|far).{0,30}(?:threshold|regime\s+shift|tipping)",
        r"\bif\s+(?:we|you|they).{0,20}(?:invest|restore|protect|stop)\b",
    ]),
    ("risk_assessment", [
        r"\b(?:risk\w*|degrad|scenario|climate|threat|loss|lost|declin\w*|vulnerab)\b",
        r"\bwhat\b.*\bif\b",
        r"\bif\b.*\bwhat\b",
        r"\bwhat\s+\w*\s*happen",
        r"\b(?:governance|enforcement|transboundary|surveillance|unesco|award|mining|saliniz\w*)\b",
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

# Dynamic site patterns loaded from the site registry (populated at runtime)
_DYNAMIC_SITE_PATTERNS: list[tuple[str, str]] = []


def register_dynamic_sites(site_names: list[str]) -> int:
    """Register additional site names for query classification.

    Called by the site registry when new sites are added. Each name gets
    a word-boundary regex pattern generated automatically.

    Returns the number of patterns registered.
    """
    global _DYNAMIC_SITE_PATTERNS  # noqa: PLW0603
    _DYNAMIC_SITE_PATTERNS = []
    seen_patterns: set[str] = set()
    for name in site_names:
        # Build a regex from the canonical name (case-insensitive word match)
        escaped = re.escape(name)
        # Also create a short form from the first two words
        parts = name.split()
        patterns = [rf"\b{escaped}\b"]
        if len(parts) >= 2:
            short = re.escape(" ".join(parts[:2]))
            patterns.append(rf"\b{short}\b")
        # Add first-word alias for common prompts like "Sundarbans" or "Cispata"
        if parts and len(parts[0]) >= 4:
            first = re.escape(parts[0])
            patterns.append(rf"\b{first}\b")
        combined = "|".join(patterns)
        pattern = f"(?:{combined})"
        if pattern not in seen_patterns:
            _DYNAMIC_SITE_PATTERNS.append((pattern, name))
            seen_patterns.add(pattern)
    return len(_DYNAMIC_SITE_PATTERNS)


def get_all_canonical_sites() -> list[str]:
    """Return all canonical site names (static + dynamic)."""
    names = list(_CANONICAL_SITES)
    for _, canonical in _DYNAMIC_SITE_PATTERNS:
        if canonical not in names:
            names.append(canonical)
    return names


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

            # Tie-break: prefer provenance/risk/concept explanation over
            # site_valuation when explicit intent keywords are present.
            if best == "site_valuation":
                if (
                    "provenance_drilldown" in scores
                    and re.search(
                        r"\b(?:evidence|provenance|dois?|source|paper|citation|support(?:s|ing|ed)?|translat\w*|mechanism|convert|become)\b|\blead\s+to\b",
                        q_lower,
                    )
                ):
                    best = "provenance_drilldown"
                elif (
                    "risk_assessment" in scores
                    and re.search(
                        r"\b(?:risk|climate|threat|if|happen|declin\w*|loss|vulnerab)\b",
                        q_lower,
                    )
                ):
                    best = "risk_assessment"
                elif (
                    "concept_explanation" in scores
                    and re.search(
                        r"\b(?:what\s+(?:is|are)|how\s+(?:does|do|can)|explain)\b.*"
                        r"\b(?:work|function|operate|mechanism|relate|link|connect|help|contribute)\b"
                        r"|\bhow\b.*\b(?:debt.?for.?nature|blue.?bonds?|reef.?insurance|parametric|mpa.?network|nature.?bonds?)\b"
                        r"|\bwhat\s+(?:is|are)\b.*\b(?:debt.?for.?nature|reef.?insurance|parametric|mpa.?network)\b",
                        q_lower,
                    )
                ):
                    best = "concept_explanation"

            # Tie-break: prefer comparison over site_valuation when
            # comparison-specific verbs are present
            if (
                best == "site_valuation"
                and "comparison" in scores
                and scores["comparison"] == scores["site_valuation"]
                and re.search(r"\b(?:rank|compar|versus|vs\.?|benchmark)\b", q_lower)
            ):
                best = "comparison"

            # Scenario vs risk tie-break: scenario_analysis requires
            # scenario-specific keywords beyond generic "what if" + risk.
            # If scenario_analysis won but lacks strong signal, demote to
            # risk_assessment (if scored). If risk/site_valuation won but
            # strong scenario signal present, promote to scenario_analysis.
            _SCENARIO_STRONG_SIGNAL = re.compile(
                r"\bwithout\s+protection\b"
                r"|\bcounterfactual\b"
                r"|\bssp[125][-\s]"
                r"|\btipping\s+point\b"
                r"|\bstress\s+test\b"
                r"|\bnature\s+var\b"
                r"|\bcarbon\s+price.{0,20}(?:at|\$|\d)"
                r"|\bblue\s+carbon\s+revenue\b"
                r"|\bcarbon\s+revenue.{0,30}(?:\$|\d)"
                r"|\binvest\s+\$?\d"
                r"|\bif\s+(?:we|you|they).{0,20}(?:invest|restore|protect|stop)\b"
                r"|\bhow\s+(?:close|far).{0,30}(?:threshold|regime|tipping)",
                re.IGNORECASE,
            )
            has_strong_scenario = bool(_SCENARIO_STRONG_SIGNAL.search(q_lower))

            if best == "scenario_analysis" and not has_strong_scenario:
                # Demote: generic "what if" without scenario specifics
                if "risk_assessment" in scores:
                    best = "risk_assessment"
            elif (
                best in ("risk_assessment", "site_valuation")
                and "scenario_analysis" in scores
                and has_strong_scenario
            ):
                # Promote: strong scenario signal overrides risk/valuation
                best = "scenario_analysis"

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
            # Route to open_domain when LLM succeeded but with low confidence.
            # LLM failure fallback is marked with _llm_failed=True and keeps
            # its default category.
            if (
                not result.pop("_llm_failed", False)
                and result.get("confidence", 0) < 0.25
            ):
                result["category"] = "open_domain"
            return result

        # No keyword match and no LLM -> open_domain
        return {
            "category": "open_domain",
            "site": site,
            "metrics": metrics,
            "confidence": 0.2,
            "caveats": caveats or [],
        }

    def _extract_metrics(self, text: str) -> list[str]:
        return [
            name for name, pat in _METRIC_KEYWORDS.items()
            if re.search(pat, text)
        ]

    def _extract_sites(self, text: str) -> list[str]:
        """Extract all mentioned sites, with dynamic registry and fuzzy fallback."""
        found: list[str] = []
        for pat, canonical in _SITE_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                if canonical not in found:
                    found.append(canonical)

        # Check dynamic patterns from site registry
        for pat, canonical in _DYNAMIC_SITE_PATTERNS:
            if canonical not in found and re.search(pat, text, re.IGNORECASE):
                found.append(canonical)

        if not found:
            # Fuzzy matching fallback: extract multi-word tokens and try
            # matching against canonical site names (static + dynamic)
            fuzzy_match = self._fuzzy_site_match(text)
            if fuzzy_match:
                found.append(fuzzy_match)

        return found

    def _extract_site(self, text: str) -> str | None:
        """Extract a single site (backwards compatible)."""
        sites = self._extract_sites(text)
        return sites[0] if sites else None

    def _fuzzy_site_match(self, text: str, cutoff: float = 0.6) -> str | None:
        """Try fuzzy matching against canonical site names (static + dynamic)."""
        all_sites = get_all_canonical_sites()
        # Build candidate words from the text (2-5 word windows)
        words = text.split()
        candidates: list[str] = []
        for window in range(5, 1, -1):
            for i in range(len(words) - window + 1):
                candidates.append(" ".join(words[i:i + window]))
        candidates.extend(words)

        # Try each candidate against canonical names
        lower_sites = [name.lower() for name in all_sites]
        for candidate in candidates:
            matches = difflib.get_close_matches(
                candidate,
                lower_sites,
                n=1,
                cutoff=cutoff,
            )
            if matches:
                # Map back to properly cased canonical name
                idx = lower_sites.index(matches[0])
                return all_sites[idx]

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
                "_llm_failed": True,
            }
