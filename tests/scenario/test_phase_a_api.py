"""Phase A API tests - classifier, parser, and route integration for scenario_analysis.

Minimum 15 tests covering:
- Classifier correctly routes scenario questions to scenario_analysis
- Existing 6 categories remain unchanged (no regressions)
- Parser extracts SSP scenarios, target years, scenario types, and site aliases
- Parser returns ScenarioRequest instances
"""

import pytest

from maris.query.classifier import QueryClassifier
from maris.scenario.scenario_parser import parse_scenario_request, ScenarioRequest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def classifier():
    """Classifier without LLM fallback."""
    return QueryClassifier(llm=None)


# ---------------------------------------------------------------------------
# Classifier: scenario_analysis category
# ---------------------------------------------------------------------------


class TestScenarioClassifier:
    """Verify that scenario questions route to scenario_analysis."""

    def test_scenario_classifier_what_if_question(self, classifier):
        result = classifier.classify("What if we invest $10M to restore coral reefs?")
        assert result["category"] == "scenario_analysis"

    def test_scenario_classifier_counterfactual_question(self, classifier):
        result = classifier.classify(
            "What would Cabo Pulmo be worth without protection?"
        )
        assert result["category"] == "scenario_analysis"

    def test_scenario_classifier_tipping_point_question(self, classifier):
        result = classifier.classify(
            "How close is Ningaloo to a tipping point?"
        )
        assert result["category"] == "scenario_analysis"

    def test_scenario_classifier_carbon_price_question(self, classifier):
        result = classifier.classify(
            "What if carbon price doubles to $50/tCO2?"
        )
        assert result["category"] == "scenario_analysis"

    def test_scenario_classifier_blue_carbon_revenue_button(self, classifier):
        """Quick-query button for blue carbon uses 'revenue' not 'price' - must still classify."""
        result = classifier.classify(
            "What blue carbon revenue could Sundarbans Reserve generate at $45/tCO2?"
        )
        assert result["category"] == "scenario_analysis"

    def test_scenario_classifier_ssp_question(self, classifier):
        result = classifier.classify(
            "What happens to Belize under SSP2-4.5 by 2050?"
        )
        assert result["category"] == "scenario_analysis"

    def test_scenario_classifier_stress_test(self, classifier):
        result = classifier.classify(
            "Run a stress test on the portfolio under compound warming"
        )
        assert result["category"] == "scenario_analysis"

    def test_scenario_classifier_nature_var(self, classifier):
        result = classifier.classify(
            "What is the portfolio nature var at 95th percentile?"
        )
        assert result["category"] == "scenario_analysis"

    def test_scenario_classifier_invest_restore(self, classifier):
        result = classifier.classify(
            "What if we invest $5M to restore mangroves at Cispata?"
        )
        assert result["category"] == "scenario_analysis"

    def test_scenario_analysis_category_returned_by_classifier(self, classifier):
        """Verify the classifier returns the literal string 'scenario_analysis'."""
        result = classifier.classify(
            "What would Sundarbans be worth without protection?"
        )
        assert result["category"] == "scenario_analysis"
        assert result["confidence"] > 0.0


# ---------------------------------------------------------------------------
# Classifier: existing categories NOT reclassified as scenario
# ---------------------------------------------------------------------------


class TestExistingCategoriesUnchanged:
    """Verify that all 6 existing categories still classify correctly."""

    def test_site_valuation_not_reclassified_as_scenario(self, classifier):
        """'What is Cabo Pulmo worth?' -> site_valuation, NOT scenario."""
        result = classifier.classify("What is Cabo Pulmo worth?")
        assert result["category"] == "site_valuation"

    def test_comparison_not_reclassified_as_scenario(self, classifier):
        """'Compare Cabo Pulmo and Great Barrier Reef' -> comparison, NOT scenario."""
        result = classifier.classify("Compare Cabo Pulmo and Great Barrier Reef")
        assert result["category"] == "comparison"

    def test_existing_categories_unchanged(self, classifier):
        """Spot-check all 6 existing categories still work correctly."""
        cases = [
            ("What is the ESV of Cabo Pulmo?", "site_valuation"),
            ("What evidence supports the valuation?", "provenance_drilldown"),
            ("Explain bridge axiom BA-001", "axiom_explanation"),
            ("Compare Cabo Pulmo and Great Barrier Reef", "comparison"),
            ("What are the governance risks for Raja Ampat?", "risk_assessment"),
            ("What is blue carbon?", "concept_explanation"),
        ]
        for question, expected in cases:
            result = classifier.classify(question)
            assert result["category"] == expected, (
                f"Expected '{expected}' for '{question}', got '{result['category']}'"
            )

    def test_pure_risk_stays_risk_assessment(self, classifier):
        """Pure risk query without scenario triggers stays as risk_assessment."""
        result = classifier.classify("What are the climate risks for Cabo Pulmo?")
        assert result["category"] == "risk_assessment"

    def test_provenance_unchanged(self, classifier):
        result = classifier.classify("What DOIs support BA-013?")
        assert result["category"] == "provenance_drilldown"

    def test_axiom_unchanged(self, classifier):
        result = classifier.classify("What is the coefficient for BA-002?")
        assert result["category"] == "axiom_explanation"


