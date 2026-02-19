"""Confidence interval propagation and response-level confidence scoring.

Implements a composite confidence model inspired by:
- GRADE framework (Cochrane): 4-level evidence certainty based on study quality,
  consistency, directness, precision, and publication bias
- IPCC likelihood scale: calibrated probability expressions with transparent
  decomposition of confidence factors
- Knowledge graph confidence propagation: multiplicative path-length discounting
  for multi-hop inference chains

The composite confidence score is:
    base_tier * path_discount * staleness_discount * sample_factor

Each factor is independently auditable and displayed as a breakdown.
"""

import math
from datetime import datetime

# Base confidence by evidence tier (GRADE-inspired)
TIER_CONFIDENCE = {"T1": 0.95, "T2": 0.80, "T3": 0.65, "T4": 0.50}

# Configurable discount parameters
PATH_DISCOUNT_PER_HOP = 0.05      # -5% per hop from source
STALENESS_THRESHOLD_YEARS = 5     # No discount for data <= 5 years old
STALENESS_DISCOUNT_PER_YEAR = 0.02  # -2% per year beyond threshold
CURRENT_YEAR = datetime.now().year


def propagate_ci(values: list[dict]) -> dict:
    """Combine confidence intervals from multiple sources.

    Each value dict has: value, ci_low, ci_high.
    Assumes independent sources - uses root-sum-of-squares for CI widths.
    """
    if not values:
        return {"total": 0.0, "ci_low": 0.0, "ci_high": 0.0}

    total = 0.0
    sum_sq_low = 0.0
    sum_sq_high = 0.0

    for v in values:
        val = float(v.get("value", 0))
        lo = float(v.get("ci_low", val))
        hi = float(v.get("ci_high", val))

        total += val
        sum_sq_low += (val - lo) ** 2
        sum_sq_high += (hi - val) ** 2

    combined_low = total - math.sqrt(sum_sq_low)
    combined_high = total + math.sqrt(sum_sq_high)

    return {
        "total": total,
        "ci_low": combined_low,
        "ci_high": combined_high,
    }


def propagate_ci_multiplicative(values: list[dict]) -> dict:
    """Multiplicative CI propagation for chained axiom evaluations.

    When axioms are applied in sequence (e.g., biomass -> tourism -> revenue),
    confidence intervals compound multiplicatively. Each step's relative
    uncertainty is combined: relative_ci = sqrt(sum(relative_ci_i^2)).
    """
    if not values:
        return {"total": 0.0, "ci_low": 0.0, "ci_high": 0.0}

    product = 1.0
    sum_sq_rel_low = 0.0
    sum_sq_rel_high = 0.0

    for v in values:
        val = float(v.get("value", 0))
        lo = float(v.get("ci_low", val))
        hi = float(v.get("ci_high", val))

        if val == 0:
            continue

        product *= val
        rel_low = (val - lo) / abs(val)
        rel_high = (hi - val) / abs(val)
        sum_sq_rel_low += rel_low ** 2
        sum_sq_rel_high += rel_high ** 2

    combined_rel_low = math.sqrt(sum_sq_rel_low)
    combined_rel_high = math.sqrt(sum_sq_rel_high)

    return {
        "total": product,
        "ci_low": product * (1 - combined_rel_low),
        "ci_high": product * (1 + combined_rel_high),
    }


def _tier_base_confidence(graph_nodes: list[dict]) -> float:
    """Calculate tier-based confidence as weighted mean of source quality.

    Multiple independent sources corroborate a claim - more high-quality
    evidence should increase confidence, not decrease it. Uses the mean
    of individual tier confidences so that the score reflects average
    evidence quality. The separate sample_factor handles the "more sources
    = more confidence" dimension.

    Tier resolution: nodes without an explicit tier default to T4 (0.50)
    to avoid overstating certainty when provenance metadata is incomplete.
    """
    if not graph_nodes:
        return 0.0

    confidences = []
    for node in graph_nodes:
        c = node.get("confidence")
        if c is not None:
            confidences.append(float(c))
        else:
            tier = node.get("source_tier") or node.get("tier")
            if tier is None:
                confidences.append(TIER_CONFIDENCE["T4"])
            else:
                confidences.append(TIER_CONFIDENCE.get(tier, 0.50))

    if not confidences:
        return 0.0

    return sum(confidences) / len(confidences)


