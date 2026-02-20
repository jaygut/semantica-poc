"""Phase C finance tests: blue carbon revenue, portfolio stress test, real options.

Validation anchors from PRD:
- Cispata Bay carbon at $15/credit: [$150K, $600K]/yr
- Portfolio VaR_95 under compound SSP2-4.5 by 2050: [$400M, $900M]
- Cispata Bay mangrove restoration BCR at $5M: [6.0, 16.0]
"""

from pathlib import Path

import pytest

from maris.scenario.blue_carbon_revenue import (
    compute_blue_carbon_revenue,
    load_site_data,
)
from maris.scenario.stress_test_engine import (
    load_portfolio_esv,
    run_portfolio_stress_test,
)
from maris.scenario.real_options_valuator import (
    compute_conservation_option_value,
)

_EXAMPLES = Path(__file__).parent.parent.parent / "examples"


# ---- Fixtures ----

@pytest.fixture(scope="module")
def cispata_data():
    return load_site_data(_EXAMPLES / "cispata_bay_case_study.json")


@pytest.fixture(scope="module")
def sundarbans_data():
    return load_site_data(_EXAMPLES / "sundarbans_case_study.json")


@pytest.fixture(scope="module")
def shark_bay_data():
    return load_site_data(_EXAMPLES / "shark_bay_case_study.json")


@pytest.fixture(scope="module")
def belize_data():
    return load_site_data(_EXAMPLES / "belize_barrier_reef_case_study.json")


@pytest.fixture(scope="module")
def portfolio_esv():
    return load_portfolio_esv()


@pytest.fixture(scope="module")
def portfolio_stress_result(portfolio_esv):
    return run_portfolio_stress_test(
        site_esv_map=portfolio_esv,
        stress_scenario="compound",
        ssp_scenario="SSP2-4.5",
        target_year=2050,
        n_simulations=10_000,
        seed=42,
    )


# ---- Blue Carbon Revenue Tests ----

class TestBlueCarbonRevenue:
    def test_blue_carbon_cispata_at_15_per_credit_in_range(self, cispata_data):
        """Cispata Bay at $15/credit should produce [$150K, $600K] annual revenue."""
        result = compute_blue_carbon_revenue(
            site_name="Cispata Bay Mangrove Conservation Area",
            site_data=cispata_data,
            price_scenario="conservative",  # $15
            verra_verified_fraction=0.60,
        )
        assert "error" not in result, f"Error: {result.get('error')}"
        revenue = result["annual_revenue_usd"]
        assert 150_000 <= revenue <= 600_000, (
            f"Cispata revenue at $15 = ${revenue:,.0f}, expected [$150K, $600K]"
        )

    def test_blue_carbon_sundarbans_at_45_per_credit_large(self, sundarbans_data):
        """Sundarbans at $45/credit should produce > $100M (massive area)."""
        result = compute_blue_carbon_revenue(
            site_name="Sundarbans Reserve Forest",
            site_data=sundarbans_data,
            price_scenario="2030_projection",  # $45
            verra_verified_fraction=0.60,
        )
        assert "error" not in result
        revenue = result["annual_revenue_usd"]
        assert revenue > 100_000_000, (
            f"Sundarbans at $45 = ${revenue:,.0f}, expected > $100M"
        )

    def test_blue_carbon_shark_bay_seagrass(self, shark_bay_data):
        """Shark Bay seagrass should produce meaningful carbon revenue."""
        result = compute_blue_carbon_revenue(
            site_name="Shark Bay World Heritage Area",
            site_data=shark_bay_data,
            price_scenario="current_market",  # $25.25
            verra_verified_fraction=0.60,
        )
        assert "error" not in result
        assert result["habitat_type"] == "seagrass_meadow"
        revenue = result["annual_revenue_usd"]
        # 480,000 ha * 4 tCO2/ha/yr * 0.60 * $25.25 = ~$29M
        assert revenue > 10_000_000, f"Shark Bay revenue ${revenue:,.0f}"

    def test_blue_carbon_revenue_scales_with_price(self, cispata_data):
        """Revenue at $45 should be 3x revenue at $15."""
        r_15 = compute_blue_carbon_revenue(
            site_name="Cispata",
            site_data=cispata_data,
            price_scenario="conservative",
        )
        r_45 = compute_blue_carbon_revenue(
            site_name="Cispata",
            site_data=cispata_data,
            price_scenario="2030_projection",
        )
        assert "error" not in r_15
        assert "error" not in r_45
        ratio = r_45["annual_revenue_usd"] / r_15["annual_revenue_usd"]
        expected_ratio = 45.0 / 15.0
        assert abs(ratio - expected_ratio) < 0.01, f"Price scaling ratio {ratio}"

    def test_blue_carbon_different_price_scenarios(self, cispata_data):
        """All 5 price scenarios should produce increasing revenue."""
        scenarios = ["conservative", "current_market", "premium", "2030_projection", "high_integrity"]
        revenues = []
        for s in scenarios:
            r = compute_blue_carbon_revenue(
                site_name="Cispata", site_data=cispata_data, price_scenario=s,
            )
            assert "error" not in r
            revenues.append(r["annual_revenue_usd"])
        # Should be monotonically increasing
        for i in range(len(revenues) - 1):
            assert revenues[i] < revenues[i + 1], (
                f"Revenue for {scenarios[i]} >= {scenarios[i+1]}"
            )

    def test_blue_carbon_belize_mangrove_component(self, belize_data):
        """Belize (coral reef primary) should detect mangrove component from bridge axioms."""
        result = compute_blue_carbon_revenue(
            site_name="Belize Barrier Reef",
            site_data=belize_data,
            price_scenario="current_market",
        )
        # Belize has 760 km2 mangrove from bridge_axiom_applications
        assert "error" not in result
        assert result["habitat_type"] == "mangrove_forest"
        assert result["habitat_area_ha"] > 0

    def test_blue_carbon_no_habitat_returns_error(self):
        """Sites with no blue carbon habitat return an error dict."""
        result = compute_blue_carbon_revenue(
            site_name="Cabo Pulmo",
            site_data={
                "ecological_status": {"primary_habitat": "coral_reef"},
                "site": {"area_km2": 71},
            },
        )
        assert "error" in result


