"""Scenario parser - extract structured ScenarioRequest from natural language.

Pattern-based extraction that works without LLM in demo mode. Extracts SSP
scenarios, time horizons, site scope, and scenario type from user questions.
"""

from __future__ import annotations

import re
from typing import Any

try:
    from maris.scenario.models import ScenarioRequest
except ImportError:
    # Minimal local fallback if models.py is not yet populated
    from pydantic import BaseModel

    class ScenarioRequest(BaseModel):  # type: ignore[no-redef]
        scenario_type: str = "counterfactual"
        site_scope: list[str] = []
        time_horizon_years: int = 10
        assumptions: dict[str, Any] = {}
        compare_against: str = "baseline"
        ssp_scenario: str | None = None
        target_year: int | None = None


# Short-name -> canonical-name mapping (mirrored from graphrag_chat.py)
_SHORT_TO_CANONICAL: dict[str, str] = {
    "cabo pulmo": "Cabo Pulmo National Park",
    "shark bay": "Shark Bay World Heritage Area",
    "ningaloo": "Ningaloo Coast World Heritage Area",
    "ningaloo coast": "Ningaloo Coast World Heritage Area",
    "belize": "Belize Barrier Reef Reserve System",
    "belize barrier": "Belize Barrier Reef Reserve System",
    "belize barrier reef": "Belize Barrier Reef Reserve System",
    "galapagos": "Galapagos Marine Reserve",
    "galapagos marine": "Galapagos Marine Reserve",
    "raja ampat": "Raja Ampat Marine Park",
    "sundarbans": "Sundarbans Reserve Forest",
    "sundarbans reserve": "Sundarbans Reserve Forest",
    "aldabra": "Aldabra Atoll",
    "aldabra atoll": "Aldabra Atoll",
    "cispata": "Cispata Bay Mangrove Conservation Area",
    "cispata bay": "Cispata Bay Mangrove Conservation Area",
    "cispatá": "Cispata Bay Mangrove Conservation Area",
    "cispatá bay": "Cispata Bay Mangrove Conservation Area",
}

# SSP pattern: "SSP1-2.6", "ssp 2 4.5", "ssp2-4.5", etc.
_SSP_RE = re.compile(r"ssp\s*([125])[-\s\.]*([0-9]+\.?[0-9]*)", re.IGNORECASE)

# Valid SSP label normalization map
_SSP_NORMALIZE: dict[str, str] = {
    "1-2.6": "SSP1-2.6",
    "1-26": "SSP1-2.6",
    "2-4.5": "SSP2-4.5",
    "2-45": "SSP2-4.5",
    "5-8.5": "SSP5-8.5",
    "5-85": "SSP5-8.5",
}

# Time horizon: "by 2050", "in 2100", "over 30 years", "for 10 years"
_YEAR_RE = re.compile(r"\b(?:by|in|over|for)\s+(\d{4})\b", re.IGNORECASE)
_YEARS_RE = re.compile(r"\b(?:over|for)\s+(\d+)\s*years?\b", re.IGNORECASE)

# Scenario type inference patterns (ordered by specificity)
_SCENARIO_TYPE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("counterfactual", re.compile(
        r"without\s+protection|counterfactual|if\s+not\s+protected"
        r"|without\s+\w+\s+protection|never\s+protected|had\s+not\s+been\s+protected"
        r"|before\s+protection|unprotected",
        re.IGNORECASE,
    )),
    ("climate", re.compile(
        r"ssp[125]|warming|climate\s+change|bleach|sea\s+level"
        r"|temperature\s+rise|ocean\s+acid",
        re.IGNORECASE,
    )),
    ("intervention", re.compile(
        r"\binvest|restore|restoration|plant|replant|expand\s+mpa"
        r"|increase\s+protection",
        re.IGNORECASE,
    )),
    ("market", re.compile(
        r"carbon\s+price|credit\s+price|carbon\s+market|blue\s+carbon\s+revenue"
        r"|carbon\s+credit|price\s+per\s+t",
        re.IGNORECASE,
    )),
    ("portfolio", re.compile(
        r"portfolio|all\s+sites|across\s+sites|combined|nature\s+var"
        r"|stress\s+test",
        re.IGNORECASE,
    )),
    ("tipping_point", re.compile(
        r"tipping\s+point|regime\s+shift|collapse|threshold|how\s+close"
        r"|how\s+far",
        re.IGNORECASE,
    )),
]


