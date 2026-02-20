"""Phase B tests: climate scenarios, tipping points, bridge axioms BA-036-040, confidence extension.

Minimum 20 tests covering all Phase B exit criteria from the PRD.
"""

import json
import pathlib

import pytest

from maris.scenario.climate_scenarios import (
    interpolate_degradation,
    run_climate_scenario,
)
from maris.scenario.models import ScenarioRequest, ScenarioResponse
from maris.scenario.tipping_point_analyzer import (
    compute_reef_function,
    get_threshold_proximity,
    get_tipping_point_site_report,
)
from maris.axioms.confidence import apply_scenario_penalties


_EXAMPLES_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "examples"


def _load_site(name: str) -> dict:
    """Helper to load a case study JSON."""
    for fn in _EXAMPLES_DIR.glob("*_case_study.json"):
        if name.lower() in fn.stem:
            with open(fn) as f:
                return json.load(f)
    raise FileNotFoundError(f"No case study for {name}")


# ---------------------------------------------------------------------------
# Climate scenario monotonicity tests
# ---------------------------------------------------------------------------

def test_climate_scenario_monotonic_ssp126_ge_ssp245():
    """SSP1-2.6 ESV must be >= SSP2-4.5 ESV for Cabo Pulmo 2050."""
    req126 = ScenarioRequest(
        scenario_type="climate", site_scope=["cabo_pulmo"],
        ssp_scenario="SSP1-2.6", target_year=2050,
    )
    req245 = ScenarioRequest(
        scenario_type="climate", site_scope=["cabo_pulmo"],
        ssp_scenario="SSP2-4.5", target_year=2050,
    )
    r126 = run_climate_scenario(req126)
    r245 = run_climate_scenario(req245)
    assert r126.scenario_case["total_esv_usd"] >= r245.scenario_case["total_esv_usd"]


def test_climate_scenario_monotonic_ssp245_ge_ssp585():
    """SSP2-4.5 ESV must be >= SSP5-8.5 ESV for Cabo Pulmo 2050."""
    req245 = ScenarioRequest(
        scenario_type="climate", site_scope=["cabo_pulmo"],
        ssp_scenario="SSP2-4.5", target_year=2050,
    )
    req585 = ScenarioRequest(
        scenario_type="climate", site_scope=["cabo_pulmo"],
        ssp_scenario="SSP5-8.5", target_year=2050,
    )
    r245 = run_climate_scenario(req245)
    r585 = run_climate_scenario(req585)
    assert r245.scenario_case["total_esv_usd"] >= r585.scenario_case["total_esv_usd"]


def test_climate_monotonic_mangrove_sundarbans():
    """SSP1-2.6 >= SSP2-4.5 >= SSP5-8.5 for mangrove site (Sundarbans) 2050."""
    results = {}
    for ssp in ["SSP1-2.6", "SSP2-4.5", "SSP5-8.5"]:
        req = ScenarioRequest(
            scenario_type="climate", site_scope=["sundarbans"],
            ssp_scenario=ssp, target_year=2050,
        )
        results[ssp] = run_climate_scenario(req)

    esv_126 = results["SSP1-2.6"].scenario_case["total_esv_usd"]
    esv_245 = results["SSP2-4.5"].scenario_case["total_esv_usd"]
    esv_585 = results["SSP5-8.5"].scenario_case["total_esv_usd"]
    assert esv_126 >= esv_245 >= esv_585


# ---------------------------------------------------------------------------
# Piecewise reef function boundary tests
# ---------------------------------------------------------------------------

def test_compute_reef_function_at_150():
    """compute_reef_function(150) must approximately equal 0.05."""
    assert abs(compute_reef_function(150) - 0.05) < 0.01


def test_compute_reef_function_at_300():
    """compute_reef_function(300) must approximately equal 0.30."""
    assert abs(compute_reef_function(300) - 0.30) < 0.01


def test_compute_reef_function_at_600():
    """compute_reef_function(600) must approximately equal 0.65."""
    assert abs(compute_reef_function(600) - 0.65) < 0.01


def test_compute_reef_function_at_1130():
    """compute_reef_function(1130) must approximately equal 0.90."""
    assert abs(compute_reef_function(1130) - 0.90) < 0.01


def test_compute_reef_function_at_1500():
    """compute_reef_function(1500) must be >= 0.99."""
    assert compute_reef_function(1500) >= 0.99


def test_compute_reef_function_continuous_at_boundaries():
    """No discontinuity at transition points between piecewise segments."""
    thresholds = [150, 300, 600, 1130]
    for threshold in thresholds:
        below = compute_reef_function(threshold - 0.01)
        at = compute_reef_function(threshold)
        above = compute_reef_function(threshold + 0.01)
        # Must be continuous: no jump > 0.001 at boundaries
        assert abs(at - below) < 0.001, f"Discontinuity at {threshold}: {below} -> {at}"
        assert abs(above - at) < 0.001, f"Discontinuity at {threshold}: {at} -> {above}"


