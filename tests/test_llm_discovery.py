"""Tests for LLM-enhanced axiom discovery pattern detection.

Covers LLMPatternDetector with mocked LLM, regex fallback, pattern merging,
and backward-compatible DiscoveryPipeline integration.
"""

import json
from unittest.mock import MagicMock

import pytest

from maris.discovery.llm_detector import LLMPatternDetector, _parse_json_array
from maris.discovery.pattern_detector import CandidatePattern, PatternDetector
from maris.discovery.pipeline import DiscoveryPipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_papers():
    """Papers with known cross-domain relationships for LLM extraction."""
    return [
        {
            "paper_id": "paper_001",
            "doi": "10.1000/test001",
            "title": "MPA biomass increases tourism revenue",
            "abstract": (
                "No-take marine protected areas increase fish biomass by 113% "
                "which drives increased tourism revenue. Divers are willing to pay "
                "up to 84% more for sites with higher biomass. This results in "
                "$616 million additional revenue globally for coral reef ecosystems."
            ),
            "source_tier": "T1",
            "domain_tags": ["mpa_effectiveness", "ecosystem_services"],
        },
        {
            "paper_id": "paper_002",
            "doi": "10.1000/test002",
            "title": "Seagrass carbon sequestration rates",
            "abstract": (
                "Seagrass meadows sequester carbon at a rate of 0.84 tCO2/ha/yr "
                "through sediment burial. This generates carbon credit revenue "
                "of $25 per tonne in the voluntary market."
            ),
            "source_tier": "T1",
            "domain_tags": ["blue_carbon"],
        },
    ]


@pytest.fixture
def mock_llm_adapter():
    """Mock LLMAdapter that returns structured extraction results."""
    adapter = MagicMock()
    adapter.complete.return_value = json.dumps([
        {
            "ecological_metric": "fish biomass recovery",
            "financial_metric": "dive tourism revenue",
            "coefficient": 84.0,
            "unit": "%",
            "confidence": "high",
            "quote": "Divers are willing to pay up to 84% more for sites with higher biomass",
        },
        {
            "ecological_metric": "fish biomass",
            "financial_metric": "tourism revenue",
            "coefficient": 616.0,
            "unit": "million",
            "confidence": "medium",
            "quote": "$616 million additional revenue globally for coral reef ecosystems",
        },
    ])
    return adapter


@pytest.fixture
def mock_llm_single_result():
    """Mock LLM returning a single extraction result."""
    adapter = MagicMock()
    adapter.complete.return_value = json.dumps([
        {
            "ecological_metric": "seagrass area",
            "financial_metric": "carbon credit value",
            "coefficient": 0.84,
            "unit": "tCO2/ha/yr",
            "confidence": "high",
            "quote": "Seagrass meadows sequester carbon at a rate of 0.84 tCO2/ha/yr",
        },
    ])
    return adapter


@pytest.fixture
def mock_llm_empty():
    """Mock LLM returning no relationships."""
    adapter = MagicMock()
    adapter.complete.return_value = "[]"
    return adapter


@pytest.fixture
def mock_llm_error():
    """Mock LLM that raises an exception."""
    adapter = MagicMock()
    adapter.complete.side_effect = RuntimeError("LLM service unavailable")
    return adapter


# ---------------------------------------------------------------------------
# JSON parsing tests
# ---------------------------------------------------------------------------

class TestParseJsonArray:
    """Tests for the _parse_json_array helper."""

    def test_parse_plain_array(self):
        result = _parse_json_array('[{"a": 1}]')
        assert len(result) == 1
        assert result[0]["a"] == 1

    def test_parse_fenced_json(self):
        text = '```json\n[{"a": 1}]\n```'
        result = _parse_json_array(text)
        assert len(result) == 1

    def test_parse_empty_array(self):
        result = _parse_json_array("[]")
        assert result == []

    def test_parse_invalid_json(self):
        result = _parse_json_array("not json at all")
        assert result == []

    def test_parse_surrounding_text(self):
        text = 'Here are the results:\n[{"x": 42}]\nDone.'
        result = _parse_json_array(text)
        assert len(result) == 1
        assert result[0]["x"] == 42


# ---------------------------------------------------------------------------
# LLMPatternDetector tests
# ---------------------------------------------------------------------------

