"""Validation tests for Cabo Pulmo case study reference data."""

import json
import re
from pathlib import Path

import pytest

CASE_STUDY_PATH = Path("examples/cabo_pulmo_case_study.json")


@pytest.fixture
def case_study():
    with open(CASE_STUDY_PATH) as f:
        return json.load(f)


# ---- Core financial values ----


class TestCoreFinancialValues:
    def test_esv_total_is_29_27m(self, case_study):
        """Total ESV must be exactly $29,270,000 (market-price)."""
        assert case_study["ecosystem_services"]["total_annual_value_usd"] == 29_270_000

    def test_service_values_sum_to_total(self, case_study):
        """Sum of all individual service values must equal total."""
        services = case_study["ecosystem_services"]["services"]
        total = case_study["ecosystem_services"]["total_annual_value_usd"]
        service_sum = sum(s["annual_value_usd"] for s in services)
        assert service_sum == total, (
            f"Sum {service_sum} != total {total}"
        )

    def test_service_types_present(self, case_study):
        """Services must include tourism, fisheries_spillover, carbon_sequestration, coastal_protection."""
        services = case_study["ecosystem_services"]["services"]
        types = {s["service_type"] for s in services}
        expected = {"tourism", "fisheries_spillover", "carbon_sequestration", "coastal_protection"}
        assert expected.issubset(types), f"Missing service types: {expected - types}"


# ---- Ecological recovery ----


class TestEcologicalRecovery:
    def test_biomass_ratio(self, case_study):
        """Recovery ratio must be 4.63."""
        metrics = case_study["ecological_recovery"]["metrics"]["fish_biomass"]
        assert metrics["recovery_ratio"] == 4.63

    def test_biomass_ci(self, case_study):
        """Biomass 95% CI must be [3.8, 5.5]."""
        metrics = case_study["ecological_recovery"]["metrics"]["fish_biomass"]
        ci = metrics["confidence_interval_95"]
        assert ci == [3.8, 5.5]


# ---- NEOLI and rating ----


class TestNEOLIAndRating:
    def test_neoli_score(self, case_study):
        """NEOLI score must be 4 out of 5."""
        neoli = case_study["neoli_assessment"]
        assert neoli["neoli_score"] == 4
        # Count true criteria to verify the score matches
        criteria = neoli["criteria"]
        true_count = sum(1 for c in criteria.values() if c["value"] is True)
        assert true_count == 4

    def test_asset_rating_aaa(self, case_study):
        """Asset rating must be AAA with composite 0.90."""
        rating = case_study["asset_quality_rating"]
        assert rating["rating"] == "AAA"
        assert rating["composite_score"] == 0.90


# ---- DOI format validation ----


class TestDOIValidation:
    def test_all_dois_valid_format(self, case_study):
        """All DOI strings in the JSON must match 10.NNNN/... format."""
        doi_pattern = re.compile(r"^10\.\d{4,}/\S+$")
        dois = _find_all_dois(case_study)
        assert len(dois) > 0, "No DOIs found in case study"
        for doi in dois:
            assert doi_pattern.match(doi), f"Invalid DOI format: {doi}"


# ---- Monte Carlo validation ----


class TestMonteCarlo:
    def test_monte_carlo_median_within_20pct(self, case_study):
        """Monte Carlo median should be within 20% of $29.27M."""
        from maris.axioms.monte_carlo import run_monte_carlo

        services = []
        for svc in case_study["ecosystem_services"]["services"]:
            val = svc["annual_value_usd"]
            ci = svc.get("confidence_interval", {})
            if isinstance(ci, dict):
                ci_low = ci.get("ci_low", val * 0.8)
                ci_high = ci.get("ci_high", val * 1.2)
            elif isinstance(ci, (list, tuple)) and len(ci) >= 2:
                ci_low, ci_high = ci[0], ci[1]
            else:
                ci_low, ci_high = val * 0.8, val * 1.2
            services.append({
                "value": val,
                "ci_low": ci_low,
                "ci_high": ci_high,
            })
        result = run_monte_carlo(services, n_simulations=10_000, seed=42)
        deviation = abs(result["median"] - 29_270_000) / 29_270_000
        assert deviation < 0.20, (
            f"Monte Carlo median {result['median']:.0f} deviates "
            f"{deviation:.1%} from $29.27M"
        )


# ---- Helpers ----


def _find_all_dois(obj, found=None):
    """Recursively find all DOI strings in nested JSON."""
    if found is None:
        found = []
    if isinstance(obj, dict):
        for key, val in obj.items():
            if key == "doi" and isinstance(val, str) and val.startswith("10."):
                found.append(val)
            else:
                _find_all_dois(val, found)
    elif isinstance(obj, list):
        for item in obj:
            _find_all_dois(item, found)
    return found