def _path_discount(n_hops: int) -> float:
    """Apply path-length discount: -5% per hop from source data.

    A direct citation (0 hops) has no discount. Each intermediate inference
    step reduces confidence.
    """
    if n_hops <= 0:
        return 1.0
    discount = 1.0 - (PATH_DISCOUNT_PER_HOP * n_hops)
    return max(0.1, discount)


def _staleness_discount(
    data_years: list[int | None],
    current_year: int | None = None,
) -> float:
    """Apply data staleness discount: -2% per year beyond threshold.

    Uses the median data year to determine discount. This prevents a single
    old foundational paper from tanking the score when most evidence is
    recent. Data <= 5 years old gets no discount.
    """
    ref_year = current_year or CURRENT_YEAR
    valid_years = sorted(y for y in data_years if y is not None and y > 0)

    if not valid_years:
        return 0.85  # No year info: assume moderate staleness

    # Use median year instead of oldest - reflects typical evidence freshness
    mid = len(valid_years) // 2
    if len(valid_years) % 2 == 0:
        median_year = (valid_years[mid - 1] + valid_years[mid]) // 2
    else:
        median_year = valid_years[mid]

    age = ref_year - median_year

    if age <= STALENESS_THRESHOLD_YEARS:
        return 1.0

    excess_years = age - STALENESS_THRESHOLD_YEARS
    discount = 1.0 - (STALENESS_DISCOUNT_PER_YEAR * excess_years)
    return max(0.3, discount)


def _sample_size_factor(n_sources: int) -> float:
    """Confidence factor based on number of supporting sources.

    Ramps linearly from 0.6 (single source) to 1.0 (4+ sources).
    A single peer-reviewed source still carries meaningful weight;
    additional sources provide incremental corroboration up to a
    saturation point at 4 independent sources.
    """
    if n_sources <= 0:
        return 0.0
    if n_sources >= 4:
        return 1.0
    # Linear ramp: 1 -> 0.6, 2 -> 0.73, 3 -> 0.87, 4 -> 1.0
    return 0.6 + 0.4 * (n_sources - 1) / 3


