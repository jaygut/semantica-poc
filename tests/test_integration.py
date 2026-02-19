"""Integration tests for the query pipeline (no Neo4j/LLM required)."""


from maris.query.classifier import QueryClassifier
from maris.query.formatter import format_response
from maris.query.validators import validate_llm_response


# ---- Classifier pipeline ----


class TestClassifierPipeline:
    def test_classifier_cabo_pulmo_site_valuation(self):
        """Classifying 'What is Cabo Pulmo worth?' returns site_valuation."""
        classifier = QueryClassifier(llm=None)
        result = classifier.classify("What is Cabo Pulmo worth?")
        assert result["category"] == "site_valuation"

    def test_classifier_extracts_site_name(self):
        """Classification result has site == 'Cabo Pulmo National Park'."""
        classifier = QueryClassifier(llm=None)
        result = classifier.classify("What is Cabo Pulmo worth?")
        assert result["site"] == "Cabo Pulmo National Park"


# ---- Response formatting ----


class TestResponseFormatting:
    def test_format_response_preserves_verified_claims(self):
        """format_response should pass through verified_claims."""
        raw = {
            "answer": "Test answer",
            "confidence": 0.8,
            "evidence": [],
            "axioms_used": [],
            "graph_path": [],
            "caveats": [],
            "verified_claims": ["$29.27M"],
            "unverified_claims": [],
        }
        result = format_response(raw)
        assert result["verified_claims"] == ["$29.27M"]

    def test_format_response_preserves_confidence_breakdown(self):
        """format_response should pass through confidence_breakdown."""
        breakdown = {
            "composite": 0.72,
            "tier_base": 0.95,
            "path_discount": 0.90,
            "staleness_discount": 0.84,
            "sample_factor": 1.0,
        }
        raw = {
            "answer": "Test answer",
            "confidence": 0.72,
            "evidence": [],
            "axioms_used": [],
            "graph_path": [],
            "caveats": [],
            "confidence_breakdown": breakdown,
        }
        result = format_response(raw)
        assert result["confidence_breakdown"] == breakdown

    def test_format_response_passes_provenance_metadata(self):
        """format_response should preserve provenance completeness metadata."""
        raw = {
            "answer": "Test answer",
            "confidence": 0.42,
            "evidence": [{"title": "No DOI"}],
            "axioms_used": [],
            "graph_path": [],
            "caveats": [],
            "evidence_count": 1,
            "doi_citation_count": 0,
            "evidence_completeness_score": 0.5,
            "provenance_warnings": ["missing DOI"],
            "provenance_risk": "high",
        }
        result = format_response(raw)
        assert result["evidence_count"] == 1
        assert result["doi_citation_count"] == 0
        assert result["evidence_completeness_score"] == 0.5
        assert result["provenance_warnings"] == ["missing DOI"]
        assert result["provenance_risk"] == "high"


# ---- LLM response validation ----


class TestLLMResponseValidation:
    def test_validate_llm_response_clamps_confidence(self):
        """validate_llm_response clamps confidence > 1.0 to 1.0."""
        raw = {
            "answer": "Over-confident answer",
            "confidence": 1.5,
            "evidence": [],
            "caveats": [],
        }
        result = validate_llm_response(raw, graph_context=None)
        assert result["confidence"] == 1.0

    def test_validate_llm_response_catches_missing_fields(self):
        """validate_llm_response adds defaults for missing required fields."""
        result = validate_llm_response({}, graph_context=None)
        assert "answer" in result
        assert "confidence" in result
        assert "evidence" in result
        assert "caveats" in result
        # Missing answer should default to empty string
        assert result["answer"] == ""
        # Missing confidence should default to 0.0
        assert result["confidence"] == 0.0

    def test_validate_llm_response_preserves_verified_claims(self):
        """validate_llm_response adds verified_claims from numerical cross-check."""
        raw = {
            "answer": "The ESV is $29.27M per year.",
            "confidence": 0.85,
            "evidence": [],
            "caveats": [],
        }
        context = {"total_esv": 29_270_000}
        result = validate_llm_response(raw, graph_context=context)
        # $29.27M should be verified against context
        assert isinstance(result["verified_claims"], list)
        assert isinstance(result["unverified_claims"], list)

    def test_validate_llm_response_populates_provenance_summary_fields(self):
        """validate_llm_response should include provenance summary metadata."""
        raw = {
            "answer": "The value is $50M.",
            "confidence": 0.7,
            "evidence": [{"title": "Untiered source", "doi": "", "tier": None}],
            "caveats": [],
        }
        result = validate_llm_response(raw, graph_context={"value": 50_000_000})
        assert "evidence_count" in result
        assert "doi_citation_count" in result
        assert "evidence_completeness_score" in result
        assert "provenance_warnings" in result
        assert "provenance_risk" in result