# ---------------------------------------------------------------------------
# Parser: SSP extraction
# ---------------------------------------------------------------------------


class TestParserSSP:
    """Verify SSP scenario extraction from natural language."""

    def test_parser_extracts_ssp_scenario(self):
        req = parse_scenario_request(
            "What happens to Belize under SSP2-4.5 by 2050?"
        )
        assert req.ssp_scenario == "SSP2-4.5"

    def test_parser_extracts_ssp1_2_6(self):
        req = parse_scenario_request("ESV under SSP1-2.6 by 2100")
        assert req.ssp_scenario == "SSP1-2.6"

    def test_parser_extracts_ssp5_8_5(self):
        req = parse_scenario_request(
            "What happens to Sundarbans under SSP5-8.5 by 2100?"
        )
        assert req.ssp_scenario == "SSP5-8.5"

    def test_parser_ssp_sets_climate_type(self):
        req = parse_scenario_request("Under SSP2-4.5 what happens?")
        assert req.scenario_type == "climate"


# ---------------------------------------------------------------------------
# Parser: target year and time horizon
# ---------------------------------------------------------------------------


class TestParserTimeHorizon:
    def test_parser_extracts_target_year(self):
        req = parse_scenario_request("What happens by 2050?")
        assert req.target_year == 2050

    def test_parser_extracts_time_horizon_years(self):
        req = parse_scenario_request("Over 30 years what happens?")
        assert req.time_horizon_years == 30

    def test_parser_target_year_sets_time_horizon(self):
        req = parse_scenario_request("What happens by 2050?")
        assert req.time_horizon_years == 25  # 2050 - 2025

    def test_parser_default_time_horizon(self):
        req = parse_scenario_request("What if protection is removed?")
        assert req.time_horizon_years == 10  # default


# ---------------------------------------------------------------------------
# Parser: scenario type inference
# ---------------------------------------------------------------------------


class TestParserScenarioType:
    def test_parser_infers_counterfactual_type(self):
        req = parse_scenario_request(
            "What would Cabo Pulmo be worth without protection?"
        )
        assert req.scenario_type == "counterfactual"

    def test_parser_infers_climate_type(self):
        req = parse_scenario_request(
            "How does warming affect Belize reef?"
        )
        assert req.scenario_type == "climate"

    def test_parser_infers_market_type(self):
        req = parse_scenario_request(
            "What blue carbon revenue at $45/tCO2 for Sundarbans?"
        )
        assert req.scenario_type == "market"

    def test_parser_infers_intervention_type(self):
        req = parse_scenario_request(
            "What if we restore 2000 hectares of mangrove?"
        )
        assert req.scenario_type == "intervention"

    def test_parser_infers_portfolio_type(self):
        req = parse_scenario_request(
            "What is the portfolio nature var under compound stress?"
        )
        assert req.scenario_type == "portfolio"

    def test_parser_infers_tipping_point_type(self):
        req = parse_scenario_request(
            "How close is Cabo Pulmo to a tipping point?"
        )
        assert req.scenario_type == "tipping_point"


# ---------------------------------------------------------------------------
# Parser: site resolution
# ---------------------------------------------------------------------------


class TestParserSiteResolution:
    def test_parser_site_alias_resolution(self):
        req = parse_scenario_request(
            "What would Cabo Pulmo be worth without protection?"
        )
        assert "Cabo Pulmo National Park" in req.site_scope

    def test_parser_site_from_explicit_param(self):
        req = parse_scenario_request(
            "Without protection what happens?",
            site="Cabo Pulmo National Park",
        )
        assert "Cabo Pulmo National Park" in req.site_scope

    def test_parser_site_alias_sundarbans(self):
        req = parse_scenario_request(
            "What happens to Sundarbans under SSP5-8.5?"
        )
        assert "Sundarbans Reserve Forest" in req.site_scope

    def test_parser_site_alias_cispata(self):
        req = parse_scenario_request(
            "Carbon revenue for Cispata Bay at $45/tCO2?"
        )
        assert "Cispata Bay Mangrove Conservation Area" in req.site_scope


# ---------------------------------------------------------------------------
# Parser: returns ScenarioRequest instance
# ---------------------------------------------------------------------------


class TestParserReturnsModel:
    def test_parser_returns_scenario_request_instance(self):
        req = parse_scenario_request(
            "What would Cabo Pulmo be worth without protection?"
        )
        assert isinstance(req, ScenarioRequest)

    def test_parser_returns_populated_fields(self):
        req = parse_scenario_request(
            "What happens to Belize under SSP2-4.5 by 2050?"
        )
        assert req.scenario_type == "climate"
        assert req.ssp_scenario == "SSP2-4.5"
        assert req.target_year == 2050
        assert len(req.site_scope) >= 1

    def test_parser_extracts_carbon_price_assumption(self):
        req = parse_scenario_request(
            "What blue carbon revenue could Sundarbans generate at $45/tCO2?"
        )
        assert req.assumptions.get("carbon_price_usd") == 45.0

    def test_parser_extracts_investment_assumption(self):
        req = parse_scenario_request(
            "What if we invest $5M to restore mangroves?"
        )
        assert req.assumptions.get("investment_usd") == 5_000_000.0