def calculate_response_confidence(
    graph_nodes: list[dict],
    n_hops: int = 1,
    current_year: int | None = None,
    provenance_certificate: dict | None = None,
    provenance_summary: dict | None = None,
) -> dict:
    """Calculate composite response confidence with full breakdown.

    Returns a dict with composite score and individual factor values, following
    the IPCC/GRADE model of transparent uncertainty decomposition.

    Parameters
    ----------
    graph_nodes : list[dict]
        Evidence nodes from the graph. Each should have 'confidence' or
        'source_tier', and optionally 'year' or 'doi'.
    n_hops : int
        Number of inference hops from raw data to the answer.
    current_year : int | None
        Override for current year (for testing).

    Returns
    -------
    dict with keys:
        composite, tier_base, path_discount, staleness_discount,
        sample_factor, evidence_quality_factor, citation_coverage_factor,
        completeness_factor, explanation
    """
    if not graph_nodes:
        return {
            "composite": 0.0,
            "tier_base": 0.0,
            "path_discount": 1.0,
            "staleness_discount": 1.0,
            "sample_factor": 0.0,
            "evidence_quality_factor": 0.0,
            "citation_coverage_factor": 0.0,
            "completeness_factor": 0.0,
            "explanation": "No evidence sources available",
        }

    tier_base = _tier_base_confidence(graph_nodes)
    path_disc = _path_discount(n_hops)

    data_years = [
        node.get("year") or node.get("measurement_year")
        for node in graph_nodes
    ]
    stale_disc = _staleness_discount(data_years, current_year)

    n_sources = len(set(
        node.get("doi", f"unknown-{i}")
        for i, node in enumerate(graph_nodes)
        if node.get("doi")
    )) or len(graph_nodes)
    sample_f = _sample_size_factor(n_sources)

    total_nodes = len(graph_nodes)
    known_tier_nodes = sum(
        1
        for node in graph_nodes
        if (node.get("source_tier") or node.get("tier")) in TIER_CONFIDENCE
    )
    evidence_quality_factor = known_tier_nodes / total_nodes if total_nodes else 0.0

    doi_nodes = sum(1 for node in graph_nodes if node.get("doi"))
    citation_coverage = doi_nodes / total_nodes if total_nodes else 0.0
    citation_coverage_factor = 0.4 + 0.6 * citation_coverage if total_nodes else 0.0

    completeness_scores: list[float] = []
    for node in graph_nodes:
        has_doi = 1.0 if node.get("doi") else 0.0
        year = node.get("year") or node.get("measurement_year")
        has_year = 1.0 if isinstance(year, int) and year > 0 else 0.0
        has_tier = 1.0 if (node.get("source_tier") or node.get("tier")) in TIER_CONFIDENCE else 0.0
        completeness_scores.append((has_doi + has_year + has_tier) / 3)
    completeness_factor = (
        sum(completeness_scores) / len(completeness_scores)
        if completeness_scores
        else 0.0
    )

    composite = (
        tier_base
        * path_disc
        * stale_disc
        * sample_f
        * evidence_quality_factor
        * citation_coverage_factor
        * completeness_factor
    )

    if provenance_summary is not None:
        evidence_count = int(provenance_summary.get("evidence_count", 0) or 0)
        doi_citation_count = int(provenance_summary.get("doi_citation_count", 0) or 0)
        has_numeric_claims = bool(provenance_summary.get("has_numeric_claims", False))
        if evidence_count == 0:
            composite = min(composite, 0.25)
        elif doi_citation_count == 0 and has_numeric_claims:
            composite = min(composite, 0.35)

    composite = max(0.0, min(1.0, composite))

    # Build human-readable explanation
    explanation_parts = []
    if tier_base >= 0.9:
        explanation_parts.append("High-quality peer-reviewed sources")
    elif tier_base >= 0.7:
        explanation_parts.append("Good quality sources with some institutional reports")
    else:
        explanation_parts.append("Mixed or lower-tier evidence sources")

    if path_disc < 0.9:
        explanation_parts.append(
            f"{n_hops}-hop inference chain reduces confidence"
        )

    valid_years = sorted(y for y in data_years if y and y > 0)
    if valid_years:
        mid = len(valid_years) // 2
        median_yr = valid_years[mid]
        ref = current_year or CURRENT_YEAR
        age = ref - median_yr
        if age > STALENESS_THRESHOLD_YEARS:
            explanation_parts.append(
                f"median data year is {median_yr} ({age} years old)"
            )

    if n_sources == 1:
        explanation_parts.append("single supporting source")
    elif n_sources <= 3:
        explanation_parts.append(f"{n_sources} supporting sources")

    if evidence_quality_factor < 1.0:
        explanation_parts.append("incomplete tier metadata reduced confidence")

    if citation_coverage < 1.0:
        explanation_parts.append(
            f"DOI citation coverage {int(citation_coverage * 100)}%"
        )

    if completeness_factor < 1.0:
        explanation_parts.append(
            f"evidence completeness {int(completeness_factor * 100)}%"
        )

    if provenance_summary is not None:
        if int(provenance_summary.get("evidence_count", 0) or 0) == 0:
            explanation_parts.append("confidence capped: no evidence items")
        elif (
            int(provenance_summary.get("doi_citation_count", 0) or 0) == 0
            and provenance_summary.get("has_numeric_claims")
        ):
            explanation_parts.append("confidence capped: numeric claims without DOI citations")

    result = {
        "composite": round(composite, 4),
        "tier_base": round(tier_base, 4),
        "path_discount": round(path_disc, 4),
        "staleness_discount": round(stale_disc, 4),
        "sample_factor": round(sample_f, 4),
        "evidence_quality_factor": round(evidence_quality_factor, 4),
        "citation_coverage_factor": round(citation_coverage_factor, 4),
        "completeness_factor": round(completeness_factor, 4),
        "explanation": "; ".join(explanation_parts) if explanation_parts else "Standard confidence",
    }

    # Attach provenance metadata if certificate provided
    if provenance_certificate is not None:
        result["provenance_depth"] = provenance_certificate.get("lineage_depth", 0)
        result["provenance_checksum"] = provenance_certificate.get("checksum", "")
        result["provenance_dois"] = provenance_certificate.get("source_dois", [])

    return result
