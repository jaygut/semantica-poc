"""Cross-paper pattern detection for quantitative cross-domain relationships.

Processes paper abstracts and extracted entities to identify patterns of the form:
  "X ecological metric [verb] Y financial/service outcome by/at/with Z coefficient"
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Domain keywords for classification
_ECOLOGICAL_KEYWORDS = {
    "biomass", "species", "biodiversity", "trophic", "habitat", "reef",
    "seagrass", "mangrove", "kelp", "coral", "fish", "otter", "shark",
    "ecosystem", "recovery", "protection", "mpa", "no-take", "marine",
    "carbon stock", "sequestration", "npp", "primary production",
}

_SERVICE_KEYWORDS = {
    "tourism", "fisheries", "flood protection", "coastal protection",
    "carbon credit", "carbon sequestration", "nursery", "wave attenuation",
    "ecosystem service", "esv", "valuation", "restoration",
}

_FINANCIAL_KEYWORDS = {
    "revenue", "value", "usd", "dollar", "billion", "million", "credit",
    "bond", "insurance", "investment", "bcr", "benefit-cost", "wtp",
    "willingness to pay", "price", "market",
}

# Patterns for extracting quantitative relationships
_COEFFICIENT_PATTERNS = [
    # "increased by X%"
    re.compile(
        r"(?:increas|decreas|reduc|enhanc|improv|declin)\w*\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%",
        re.IGNORECASE,
    ),
    # "X-fold" or "Xx"
    re.compile(
        r"(\d+(?:\.\d+)?)\s*[-]?\s*fold|(\d+(?:\.\d+)?)\s*x\b",
        re.IGNORECASE,
    ),
    # "$X million/billion"
    re.compile(
        r"\$\s*(\d+(?:\.\d+)?)\s*(million|billion|trillion|M|B|T)\b",
        re.IGNORECASE,
    ),
    # "X tCO2/ha/yr" or similar rate
    re.compile(
        r"(\d+(?:\.\d+)?)\s*(?:tCO2|t\s*CO2|tonnes?\s*CO2)\s*/\s*ha\s*/\s*yr",
        re.IGNORECASE,
    ),
    # "ratio of X" or "multiplier of X"
    re.compile(
        r"(?:ratio|multiplier)\s+(?:of\s+)?(\d+(?:\.\d+)?)",
        re.IGNORECASE,
    ),
]

# Verbs indicating a causal relationship
_CAUSAL_VERBS = re.compile(
    r"\b(?:increas|decreas|driv|caus|lead|result|contribut|provid|generat|"
    r"support|enhanc|reduc|protect|restor|sequester|store|yield|produc)\w*\b",
    re.IGNORECASE,
)


@dataclass
class CandidatePattern:
    """A quantitative cross-domain relationship detected in a paper."""

    relationship_type: str
    coefficient_value: float
    coefficient_unit: str = ""
    source_doi: str = ""
    source_quote: str = ""
    confidence: float = 0.0
    domain_from: str = ""
    domain_to: str = ""
    habitat: str = ""
    paper_id: str = ""


def _classify_domain(text: str) -> str:
    """Classify a text snippet into ecological, service, or financial domain."""
    text_lower = text.lower()
    scores = {"ecological": 0, "service": 0, "financial": 0}

    for kw in _ECOLOGICAL_KEYWORDS:
        if kw in text_lower:
            scores["ecological"] += 1
    for kw in _SERVICE_KEYWORDS:
        if kw in text_lower:
            scores["service"] += 1
    for kw in _FINANCIAL_KEYWORDS:
        if kw in text_lower:
            scores["financial"] += 1

    if max(scores.values()) == 0:
        return "unknown"
    return max(scores, key=lambda k: scores[k])


def _detect_habitat(text: str) -> str:
    """Detect habitat type from text."""
    text_lower = text.lower()
    habitat_map = {
        "coral reef": "coral_reef",
        "coral": "coral_reef",
        "reef": "coral_reef",
        "seagrass": "seagrass_meadow",
        "mangrove": "mangrove_forest",
        "kelp": "kelp_forest",
        "rocky reef": "rocky_reef",
    }
    for phrase, habitat in habitat_map.items():
        if phrase in text_lower:
            return habitat
    return ""


def _extract_coefficients(text: str) -> list[tuple[float, str, str]]:
    """Extract numeric coefficients from text.

    Returns list of (value, unit, quote) tuples.
    """
    results = []
    for pattern in _COEFFICIENT_PATTERNS:
        for match in pattern.finditer(text):
            # Get the matched numeric value
            groups = [g for g in match.groups() if g is not None]
            if not groups:
                continue

            # First group is the numeric value for most patterns
            try:
                value = float(groups[0])
            except (ValueError, IndexError):
                continue

            unit = groups[1] if len(groups) > 1 else ""

            # Extract surrounding context as quote
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            quote = text[start:end].strip()

            results.append((value, unit, quote))

    return results


class PatternDetector:
    """Detect quantitative cross-domain relationships in paper abstracts.

    Scans paper text for patterns like:
    - "X ecological metric [verb] Y financial outcome by Z coefficient"
    - Quantitative rates, ratios, percentages with causal language
    """

    def __init__(self, min_confidence: float = 0.3) -> None:
        self._min_confidence = min_confidence

    def detect_patterns(self, papers: list[dict[str, Any]]) -> list[CandidatePattern]:
        """Detect patterns across a corpus of papers.

        Args:
            papers: List of dicts with keys: paper_id, doi, title, abstract,
                    domain_tags (optional), source_tier (optional).

        Returns:
            List of CandidatePattern objects found.
        """
        all_patterns: list[CandidatePattern] = []

        for paper in papers:
            abstract = paper.get("abstract", "")
            if not abstract:
                continue

            patterns = self._detect_in_text(
                text=abstract,
                paper_id=paper.get("paper_id", ""),
                doi=paper.get("doi", ""),
                source_tier=paper.get("source_tier", "T1"),
            )
            all_patterns.extend(patterns)

        logger.info("Detected %d candidate patterns from %d papers", len(all_patterns), len(papers))
        return all_patterns

    def _detect_in_text(
        self,
        text: str,
        paper_id: str = "",
        doi: str = "",
        source_tier: str = "T1",
    ) -> list[CandidatePattern]:
        """Detect patterns in a single text."""
        patterns: list[CandidatePattern] = []

        # Check if text has causal language
        if not _CAUSAL_VERBS.search(text):
            return patterns

        # Extract coefficients
        coefficients = _extract_coefficients(text)
        if not coefficients:
            return patterns

        # Classify domains from text
        # Split text into sentences for context
        sentences = re.split(r"[.;]\s+", text)

        for value, unit, quote in coefficients:
            # Find the sentence containing this coefficient
            context = ""
            for sent in sentences:
                if quote[:20] in sent or str(value) in sent:
                    context = sent
                    break
            if not context:
                context = text

            # Classify source and target domains
            domain_from = _classify_domain(context)
            domain_to = self._infer_target_domain(context, domain_from)

            # Skip if same domain or unknown
            if domain_from == domain_to or domain_from == "unknown" or domain_to == "unknown":
                continue

            habitat = _detect_habitat(context)

            # Compute confidence based on evidence quality
            confidence = self._compute_confidence(
                source_tier=source_tier,
                has_causal_verb=bool(_CAUSAL_VERBS.search(context)),
                has_quantification=True,
                domain_cross=domain_from != domain_to,
            )

            if confidence < self._min_confidence:
                continue

            # Determine relationship type
            rel_type = f"{domain_from}_to_{domain_to}"

            patterns.append(CandidatePattern(
                relationship_type=rel_type,
                coefficient_value=value,
                coefficient_unit=unit,
                source_doi=doi,
                source_quote=quote[:200],
                confidence=confidence,
                domain_from=domain_from,
                domain_to=domain_to,
                habitat=habitat,
                paper_id=paper_id,
            ))

        return patterns

    def _infer_target_domain(self, context: str, source_domain: str) -> str:
        """Infer the target domain based on context and source domain."""
        context_lower = context.lower()

        # If source is ecological, look for service or financial targets
        if source_domain == "ecological":
            for kw in _SERVICE_KEYWORDS:
                if kw in context_lower:
                    return "service"
            for kw in _FINANCIAL_KEYWORDS:
                if kw in context_lower:
                    return "financial"
            # Ecological-to-ecological is valid (e.g., biomass -> resilience)
            return "ecological"

        if source_domain == "service":
            for kw in _FINANCIAL_KEYWORDS:
                if kw in context_lower:
                    return "financial"
            return "service"

        if source_domain == "financial":
            return "financial"

        return "unknown"

    def _compute_confidence(
        self,
        source_tier: str,
        has_causal_verb: bool,
        has_quantification: bool,
        domain_cross: bool,
    ) -> float:
        """Compute a confidence score for a detected pattern."""
        score = 0.0

        # Source tier contributes most
        tier_scores = {"T1": 0.4, "T2": 0.3, "T3": 0.2, "T4": 0.1}
        score += tier_scores.get(source_tier, 0.1)

        # Causal language
        if has_causal_verb:
            score += 0.2

        # Quantification present
        if has_quantification:
            score += 0.2

        # Cross-domain relationship
        if domain_cross:
            score += 0.2

        return min(score, 1.0)
