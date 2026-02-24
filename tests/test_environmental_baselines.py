"""Unit tests for maris/scenario/environmental_baselines.py.

Covers:
  - extract_sst_baseline() with list-format bins
  - extract_sst_baseline() with dict-format bins
  - extract_sst_baseline() with empty/missing data
  - compute_warming_impact() exceeding bleaching threshold
  - compute_warming_impact() below bleaching threshold
  - _parse_distribution_bins() with various formats
"""

from __future__ import annotations

import pytest

from maris.scenario.environmental_baselines import (
    CORAL_BLEACHING_THRESHOLD_C,
    _parse_distribution_bins,
    compute_warming_impact,
    extract_sst_baseline,
)


# ---------------------------------------------------------------------------
# extract_sst_baseline - list format bins
# ---------------------------------------------------------------------------

class TestExtractSstBaselineListFormat:
    """Tests for extract_sst_baseline with list-of-dicts bin format."""

    def test_basic_list_bins(self) -> None:
        env_stats = {
            "sst": [
                {"bin": 24.0, "count": 100},
                {"bin": 25.0, "count": 200},
                {"bin": 26.0, "count": 300},
                {"bin": 27.0, "count": 250},
                {"bin": 28.0, "count": 150},
            ],
        }
        result = extract_sst_baseline(env_stats)
        assert result["median_sst_c"] is not None
        assert result["mean_sst_c"] is not None
        assert result["n_records"] == 1000
        assert result["sst_range_c"] == (24.0, 28.0)
        assert result["source"] == "OBIS environmental statistics"

    def test_median_calculation(self) -> None:
        """Median should be the bin where cumulative count crosses 50%."""
        env_stats = {
            "sst": [
                {"bin": 20.0, "count": 10},
                {"bin": 25.0, "count": 10},
                {"bin": 30.0, "count": 80},
            ],
        }
        result = extract_sst_baseline(env_stats)
        # 50% of 100 = 50. Cumulative: 10, 20, 100 - crosses at bin 30.0
        assert result["median_sst_c"] == 30.0

    def test_mean_calculation(self) -> None:
        """Mean should be weighted average of bin * count."""
        env_stats = {
            "sst": [
                {"bin": 20.0, "count": 50},
                {"bin": 30.0, "count": 50},
            ],
        }
        result = extract_sst_baseline(env_stats)
        assert result["mean_sst_c"] == 25.0

    def test_bleaching_proximity(self) -> None:
        """Bleaching proximity should be threshold minus median."""
        env_stats = {
            "sst": [
                {"bin": 27.0, "count": 100},
            ],
        }
        result = extract_sst_baseline(env_stats)
        assert result["bleaching_proximity_c"] == pytest.approx(
            CORAL_BLEACHING_THRESHOLD_C - 27.0, abs=0.01,
        )


# ---------------------------------------------------------------------------
# extract_sst_baseline - dict format bins
# ---------------------------------------------------------------------------

class TestExtractSstBaselineDictFormat:
    """Tests for extract_sst_baseline with dict (numeric keys) bin format."""

    def test_dict_numeric_keys(self) -> None:
        env_stats = {
            "sst": {
                "22": 50,
                "24": 100,
                "26": 200,
                "28": 100,
            },
        }
        result = extract_sst_baseline(env_stats)
        assert result["median_sst_c"] is not None
        assert result["mean_sst_c"] is not None
        assert result["n_records"] == 450
        assert result["sst_range_c"] == (22.0, 28.0)

    def test_nested_bins_key(self) -> None:
        env_stats = {
            "sst": {
                "bins": [
                    {"bin": 25.0, "count": 100},
                    {"bin": 26.0, "count": 200},
                ],
            },
        }
        result = extract_sst_baseline(env_stats)
        assert result["n_records"] == 300
        assert result["sst_range_c"] == (25.0, 26.0)


# ---------------------------------------------------------------------------
# extract_sst_baseline - empty/missing data
# ---------------------------------------------------------------------------