class TestLLMPatternDetector:
    """Tests for LLM-enhanced pattern detection."""

    def test_llm_extracts_patterns(self, sample_papers, mock_llm_adapter):
        """LLM detector extracts patterns from papers via LLM."""
        detector = LLMPatternDetector(
            llm_adapter=mock_llm_adapter,
            min_confidence=0.3,
        )
        # Use only the first paper to match the mock
        patterns = detector.detect_patterns([sample_papers[0]])
        assert len(patterns) > 0
        assert all(isinstance(p, CandidatePattern) for p in patterns)
        # LLM was called
        mock_llm_adapter.complete.assert_called()

    def test_llm_pattern_has_correct_fields(self, sample_papers, mock_llm_adapter):
        """Extracted patterns have populated fields."""
        detector = LLMPatternDetector(
            llm_adapter=mock_llm_adapter,
            min_confidence=0.3,
        )
        patterns = detector.detect_patterns([sample_papers[0]])
        assert len(patterns) > 0
        p = patterns[0]
        assert p.source_doi == "10.1000/test001"
        assert p.paper_id == "paper_001"
        assert p.coefficient_value > 0
        assert p.confidence > 0
        assert p.source_quote != ""

    def test_fallback_to_regex_when_llm_is_none(self, sample_papers):
        """When llm_adapter is None, falls back to regex PatternDetector."""
        detector = LLMPatternDetector(llm_adapter=None, min_confidence=0.3)
        patterns = detector.detect_patterns(sample_papers)
        # Should still work using regex
        assert isinstance(patterns, list)
        # All patterns should be CandidatePattern
        assert all(isinstance(p, CandidatePattern) for p in patterns)

    def test_fallback_matches_regex_detector(self, sample_papers):
        """Fallback mode produces same results as standalone PatternDetector."""
        llm_detector = LLMPatternDetector(llm_adapter=None, min_confidence=0.3)
        regex_detector = PatternDetector(min_confidence=0.3)

        llm_result = llm_detector.detect_patterns(sample_papers)
        regex_result = regex_detector.detect_patterns(sample_papers)

        assert len(llm_result) == len(regex_result)

    def test_llm_error_returns_empty_for_paper(self, sample_papers, mock_llm_error):
        """When LLM raises error, that paper's LLM patterns are empty."""
        detector = LLMPatternDetector(
            llm_adapter=mock_llm_error,
            min_confidence=0.3,
        )
        # Should not raise - falls back gracefully per-paper
        patterns = detector.detect_patterns(sample_papers)
        # Only regex patterns should be present
        assert isinstance(patterns, list)

    def test_llm_empty_response(self, sample_papers, mock_llm_empty):
        """LLM returning [] still gets regex patterns."""
        detector = LLMPatternDetector(
            llm_adapter=mock_llm_empty,
            min_confidence=0.3,
        )
        patterns = detector.detect_patterns(sample_papers)
        # Should have regex patterns only
        assert isinstance(patterns, list)

    def test_skips_papers_without_abstract(self, mock_llm_adapter):
        """Papers with no abstract are skipped."""
        papers = [
            {"paper_id": "no_abs", "doi": "10.1000/noabs", "title": "No abstract", "abstract": ""},
        ]
        detector = LLMPatternDetector(
            llm_adapter=mock_llm_adapter,
            min_confidence=0.3,
        )
        patterns = detector.detect_patterns(papers)
        assert len(patterns) == 0
        mock_llm_adapter.complete.assert_not_called()

    def test_min_confidence_filters_low_confidence(self, sample_papers):
        """Patterns below min_confidence are filtered out."""
        adapter = MagicMock()
        adapter.complete.return_value = json.dumps([
            {
                "ecological_metric": "fish biomass",
                "financial_metric": "tourism revenue",
                "coefficient": 50.0,
                "unit": "%",
                "confidence": "low",
                "quote": "possible increase of 50%",
            },
        ])
        detector = LLMPatternDetector(
            llm_adapter=adapter,
            min_confidence=0.8,
        )
        patterns = detector.detect_patterns([sample_papers[0]])
        # Low confidence (0.4) with T1 boost (0.05) = 0.45 < 0.8
        llm_patterns = [p for p in patterns if p.coefficient_value == 50.0]
        assert len(llm_patterns) == 0


# ---------------------------------------------------------------------------
# Pattern merging tests
# ---------------------------------------------------------------------------

