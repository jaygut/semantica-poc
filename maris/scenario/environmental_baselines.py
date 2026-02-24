"""Environmental baselines from OBIS observation data.

Extracts SST (sea surface temperature) and other environmental statistics
from OBIS distribution bins, providing empirical anchors for climate
scenario projections.

These baselines enrich scenario outputs with observed conditions but
do NOT alter the core SSP degradation calculations, which are based on
IPCC AR6 WG2 Ch.3 literature anchors.
"""

from __future__ import annotations

from typing import Any


# Coral bleaching threshold (MMM + 1C, NOAA Coral Reef Watch standard)
# Source: doi:10.1007/s00338-018-1755-4 (Skirving et al. 2019)
CORAL_BLEACHING_THRESHOLD_C = 29.0


def extract_sst_baseline(env_stats: dict[str, Any]) -> dict[str, Any]:
    """Extract SST baseline from OBIS environmental statistics.

    The OBIS /statistics/env endpoint returns distribution bins for
    temperature. This function computes summary statistics.

    Args:
        env_stats: Raw response from OBIS /statistics/env.
                   Expected to have a "sst" key with distribution bins.

    Returns dict with:
        median_sst_c: Median SST from distribution (float or None)
        mean_sst_c: Mean SST (float or None)
        sst_range_c: (min, max) observed range (tuple or None)
        n_records: Number of records with SST data
        bleaching_proximity_c: Distance from median to bleaching threshold
        source: "OBIS environmental statistics"
    """
    sst_data = env_stats.get("sst") or env_stats.get("temperature") or {}

    if not sst_data:
        return {
            "median_sst_c": None,
            "mean_sst_c": None,
            "sst_range_c": None,
            "n_records": 0,
            "bleaching_proximity_c": None,
            "source": "OBIS environmental statistics",
        }

    # OBIS returns distribution bins: list of {"bin": float, "count": int}
    # or sometimes as a dict with bin edges
    bins = _parse_distribution_bins(sst_data)

    if not bins:
        return {
            "median_sst_c": None,
            "mean_sst_c": None,
            "sst_range_c": None,
            "n_records": 0,
            "bleaching_proximity_c": None,
            "source": "OBIS environmental statistics",
        }

    # Compute statistics from bins
    total_count = sum(b["count"] for b in bins)
    if total_count == 0:
        return {
            "median_sst_c": None,
            "mean_sst_c": None,
            "sst_range_c": None,
            "n_records": 0,
            "bleaching_proximity_c": None,
            "source": "OBIS environmental statistics",
        }

    # Mean
    weighted_sum = sum(b["bin"] * b["count"] for b in bins)
    mean_sst = round(weighted_sum / total_count, 2)

    # Median (find bin where cumulative count crosses 50%)
    cumulative = 0
    median_sst = bins[len(bins) // 2]["bin"]  # fallback
    for b in bins:
        cumulative += b["count"]
        if cumulative >= total_count / 2:
            median_sst = round(b["bin"], 2)
            break

    # Range
    valid_bins = [b for b in bins if b["count"] > 0]
    sst_range = (
        round(valid_bins[0]["bin"], 2),
        round(valid_bins[-1]["bin"], 2),
    ) if valid_bins else None

    # Bleaching proximity
    bleaching_proximity = round(CORAL_BLEACHING_THRESHOLD_C - median_sst, 2)

    return {
        "median_sst_c": median_sst,
        "mean_sst_c": mean_sst,
        "sst_range_c": sst_range,
        "n_records": total_count,
        "bleaching_proximity_c": bleaching_proximity,
        "source": "OBIS environmental statistics",
    }


def compute_warming_impact(
    baseline_sst_c: float,
    warming_c: float,
    habitat: str = "coral_reef",
) -> dict[str, Any]:
    """Compute climate warming impact relative to observed baseline.

    Informational only - does NOT replace SSP degradation calculations.

    Args:
        baseline_sst_c: Observed median SST (from extract_sst_baseline)
        warming_c: Projected warming under SSP scenario (from SSP_SCENARIOS)
        habitat: Habitat type for threshold selection

    Returns dict with:
        projected_sst_c: baseline + warming
        exceeds_bleaching_threshold: bool (coral reef only)
        margin_above_threshold_c: how far above threshold (negative = still below)
        confidence_note: explanation of estimate basis
    """
    projected = round(baseline_sst_c + warming_c, 2)

    exceeds_threshold = False
    margin = None

    if habitat == "coral_reef":
        margin = round(projected - CORAL_BLEACHING_THRESHOLD_C, 2)
        exceeds_threshold = projected > CORAL_BLEACHING_THRESHOLD_C

    confidence_note = (
        f"Baseline SST {baseline_sst_c}C + {warming_c}C warming = {projected}C projected. "
    )
    if exceeds_threshold:
        confidence_note += (
            f"Exceeds coral bleaching threshold ({CORAL_BLEACHING_THRESHOLD_C}C) "
            f"by {margin}C."
        )
    elif margin is not None:
        confidence_note += (
            f"Remains {abs(margin)}C below coral bleaching threshold "
            f"({CORAL_BLEACHING_THRESHOLD_C}C)."
        )

    return {
        "projected_sst_c": projected,
        "exceeds_bleaching_threshold": exceeds_threshold,
        "margin_above_threshold_c": margin,
        "confidence_note": confidence_note,
    }


def _parse_distribution_bins(sst_data: Any) -> list[dict[str, Any]]:
    """Parse OBIS SST distribution bins from various response formats.

    OBIS may return bins as:
    1. List of {"bin": float, "count": int}
    2. Dict with numeric keys {"20": count, "21": count, ...}
    3. Nested structure with "bins" key
    """
    if isinstance(sst_data, list):
        result = []
        for item in sst_data:
            if isinstance(item, dict) and "bin" in item:
                result.append({
                    "bin": float(item["bin"]),
                    "count": int(item.get("count", 0)),
                })
        return sorted(result, key=lambda x: x["bin"])

    if isinstance(sst_data, dict):
        # Check for nested bins
        if "bins" in sst_data:
            return _parse_distribution_bins(sst_data["bins"])

        # Try numeric keys
        result = []
        for key, value in sst_data.items():
            try:
                bin_val = float(key)
                count = int(value) if isinstance(value, (int, float)) else 0
                result.append({"bin": bin_val, "count": count})
            except (ValueError, TypeError):
                continue
        return sorted(result, key=lambda x: x["bin"])

    return []