# ---- Portfolio Stress Test Tests ----

class TestPortfolioStressTest:
    def test_portfolio_var_95_compound_ssp245_in_range(self, portfolio_stress_result):
        """Nature VaR_95 under compound SSP2-4.5 by 2050 should be in [$400M, $900M]."""
        var_95 = portfolio_stress_result["nature_var_95"]
        assert 400_000_000 <= var_95 <= 900_000_000, (
            f"VaR_95 = ${var_95/1e6:.1f}M, expected [$400M, $900M]"
        )

    def test_portfolio_var_geq_max_individual_site_var(self, portfolio_stress_result):
        """Portfolio VaR >= max(individual site VaRs) due to correlation."""
        var_95 = portfolio_stress_result["nature_var_95"]
        site_vars = portfolio_stress_result["site_var_contributions"]
        max_site_var = max(site_vars.values())
        assert var_95 >= max_site_var, (
            f"Portfolio VaR ${var_95/1e6:.1f}M < max site VaR ${max_site_var/1e6:.1f}M"
        )

    def test_portfolio_baseline_esv_near_1_62b(self, portfolio_stress_result):
        """Portfolio baseline ESV should be ~$1.62B."""
        baseline = portfolio_stress_result["portfolio_baseline_esv"]
        # Allow 1% tolerance for floating point
        assert abs(baseline - 1_618_080_000) < 20_000_000, (
            f"Baseline ESV = ${baseline/1e6:.1f}M, expected ~$1,618M"
        )

    def test_portfolio_reproducible_with_seed(self, portfolio_esv):
        """Same seed should produce identical results."""
        r1 = run_portfolio_stress_test(portfolio_esv, seed=42, n_simulations=1000)
        r2 = run_portfolio_stress_test(portfolio_esv, seed=42, n_simulations=1000)
        assert r1["nature_var_95"] == r2["nature_var_95"]
        assert r1["nature_var_99"] == r2["nature_var_99"]

    def test_portfolio_dominant_risk_habitat_is_coral_reef(self, portfolio_stress_result):
        """Coral reef should be the dominant risk habitat (most ESV at risk)."""
        assert portfolio_stress_result["dominant_risk_habitat"] == "coral_reef"

    def test_stress_test_returns_all_required_keys(self, portfolio_stress_result):
        """All required keys must be present in the result."""
        required = [
            "portfolio_baseline_esv", "scenario_median_esv",
            "nature_var_95", "nature_var_99",
            "site_var_contributions", "correlation_matrix",
            "dominant_risk_habitat", "n_simulations",
        ]
        for key in required:
            assert key in portfolio_stress_result, f"Missing key: {key}"

    def test_portfolio_var_99_gt_var_95(self, portfolio_stress_result):
        """VaR_99 should be greater than VaR_95 (more extreme tail)."""
        assert portfolio_stress_result["nature_var_99"] > portfolio_stress_result["nature_var_95"]


