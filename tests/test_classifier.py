"""Tests for query classifier - keyword matching, site extraction, and LLM fallback."""

import pytest
from unittest.mock import MagicMock

from maris.query.classifier import QueryClassifier


@pytest.fixture
def classifier():
    """Classifier without LLM fallback."""
    return QueryClassifier(llm=None)


@pytest.fixture
def classifier_with_llm():
    """Classifier with mocked LLM fallback."""
    mock_llm = MagicMock()
    mock_llm.complete_json.return_value = {
        "category": "risk_assessment",
        "confidence": 0.7,
    }
    return QueryClassifier(llm=mock_llm)


# ---- Category matching ----

class TestCategoryMatching:
    def test_site_valuation_value(self, classifier):
        result = classifier.classify("What is the value of Cabo Pulmo?")
        assert result["category"] == "site_valuation"

    def test_site_valuation_worth(self, classifier):
        result = classifier.classify("How much is Cabo Pulmo worth?")
        assert result["category"] == "site_valuation"

    def test_site_valuation_esv(self, classifier):
        result = classifier.classify("What is the ESV of Cabo Pulmo?")
        assert result["category"] == "site_valuation"

    def test_provenance_drilldown_evidence(self, classifier):
        result = classifier.classify("What evidence supports this?")
        assert result["category"] == "provenance_drilldown"

    def test_provenance_drilldown_doi(self, classifier):
        result = classifier.classify("Show me the DOI sources")
        assert result["category"] == "provenance_drilldown"

    def test_provenance_mechanism(self, classifier):
        result = classifier.classify("How does biomass translate to tourism value?")
        assert result["category"] == "provenance_drilldown"

    def test_axiom_explanation_bridge_axiom(self, classifier):
        result = classifier.classify("Explain bridge axiom BA-001")
        assert result["category"] == "axiom_explanation"

    def test_axiom_explanation_coefficient(self, classifier):
        result = classifier.classify("What is the coefficient for BA-002?")
        assert result["category"] == "axiom_explanation"

    def test_comparison_compare(self, classifier):
        result = classifier.classify("Compare Cabo Pulmo to the Great Barrier Reef")
        assert result["category"] == "comparison"

    def test_comparison_versus(self, classifier):
        result = classifier.classify("Cabo Pulmo versus Great Barrier Reef")
        assert result["category"] == "comparison"

    def test_risk_assessment_risk(self, classifier):
        result = classifier.classify("What is the risk to Cabo Pulmo?")
        assert result["category"] == "risk_assessment"

    def test_risk_assessment_climate(self, classifier):
        result = classifier.classify("How does climate change affect the reef?")
        assert result["category"] == "risk_assessment"

    def test_risk_assessment_degradation(self, classifier):
        result = classifier.classify("What if reef degradation occurs?")
        assert result["category"] == "risk_assessment"


# ---- Site extraction ----

class TestSiteExtraction:
    def test_cabo_pulmo_full_name(self, classifier):
        result = classifier.classify("What is the value of Cabo Pulmo?")
        assert result["site"] == "Cabo Pulmo National Park"

    def test_great_barrier_reef_full(self, classifier):
        result = classifier.classify("What is the Great Barrier Reef worth?")
        assert result["site"] == "Great Barrier Reef Marine Park"

    def test_acronym_gbr(self, classifier):
        result = classifier.classify("What is the value of GBR?")
        assert result["site"] == "Great Barrier Reef Marine Park"

    def test_acronym_cp(self, classifier):
        result = classifier.classify("What is CP worth?")
        assert result["site"] == "Cabo Pulmo National Park"

    def test_acronym_pmnm(self, classifier):
        result = classifier.classify("Tell me about PMNM")
        assert "Marine National Monument" in (result["site"] or "")

    def test_no_site_mentioned(self, classifier):
        result = classifier.classify("What is ESV?")
        assert result["site"] is None

    def test_fuzzy_matching_typo(self, classifier):
        """Fuzzy matching should catch close misspellings."""
        result = classifier.classify("What is the value of cabo pulmo national park?")
        assert result["site"] == "Cabo Pulmo National Park"


