"""Phase E invariant tests for the v6 Scenario Intelligence engine.

These 13 tests verify the non-negotiable invariants documented in the
V6 Scenario Intelligence PRD section E.3. Each test uses real module
implementations and real data from examples/ JSON files - no mocking
of scenario engines.

Every invariant here must pass before merge.
"""

from __future__ import annotations

import json
import pathlib

from maris.scenario.models import ScenarioRequest
from maris.scenario.counterfactual_engine import run_counterfactual
from maris.scenario.climate_scenarios import run_climate_scenario
from maris.scenario.tipping_point_analyzer import compute_reef_function
from maris.scenario.blue_carbon_revenue import compute_blue_carbon_revenue
from maris.scenario.stress_test_engine import run_portfolio_stress_test
from maris.scenario.real_options_valuator import compute_conservation_option_value

_EXAMPLES_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "examples"

# All 9 portfolio site names as they appear in case study JSON site.name
_ALL_SITES = [
    "Cabo Pulmo National Park",
    "Shark Bay World Heritage Area",
    "Ningaloo Coast World Heritage Area",
    "Belize Barrier Reef Reserve System",
    "Galapagos Marine Reserve",
    "Raja Ampat Marine Protected Area Network",
    "Sundarbans Reserve Forest",
    "Aldabra Atoll Special Reserve",
    "Cispata Bay Mangrove Conservation Area",
]


def _load_site_json(filename: str) -> dict:
    """Load a case study JSON file from examples/."""
    path = _EXAMPLES_DIR / filename
    with open(path) as f:
        return json.load(f)


# -----------------------------------------------------------------------
# 1. Scenario confidence never exceeds baseline
# -----------------------------------------------------------------------

def test_scenario_confidence_never_exceeds_baseline():
    """Scenario confidence must be <= baseline confidence for same query."""
    # Counterfactual baseline confidence is 0.85 for site-specific models
    base_confidence = 0.85

    # Run a counterfactual with site-specific model (Cabo Pulmo)
    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["Cabo Pulmo National Park"],
    )
    response = run_counterfactual(req)
    assert response.confidence <= base_confidence, (
        f"Scenario confidence {response.confidence} exceeds baseline {base_confidence}"
    )

    # Run a climate scenario with temporal + SSP penalties
    climate_req = ScenarioRequest(
        scenario_type="climate",
        site_scope=["Cabo Pulmo National Park"],
        ssp_scenario="SSP5-8.5",
        target_year=2100,
    )
    climate_response = run_climate_scenario(climate_req)
    assert climate_response.confidence <= base_confidence, (
        f"Climate scenario confidence {climate_response.confidence} exceeds baseline {base_confidence}"
    )

    # Climate scenario with heavier penalties should be lower
    assert climate_response.confidence < response.confidence, (
        "SSP5-8.5 2100 climate scenario should have lower confidence than counterfactual"
    )


# -----------------------------------------------------------------------
# 2. Counterfactual ESV < current ESV for all 9 sites
# -----------------------------------------------------------------------

def test_counterfactual_esv_less_than_current_all_sites():
    """Counterfactual ESV must be <= current ESV for all 9 protected sites."""
    for site_name in _ALL_SITES:
        req = ScenarioRequest(
            scenario_type="counterfactual",
            site_scope=[site_name],
        )
        response = run_counterfactual(req)
        assert response.scenario_validity != "out_of_domain", (
            f"Counterfactual for '{site_name}' returned out_of_domain - "
            f"expected valid response"
        )

        baseline_total = response.baseline_case.get("total_esv_usd", 0)
        scenario_total = response.scenario_case.get("total_esv_usd", 0)

        assert scenario_total < baseline_total, (
            f"Counterfactual ESV ({scenario_total:,.0f}) >= baseline ESV "
            f"({baseline_total:,.0f}) for '{site_name}'"
        )


# -----------------------------------------------------------------------
# 3. Climate scenario monotonic by SSP
# -----------------------------------------------------------------------

def test_climate_scenario_monotonic_by_ssp():
    """SSP1-2.6 ESV >= SSP2-4.5 ESV >= SSP5-8.5 ESV for same site and year."""
    ssps = ["SSP1-2.6", "SSP2-4.5", "SSP5-8.5"]
    esv_by_ssp = {}

    for ssp in ssps:
        req = ScenarioRequest(
            scenario_type="climate",
            site_scope=["Cabo Pulmo National Park"],
            ssp_scenario=ssp,
            target_year=2050,
        )
        response = run_climate_scenario(req)
        esv_by_ssp[ssp] = response.scenario_case.get("total_esv_usd", 0)

    assert esv_by_ssp["SSP1-2.6"] >= esv_by_ssp["SSP2-4.5"], (
        f"SSP1-2.6 ESV ({esv_by_ssp['SSP1-2.6']:,.0f}) < SSP2-4.5 ESV "
        f"({esv_by_ssp['SSP2-4.5']:,.0f})"
    )
    assert esv_by_ssp["SSP2-4.5"] >= esv_by_ssp["SSP5-8.5"], (
        f"SSP2-4.5 ESV ({esv_by_ssp['SSP2-4.5']:,.0f}) < SSP5-8.5 ESV "
        f"({esv_by_ssp['SSP5-8.5']:,.0f})"
    )


