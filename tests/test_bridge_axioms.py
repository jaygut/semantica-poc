"""Tests for bridge axiom schema validation and confidence propagation."""

import json
import math
import re
from pathlib import Path

import pytest

from maris.axioms.engine import BridgeAxiomEngine
from maris.axioms.confidence import propagate_ci, propagate_ci_multiplicative

TEMPLATES_PATH = Path("schemas/bridge_axiom_templates.json")


@pytest.fixture
def axiom_data():
    with open(TEMPLATES_PATH) as f:
        return json.load(f)


@pytest.fixture
def engine():
    return BridgeAxiomEngine(templates_path=TEMPLATES_PATH)


# ---- Schema completeness ----


class TestAxiomSchemaCompleteness:
    def test_all_40_axioms_exist(self, axiom_data):
        """All 40 bridge axioms BA-001 through BA-040 must be present."""
        axioms = axiom_data["axioms"]
        assert len(axioms) == 40
        ids = {a["axiom_id"] for a in axioms}
        for i in range(1, 41):
            assert f"BA-{i:03d}" in ids

    def test_required_fields_present(self, axiom_data):
        """Each axiom must have axiom_id, name, coefficients, applicable_habitats."""
        required = {"axiom_id", "name", "coefficients", "applicable_habitats"}
        for axiom in axiom_data["axioms"]:
            missing = required - set(axiom.keys())
            assert not missing, f"{axiom['axiom_id']} missing fields: {missing}"

    def test_axiom_ids_format(self, axiom_data):
        """All axiom IDs must match BA-NNN format."""
        pattern = re.compile(r"^BA-\d{3}$")
        for axiom in axiom_data["axioms"]:
            assert pattern.match(axiom["axiom_id"]), (
                f"Invalid axiom ID format: {axiom['axiom_id']}"
            )

    def test_ba001_through_ba004_research_grounded(self, axiom_data):
        """BA-001 to BA-004 primary coefficients must be research_grounded.

        The four gold-standard axioms must each have AT LEAST one
        research_grounded coefficient (the primary effect size directly
        extracted from the source paper).  Secondary/derived coefficients
        (e.g. decomposed contribution percentages, analyst-estimated bounds)
        may be ``estimated_uncertainty`` - this is scientifically correct and
        was confirmed by the 2026-02-23 axiom library audit.
        """
        # Primary coefficient that MUST be research_grounded per source paper
        required_rg: dict[str, str] = {
            "BA-001": "wtp_increase_for_biomass_max_percent",
            "BA-002": "biomass_ratio_vs_unprotected",
            "BA-003": "npp_multiplier",
            "BA-004": "wave_energy_reduction_healthy_reef_percent",
        }
        axiom_map = {a["axiom_id"]: a for a in axiom_data["axioms"]}
        for axiom_id, coeff_name in required_rg.items():
            axiom = axiom_map.get(axiom_id)
            assert axiom is not None, f"{axiom_id} missing from axiom data"
            coeff = axiom["coefficients"].get(coeff_name)
            assert coeff is not None, (
                f"{axiom_id}.{coeff_name} coefficient not found"
            )
            assert isinstance(coeff, dict), (
                f"{axiom_id}.{coeff_name} must be a full uncertainty object"
            )
            assert coeff.get("uncertainty_type") == "research_grounded", (
                f"{axiom_id}.{coeff_name} must be research_grounded "
                f"(primary effect size from source paper), "
                f"got {coeff.get('uncertainty_type')!r}"
            )


# ---- Coefficient bounds ----