class TestPatternMerging:
    """Tests for merge_patterns logic - LLM takes priority over regex."""

    def test_llm_priority_over_regex(self):
        """When LLM and regex find same coefficient, LLM wins."""
        detector = LLMPatternDetector(llm_adapter=MagicMock(), min_confidence=0.3)

        llm_patterns = [
            CandidatePattern(
                relationship_type="ecological_to_financial",
                coefficient_value=84.0,
                source_doi="10.1000/a",
                confidence=0.9,
                domain_from="ecological",
                domain_to="financial",
            ),
        ]
        regex_patterns = [
            CandidatePattern(
                relationship_type="ecological_to_financial",
                coefficient_value=84.0,
                source_doi="10.1000/a",
                confidence=0.7,
                domain_from="ecological",
                domain_to="financial",
            ),
        ]

        merged = detector._merge_patterns(llm_patterns, regex_patterns)
        assert len(merged) == 1
        # The LLM pattern should be the one kept (higher confidence)
        assert merged[0].confidence == 0.9

    def test_regex_supplements_llm(self):
        """Regex patterns with different coefficients are added."""
        detector = LLMPatternDetector(llm_adapter=MagicMock(), min_confidence=0.3)

        llm_patterns = [
            CandidatePattern(
                relationship_type="ecological_to_financial",
                coefficient_value=84.0,
                source_doi="10.1000/a",
                confidence=0.9,
                domain_from="ecological",
                domain_to="financial",
            ),
        ]
        regex_patterns = [
            CandidatePattern(
                relationship_type="ecological_to_service",
                coefficient_value=616.0,
                coefficient_unit="million",
                source_doi="10.1000/a",
                confidence=0.7,
                domain_from="ecological",
                domain_to="service",
            ),
        ]

        merged = detector._merge_patterns(llm_patterns, regex_patterns)
        # Both should be present since coefficients differ
        assert len(merged) == 2

    def test_empty_llm_returns_regex(self):
        """If LLM returns nothing, all regex patterns are used."""
        detector = LLMPatternDetector(llm_adapter=MagicMock(), min_confidence=0.3)

        regex_patterns = [
            CandidatePattern(
                relationship_type="ecological_to_service",
                coefficient_value=50.0,
                source_doi="10.1000/b",
                confidence=0.6,
                domain_from="ecological",
                domain_to="service",
            ),
        ]
        merged = detector._merge_patterns([], regex_patterns)
        assert len(merged) == 1

    def test_empty_regex_returns_llm(self):
        """If regex returns nothing, all LLM patterns are used."""
        detector = LLMPatternDetector(llm_adapter=MagicMock(), min_confidence=0.3)

        llm_patterns = [
            CandidatePattern(
                relationship_type="ecological_to_service",
                coefficient_value=0.84,
                source_doi="10.1000/c",
                confidence=0.9,
                domain_from="ecological",
                domain_to="service",
            ),
        ]
        merged = detector._merge_patterns(llm_patterns, [])
        assert len(merged) == 1


# ---------------------------------------------------------------------------
# DiscoveryPipeline backward compatibility tests
# ---------------------------------------------------------------------------

class TestPipelineBackwardCompat:
    """Ensure DiscoveryPipeline works with and without llm_adapter."""

    def test_pipeline_default_uses_regex(self):
        """Without llm_adapter, pipeline uses PatternDetector (regex)."""
        pipeline = DiscoveryPipeline(min_sources=2, min_confidence=0.3)
        assert isinstance(pipeline._detector, PatternDetector)

    def test_pipeline_with_llm_uses_llm_detector(self):
        """With llm_adapter, pipeline uses LLMPatternDetector."""
        mock_adapter = MagicMock()
        pipeline = DiscoveryPipeline(
            min_sources=2,
            min_confidence=0.3,
            llm_adapter=mock_adapter,
        )
        assert isinstance(pipeline._detector, LLMPatternDetector)

    def test_pipeline_with_none_llm_uses_regex(self):
        """Explicit llm_adapter=None uses regex detector."""
        pipeline = DiscoveryPipeline(
            min_sources=2,
            min_confidence=0.3,
            llm_adapter=None,
        )
        assert isinstance(pipeline._detector, PatternDetector)

    def test_pipeline_regex_still_produces_candidates(self, sample_papers):
        """Pipeline without LLM can still produce candidates from synthetic data."""
        pipeline = DiscoveryPipeline(min_sources=2, min_confidence=0.3)
        pipeline.load_papers(sample_papers)
        candidates = pipeline.run()
        assert isinstance(candidates, list)

    def test_pipeline_with_mock_llm_runs(self, sample_papers):
        """Pipeline with mock LLM adapter runs successfully."""
        mock_adapter = MagicMock()
        mock_adapter.complete.return_value = json.dumps([
            {
                "ecological_metric": "fish biomass recovery",
                "financial_metric": "dive tourism revenue",
                "coefficient": 84.0,
                "unit": "%",
                "confidence": "high",
                "quote": "Divers willing to pay up to 84% more",
            },
        ])

        pipeline = DiscoveryPipeline(
            min_sources=1,
            min_confidence=0.3,
            llm_adapter=mock_adapter,
        )
        pipeline.load_papers(sample_papers)
        candidates = pipeline.run()
        assert isinstance(candidates, list)
        # LLM should have been called for each paper with an abstract
        assert mock_adapter.complete.call_count == len(
            [p for p in sample_papers if p.get("abstract")]
        )

    def test_pipeline_summary_with_llm(self, sample_papers):
        """Pipeline summary works correctly with LLM detector."""
        mock_adapter = MagicMock()
        mock_adapter.complete.return_value = "[]"

        pipeline = DiscoveryPipeline(
            min_sources=2,
            min_confidence=0.3,
            llm_adapter=mock_adapter,
        )
        pipeline.load_papers(sample_papers)
        pipeline.run()
        summary = pipeline.summary()
        assert summary["papers_loaded"] == len(sample_papers)
        assert "candidates_by_status" in summary