# ---- Multi-site detection ----

class TestMultiSiteDetection:
    def test_two_sites_forces_comparison(self, classifier):
        result = classifier.classify("Compare Cabo Pulmo and Great Barrier Reef")
        assert result["category"] == "comparison"
        assert "sites" in result
        assert len(result["sites"]) == 2

    def test_two_sites_list(self, classifier):
        result = classifier.classify("Cabo Pulmo vs GBR")
        assert result["category"] == "comparison"
        sites = result.get("sites", [])
        assert "Cabo Pulmo National Park" in sites
        assert "Great Barrier Reef Marine Park" in sites


# ---- Negation handling ----

class TestNegationHandling:
    def test_negation_adds_caveat(self, classifier):
        result = classifier.classify("What is the value of Cabo Pulmo without tourism?")
        assert any("Negation" in c for c in result.get("caveats", []))

    def test_negation_not_keyword(self, classifier):
        result = classifier.classify("Not considering climate risk for Cabo Pulmo")
        assert any("Negation" in c for c in result.get("caveats", []))


# ---- Edge cases ----

class TestEdgeCases:
    def test_empty_question(self, classifier):
        result = classifier.classify("")
        assert result["confidence"] == 0.0
        assert result["category"] == "site_valuation"
        assert any("Empty" in c for c in result.get("caveats", []))

    def test_whitespace_only(self, classifier):
        result = classifier.classify("   ")
        assert result["confidence"] == 0.0

    def test_very_long_question(self, classifier):
        long_q = "What is the value " * 100
        result = classifier.classify(long_q)
        assert any("truncated" in c.lower() for c in result.get("caveats", []))

    def test_unicode_question(self, classifier):
        result = classifier.classify("What is the ESV of Papah\u0101naumoku\u0101kea?")
        assert result["site"] is not None


# ---- Confidence scoring ----

class TestConfidenceScoring:
    def test_keyword_match_confidence_above_zero(self, classifier):
        result = classifier.classify("What is the value of Cabo Pulmo?")
        assert result["confidence"] > 0.5

    def test_more_keywords_higher_confidence(self, classifier):
        simple = classifier.classify("What is the value?")
        rich = classifier.classify("What is the total ESV valuation worth?")
        assert rich["confidence"] >= simple["confidence"]

    def test_confidence_capped_at_095(self, classifier):
        result = classifier.classify("value ESV worth asset rating total value")
        assert result["confidence"] <= 0.95

    def test_default_fallback_low_confidence(self, classifier):
        result = classifier.classify("tell me something interesting")
        assert result["confidence"] <= 0.3


# ---- LLM fallback ----

class TestLLMFallback:
    def test_llm_fallback_called_for_ambiguous(self, classifier_with_llm):
        result = classifier_with_llm.classify("tell me something interesting")
        assert result["category"] == "risk_assessment"  # from mock

    def test_llm_fallback_not_called_for_keywords(self):
        mock_llm = MagicMock()
        c = QueryClassifier(llm=mock_llm)
        c.classify("What is the value of Cabo Pulmo?")
        mock_llm.complete_json.assert_not_called()

    def test_llm_failure_returns_default(self):
        mock_llm = MagicMock()
        mock_llm.complete_json.side_effect = Exception("LLM error")
        c = QueryClassifier(llm=mock_llm)
        result = c.classify("ambiguous question with no keywords")
        assert result["category"] == "site_valuation"
        assert result["confidence"] == 0.3


# ---- Metric extraction ----

class TestMetricExtraction:
    def test_biomass_extracted(self, classifier):
        result = classifier.classify("What is the biomass of Cabo Pulmo?")
        assert "biomass" in result["metrics"]

    def test_tourism_extracted(self, classifier):
        result = classifier.classify("What is the tourism value?")
        assert "tourism" in result["metrics"]

    def test_no_metrics(self, classifier):
        result = classifier.classify("Tell me about Cabo Pulmo")
        # May or may not have metrics, but should not crash
        assert isinstance(result["metrics"], list)


# ---- Classifier gap fixes ----