class TestExtractSstBaselineEmpty:
    """Tests for extract_sst_baseline with missing or empty data."""

    def test_empty_dict(self) -> None:
        result = extract_sst_baseline({})
        assert result["median_sst_c"] is None
        assert result["mean_sst_c"] is None
        assert result["n_records"] == 0
        assert result["bleaching_proximity_c"] is None

    def test_empty_sst_key(self) -> None:
        result = extract_sst_baseline({"sst": {}})
        assert result["median_sst_c"] is None
        assert result["n_records"] == 0

    def test_none_sst_value(self) -> None:
        result = extract_sst_baseline({"sst": None})
        assert result["median_sst_c"] is None

    def test_zero_count_bins(self) -> None:
        env_stats = {
            "sst": [
                {"bin": 25.0, "count": 0},
                {"bin": 26.0, "count": 0},
            ],
        }
        result = extract_sst_baseline(env_stats)
        assert result["median_sst_c"] is None
        assert result["n_records"] == 0

    def test_temperature_alias_key(self) -> None:
        """Should also accept 'temperature' as key name."""
        env_stats = {
            "temperature": [
                {"bin": 26.0, "count": 100},
            ],
        }
        result = extract_sst_baseline(env_stats)
        assert result["median_sst_c"] == 26.0
        assert result["n_records"] == 100


# ---------------------------------------------------------------------------
# compute_warming_impact
# ---------------------------------------------------------------------------

class TestComputeWarmingImpact:
    """Tests for compute_warming_impact."""

    def test_exceeds_threshold(self) -> None:
        result = compute_warming_impact(27.5, 2.5, habitat="coral_reef")
        assert result["projected_sst_c"] == 30.0
        assert result["exceeds_bleaching_threshold"] is True
        assert result["margin_above_threshold_c"] == pytest.approx(1.0, abs=0.01)
        assert "Exceeds" in result["confidence_note"]

    def test_below_threshold(self) -> None:
        result = compute_warming_impact(25.0, 2.0, habitat="coral_reef")
        assert result["projected_sst_c"] == 27.0
        assert result["exceeds_bleaching_threshold"] is False
        assert result["margin_above_threshold_c"] == pytest.approx(-2.0, abs=0.01)
        assert "Remains" in result["confidence_note"]

    def test_exactly_at_threshold(self) -> None:
        result = compute_warming_impact(27.0, 2.0, habitat="coral_reef")
        assert result["projected_sst_c"] == 29.0
        # At exactly threshold, not exceeded
        assert result["exceeds_bleaching_threshold"] is False
        assert result["margin_above_threshold_c"] == 0.0

    def test_non_reef_habitat(self) -> None:
        """Non-reef habitats should not have bleaching threshold logic."""
        result = compute_warming_impact(25.0, 2.0, habitat="mangrove_forest")
        assert result["projected_sst_c"] == 27.0
        assert result["exceeds_bleaching_threshold"] is False
        assert result["margin_above_threshold_c"] is None

    def test_zero_warming(self) -> None:
        result = compute_warming_impact(26.0, 0.0, habitat="coral_reef")
        assert result["projected_sst_c"] == 26.0
        assert result["exceeds_bleaching_threshold"] is False


# ---------------------------------------------------------------------------
# _parse_distribution_bins
# ---------------------------------------------------------------------------

class TestParseDistributionBins:
    """Tests for _parse_distribution_bins with various input formats."""

    def test_list_of_dicts(self) -> None:
        data = [
            {"bin": 28.0, "count": 10},
            {"bin": 26.0, "count": 20},
            {"bin": 27.0, "count": 15},
        ]
        result = _parse_distribution_bins(data)
        assert len(result) == 3
        # Should be sorted by bin value
        assert result[0]["bin"] == 26.0
        assert result[1]["bin"] == 27.0
        assert result[2]["bin"] == 28.0

    def test_dict_with_numeric_keys(self) -> None:
        data = {"25": 100, "26": 200, "27": 150}
        result = _parse_distribution_bins(data)
        assert len(result) == 3
        assert result[0] == {"bin": 25.0, "count": 100}

    def test_dict_with_nested_bins(self) -> None:
        data = {
            "bins": [
                {"bin": 24.0, "count": 50},
                {"bin": 25.0, "count": 100},
            ],
        }
        result = _parse_distribution_bins(data)
        assert len(result) == 2

    def test_empty_list(self) -> None:
        assert _parse_distribution_bins([]) == []

    def test_empty_dict(self) -> None:
        assert _parse_distribution_bins({}) == []

    def test_non_dict_non_list(self) -> None:
        assert _parse_distribution_bins("not valid") == []
        assert _parse_distribution_bins(42) == []
        assert _parse_distribution_bins(None) == []

    def test_dict_with_non_numeric_keys_skipped(self) -> None:
        data = {"25": 100, "not_a_number": 50, "26": 200}
        result = _parse_distribution_bins(data)
        assert len(result) == 2

    def test_list_with_missing_count_defaults_zero(self) -> None:
        data = [{"bin": 25.0}]
        result = _parse_distribution_bins(data)
        assert len(result) == 1
        assert result[0]["count"] == 0