def test_compute_reef_function_monotonically_increasing():
    """Reef function must be monotonically increasing with biomass."""
    biomass_values = list(range(0, 2001, 10))
    prev_rf = -1.0
    for b in biomass_values:
        rf = compute_reef_function(b)
        assert rf >= prev_rf, f"Not monotonic at {b}: {prev_rf} > {rf}"
        prev_rf = rf


# ---------------------------------------------------------------------------
# Tipping point site report
# ---------------------------------------------------------------------------

def test_tipping_point_site_report_cabo_pulmo():
    """Cabo Pulmo site report must have expected structure and valid biomass."""
    site_data = _load_site("cabo_pulmo")
    report = get_tipping_point_site_report(site_data)

    assert report.get("applicable") is True
    assert report["current_biomass_kg_ha"] == pytest.approx(926.0, abs=1.0)
    assert report["reef_function_current"] == pytest.approx(0.804, abs=0.01)
    assert report["headroom_pct"] > 0
    assert report["esv_at_collapse"] > 0
    assert report["esv_at_collapse"] < report["esv_current"]


def test_threshold_proximity_returns_string():
    """get_threshold_proximity must return a non-empty string for any biomass value."""
    for biomass in [50, 150, 300, 600, 926, 1130, 1500, 2000]:
        result = get_threshold_proximity(biomass)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Bridge axiom BA-036 to BA-040 in templates JSON
# ---------------------------------------------------------------------------

def test_ba036_to_ba040_in_templates_json():
    """BA-036 through BA-040 must be present in bridge_axiom_templates.json with T1 evidence."""
    templates_path = pathlib.Path(__file__).resolve().parent.parent.parent / "schemas" / "bridge_axiom_templates.json"
    with open(templates_path) as f:
        data = json.load(f)

    axiom_ids = {a["axiom_id"] for a in data["axioms"]}
    for ba_id in ["BA-036", "BA-037", "BA-038", "BA-039", "BA-040"]:
        assert ba_id in axiom_ids, f"{ba_id} missing from bridge_axiom_templates.json"

    # Verify evidence tier
    for axiom in data["axioms"]:
        if axiom["axiom_id"] in {"BA-036", "BA-037", "BA-038", "BA-039", "BA-040"}:
            assert axiom["evidence_tier"] == "T1", f"{axiom['axiom_id']} not T1"
            assert len(axiom.get("sources", [])) > 0, f"{axiom['axiom_id']} has no sources"

    # Verify BA-036 to BA-039 cite McClanahan DOI
    mcclanahan_doi = "10.1073/pnas.1106861108"
    for axiom in data["axioms"]:
        if axiom["axiom_id"] in {"BA-036", "BA-037", "BA-038", "BA-039"}:
            source_dois = [s["doi"] for s in axiom.get("sources", [])]
            assert mcclanahan_doi in source_dois, f"{axiom['axiom_id']} missing McClanahan DOI"

    # Verify BA-040 cites bleaching threshold DOI
    bleaching_doi = "10.1038/s41467-025-65015-4"
    for axiom in data["axioms"]:
        if axiom["axiom_id"] == "BA-040":
            source_dois = [s["doi"] for s in axiom.get("sources", [])]
            assert bleaching_doi in source_dois, "BA-040 missing bleaching threshold DOI"


def test_ba036_to_ba040_in_bridge_axioms_json():
    """BA-036 through BA-040 must also be present in bridge_axioms.json."""
    ba_path = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "semantica_export" / "bridge_axioms.json"
    with open(ba_path) as f:
        data = json.load(f)

    axiom_ids = {a["axiom_id"] for a in data["bridge_axioms"]}
    for ba_id in ["BA-036", "BA-037", "BA-038", "BA-039", "BA-040"]:
        assert ba_id in axiom_ids, f"{ba_id} missing from bridge_axioms.json"


# ---------------------------------------------------------------------------
# Scenario confidence penalties
# ---------------------------------------------------------------------------

def test_apply_scenario_penalties_reduces_confidence():
    """Scenario penalties must reduce confidence from base."""
    req = ScenarioRequest(
        scenario_type="climate", site_scope=["cabo_pulmo"],
        ssp_scenario="SSP2-4.5", target_year=2050,
    )
    adjusted, penalties = apply_scenario_penalties(0.85, req)
    assert adjusted < 0.85
    assert len(penalties) > 0


def test_apply_scenario_penalties_temporal_penalty():
    """Temporal extrapolation penalty should increase with target year."""
    req_near = ScenarioRequest(
        scenario_type="climate", site_scope=["cabo_pulmo"],
        ssp_scenario="SSP2-4.5", target_year=2035,
    )
    req_far = ScenarioRequest(
        scenario_type="climate", site_scope=["cabo_pulmo"],
        ssp_scenario="SSP2-4.5", target_year=2100,
    )
    adj_near, _ = apply_scenario_penalties(0.85, req_near)
    adj_far, _ = apply_scenario_penalties(0.85, req_far)
    assert adj_near > adj_far, "Nearer target should have higher confidence"