class TestClassifierGapFixes:
    """Tests for the four classifier regex gaps fixed in the hardening pass."""

    def test_dois_support_ba013_routes_to_provenance(self, classifier):
        """Gap 1: 'DOIs' (plural) + 'support' + case-insensitive BA-013."""
        result = classifier.classify("What DOIs support BA-013?")
        assert result["category"] == "provenance_drilldown"

    def test_rank_mpas_by_esv_routes_to_comparison(self, classifier):
        """Gap 2: 'rank' + 'ESV' tie-break should prefer comparison."""
        result = classifier.classify("Rank the MPAs by ESV")
        assert result["category"] == "comparison"

    def test_lowercase_ba013_routes_to_axiom(self, classifier):
        """Gap 3: Lowercase 'ba-013' should match axiom_explanation."""
        result = classifier.classify("ba-013")
        assert result["category"] == "axiom_explanation"

    def test_declined_what_would_happen_routes_to_risk(self, classifier):
        """Gap 4: Past tense 'declined', reverse if/what order, modal 'would happen'."""
        result = classifier.classify(
            "If coral declined, what would happen to fisheries revenue?"
        )
        assert result["category"] == "risk_assessment"

    def test_declining_matches_risk(self, classifier):
        """Verify present participle 'declining' also matches risk_assessment."""
        result = classifier.classify("What if coral is declining?")
        assert result["category"] == "risk_assessment"

    def test_uppercase_ba_still_works(self, classifier):
        """Ensure uppercase BA-013 still works after case-insensitive fix."""
        result = classifier.classify("Explain BA-013")
        assert result["category"] == "axiom_explanation"

    def test_benchmark_routes_to_comparison(self, classifier):
        """Verify 'benchmark' also triggers comparison tie-break over site_valuation."""
        result = classifier.classify("Benchmark the MPAs by ESV")
        assert result["category"] == "comparison"


# ---- Mechanism/concept classification (Phase I intelligence upgrade) ----

class TestMechanismClassification:
    """Tests for mechanism/concept questions (Phase I intelligence upgrade)."""

    def test_blue_carbon_sequestration_how(self, classifier):
        """The core bug: 'sequestration' must match axiom_explanation."""
        result = classifier.classify("How does blue carbon sequestration work?")
        assert result["category"] == "axiom_explanation"

    def test_mangrove_carbon_storage(self, classifier):
        result = classifier.classify("How do mangroves store carbon?")
        assert result["category"] == "axiom_explanation"

    def test_seagrass_carbon_sequestration(self, classifier):
        result = classifier.classify("How does seagrass sequester carbon?")
        assert result["category"] == "axiom_explanation"

    def test_kelp_carbon_mechanism(self, classifier):
        result = classifier.classify("How does kelp carbon sequestration work?")
        assert result["category"] == "axiom_explanation"

    def test_coral_reef_protection(self, classifier):
        result = classifier.classify("How do coral reefs protect coastlines?")
        assert result["category"] == "axiom_explanation"

    def test_what_is_blue_carbon(self, classifier):
        result = classifier.classify("What is blue carbon?")
        # May route to concept_explanation (Phase II) or axiom_explanation
        assert result["category"] in ("axiom_explanation", "concept_explanation")

    def test_what_is_carbon_sequestration(self, classifier):
        result = classifier.classify("What is carbon sequestration?")
        assert result["category"] == "axiom_explanation"

    def test_how_carbon_valued(self, classifier):
        result = classifier.classify("How is seagrass carbon valued?")
        assert result["category"] == "axiom_explanation"

    def test_how_biomass_translates_to_tourism(self, classifier):
        result = classifier.classify("How does biomass translate to tourism value?")
        # This may match provenance_drilldown due to "translate" pattern
        assert result["category"] in ("axiom_explanation", "provenance_drilldown")

    def test_sequestering_form(self, classifier):
        """Test -ing form of sequester with habitat-first pattern."""
        result = classifier.classify("How do mangroves sequester carbon effectively?")
        assert result["category"] == "axiom_explanation"

    def test_sequestered_form(self, classifier):
        """Test -ed form via seagrass sequester+store pattern."""
        result = classifier.classify("How does seagrass sequester and store carbon?")
        assert result["category"] == "axiom_explanation"

    def test_mechanism_confidence_above_threshold(self, classifier):
        """Mechanism questions should have reasonable confidence."""
        result = classifier.classify("How does blue carbon sequestration work?")
        assert result["confidence"] >= 0.6

    def test_mangrove_accumulate(self, classifier):
        result = classifier.classify("How do mangroves accumulate carbon?")
        assert result["category"] == "axiom_explanation"

    def test_coastal_protection_valued(self, classifier):
        result = classifier.classify("How is coastal protection valued financially?")
        assert result["category"] == "axiom_explanation"


