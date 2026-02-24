"""Site observation quality scoring from OBIS QC statistics.

Computes a composite quality score (0-1) for each site based on:
- Record density (records normalized against portfolio)
- Dataset diversity (number of independent data sources)
- QC pass rate (fraction of records passing quality flags)
- Temporal coverage (monitoring year span)

The composite score adjusts confidence in site-level claims.
"""

from __future__ import annotations

import math
from typing import Any


# Weights must sum to 1.0
QUALITY_WEIGHTS = {
    "record_density": 0.25,
    "dataset_diversity": 0.25,
    "qc_pass_rate": 0.30,
    "temporal_coverage": 0.20,
}


def compute_observation_quality(
    statistics: dict[str, Any],
    qc_statistics: dict[str, Any],
    portfolio_max_records: int = 10_000,
) -> dict[str, Any]:
    """Compute site observation quality from OBIS statistics.

    Args:
        statistics: OBIS /statistics response (records, species, datasets,
            yearmin, yearmax).
        qc_statistics: OBIS /statistics/qc response (on_land, no_depth, etc.).
        portfolio_max_records: Normalization reference for record density.

    Returns dict with:
        record_density_score (0-1): log-scaled records / portfolio max
        dataset_diversity_score (0-1): log-scaled dataset count
        qc_pass_rate (0-1): fraction of records without QC flags
        temporal_coverage_score (0-1): year range / expected span (30 years)
        composite_quality_score (0-1): weighted mean of factors
        explanation: human-readable summary
    """
    total_records = int(statistics.get("records", 0))
    dataset_count = int(statistics.get("datasets", 0))
    year_min = statistics.get("yearmin")
    year_max = statistics.get("yearmax")

    # 1. Record density (log-scaled, capped at 1.0)
    if total_records > 0 and portfolio_max_records > 0:
        record_density_score = min(
            1.0, math.log1p(total_records) / math.log1p(portfolio_max_records)
        )
    else:
        record_density_score = 0.0

    # 2. Dataset diversity (log-scaled: 1 dataset ~ 0.3, 10+ ~ 0.9, 30+ = 1.0)
    if dataset_count > 0:
        dataset_diversity_score = min(
            1.0, math.log1p(dataset_count) / math.log1p(30)
        )
    else:
        dataset_diversity_score = 0.0

    # 3. QC pass rate
    total_qc = int(qc_statistics.get("total", total_records))
    flagged = 0
    for flag_key in ("on_land", "no_depth", "no_match", "shoredistance"):
        flagged += int(qc_statistics.get(flag_key, 0))
    if total_qc > 0:
        qc_pass_rate = max(0.0, 1.0 - (flagged / total_qc))
    else:
        qc_pass_rate = 0.5  # Unknown QC = moderate confidence

    # 4. Temporal coverage (year range / expected 30-year span)
    expected_span = 30
    if year_min and year_max:
        actual_span = int(year_max) - int(year_min)
        temporal_coverage_score = min(1.0, max(0.0, actual_span / expected_span))
    else:
        temporal_coverage_score = 0.0

    # 5. Composite (weighted mean)
    composite = (
        QUALITY_WEIGHTS["record_density"] * record_density_score
        + QUALITY_WEIGHTS["dataset_diversity"] * dataset_diversity_score
        + QUALITY_WEIGHTS["qc_pass_rate"] * qc_pass_rate
        + QUALITY_WEIGHTS["temporal_coverage"] * temporal_coverage_score
    )
    composite = round(max(0.0, min(1.0, composite)), 4)

    # Explanation
    parts = []
    if total_records:
        parts.append(f"{total_records:,} OBIS records")
    if dataset_count:
        parts.append(f"{dataset_count} datasets")
    if year_min and year_max:
        parts.append(f"monitoring {year_min}-{year_max}")
    parts.append(f"QC pass rate {qc_pass_rate:.0%}")

    return {
        "record_density_score": round(record_density_score, 4),
        "dataset_diversity_score": round(dataset_diversity_score, 4),
        "qc_pass_rate": round(qc_pass_rate, 4),
        "temporal_coverage_score": round(temporal_coverage_score, 4),
        "composite_quality_score": composite,
        "total_records": total_records,
        "dataset_count": dataset_count,
        "year_range": (int(year_min), int(year_max)) if year_min and year_max else None,
        "explanation": "; ".join(parts),
    }
