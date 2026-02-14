"""Tests for rule_compiler module.

Verifies that compile_axiom, compile_all, and compile_from_templates
produce correct InferenceRule objects, and that the InferenceEngine
refactor introduces zero behavioral changes.
"""

import json
import os
import tempfile

import pytest

from maris.provenance.bridge_axiom import BridgeAxiom
from maris.reasoning.rule_compiler import (
    compile_axiom,
    compile_all,
    compile_from_templates,
    _template_entry_to_axiom,
    _category_to_domains,
)
from maris.reasoning.inference_engine import InferenceEngine, InferenceRule


@pytest.fixture
def sample_axiom():
    """A single bridge axiom for testing."""
    return BridgeAxiom(
        axiom_id="BA-001",
        name="mpa_biomass_dive_tourism_value",
        rule="IF full_protection(Site) THEN wtp_increase(Site, 84%)",
        coefficient=0.84,
        input_domain="ecological",
        output_domain="service",
        source_doi="10.1038/s41598-024-83664-1",
        confidence="high",
        applicable_habitats=["coral_reef"],
    )


@pytest.fixture
def sample_axioms():
    """Multiple bridge axioms spanning ecological -> service -> financial."""
    return [
        BridgeAxiom(
            axiom_id="BA-001",
            name="mpa_biomass_dive_tourism_value",
            rule="IF full_protection(Site) THEN wtp_increase(Site, 84%)",
            coefficient=0.84,
            input_domain="ecological",
            output_domain="service",
            source_doi="10.1038/s41598-024-83664-1",
            confidence="high",
            applicable_habitats=["coral_reef"],
        ),
        BridgeAxiom(
            axiom_id="BA-014",
            name="carbon_stock_to_credit_value",
            rule="IF sequestration_tCO2_yr(Site, S) THEN credit_revenue(Site, S*30)",
            coefficient=30.0,
            input_domain="service",
            output_domain="financial",
            source_doi="10.1038/s44183-025-00111-y",
            confidence=0.85,
            applicable_habitats=["seagrass_meadow"],
        ),
        BridgeAxiom(
            axiom_id="BA-013",
            name="seagrass_carbon_sequestration_rate",
            rule="IF seagrass_area(Site, A) THEN sequestration(Site, A*0.84)",
            coefficient=0.84,
            input_domain="ecological",
            output_domain="service",
            source_doi="10.1038/s41467-025-64667-6",
            confidence="high",
            applicable_habitats=["seagrass_meadow"],
        ),
    ]


# ---------------------------------------------------------------------------
# compile_axiom tests
# ---------------------------------------------------------------------------

class TestCompileAxiom:
    def test_produces_inference_rule(self, sample_axiom):
        rule = compile_axiom(sample_axiom)
        assert isinstance(rule, InferenceRule)

    def test_rule_id_format(self, sample_axiom):
        rule = compile_axiom(sample_axiom)
        assert rule.rule_id == "rule:BA-001"

    def test_preserves_axiom_reference(self, sample_axiom):
        rule = compile_axiom(sample_axiom)
        assert rule.axiom is sample_axiom
        assert rule.axiom.axiom_id == "BA-001"

    def test_maps_domains(self, sample_axiom):
        rule = compile_axiom(sample_axiom)
        assert rule.input_domain == "ecological"
        assert rule.output_domain == "service"

    def test_maps_condition_from_rule(self, sample_axiom):
        rule = compile_axiom(sample_axiom)
        assert rule.condition == sample_axiom.rule

    def test_maps_applicable_habitats(self, sample_axiom):
        rule = compile_axiom(sample_axiom)
        assert rule.applicable_habitats == ["coral_reef"]


# ---------------------------------------------------------------------------
# compile_all tests
# ---------------------------------------------------------------------------

class TestCompileAll:
    def test_compiles_multiple_axioms(self, sample_axioms):
        rules = compile_all(sample_axioms)
        assert len(rules) == 3

    def test_keys_are_rule_ids(self, sample_axioms):
        rules = compile_all(sample_axioms)
        assert "rule:BA-001" in rules
        assert "rule:BA-014" in rules
        assert "rule:BA-013" in rules

    def test_values_are_inference_rules(self, sample_axioms):
        rules = compile_all(sample_axioms)
        for rule in rules.values():
            assert isinstance(rule, InferenceRule)

    def test_empty_list(self):
        rules = compile_all([])
        assert rules == {}


# ---------------------------------------------------------------------------
# compile_from_templates tests
# ---------------------------------------------------------------------------