# -----------------------------------------------------------------------
# 4. Tipping point piecewise continuous
# -----------------------------------------------------------------------

def test_tipping_point_piecewise_continuous():
    """compute_reef_function must be continuous across all threshold boundaries."""
    thresholds = [150, 300, 600, 1130]
    eps = 0.01  # Small epsilon for continuity check
    max_discontinuity = 0.02  # Maximum allowed jump

    for threshold in thresholds:
        val_below = compute_reef_function(threshold - eps)
        val_at = compute_reef_function(threshold)
        val_above = compute_reef_function(threshold + eps)

        # Check continuity from below
        assert abs(val_at - val_below) < max_discontinuity, (
            f"Discontinuity at {threshold} kg/ha from below: "
            f"f({threshold}-eps)={val_below:.6f}, f({threshold})={val_at:.6f}, "
            f"gap={abs(val_at - val_below):.6f}"
        )

        # Check continuity from above
        assert abs(val_above - val_at) < max_discontinuity, (
            f"Discontinuity at {threshold} kg/ha from above: "
            f"f({threshold})={val_at:.6f}, f({threshold}+eps)={val_above:.6f}, "
            f"gap={abs(val_above - val_at):.6f}"
        )


# -----------------------------------------------------------------------
# 5. Tipping point boundary values
# -----------------------------------------------------------------------

def test_tipping_point_boundary_values():
    """compute_reef_function at exact threshold kg/ha values matches expected."""
    assert abs(compute_reef_function(150) - 0.05) < 0.01, (
        f"compute_reef_function(150)={compute_reef_function(150):.4f}, expected ~0.05"
    )
    assert abs(compute_reef_function(300) - 0.30) < 0.01, (
        f"compute_reef_function(300)={compute_reef_function(300):.4f}, expected ~0.30"
    )
    assert abs(compute_reef_function(600) - 0.65) < 0.01, (
        f"compute_reef_function(600)={compute_reef_function(600):.4f}, expected ~0.65"
    )
    assert abs(compute_reef_function(1130) - 0.90) < 0.01, (
        f"compute_reef_function(1130)={compute_reef_function(1130):.4f}, expected ~0.90"
    )
    assert compute_reef_function(1500) >= 0.99, (
        f"compute_reef_function(1500)={compute_reef_function(1500):.4f}, expected >= 0.99"
    )


# -----------------------------------------------------------------------
# 6. Delta equals scenario minus baseline
# -----------------------------------------------------------------------

def test_delta_equals_scenario_minus_baseline():
    """delta.absolute_change must equal scenario_value - baseline_value for every metric."""
    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["Cabo Pulmo National Park"],
    )
    response = run_counterfactual(req)

    for delta in response.deltas:
        expected_change = delta.scenario_value - delta.baseline_value
        assert abs(delta.absolute_change - expected_change) < 0.01, (
            f"Delta arithmetic error for '{delta.metric}': "
            f"absolute_change={delta.absolute_change:.2f}, "
            f"scenario - baseline = {expected_change:.2f}"
        )


# -----------------------------------------------------------------------
# 7. No omitted uncertainty
# -----------------------------------------------------------------------

def test_scenario_response_no_omitted_uncertainty():
    """All ScenarioResponse objects must have non-null uncertainty field."""
    # Test counterfactual
    cf_req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["Cabo Pulmo National Park"],
    )
    cf_response = run_counterfactual(cf_req)
    assert cf_response.uncertainty is not None, (
        "Counterfactual response has null uncertainty"
    )
    assert cf_response.uncertainty.n_simulations > 0 or cf_response.uncertainty.p5 != 0, (
        "Uncertainty appears uninitialized"
    )

    # Test climate
    cl_req = ScenarioRequest(
        scenario_type="climate",
        site_scope=["Cabo Pulmo National Park"],
        ssp_scenario="SSP2-4.5",
        target_year=2050,
    )
    cl_response = run_climate_scenario(cl_req)
    assert cl_response.uncertainty is not None, (
        "Climate response has null uncertainty"
    )
    assert cl_response.uncertainty.n_simulations > 0, (
        "Climate uncertainty has 0 simulations"
    )


# -----------------------------------------------------------------------
# 8. Carbon revenue Cispata Bay validates against actuals
# -----------------------------------------------------------------------

def test_carbon_revenue_cispata_bay_validates_against_actuals():
    """Cispata Bay carbon revenue at $15/credit must be in [$150K, $600K] range."""
    site_data = _load_site_json("cispata_bay_case_study.json")
    result = compute_blue_carbon_revenue(
        site_name="Cispata Bay Mangrove Conservation Area",
        site_data=site_data,
        price_scenario="conservative",  # $15/credit
    )

    assert "error" not in result, (
        f"compute_blue_carbon_revenue returned error: {result.get('error')}"
    )

    annual_revenue = result["annual_revenue_usd"]
    assert 150_000 <= annual_revenue <= 600_000, (
        f"Cispata Bay annual revenue at $15/credit = ${annual_revenue:,.0f}, "
        f"expected [$150K, $600K]. "
        f"Area: {result.get('habitat_area_ha')} ha, "
        f"Rate: {result.get('seq_rate_tco2_ha_yr')} tCO2/ha/yr, "
        f"Verified fraction: {result.get('verra_verified_fraction')}"
    )