def test_apply_scenario_penalties_ssp_penalty():
    """Higher emission SSP should have higher penalty."""
    req_low = ScenarioRequest(
        scenario_type="climate", site_scope=["cabo_pulmo"],
        ssp_scenario="SSP1-2.6", target_year=2050,
    )
    req_high = ScenarioRequest(
        scenario_type="climate", site_scope=["cabo_pulmo"],
        ssp_scenario="SSP5-8.5", target_year=2050,
    )
    adj_low, _ = apply_scenario_penalties(0.85, req_low)
    adj_high, _ = apply_scenario_penalties(0.85, req_high)
    assert adj_low > adj_high, "Lower emission SSP should have higher confidence"


def test_apply_scenario_penalties_never_below_min():
    """Scenario confidence must never drop below 0.10."""
    req = ScenarioRequest(
        scenario_type="climate", site_scope=["cabo_pulmo"],
        ssp_scenario="SSP5-8.5", target_year=2100,
    )
    adjusted, _ = apply_scenario_penalties(0.20, req)
    assert adjusted >= 0.10


def test_scenario_confidence_le_base_confidence():
    """Scenario confidence must always be <= base confidence."""
    for base in [0.85, 0.70, 0.50, 0.30, 0.15]:
        req = ScenarioRequest(
            scenario_type="climate", site_scope=["cabo_pulmo"],
            ssp_scenario="SSP2-4.5", target_year=2050,
        )
        adjusted, _ = apply_scenario_penalties(base, req)
        assert adjusted <= base


# ---------------------------------------------------------------------------
# Interpolation tests
# ---------------------------------------------------------------------------

def test_interpolate_degradation_between_anchors():
    """Interpolation between 2025 and 2050 must produce values in [0, anchor]."""
    # At 2037.5 (midpoint), should be ~50% of 2050 anchor
    low, high = interpolate_degradation("SSP2-4.5", "coral_reef", 2038)
    # 2050 anchor for SSP2-4.5 coral_reef: (0.50, 0.70)
    # At 2038: t = (2038 - 2025) / (2050 - 2025) = 13/25 = 0.52
    expected_low = 0.52 * 0.50
    expected_high = 0.52 * 0.70
    assert abs(low - expected_low) < 0.01
    assert abs(high - expected_high) < 0.01


def test_interpolate_degradation_at_base_year():
    """At 2025, degradation should be 0."""
    low, high = interpolate_degradation("SSP5-8.5", "coral_reef", 2025)
    assert low == 0.0
    assert high == 0.0


def test_interpolate_degradation_at_2050():
    """At 2050, should match anchor exactly."""
    low, high = interpolate_degradation("SSP2-4.5", "coral_reef", 2050)
    assert abs(low - 0.50) < 0.001
    assert abs(high - 0.70) < 0.001


def test_interpolate_degradation_at_2100():
    """At 2100, should match anchor exactly."""
    low, high = interpolate_degradation("SSP5-8.5", "coral_reef", 2100)
    assert abs(low - 0.99) < 0.001
    assert abs(high - 1.00) < 0.001


# ---------------------------------------------------------------------------
# Climate scenario returns proper response type
# ---------------------------------------------------------------------------

def test_climate_scenario_returns_scenario_response():
    """run_climate_scenario must return a ScenarioResponse with all required fields."""
    req = ScenarioRequest(
        scenario_type="climate", site_scope=["cabo_pulmo"],
        ssp_scenario="SSP2-4.5", target_year=2050,
    )
    result = run_climate_scenario(req)
    assert isinstance(result, ScenarioResponse)
    assert result.baseline_case.get("total_esv_usd") > 0
    assert result.scenario_case.get("total_esv_usd") > 0
    assert result.scenario_case["total_esv_usd"] < result.baseline_case["total_esv_usd"]
    assert result.confidence > 0
    assert result.confidence <= 0.85
    assert len(result.propagation_trace) > 0
    assert len(result.deltas) > 0
    assert result.uncertainty.p5 < result.uncertainty.p50 < result.uncertainty.p95
    assert len(result.caveats) > 0
    assert result.scenario_validity in ("in_domain", "partially_out_of_domain", "out_of_domain")


def test_climate_scenario_invalid_ssp_fails_closed():
    """Invalid SSP must return fail-closed response."""
    req = ScenarioRequest(
        scenario_type="climate", site_scope=["cabo_pulmo"],
        ssp_scenario="SSP9-9.9", target_year=2050,
    )
    result = run_climate_scenario(req)
    assert result.confidence == 0.0
    assert "insufficient" in result.answer.lower()


def test_climate_scenario_missing_site_fails_closed():
    """Unknown site must return fail-closed response."""
    req = ScenarioRequest(
        scenario_type="climate", site_scope=["atlantis"],
        ssp_scenario="SSP2-4.5", target_year=2050,
    )
    result = run_climate_scenario(req)
    assert result.confidence == 0.0
    assert "insufficient" in result.answer.lower()