class TestCompileFromTemplates:
    def test_loads_from_templates_file(self):
        templates_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "schemas",
            "bridge_axiom_templates.json",
        )
        if not os.path.exists(templates_path):
            pytest.skip("bridge_axiom_templates.json not found")
        rules = compile_from_templates(templates_path)
        assert len(rules) >= 16
        assert all(isinstance(r, InferenceRule) for r in rules.values())

    def test_loads_from_minimal_json(self):
        template_data = {
            "axioms": [
                {
                    "axiom_id": "BA-TEST",
                    "name": "test_axiom",
                    "category": "ecological_to_service",
                    "description": "Test axiom for unit tests",
                    "pattern": "IF test THEN result",
                    "coefficients": {
                        "primary": {"value": 1.5, "ci_low": 1.0, "ci_high": 2.0}
                    },
                    "applicable_habitats": ["coral_reef"],
                    "evidence_sources": [
                        {"doi": "10.1234/test", "tier": "T1"}
                    ],
                    "caveats": ["test caveat"],
                }
            ]
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(template_data, f)
            temp_path = f.name

        try:
            rules = compile_from_templates(temp_path)
            assert len(rules) == 1
            rule = rules["rule:BA-TEST"]
            assert rule.axiom.name == "test_axiom"
            assert rule.axiom.coefficient == 1.5
            assert rule.axiom.ci_low == 1.0
            assert rule.axiom.ci_high == 2.0
            assert rule.axiom.source_doi == "10.1234/test"
            assert rule.input_domain == "ecological"
            assert rule.output_domain == "service"
            assert rule.applicable_habitats == ["coral_reef"]
        finally:
            os.unlink(temp_path)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestCategoryToDomains:
    def test_ecological_to_service(self):
        assert _category_to_domains("ecological_to_service") == ("ecological", "service")

    def test_service_to_financial(self):
        assert _category_to_domains("service_to_financial") == ("service", "financial")

    def test_ecological_to_financial(self):
        assert _category_to_domains("ecological_to_financial") == ("ecological", "financial")

    def test_unknown_defaults(self):
        assert _category_to_domains("unknown") == ("ecological", "service")


class TestTemplateEntryToAxiom:
    def test_converts_entry(self):
        entry = {
            "axiom_id": "BA-099",
            "name": "test_axiom",
            "category": "service_to_financial",
            "pattern": "IF x THEN y",
            "coefficients": {"primary": 42.0},
            "applicable_habitats": ["mangrove"],
            "evidence_sources": [{"doi": "10.9999/test"}],
            "caveats": ["sample caveat"],
        }
        axiom = _template_entry_to_axiom(entry)
        assert isinstance(axiom, BridgeAxiom)
        assert axiom.axiom_id == "BA-099"
        assert axiom.coefficient == 42.0
        assert axiom.input_domain == "service"
        assert axiom.output_domain == "financial"
        assert axiom.source_doi == "10.9999/test"
        assert axiom.applicable_habitats == ["mangrove"]

    def test_handles_nested_coefficient(self):
        entry = {
            "axiom_id": "BA-100",
            "category": "ecological_to_service",
            "coefficients": {
                "primary": {"value": 3.14, "ci_low": 2.0, "ci_high": 4.0}
            },
            "evidence_sources": [],
        }
        axiom = _template_entry_to_axiom(entry)
        assert axiom.coefficient == 3.14
        assert axiom.ci_low == 2.0
        assert axiom.ci_high == 4.0

    def test_handles_empty_coefficients(self):
        entry = {
            "axiom_id": "BA-101",
            "category": "ecological_to_service",
            "coefficients": {},
            "evidence_sources": [],
        }
        axiom = _template_entry_to_axiom(entry)
        assert axiom.coefficient == 0.0


# ---------------------------------------------------------------------------
# InferenceEngine behavioral equivalence (regression)
# ---------------------------------------------------------------------------

class TestInferenceEngineRefactorRegression:
    """Verify InferenceEngine behaves identically after refactor."""

    def test_register_axiom_returns_rule_id(self, sample_axiom):
        engine = InferenceEngine()
        rule_id = engine.register_axiom(sample_axiom)
        assert rule_id == "rule:BA-001"

    def test_register_axiom_creates_correct_rule(self, sample_axiom):
        engine = InferenceEngine()
        engine.register_axiom(sample_axiom)
        rule = engine.get_rule("rule:BA-001")
        assert rule is not None
        assert rule.axiom.axiom_id == "BA-001"
        assert rule.input_domain == "ecological"
        assert rule.output_domain == "service"
        assert rule.condition == sample_axiom.rule
        assert rule.applicable_habitats == ["coral_reef"]

    def test_register_axioms_count(self, sample_axioms):
        engine = InferenceEngine()
        count = engine.register_axioms(sample_axioms)
        assert count == 3
        assert engine.rule_count == 3

    def test_forward_chain_unchanged(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axioms(sample_axioms)
        facts = {"ecological": {"biomass_ratio": 4.63}}
        steps = engine.forward_chain(facts)
        axiom_ids = {s.axiom_id for s in steps}
        assert "BA-001" in axiom_ids or "BA-013" in axiom_ids
        assert "BA-014" in axiom_ids

    def test_backward_chain_unchanged(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axioms(sample_axioms)
        needed = engine.backward_chain("financial")
        axiom_ids = [n["axiom_id"] for n in needed]
        assert "BA-014" in axiom_ids

    def test_find_chain_unchanged(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axioms(sample_axioms)
        chain = engine.find_chain("ecological", "financial")
        assert len(chain) == 2
        assert chain[0].input_domain == "ecological"
        assert chain[-1].output_domain == "financial"