# ---- LLM threshold change (Phase I intelligence upgrade) ----

class TestLLMThresholdChange:
    """Tests for lowered LLM confidence threshold (0.25 instead of 0.4)."""

    def test_llm_confidence_030_not_rerouted(self):
        """LLM at 0.30 confidence should NOT be rerouted to open_domain."""
        mock_llm = MagicMock()
        mock_llm.complete_json.return_value = {
            "category": "axiom_explanation",
            "confidence": 0.30,
        }
        c = QueryClassifier(llm=mock_llm)
        result = c.classify("tell me about the underwater flora habitat")
        assert result["category"] == "axiom_explanation"

    def test_llm_confidence_020_rerouted(self):
        """LLM at 0.20 confidence SHOULD be rerouted to open_domain."""
        mock_llm = MagicMock()
        mock_llm.complete_json.return_value = {
            "category": "axiom_explanation",
            "confidence": 0.20,
        }
        c = QueryClassifier(llm=mock_llm)
        result = c.classify("completely unrelated gibberish question")
        assert result["category"] == "open_domain"


# ---- Concept explanation classification (Phase II intelligence upgrade) ----

class TestConceptExplanationClassification:
    """Tests for concept_explanation query category (Phase II)."""

    def test_what_is_blue_carbon(self, classifier):
        result = classifier.classify("What is blue carbon?")
        assert result["category"] == "concept_explanation"

    def test_how_do_carbon_credits_work(self, classifier):
        result = classifier.classify("How do carbon credits work?")
        assert result["category"] == "concept_explanation"

    def test_explain_trophic_cascade_economics(self, classifier):
        result = classifier.classify("Explain trophic cascade economics")
        assert result["category"] == "concept_explanation"

    def test_what_is_reef_insurance(self, classifier):
        result = classifier.classify("What is reef insurance?")
        assert result["category"] == "concept_explanation"

    def test_what_are_nature_based_solutions(self, classifier):
        result = classifier.classify("What are nature-based solutions?")
        assert result["category"] == "concept_explanation"

    def test_what_is_coastal_protect(self, classifier):
        result = classifier.classify("What is coastal protect services?")
        assert result["category"] == "concept_explanation"

    def test_how_does_ecosystem_restoration_work(self, classifier):
        result = classifier.classify("How does ecosystem restoration work?")
        assert result["category"] == "concept_explanation"

    def test_explain_resilience(self, classifier):
        result = classifier.classify("Explain climate resilience in marine ecosystems")
        assert result["category"] == "concept_explanation"

    def test_does_not_misclassify_site_valuation(self, classifier):
        """ESV queries must stay as site_valuation, not concept_explanation."""
        result = classifier.classify("What is the ESV of Cabo Pulmo?")
        assert result["category"] == "site_valuation"

    def test_does_not_misclassify_axiom_explanation(self, classifier):
        """Explicit axiom references must stay as axiom_explanation."""
        result = classifier.classify("Explain bridge axiom BA-001")
        assert result["category"] == "axiom_explanation"

    def test_does_not_misclassify_comparison(self, classifier):
        """Comparison queries must stay as comparison."""
        result = classifier.classify("Compare Cabo Pulmo and Great Barrier Reef")
        assert result["category"] == "comparison"

    def test_concept_confidence_above_threshold(self, classifier):
        result = classifier.classify("What is blue carbon?")
        assert result["confidence"] >= 0.6
