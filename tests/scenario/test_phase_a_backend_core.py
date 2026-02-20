"""Phase A Backend Core tests for maris/scenario/ module.

Tests constants, models, and counterfactual engine.
Minimum 15 tests covering all validation anchors from the PRD.
"""

import time

import pytest


# ---------------------------------------------------------------------------
# Constants tests
# ---------------------------------------------------------------------------

def test_constants_importable_without_services():
    """Constants module must import without Neo4j or any running service."""
    from maris.scenario.constants import (
        BIOMASS_THRESHOLDS,
        BLUE_CARBON_SEQUESTRATION,
        CARBON_PRICE_SCENARIOS,
        SCENARIO_CONFIDENCE_PENALTIES,
        SERVICE_REEF_SENSITIVITY,
        SSP_SCENARIOS,
    )
    assert SSP_SCENARIOS is not None
    assert BIOMASS_THRESHOLDS is not None
    assert CARBON_PRICE_SCENARIOS is not None
    assert BLUE_CARBON_SEQUESTRATION is not None
    assert SERVICE_REEF_SENSITIVITY is not None
    assert SCENARIO_CONFIDENCE_PENALTIES is not None


def test_ssp_scenarios_all_keys_present():
    """All three SSP scenarios must be present with required fields."""
    from maris.scenario.constants import SSP_SCENARIOS

    expected_ssps = {"SSP1-2.6", "SSP2-4.5", "SSP5-8.5"}
    assert set(SSP_SCENARIOS.keys()) == expected_ssps

    required_fields = {
        "label", "warming_2100_c", "sea_level_rise_m_range",
        "coral_loss_pct_by_2050", "coral_loss_pct_by_2100",
        "mangrove_sea_level_risk",
    }
    for ssp_key, ssp_data in SSP_SCENARIOS.items():
        for field in required_fields:
            assert field in ssp_data, f"Missing {field} in {ssp_key}"


def test_biomass_thresholds_all_keys_present():
    """All biomass thresholds must be present with required fields."""
    from maris.scenario.constants import BIOMASS_THRESHOLDS

    expected_thresholds = {"pristine", "warning", "mmsy_upper", "mmsy_lower", "collapse"}
    assert set(BIOMASS_THRESHOLDS.keys()) == expected_thresholds

    for name, data in BIOMASS_THRESHOLDS.items():
        assert "kg_ha" in data, f"Missing kg_ha in {name}"
        assert "reef_function_pct" in data, f"Missing reef_function_pct in {name}"
        assert "label" in data, f"Missing label in {name}"


def test_all_carbon_price_scenarios_present():
    """All five carbon price scenarios must be present."""
    from maris.scenario.constants import CARBON_PRICE_SCENARIOS

    expected = {"conservative", "current_market", "premium", "2030_projection", "high_integrity"}
    assert set(CARBON_PRICE_SCENARIOS.keys()) == expected

    for name, data in CARBON_PRICE_SCENARIOS.items():
        assert "price_usd" in data, f"Missing price_usd in {name}"
        assert "label" in data, f"Missing label in {name}"
        assert data["price_usd"] > 0, f"Non-positive price in {name}"


def test_service_sensitivity_all_keys_present():
    """Service sensitivity table must cover all service types and thresholds."""
    from maris.scenario.constants import SERVICE_REEF_SENSITIVITY

    expected_services = {"tourism", "fisheries", "coastal_protection", "carbon_sequestration"}
    assert set(SERVICE_REEF_SENSITIVITY.keys()) == expected_services

    expected_thresholds = {"warning", "mmsy_upper", "mmsy_lower", "collapse"}
    for svc, data in SERVICE_REEF_SENSITIVITY.items():
        for threshold in expected_thresholds:
            assert threshold in data, f"Missing {threshold} in {svc}"
            assert 0.0 <= data[threshold] <= 1.0, f"Out of range: {svc}.{threshold}={data[threshold]}"


def test_ssp_warming_monotonic():
    """SSP warming must increase monotonically from SSP1-2.6 to SSP5-8.5."""
    from maris.scenario.constants import SSP_SCENARIOS

    assert SSP_SCENARIOS["SSP1-2.6"]["warming_2100_c"] < SSP_SCENARIOS["SSP2-4.5"]["warming_2100_c"]
    assert SSP_SCENARIOS["SSP2-4.5"]["warming_2100_c"] < SSP_SCENARIOS["SSP5-8.5"]["warming_2100_c"]


# ---------------------------------------------------------------------------
# Models tests
# ---------------------------------------------------------------------------

