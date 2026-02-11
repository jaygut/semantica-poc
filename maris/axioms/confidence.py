"""Confidence interval propagation and response-level confidence scoring."""

import math


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


def calculate_response_confidence(graph_nodes: list[dict]) -> float:
    """Calculate overall response confidence as the minimum across all cited nodes.

    Each node dict may have a 'confidence' or 'source_tier' field.
    Tier-based confidence: T1=0.95, T2=0.80, T3=0.65, T4=0.50.
    """
    tier_confidence = {"T1": 0.95, "T2": 0.80, "T3": 0.65, "T4": 0.50}

    if not graph_nodes:
        return 0.0

    confidences = []
    for node in graph_nodes:
        c = node.get("confidence")
        if c is not None:
            confidences.append(float(c))
        else:
            tier = node.get("source_tier") or node.get("tier", "T4")
            confidences.append(tier_confidence.get(tier, 0.50))

    return min(confidences) if confidences else 0.0