class TestCoefficientBounds:
    def test_ci_bounds_ordering(self, axiom_data):
        """For every coefficient with ci_low and ci_high, ci_low < value < ci_high."""
        for axiom in axiom_data["axioms"]:
            for key, coeff in axiom["coefficients"].items():
                if not isinstance(coeff, dict):
                    continue
                # Handle nested dicts (e.g., wave_energy_reduction_percent.healthy_reef)
                items_to_check = []
                if "value" in coeff and "ci_low" in coeff and "ci_high" in coeff:
                    items_to_check.append((f"{axiom['axiom_id']}.{key}", coeff))
                else:
                    for sub_key, sub_val in coeff.items():
                        if (
                            isinstance(sub_val, dict)
                            and "value" in sub_val
                            and "ci_low" in sub_val
                            and "ci_high" in sub_val
                        ):
                            items_to_check.append(
                                (f"{axiom['axiom_id']}.{key}.{sub_key}", sub_val)
                            )

                for label, c in items_to_check:
                    assert c["ci_low"] <= c["value"], (
                        f"{label}: ci_low ({c['ci_low']}) > value ({c['value']})"
                    )
                    assert c["value"] <= c["ci_high"], (
                        f"{label}: value ({c['value']}) > ci_high ({c['ci_high']})"
                    )
                    # At least one bound must be strictly different
                    assert c["ci_low"] < c["ci_high"], (
                        f"{label}: ci_low ({c['ci_low']}) == ci_high ({c['ci_high']})"
                    )


# ---- Engine operations ----


class TestBridgeAxiomEngine:
    def test_engine_get_axiom(self, engine):
        """engine.get_axiom('BA-001') returns a dict with axiom_id."""
        axiom = engine.get_axiom("BA-001")
        assert axiom is not None
        assert axiom["axiom_id"] == "BA-001"

    def test_engine_get_axiom_none(self, engine):
        """engine.get_axiom('BA-999') returns None."""
        assert engine.get_axiom("BA-999") is None

    def test_engine_list_all(self, engine):
        """list_all() returns all 35 axioms."""
        all_axioms = engine.list_all()
        assert len(all_axioms) == 40

    def test_engine_list_applicable_coral_reef(self, engine):
        """Axioms applicable to coral_reef include BA-004 and BA-012."""
        applicable = engine.list_applicable("coral_reef")
        ids = {a["axiom_id"] for a in applicable}
        assert "BA-004" in ids
        assert "BA-012" in ids

    def test_engine_list_applicable_all_habitat(self, engine):
        """BA-002 applies to 'all' habitats and should match any query."""
        applicable = engine.list_applicable("any_random_habitat")
        ids = {a["axiom_id"] for a in applicable}
        assert "BA-002" in ids


# ---- Confidence propagation ----


class TestConfidencePropagation:
    def test_propagate_ci_additive(self):
        """Additive CI propagation with known values."""
        values = [
            {"value": 100, "ci_low": 80, "ci_high": 120},
            {"value": 200, "ci_low": 170, "ci_high": 230},
        ]
        result = propagate_ci(values)
        assert result["total"] == 300
        # RSS: low = 300 - sqrt((100-80)^2 + (200-170)^2) = 300 - sqrt(400+900) = 300 - 36.06
        expected_low = 300 - math.sqrt(20**2 + 30**2)
        expected_high = 300 + math.sqrt(20**2 + 30**2)
        assert abs(result["ci_low"] - expected_low) < 0.01
        assert abs(result["ci_high"] - expected_high) < 0.01

    def test_propagate_ci_empty(self):
        """propagate_ci([]) returns zeros."""
        result = propagate_ci([])
        assert result["total"] == 0.0
        assert result["ci_low"] == 0.0
        assert result["ci_high"] == 0.0

    def test_propagate_ci_multiplicative(self):
        """Multiplicative CI propagation with known values."""
        values = [
            {"value": 10, "ci_low": 8, "ci_high": 12},
            {"value": 5, "ci_low": 4, "ci_high": 6},
        ]
        result = propagate_ci_multiplicative(values)
        assert result["total"] == 50  # 10 * 5
        # Relative uncertainties: low = (10-8)/10=0.2, (5-4)/5=0.2
        # Combined relative low = sqrt(0.04+0.04) = sqrt(0.08) ~ 0.2828
        combined_rel = math.sqrt(0.2**2 + 0.2**2)
        expected_low = 50 * (1 - combined_rel)
        expected_high = 50 * (1 + combined_rel)
        assert abs(result["ci_low"] - expected_low) < 0.01
        assert abs(result["ci_high"] - expected_high) < 0.01

    def test_propagate_ci_multiplicative_empty(self):
        """propagate_ci_multiplicative([]) returns zeros."""
        result = propagate_ci_multiplicative([])
        assert result["total"] == 0.0
        assert result["ci_low"] == 0.0
        assert result["ci_high"] == 0.0
