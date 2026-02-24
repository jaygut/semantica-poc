"""Tests for site observation quality scoring (maris/sites/observation_quality.py)."""

from __future__ import annotations

import pytest

from maris.sites.observation_quality import (
    QUALITY_WEIGHTS,
    compute_observation_quality,
)


class TestComputeObservationQuality:
    """Tests for the composite observation quality scorer."""

    def test_full_data_produces_valid_composite(self):
        stats = {"records": 5000, "datasets": 15, "yearmin": 1990, "yearmax": 2024}
        qc = {"total": 5000, "on_land": 50, "no_depth": 100, "no_match": 30, "shoredistance": 20}
        result = compute_observation_quality(stats, qc)

        assert 0.0 <= result["composite_quality_score"] <= 1.0
        assert result["total_records"] == 5000
        assert result["dataset_count"] == 15
        assert result["year_range"] == (1990, 2024)
        assert result["explanation"]

    def test_empty_statistics_returns_zero_scores(self):
        result = compute_observation_quality({}, {})

        assert result["record_density_score"] == 0.0
        assert result["dataset_diversity_score"] == 0.0
        assert result["temporal_coverage_score"] == 0.0
        # QC pass rate defaults to 0.5 when unknown
        assert result["qc_pass_rate"] == 0.5
        assert result["total_records"] == 0
        assert result["dataset_count"] == 0
        assert result["year_range"] is None

    def test_high_qc_flags_gives_low_pass_rate(self):
        stats = {"records": 1000, "datasets": 5, "yearmin": 2010, "yearmax": 2020}
        qc = {"total": 1000, "on_land": 400, "no_depth": 300, "no_match": 200, "shoredistance": 50}
        result = compute_observation_quality(stats, qc)

        # 950 flagged out of 1000 -> pass rate 0.05
        assert result["qc_pass_rate"] == pytest.approx(0.05, abs=0.01)
        # Composite should be lower than with clean data
        assert result["composite_quality_score"] < 0.5

    def test_single_dataset_gives_low_diversity(self):
        stats = {"records": 100, "datasets": 1, "yearmin": 2020, "yearmax": 2022}
        qc = {"total": 100, "on_land": 0, "no_depth": 0, "no_match": 0, "shoredistance": 0}
        result = compute_observation_quality(stats, qc)

        # log1p(1) / log1p(30) ~ 0.2
        assert result["dataset_diversity_score"] < 0.3

    def test_composite_always_in_zero_one(self):
        """Composite stays bounded even with extreme inputs."""
        stats = {"records": 999_999_999, "datasets": 500, "yearmin": 1900, "yearmax": 2025}
        qc = {"total": 999_999_999, "on_land": 0, "no_depth": 0, "no_match": 0, "shoredistance": 0}
        result = compute_observation_quality(stats, qc)

        assert 0.0 <= result["composite_quality_score"] <= 1.0

    def test_weights_sum_to_one(self):
        total = sum(QUALITY_WEIGHTS.values())
        assert total == pytest.approx(1.0)

    def test_zero_records_zero_density(self):
        stats = {"records": 0, "datasets": 5, "yearmin": 2010, "yearmax": 2020}
        qc = {"total": 0}
        result = compute_observation_quality(stats, qc)

        assert result["record_density_score"] == 0.0

    def test_no_year_range_zero_temporal(self):
        stats = {"records": 100, "datasets": 5}
        qc = {"total": 100, "on_land": 0, "no_depth": 0, "no_match": 0, "shoredistance": 0}
        result = compute_observation_quality(stats, qc)

        assert result["temporal_coverage_score"] == 0.0
        assert result["year_range"] is None

    def test_thirty_year_span_gives_full_temporal(self):
        stats = {"records": 100, "datasets": 1, "yearmin": 1994, "yearmax": 2024}
        qc = {"total": 100}
        result = compute_observation_quality(stats, qc)

        assert result["temporal_coverage_score"] == 1.0

    def test_portfolio_max_records_scaling(self):
        stats = {"records": 10_000, "datasets": 10, "yearmin": 2000, "yearmax": 2020}
        qc = {"total": 10_000}

        r1 = compute_observation_quality(stats, qc, portfolio_max_records=10_000)
        r2 = compute_observation_quality(stats, qc, portfolio_max_records=100_000)

        # Same records, higher portfolio max -> lower density score
        assert r1["record_density_score"] >= r2["record_density_score"]

    def test_explanation_includes_record_count(self):
        stats = {"records": 42, "datasets": 3, "yearmin": 2015, "yearmax": 2023}
        qc = {"total": 42}
        result = compute_observation_quality(stats, qc)

        assert "42 OBIS records" in result["explanation"]
        assert "3 datasets" in result["explanation"]
        assert "monitoring 2015-2023" in result["explanation"]