def test_scenario_request_serialization():
    """ScenarioRequest must serialize and deserialize correctly."""
    from maris.scenario.models import ScenarioRequest

    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["cabo_pulmo"],
        time_horizon_years=10,
        assumptions={"protection_removed": True},
    )
    data = req.model_dump()
    assert data["scenario_type"] == "counterfactual"
    assert data["site_scope"] == ["cabo_pulmo"]

    # Round-trip
    req2 = ScenarioRequest.model_validate(data)
    assert req2.scenario_type == req.scenario_type


def test_scenario_response_serialization():
    """ScenarioResponse must serialize with all required fields."""
    from maris.scenario.models import (
        PropagationStep,
        ScenarioDelta,
        ScenarioRequest,
        ScenarioResponse,
        ScenarioUncertainty,
    )

    resp = ScenarioResponse(
        scenario_request=ScenarioRequest(
            scenario_type="counterfactual",
            site_scope=["test_site"],
        ),
        baseline_case={"total_esv_usd": 100.0},
        scenario_case={"total_esv_usd": 50.0},
        deltas=[ScenarioDelta(
            metric="total", baseline_value=100, scenario_value=50,
            absolute_change=-50, percent_change=-50.0,
        )],
        propagation_trace=[PropagationStep(
            axiom_id="BA-001", description="test",
            input_value=100, input_parameter="x",
            output_value=50, output_parameter="y",
        )],
        uncertainty=ScenarioUncertainty(
            p5=-60, p50=-50, p95=-40, dominant_driver="test",
        ),
        confidence=0.85,
        confidence_penalties=[],
        scenario_validity="in_domain",
        answer="Test answer",
        caveats=["Test caveat"],
        axioms_used=["BA-001"],
    )
    data = resp.model_dump()
    assert "scenario_request" in data
    assert "uncertainty" in data
    assert data["confidence"] == 0.85


def test_scenario_request_type_validation():
    """ScenarioRequest must reject invalid scenario types."""
    from maris.scenario.models import ScenarioRequest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ScenarioRequest(
            scenario_type="invalid_type",
            site_scope=["test"],
        )


# ---------------------------------------------------------------------------
# Counterfactual engine tests
# ---------------------------------------------------------------------------

def test_counterfactual_cabo_pulmo_delta_in_range():
    """VALIDATION ANCHOR: Cabo Pulmo counterfactual delta in [-$26M, -$18M]."""
    from maris.scenario.counterfactual_engine import run_counterfactual
    from maris.scenario.models import ScenarioRequest

    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["cabo_pulmo"],
    )
    resp = run_counterfactual(req)

    # Find total delta
    total_delta = None
    for d in resp.deltas:
        if d.metric == "total_esv":
            total_delta = d.absolute_change
            break

    assert total_delta is not None, "Missing total_esv delta"
    assert -26e6 <= total_delta <= -18e6, (
        f"Cabo Pulmo delta {total_delta/1e6:.1f}M out of range [-26M, -18M]"
    )


def test_counterfactual_esv_always_less_than_baseline():
    """Counterfactual ESV must be <= baseline ESV for all protected sites."""
    from maris.scenario.counterfactual_engine import run_counterfactual
    from maris.scenario.models import ScenarioRequest

    for site in ["cabo_pulmo", "shark_bay", "sundarbans", "belize", "ningaloo"]:
        req = ScenarioRequest(
            scenario_type="counterfactual",
            site_scope=[site],
        )
        resp = run_counterfactual(req)
        baseline_esv = resp.baseline_case.get("total_esv_usd", 0)
        scenario_esv = resp.scenario_case.get("total_esv_usd", 0)
        assert scenario_esv <= baseline_esv, (
            f"{site}: scenario ESV ({scenario_esv}) > baseline ({baseline_esv})"
        )


def test_counterfactual_shark_bay():
    """Shark Bay counterfactual: 10% seagrass retention."""
    from maris.scenario.counterfactual_engine import run_counterfactual
    from maris.scenario.models import ScenarioRequest

    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["shark_bay"],
    )
    resp = run_counterfactual(req)

    baseline_esv = resp.baseline_case.get("total_esv_usd", 0)
    scenario_esv = resp.scenario_case.get("total_esv_usd", 0)

    assert baseline_esv == pytest.approx(21_500_000, rel=0.01)
    assert scenario_esv == pytest.approx(baseline_esv * 0.10, rel=0.01)


def test_counterfactual_sundarbans_carbon_zero():
    """Sundarbans full deforestation: carbon sequestration must be zero."""
    from maris.scenario.counterfactual_engine import run_counterfactual
    from maris.scenario.models import ScenarioRequest

    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["sundarbans"],
    )
    resp = run_counterfactual(req)

    scenario_services = resp.scenario_case.get("services", {})
    carbon = scenario_services.get("carbon_sequestration", -1)
    assert carbon == 0.0, f"Sundarbans carbon should be 0 under deforestation, got {carbon}"


