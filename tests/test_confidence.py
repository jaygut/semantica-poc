"""Tests for confidence interval propagation and response confidence scoring."""

import pytest

from maris.axioms.confidence import (
    propagate_ci,
    calculate_response_confidence,
    _tier_base_confidence,
    _path_discount,
    _staleness_discount,
    _sample_size_factor,
    TIER_CONFIDENCE,
)


class TestPropagateCi:
    def test_single_value(self):
        values = [{"value": 100, "ci_low": 80, "ci_high": 120}]
        result = propagate_ci(values)
        assert result["total"] == 100
        assert result["ci_low"] == 80
        assert result["ci_high"] == 120

    def test_multiple_values(self):
        values = [
            {"value": 100, "ci_low": 80, "ci_high": 120},
            {"value": 200, "ci_low": 180, "ci_high": 220},
        ]
        result = propagate_ci(values)
        assert result["total"] == 300
        assert result["ci_low"] < 300
        assert result["ci_high"] > 300

    def test_empty_list(self):
        result = propagate_ci([])
        assert result["total"] == 0.0
        assert result["ci_low"] == 0.0
        assert result["ci_high"] == 0.0

    def test_zero_width_ci(self):
        values = [{"value": 50, "ci_low": 50, "ci_high": 50}]
        result = propagate_ci(values)
        assert result["total"] == 50
        assert result["ci_low"] == 50
        assert result["ci_high"] == 50

    def test_missing_ci_defaults_to_value(self):
        values = [{"value": 100}]
        result = propagate_ci(values)
        assert result["total"] == 100
        assert result["ci_low"] == 100
        assert result["ci_high"] == 100


class TestTierBaseConfidence:
    def test_t1_confidence(self):
        nodes = [{"source_tier": "T1"}]
        assert _tier_base_confidence(nodes) == 0.95

    def test_t2_confidence(self):
        nodes = [{"source_tier": "T2"}]
        assert _tier_base_confidence(nodes) == 0.80

    def test_t3_confidence(self):
        nodes = [{"source_tier": "T3"}]
        assert _tier_base_confidence(nodes) == 0.65

    def test_t4_confidence(self):
        nodes = [{"source_tier": "T4"}]
        assert _tier_base_confidence(nodes) == 0.50

    def test_unknown_tier_defaults_to_050(self):
        nodes = [{"source_tier": "TX"}]
        assert _tier_base_confidence(nodes) == 0.50

    def test_empty_returns_zero(self):
        assert _tier_base_confidence([]) == 0.0

    def test_explicit_confidence_used(self):
        nodes = [{"confidence": 0.72}]
        assert _tier_base_confidence(nodes) == 0.72

    def test_corroborating_evidence_uses_mean(self):
        """Two nodes should use mean of tier confidences."""
        nodes = [{"source_tier": "T1"}, {"source_tier": "T4"}]
        conf = _tier_base_confidence(nodes)
        assert conf == pytest.approx((0.95 + 0.50) / 2)

    def test_independent_evidence_uses_mean(self):
        """Two nodes with different DOIs should use mean."""
        nodes = [
            {"source_tier": "T1", "doi": "10.1234/a"},
            {"source_tier": "T2", "doi": "10.1234/b"},
        ]
        conf = _tier_base_confidence(nodes)
        assert conf == pytest.approx((0.95 + 0.80) / 2)


class TestPathDiscount:
    def test_zero_hops_no_discount(self):
        assert _path_discount(0) == 1.0

    def test_one_hop_five_percent(self):
        assert _path_discount(1) == 0.95

    def test_two_hops(self):
        assert _path_discount(2) == 0.90

    def test_minimum_floor(self):
        """Even many hops should not go below 0.1."""
        assert _path_discount(100) >= 0.1


class TestStalenessDiscount:
    def test_recent_data_no_discount(self):
        assert _staleness_discount([2025], current_year=2026) == 1.0

    def test_old_data_gets_discount(self):
        discount = _staleness_discount([2009], current_year=2026)
        assert discount < 1.0

    def test_no_year_info_moderate_discount(self):
        assert _staleness_discount([]) == 0.85

    def test_minimum_floor(self):
        assert _staleness_discount([1950], current_year=2026) >= 0.3


class TestSampleSizeFactor:
    def test_zero_sources(self):
        assert _sample_size_factor(0) == 0.0

    def test_one_source(self):
        assert _sample_size_factor(1) == 0.6

    def test_two_sources(self):
        f = _sample_size_factor(2)
        assert 0.73 < f < 0.74  # linear ramp: 0.6 + 0.4*(1/3)

    def test_ten_sources(self):
        f = _sample_size_factor(10)
        assert f > 0.6

    def test_monotonically_increasing_from_two(self):
        """From 2+ sources, factor increases monotonically."""
        factors = [_sample_size_factor(n) for n in range(2, 20)]
        for i in range(len(factors) - 1):
            assert factors[i] <= factors[i + 1]


class TestCompositeConfidence:
    def test_returns_dict_with_breakdown(self):
        nodes = [{"source_tier": "T1"}]
        result = calculate_response_confidence(nodes, n_hops=1, current_year=2026)
        assert "composite" in result
        assert "tier_base" in result
        assert "path_discount" in result
        assert "staleness_discount" in result
        assert "sample_factor" in result
        assert "explanation" in result

    def test_empty_list_returns_zero_composite(self):
        result = calculate_response_confidence([])
        assert result["composite"] == 0.0
        assert result["sample_factor"] == 0.0

    def test_composite_bounded_zero_to_one(self):
        nodes = [{"source_tier": "T1", "doi": "10.1234/a", "year": 2024}]
        result = calculate_response_confidence(nodes, n_hops=1, current_year=2026)
        assert 0.0 <= result["composite"] <= 1.0

    def test_high_quality_recent_data_high_composite(self):
        nodes = [
            {"source_tier": "T1", "doi": "10.1234/a", "year": 2024},
            {"source_tier": "T1", "doi": "10.1234/b", "year": 2025},
            {"source_tier": "T1", "doi": "10.1234/c", "year": 2023},
        ]
        result = calculate_response_confidence(nodes, n_hops=1, current_year=2026)
        assert result["composite"] > 0.2

    def test_explanation_nonempty(self):
        nodes = [{"source_tier": "T1"}]
        result = calculate_response_confidence(nodes, n_hops=1, current_year=2026)
        assert len(result["explanation"]) > 0

    def test_more_hops_lower_composite(self):
        nodes = [{"source_tier": "T1", "year": 2024}]
        r1 = calculate_response_confidence(nodes, n_hops=1, current_year=2026)
        r3 = calculate_response_confidence(nodes, n_hops=3, current_year=2026)
        assert r3["composite"] <= r1["composite"]