# -----------------------------------------------------------------------
# 9. Portfolio VaR >= max individual site VaR
# -----------------------------------------------------------------------

def test_portfolio_var_geq_max_individual_site_var():
    """Portfolio VaR >= max(individual site VaRs) due to correlation."""
    result = run_portfolio_stress_test(
        stress_scenario="compound",
        ssp_scenario="SSP2-4.5",
        target_year=2050,
        n_simulations=10_000,
        seed=42,
    )

    portfolio_var_95 = result["nature_var_95"]
    site_var_contributions = result["site_var_contributions"]
    max_individual_var = max(site_var_contributions.values())

    assert portfolio_var_95 >= max_individual_var, (
        f"Portfolio VaR_95 ({portfolio_var_95:,.0f}) < max individual site VaR "
        f"({max_individual_var:,.0f})"
    )


# -----------------------------------------------------------------------
# 10. BCR Cispata mangrove restoration in valid range
# -----------------------------------------------------------------------

def test_bcr_cispata_mangrove_restoration_in_valid_range():
    """Cispata Bay BCR from real_options_valuator must be in [6.0, 16.0]."""
    site_data = _load_site_json("cispata_bay_case_study.json")
    result = compute_conservation_option_value(
        site_data=site_data,
        investment_cost_usd=5_000_000,
        time_horizon_years=20,
        discount_rate=0.04,
        n_simulations=10_000,
        seed=42,
    )

    bcr = result["bcr"]
    assert 6.0 <= bcr <= 16.0, (
        f"Cispata Bay BCR = {bcr:.2f}, expected [6.0, 16.0]. "
        f"Static NPV: ${result['static_npv']:,.0f}, "
        f"Option value: ${result['option_value']:,.0f}"
    )


# -----------------------------------------------------------------------
# 11. Cabo Pulmo counterfactual delta in expected range
# -----------------------------------------------------------------------

def test_counterfactual_cabo_pulmo_delta_in_expected_range():
    """Cabo Pulmo counterfactual delta in [-$26M, -$18M]."""
    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["Cabo Pulmo National Park"],
    )
    response = run_counterfactual(req)

    # Find the total_esv delta
    total_delta = None
    for delta in response.deltas:
        if delta.metric == "total_esv":
            total_delta = delta.absolute_change
            break

    assert total_delta is not None, "No total_esv delta found in response"
    assert -26_000_000 <= total_delta <= -18_000_000, (
        f"Cabo Pulmo counterfactual total delta = ${total_delta:,.0f}, "
        f"expected [-$26M, -$18M]"
    )


# -----------------------------------------------------------------------
# 12. Fail closed on missing site data
# -----------------------------------------------------------------------

def test_fail_closed_on_missing_site_data():
    """Unknown site must return insufficient_scenario_evidence, not an exception."""
    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["Nonexistent Underwater Fantasy MPA"],
    )

    # Must NOT crash with unhandled exception
    response = run_counterfactual(req)

    # Should return out_of_domain validity
    assert response.scenario_validity == "out_of_domain", (
        f"Expected out_of_domain for unknown site, got '{response.scenario_validity}'"
    )

    # Answer should reference insufficient evidence
    assert "insufficient" in response.answer.lower() or "no case study" in response.answer.lower(), (
        f"Expected insufficient evidence message, got: '{response.answer}'"
    )


# -----------------------------------------------------------------------
# 13. Out of domain scenarios flagged
# -----------------------------------------------------------------------

def test_out_of_domain_scenarios_flagged():
    """Scenarios beyond 2100 or with invalid SSP labels must be flagged as out_of_domain."""
    # Test 1: Year beyond 2100
    req_future = ScenarioRequest(
        scenario_type="climate",
        site_scope=["Cabo Pulmo National Park"],
        ssp_scenario="SSP2-4.5",
        target_year=2200,
    )
    # Should either return out_of_domain or partially_out_of_domain, but not crash
    response_future = run_climate_scenario(req_future)
    # 2200 is well beyond IPCC anchor range - should be flagged
    assert response_future.scenario_validity in ("out_of_domain", "partially_out_of_domain"), (
        f"Year 2200 scenario should be flagged, got '{response_future.scenario_validity}'"
    )

    # Test 2: Invalid SSP label
    req_bad_ssp = ScenarioRequest(
        scenario_type="climate",
        site_scope=["Cabo Pulmo National Park"],
        ssp_scenario="SSP9-9.9",
        target_year=2050,
    )
    response_bad_ssp = run_climate_scenario(req_bad_ssp)
    assert response_bad_ssp.scenario_validity == "out_of_domain", (
        f"Invalid SSP scenario should be out_of_domain, got '{response_bad_ssp.scenario_validity}'"
    )