def test_propagation_trace_not_empty():
    """Every counterfactual response must have a non-empty propagation trace."""
    from maris.scenario.counterfactual_engine import run_counterfactual
    from maris.scenario.models import ScenarioRequest

    for site in ["cabo_pulmo", "shark_bay", "sundarbans"]:
        req = ScenarioRequest(
            scenario_type="counterfactual",
            site_scope=[site],
        )
        resp = run_counterfactual(req)
        assert len(resp.propagation_trace) > 0, f"{site}: empty propagation trace"


def test_uncertainty_p5_lt_p50_lt_p95():
    """Uncertainty envelope: P5 <= P50 <= P95 (for negative deltas, P5 < P50 < P95 in absolute terms)."""
    from maris.scenario.counterfactual_engine import run_counterfactual
    from maris.scenario.models import ScenarioRequest

    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["cabo_pulmo"],
    )
    resp = run_counterfactual(req)

    unc = resp.uncertainty
    # For negative deltas, P5 is more negative (worse) and P95 is less negative
    assert unc.p5 <= unc.p50 <= unc.p95, (
        f"Uncertainty ordering violated: P5={unc.p5}, P50={unc.p50}, P95={unc.p95}"
    )


def test_run_under_5_seconds():
    """Counterfactual engine must complete in under 5 seconds without Neo4j."""
    from maris.scenario.counterfactual_engine import run_counterfactual
    from maris.scenario.models import ScenarioRequest

    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["cabo_pulmo"],
    )

    start = time.time()
    run_counterfactual(req)
    elapsed = time.time() - start

    assert elapsed < 5.0, f"Counterfactual took {elapsed:.2f}s (>5s limit)"


def test_unknown_site_returns_insufficient_evidence():
    """Unknown site must return insufficient_scenario_evidence, not an exception."""
    from maris.scenario.counterfactual_engine import run_counterfactual
    from maris.scenario.models import ScenarioRequest

    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["nonexistent_fantasy_reef"],
    )
    resp = run_counterfactual(req)

    assert resp.confidence == 0.0
    assert resp.scenario_validity == "out_of_domain"
    assert "insufficient" in resp.answer.lower()


def test_cabo_pulmo_scenario_value_in_range():
    """Cabo Pulmo counterfactual scenario ESV must be in [$3M, $12M]."""
    from maris.scenario.counterfactual_engine import run_counterfactual
    from maris.scenario.models import ScenarioRequest

    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["cabo_pulmo"],
    )
    resp = run_counterfactual(req)
    scenario_esv = resp.scenario_case.get("total_esv_usd", 0)

    assert 3e6 <= scenario_esv <= 12e6, (
        f"Cabo Pulmo scenario ESV ${scenario_esv/1e6:.1f}M outside [$3M, $12M]"
    )


def test_deltas_sum_consistent():
    """Sum of individual service deltas must match total delta."""
    from maris.scenario.counterfactual_engine import run_counterfactual
    from maris.scenario.models import ScenarioRequest

    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["cabo_pulmo"],
    )
    resp = run_counterfactual(req)

    service_deltas = [d.absolute_change for d in resp.deltas if d.metric != "total_esv"]
    total_delta = next(d.absolute_change for d in resp.deltas if d.metric == "total_esv")

    assert sum(service_deltas) == pytest.approx(total_delta, rel=0.01)


def test_axioms_used_not_empty():
    """Every valid counterfactual response must list axioms used."""
    from maris.scenario.counterfactual_engine import run_counterfactual
    from maris.scenario.models import ScenarioRequest

    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["cabo_pulmo"],
    )
    resp = run_counterfactual(req)
    assert len(resp.axioms_used) > 0


def test_caveats_not_empty():
    """Every counterfactual response must include caveats."""
    from maris.scenario.counterfactual_engine import run_counterfactual
    from maris.scenario.models import ScenarioRequest

    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=["cabo_pulmo"],
    )
    resp = run_counterfactual(req)
    assert len(resp.caveats) > 0


def test_no_site_returns_insufficient_evidence():
    """Empty site_scope must return fail-closed response."""
    from maris.scenario.counterfactual_engine import run_counterfactual
    from maris.scenario.models import ScenarioRequest

    req = ScenarioRequest(
        scenario_type="counterfactual",
        site_scope=[],
    )
    resp = run_counterfactual(req)
    assert resp.confidence == 0.0
    assert resp.scenario_validity == "out_of_domain"