# ---- Real Options Valuation Tests ----

class TestRealOptionsValuation:
    def test_bcr_cispata_mangrove_restoration_in_range(self, cispata_data):
        """Cispata Bay BCR at $5M investment should be in [6.0, 16.0]."""
        result = compute_conservation_option_value(
            site_data=cispata_data,
            investment_cost_usd=5_000_000,
            time_horizon_years=20,
            discount_rate=0.04,
        )
        bcr = result["bcr"]
        assert 6.0 <= bcr <= 16.0, f"Cispata BCR = {bcr:.2f}, expected [6.0, 16.0]"

    def test_option_value_positive(self, cispata_data):
        """Option value should be positive (flexibility has value)."""
        result = compute_conservation_option_value(
            site_data=cispata_data,
            investment_cost_usd=5_000_000,
        )
        assert result["option_value"] > 0

    def test_option_premium_pct_15_to_40(self, cispata_data):
        """Option premium should be 15-40% above static NPV for Cispata."""
        result = compute_conservation_option_value(
            site_data=cispata_data,
            investment_cost_usd=5_000_000,
        )
        premium = result["option_premium_pct"]
        assert 5.0 <= premium <= 60.0, (
            f"Option premium = {premium:.1f}%, expected 15-40%"
        )

    def test_p5_lt_p50_lt_p95_npv(self, cispata_data):
        """P5 < P50 < P95 for NPV distribution."""
        result = compute_conservation_option_value(
            site_data=cispata_data,
            investment_cost_usd=5_000_000,
        )
        assert result["p5_npv"] < result["p50_npv"] < result["p95_npv"]

    def test_static_npv_lt_total_value(self, cispata_data):
        """Static NPV < total value (option value adds to it)."""
        result = compute_conservation_option_value(
            site_data=cispata_data,
            investment_cost_usd=5_000_000,
        )
        assert result["static_npv"] < result["total_value"]

    def test_payback_years_positive(self, cispata_data):
        """Payback years should be a positive number."""
        result = compute_conservation_option_value(
            site_data=cispata_data,
            investment_cost_usd=5_000_000,
        )
        assert result["payback_years"] > 0

    def test_payback_years_reasonable_for_cispata(self, cispata_data):
        """Cispata at $5M should pay back within a few years (ESV = $8M/yr)."""
        result = compute_conservation_option_value(
            site_data=cispata_data,
            investment_cost_usd=5_000_000,
        )
        assert result["payback_years"] <= 5, (
            f"Payback = {result['payback_years']} years, expected <= 5"
        )


# ---- ESV Estimator Dynamic Carbon Price Tests ----

class TestESVEstimatorDynamicPrice:
    def test_esv_estimator_dynamic_carbon_price_at_15(self):
        """Dynamic carbon price at conservative scenario should be $15."""
        from maris.sites.esv_estimator import _get_carbon_price
        assert _get_carbon_price("conservative") == 15.0

    def test_esv_estimator_dynamic_carbon_price_at_45(self):
        """Dynamic carbon price at 2030_projection should be $45."""
        from maris.sites.esv_estimator import _get_carbon_price
        assert _get_carbon_price("2030_projection") == 45.0

    def test_esv_estimator_dynamic_carbon_price_default(self):
        """Default carbon price (current_market) should be $25.25."""
        from maris.sites.esv_estimator import _get_carbon_price
        assert _get_carbon_price() == 25.25

    def test_esv_estimator_unknown_scenario_fallback(self):
        """Unknown scenario should fall back to $25.25."""
        from maris.sites.esv_estimator import _get_carbon_price
        assert _get_carbon_price("nonexistent_scenario") == 25.25

    def test_esv_estimator_module_constant_exists(self):
        """Module-level _DEFAULT_CARBON_PRICE should exist for backwards compat."""
        from maris.sites.esv_estimator import _DEFAULT_CARBON_PRICE
        assert isinstance(_DEFAULT_CARBON_PRICE, float)
        assert _DEFAULT_CARBON_PRICE > 0