def _resolve_site(text: str, explicit_site: str | None = None) -> list[str]:
    """Resolve site names from question text and/or explicit site parameter."""
    sites: list[str] = []

    if explicit_site:
        # Check alias map first
        canonical = _SHORT_TO_CANONICAL.get(explicit_site.lower())
        if canonical:
            sites.append(canonical)
        else:
            sites.append(explicit_site)

    # Also scan question text for additional site mentions
    q_lower = text.lower()
    for alias in sorted(_SHORT_TO_CANONICAL, key=len, reverse=True):
        if alias in q_lower:
            canonical = _SHORT_TO_CANONICAL[alias]
            if canonical not in sites:
                sites.append(canonical)

    return sites


def _extract_ssp(text: str) -> str | None:
    """Extract and normalize SSP scenario label from text."""
    m = _SSP_RE.search(text)
    if not m:
        return None
    group_num = m.group(1)
    group_sub = m.group(2)
    raw_key = f"{group_num}-{group_sub}"
    normalized = _SSP_NORMALIZE.get(raw_key)
    if normalized:
        return normalized
    # Try without decimal
    raw_key_nodot = f"{group_num}-{group_sub.replace('.', '')}"
    return _SSP_NORMALIZE.get(raw_key_nodot)


def _extract_target_year(text: str) -> int | None:
    """Extract target year from text (e.g. 'by 2050')."""
    m = _YEAR_RE.search(text)
    if m:
        year = int(m.group(1))
        if 2025 <= year <= 2200:
            return year
    return None


def _extract_time_horizon_years(text: str) -> int | None:
    """Extract time horizon in years (e.g. 'over 30 years')."""
    m = _YEARS_RE.search(text)
    if m:
        years = int(m.group(1))
        if 1 <= years <= 200:
            return years
    return None


def _infer_scenario_type(text: str) -> str:
    """Infer scenario type from question keywords."""
    for scenario_type, pattern in _SCENARIO_TYPE_PATTERNS:
        if pattern.search(text):
            return scenario_type
    return "counterfactual"


def _extract_assumptions(text: str) -> dict[str, Any]:
    """Extract scenario-specific assumptions from the question text."""
    assumptions: dict[str, Any] = {}

    # Carbon price extraction: "$45/tCO2", "at $45", "$45 per ton"
    price_match = re.search(
        r"\$(\d+(?:\.\d+)?)\s*(?:/\s*t(?:co2e?)?|per\s+t)", text, re.IGNORECASE
    )
    if price_match:
        assumptions["carbon_price_usd"] = float(price_match.group(1))

    # Investment amount: "invest $5M", "invest $50 million"
    invest_match = re.search(
        r"invest\s+\$(\d+(?:\.\d+)?)\s*([mMbB](?:illion)?)?", text, re.IGNORECASE
    )
    if invest_match:
        amount = float(invest_match.group(1))
        unit = (invest_match.group(2) or "").lower()
        if unit.startswith("b"):
            amount *= 1_000_000_000
        elif unit.startswith("m"):
            amount *= 1_000_000
        assumptions["investment_usd"] = amount

    return assumptions


def parse_scenario_request(
    question: str,
    site: str | None = None,
    classification: dict | None = None,
) -> ScenarioRequest:
    """Parse a natural-language scenario question into a structured request.

    Pattern-based extraction that works without LLM in demo mode.

    Args:
        question: The user's scenario question.
        site: Optional explicit site from prior classification.
        classification: Optional classification dict with metadata.

    Returns:
        A ScenarioRequest with extracted parameters.
    """
    site_scope = _resolve_site(question, site)
    ssp = _extract_ssp(question)
    target_year = _extract_target_year(question)
    time_horizon_years = _extract_time_horizon_years(question)
    scenario_type = _infer_scenario_type(question)
    assumptions = _extract_assumptions(question)

    # If SSP is detected but type wasn't explicitly climate, override
    if ssp and scenario_type not in ("climate",):
        scenario_type = "climate"

    # Compute time_horizon_years from target_year if not explicitly given
    if target_year and not time_horizon_years:
        time_horizon_years = max(1, target_year - 2025)
    elif not time_horizon_years:
        time_horizon_years = 10

    return ScenarioRequest(
        scenario_type=scenario_type,
        site_scope=site_scope,
        time_horizon_years=time_horizon_years,
        assumptions=assumptions,
        compare_against="baseline",
        ssp_scenario=ssp,
        target_year=target_year,
    )
