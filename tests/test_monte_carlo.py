"""Tests for Monte Carlo ESV simulation."""

import numpy as np
import pytest

from maris.axioms.monte_carlo import run_monte_carlo


class TestReproducibility:
    def test_same_seed_same_result(self):
        services = [{"value": 100, "ci_low": 80, "ci_high": 120}]
        r1 = run_monte_carlo(services, n_simulations=1000, seed=42)
        r2 = run_monte_carlo(services, n_simulations=1000, seed=42)
        assert r1["median"] == r2["median"]
        assert r1["mean"] == r2["mean"]
        assert r1["p5"] == r2["p5"]
        assert r1["p95"] == r2["p95"]

    def test_different_seed_different_result(self):
        services = [{"value": 100, "ci_low": 80, "ci_high": 120}]
        r1 = run_monte_carlo(services, n_simulations=1000, seed=42)
        r2 = run_monte_carlo(services, n_simulations=1000, seed=99)
        # Very unlikely to be identical
        assert r1["median"] != r2["median"]


class TestOutputShape:
    def test_has_required_keys(self, sample_services):
        result = run_monte_carlo(sample_services, n_simulations=1000, seed=42)
        assert "median" in result
        assert "mean" in result
        assert "p5" in result
        assert "p95" in result
        assert "std" in result
        assert "n_simulations" in result
        assert "simulations" in result

    def test_simulations_array_length(self, sample_services):
        n = 5000
        result = run_monte_carlo(sample_services, n_simulations=n, seed=42)
        assert len(result["simulations"]) == n

    def test_p5_less_than_median_less_than_p95(self, sample_services):
        result = run_monte_carlo(sample_services, n_simulations=10000, seed=42)
        assert result["p5"] <= result["median"] <= result["p95"]

    def test_n_simulations_recorded(self, sample_services):
        result = run_monte_carlo(sample_services, n_simulations=500, seed=42)
        assert result["n_simulations"] == 500


class TestParameterSensitivity:
    def test_wider_ci_produces_wider_distribution(self):
        narrow = [{"value": 100, "ci_low": 95, "ci_high": 105}]
        wide = [{"value": 100, "ci_low": 50, "ci_high": 150}]
        r_narrow = run_monte_carlo(narrow, n_simulations=10000, seed=42)
        r_wide = run_monte_carlo(wide, n_simulations=10000, seed=42)
        assert r_wide["std"] > r_narrow["std"]

    def test_higher_value_produces_higher_median(self):
        low = [{"value": 50, "ci_low": 40, "ci_high": 60}]
        high = [{"value": 200, "ci_low": 180, "ci_high": 220}]
        r_low = run_monte_carlo(low, n_simulations=10000, seed=42)
        r_high = run_monte_carlo(high, n_simulations=10000, seed=42)
        assert r_high["median"] > r_low["median"]


class TestEdgeCases:
    def test_single_service(self):
        services = [{"value": 1000, "ci_low": 800, "ci_high": 1200}]
        result = run_monte_carlo(services, n_simulations=1000, seed=42)
        assert result["median"] > 0

    def test_zero_ci_returns_constant(self):
        services = [{"value": 100, "ci_low": 100, "ci_high": 100}]
        result = run_monte_carlo(services, n_simulations=1000, seed=42)
        assert result["std"] == 0.0
        assert result["median"] == 100.0
        assert result["p5"] == 100.0
        assert result["p95"] == 100.0

    def test_empty_services_returns_zeros(self):
        result = run_monte_carlo([], n_simulations=100, seed=42)
        assert result["median"] == 0.0
        assert result["mean"] == 0.0

    def test_missing_ci_uses_defaults(self):
        """Services without ci_low/ci_high should use default +/-30%."""
        services = [{"value": 1000}]
        result = run_monte_carlo(services, n_simulations=10000, seed=42)
        # Should produce a distribution centered around 1000
        assert 800 < result["median"] < 1200

    def test_large_number_of_simulations(self):
        services = [{"value": 100, "ci_low": 80, "ci_high": 120}]
        result = run_monte_carlo(services, n_simulations=50000, seed=42)
        # With many simulations, mean should be close to mode/value
        assert abs(result["mean"] - 100) < 5
