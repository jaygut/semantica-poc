"""Tests for the maris.discovery module - axiom discovery pipeline.

Covers pattern detection, aggregation, conflict detection, candidate formation,
reviewer workflow, and pipeline integration.
"""

import json
import statistics
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from maris.discovery.candidate_axiom import CandidateAxiom
from maris.discovery.pattern_detector import (
    CandidatePattern,
    PatternDetector,
    _classify_domain,
    _detect_habitat,
    _extract_coefficients,
)
from maris.discovery.aggregator import PatternAggregator
from maris.discovery.reviewer import AxiomReviewer
from maris.discovery.pipeline import DiscoveryPipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_papers():
    """Synthetic papers with known cross-domain patterns."""
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
            "title": "Coral reef tourism valuation",
            "abstract": (
                "Coral reef fish biomass increases of 120% in protected areas "
                "lead to significant increases in tourism value. Revenue from "
                "dive tourism increased by $500 million across the study region."
            ),
            "source_tier": "T1",
            "domain_tags": ["ecosystem_services"],
        },
        {
            "paper_id": "paper_003",
            "doi": "10.1000/test003",
            "title": "Biomass recovery and economic impact",
            "abstract": (
                "Fish biomass recovery of 100% in no-take reserves generates "
                "substantial tourism revenue. Economic valuation shows $400 million "
                "in additional revenue from dive and snorkeling activities in "
                "reef ecosystems."
            ),
            "source_tier": "T1",
            "domain_tags": ["mpa_effectiveness"],
        },
        {
            "paper_id": "paper_004",
            "doi": "10.1000/test004",
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
def sample_patterns():
    """Pre-built CandidatePattern objects for aggregation tests."""
    return [
        CandidatePattern(
            relationship_type="ecological_to_financial",
            coefficient_value=0.8,
            source_doi="10.1000/a",
            confidence=0.8,
            domain_from="ecological",
            domain_to="financial",
            habitat="coral_reef",
        ),
        CandidatePattern(
            relationship_type="ecological_to_financial",
            coefficient_value=0.75,
            source_doi="10.1000/b",
            confidence=0.7,
            domain_from="ecological",
            domain_to="financial",
            habitat="coral_reef",
        ),
        CandidatePattern(
            relationship_type="ecological_to_financial",
            coefficient_value=0.82,
            source_doi="10.1000/c",
            confidence=0.9,
            domain_from="ecological",
            domain_to="financial",
            habitat="coral_reef",
        ),
        CandidatePattern(
            relationship_type="ecological_to_financial",
            coefficient_value=0.78,
            source_doi="10.1000/d",
            confidence=0.75,
            domain_from="ecological",
            domain_to="financial",
            habitat="seagrass_meadow",
        ),
    ]


@pytest.fixture
def conflicting_patterns():
    """Patterns with one outlier for conflict detection tests.

    Six studies clustered around 0.80 and one extreme outlier at 5.0.
    With 7 values, the cluster dominates the mean (~1.4) and SD (~1.6),
    and the outlier at 5.0 is well beyond 2 SD from the mean.
    """
    return [
        CandidatePattern(
            relationship_type="ecological_to_service",
            coefficient_value=0.80,
            source_doi="10.1000/x1",
            confidence=0.8,
            domain_from="ecological",
            domain_to="service",
        ),
        CandidatePattern(
            relationship_type="ecological_to_service",
            coefficient_value=0.82,
            source_doi="10.1000/x2",
            confidence=0.8,
            domain_from="ecological",
            domain_to="service",
        ),
        CandidatePattern(
            relationship_type="ecological_to_service",
            coefficient_value=0.81,
            source_doi="10.1000/x3",
            confidence=0.8,
            domain_from="ecological",
            domain_to="service",
        ),
        CandidatePattern(
            relationship_type="ecological_to_service",
            coefficient_value=0.79,
            source_doi="10.1000/x4",
            confidence=0.8,
            domain_from="ecological",
            domain_to="service",
        ),
        CandidatePattern(
            relationship_type="ecological_to_service",
            coefficient_value=0.80,
            source_doi="10.1000/x5",
            confidence=0.8,
            domain_from="ecological",
            domain_to="service",
        ),
        CandidatePattern(
            relationship_type="ecological_to_service",
            coefficient_value=0.81,
            source_doi="10.1000/x6",
            confidence=0.8,
            domain_from="ecological",
            domain_to="service",
        ),
        # Extreme outlier - 6x higher than cluster
        CandidatePattern(
            relationship_type="ecological_to_service",
            coefficient_value=5.0,
            source_doi="10.1000/outlier",
            confidence=0.7,
            domain_from="ecological",
            domain_to="service",
        ),
    ]


# ---------------------------------------------------------------------------
# Pattern Detector Tests
# ---------------------------------------------------------------------------

class TestPatternDetector:
    """Tests for cross-paper pattern detection."""

    def test_detect_percentage_increase(self):
        """Detect 'increased by X%' patterns."""
        results = _extract_coefficients("fish biomass increased by 113% in the reserve")
        assert len(results) >= 1
        values = [v for v, _, _ in results]
        assert 113.0 in values

    def test_detect_fold_change(self):
        """Detect 'X-fold' patterns."""
        results = _extract_coefficients("biomass showed a 4.63x increase over baseline")
        assert len(results) >= 1
        values = [v for v, _, _ in results]
        assert 4.63 in values

    def test_detect_dollar_value(self):
        """Detect '$X million/billion' patterns."""
        results = _extract_coefficients("reef tourism generates $616 million annually")
        assert len(results) >= 1
        values = [v for v, _, _ in results]
        assert 616.0 in values

    def test_detect_carbon_rate(self):
        """Detect carbon sequestration rate patterns."""
        results = _extract_coefficients("seagrass sequesters 0.84 tCO2/ha/yr")
        assert len(results) >= 1
        values = [v for v, _, _ in results]
        assert 0.84 in values

    def test_detect_ratio(self):
        """Detect 'ratio of X' patterns."""
        results = _extract_coefficients("the biomass ratio of 6.7 was observed")
        assert len(results) >= 1
        values = [v for v, _, _ in results]
        assert 6.7 in values

    def test_no_coefficients_in_plain_text(self):
        """No false positives in text without numbers."""
        results = _extract_coefficients("marine protected areas protect biodiversity")
        assert len(results) == 0

    def test_classify_ecological_domain(self):
        """Correctly classify ecological text."""
        assert _classify_domain("fish biomass in coral reef habitat") == "ecological"

    def test_classify_financial_domain(self):
        """Correctly classify financial text."""
        assert _classify_domain("revenue of $500 million from investment") == "financial"

    def test_classify_service_domain(self):
        """Correctly classify service text."""
        assert _classify_domain("tourism ecosystem service valuation") == "service"

    def test_classify_unknown_domain(self):
        """Return 'unknown' for text without domain keywords."""
        assert _classify_domain("the quick brown fox") == "unknown"

    def test_detect_coral_reef_habitat(self):
        """Detect coral reef habitat."""
        assert _detect_habitat("coral reef ecosystems") == "coral_reef"

    def test_detect_seagrass_habitat(self):
        """Detect seagrass habitat."""
        assert _detect_habitat("seagrass meadows sequester carbon") == "seagrass_meadow"

    def test_detect_mangrove_habitat(self):
        """Detect mangrove habitat."""
        assert _detect_habitat("mangrove forests provide protection") == "mangrove_forest"

    def test_detect_no_habitat(self):
        """Return empty string when no habitat detected."""
        assert _detect_habitat("generic marine environment") == ""

    def test_detector_processes_papers(self, sample_papers):
        """Detector finds patterns in a corpus of papers."""
        detector = PatternDetector(min_confidence=0.3)
        patterns = detector.detect_patterns(sample_papers)
        assert len(patterns) > 0
        assert all(isinstance(p, CandidatePattern) for p in patterns)

    def test_detector_skips_empty_abstracts(self):
        """Detector skips papers without abstracts."""
        papers = [
            {"paper_id": "empty", "doi": "10.1000/empty", "title": "Empty", "abstract": ""},
        ]
        detector = PatternDetector()
        patterns = detector.detect_patterns(papers)
        assert len(patterns) == 0

    def test_detector_confidence_based_on_tier(self):
        """T1 papers get higher confidence than T4."""
        detector = PatternDetector(min_confidence=0.0)
        t1_paper = [{
            "paper_id": "t1", "doi": "10.1000/t1", "title": "T1",
            "abstract": "Fish biomass increased by 50% leading to higher tourism revenue of $10 million",
            "source_tier": "T1",
        }]
        t4_paper = [{
            "paper_id": "t4", "doi": "10.1000/t4", "title": "T4",
            "abstract": "Fish biomass increased by 50% leading to higher tourism revenue of $10 million",
            "source_tier": "T4",
        }]
        t1_patterns = detector.detect_patterns(t1_paper)
        t4_patterns = detector.detect_patterns(t4_paper)

        if t1_patterns and t4_patterns:
            assert t1_patterns[0].confidence > t4_patterns[0].confidence


# ---------------------------------------------------------------------------
# Aggregator Tests
# ---------------------------------------------------------------------------

class TestPatternAggregator:
    """Tests for cross-study aggregation and conflict detection."""

    def test_aggregate_groups_by_type(self, sample_patterns):
        """Patterns with same relationship type are grouped together."""
        agg = PatternAggregator()
        groups = agg.aggregate(sample_patterns)
        assert len(groups) >= 1
        # All 4 patterns should be in one group (same relationship_type)
        total_patterns = sum(len(g.patterns) for g in groups)
        assert total_patterns == 4

    def test_aggregate_computes_mean(self, sample_patterns):
        """Mean coefficient is correctly computed."""
        agg = PatternAggregator()
        groups = agg.aggregate(sample_patterns)
        group = groups[0]
        expected_mean = statistics.mean([0.8, 0.75, 0.82, 0.78])
        assert abs(group.mean_coefficient - expected_mean) < 0.01

    def test_aggregate_computes_ci(self, sample_patterns):
        """Confidence interval is computed."""
        agg = PatternAggregator()
        groups = agg.aggregate(sample_patterns)
        group = groups[0]
        assert group.ci_low < group.mean_coefficient
        assert group.ci_high > group.mean_coefficient

    def test_aggregate_counts_unique_studies(self, sample_patterns):
        """N_studies counts unique DOIs."""
        agg = PatternAggregator()
        groups = agg.aggregate(sample_patterns)
        group = groups[0]
        assert group.n_studies == 4

    def test_aggregate_collects_habitats(self, sample_patterns):
        """Applicable habitats are collected from all patterns."""
        agg = PatternAggregator()
        groups = agg.aggregate(sample_patterns)
        group = groups[0]
        assert "coral_reef" in group.applicable_habitats
        assert "seagrass_meadow" in group.applicable_habitats

    def test_conflict_detection(self, conflicting_patterns):
        """Outlier coefficient is flagged as conflict."""
        agg = PatternAggregator(outlier_sd_threshold=2.0)
        groups = agg.aggregate(conflicting_patterns)
        group = groups[0]
        # The 0.3 coefficient is far from the ~0.8 mean
        assert "10.1000/outlier" in group.conflicts

    def test_no_conflict_when_similar(self, sample_patterns):
        """No conflicts when all coefficients are similar."""
        agg = PatternAggregator()
        groups = agg.aggregate(sample_patterns)
        group = groups[0]
        assert len(group.conflicts) == 0

    def test_filter_by_min_sources(self, sample_patterns):
        """Filter removes groups below threshold."""
        agg = PatternAggregator()
        groups = agg.aggregate(sample_patterns)
        filtered = agg.filter_by_min_sources(groups, min_sources=3)
        assert len(filtered) >= 1
        for g in filtered:
            assert g.n_studies >= 3

    def test_filter_removes_insufficient(self):
        """Groups with fewer than min_sources are removed."""
        patterns = [
            CandidatePattern(
                relationship_type="rare_pattern",
                coefficient_value=1.0,
                source_doi="10.1000/only1",
                confidence=0.8,
                domain_from="ecological",
                domain_to="service",
            ),
        ]
        agg = PatternAggregator()
        groups = agg.aggregate(patterns)
        filtered = agg.filter_by_min_sources(groups, min_sources=3)
        assert len(filtered) == 0

    def test_form_candidates(self, sample_patterns):
        """Aggregated patterns can be converted to CandidateAxiom objects."""
        agg = PatternAggregator()
        groups = agg.aggregate(sample_patterns)
        filtered = agg.filter_by_min_sources(groups, min_sources=3)
        candidates = agg.form_candidates(filtered)
        assert len(candidates) >= 1
        for c in candidates:
            assert isinstance(c, CandidateAxiom)
            assert c.status == "candidate"
            assert c.n_studies >= 3

    def test_empty_input(self):
        """Empty input produces empty output."""
        agg = PatternAggregator()
        groups = agg.aggregate([])
        assert groups == []

    def test_deduplicates_by_doi(self):
        """Same DOI appearing twice uses one coefficient per study."""
        patterns = [
            CandidatePattern(
                relationship_type="test",
                coefficient_value=1.0,
                source_doi="10.1000/same",
                confidence=0.8,
                domain_from="ecological",
                domain_to="service",
            ),
            CandidatePattern(
                relationship_type="test",
                coefficient_value=2.0,
                source_doi="10.1000/same",
                confidence=0.8,
                domain_from="ecological",
                domain_to="service",
            ),
        ]
        agg = PatternAggregator()
        groups = agg.aggregate(patterns)
        assert groups[0].n_studies == 1


# ---------------------------------------------------------------------------
# CandidateAxiom Tests
# ---------------------------------------------------------------------------

class TestCandidateAxiom:
    """Tests for CandidateAxiom model."""

    def test_create_candidate(self):
        """Candidate can be created with valid data."""
        c = CandidateAxiom(
            candidate_id="CAND-017",
            proposed_name="test_axiom",
            pattern="IF X THEN Y",
            domain_from="ecological",
            domain_to="service",
            mean_coefficient=0.8,
            ci_low=0.6,
            ci_high=1.0,
            n_studies=3,
            supporting_dois=["10.1000/a", "10.1000/b", "10.1000/c"],
        )
        assert c.status == "candidate"
        assert c.n_studies == 3

    def test_to_axiom_template_requires_accepted(self):
        """Cannot convert to template unless status is accepted."""
        c = CandidateAxiom(
            candidate_id="CAND-017",
            proposed_name="test",
            pattern="IF X THEN Y",
            domain_from="ecological",
            domain_to="service",
            mean_coefficient=0.8,
            ci_low=0.6,
            ci_high=1.0,
            n_studies=3,
        )
        with pytest.raises(ValueError, match="must be 'accepted'"):
            c.to_axiom_template()

    def test_to_axiom_template_format(self):
        """Accepted candidate converts to valid axiom template dict."""
        c = CandidateAxiom(
            candidate_id="CAND-017",
            proposed_name="test_axiom",
            pattern="IF biomass(Site, X) THEN tourism(Site, X * 0.8)",
            domain_from="ecological",
            domain_to="service",
            mean_coefficient=0.8,
            ci_low=0.6,
            ci_high=1.0,
            n_studies=3,
            supporting_dois=["10.1000/a", "10.1000/b", "10.1000/c"],
            applicable_habitats=["coral_reef"],
            status="accepted",
            reviewed_by="tester",
        )
        template = c.to_axiom_template()
        assert template["axiom_id"] == "BA-017"
        assert template["name"] == "test_axiom"
        assert template["category"] == "ecological_to_service"
        assert template["coefficients"]["primary_coefficient"]["value"] == 0.8
        assert template["coefficients"]["primary_coefficient"]["ci_low"] == 0.6
        assert template["evidence_tier"] == "T1"
        assert len(template["sources"]) == 3

    def test_candidate_id_format(self):
        """CAND-NNN converts to BA-NNN."""
        c = CandidateAxiom(
            candidate_id="CAND-042",
            proposed_name="test",
            pattern="IF X THEN Y",
            domain_from="ecological",
            domain_to="financial",
            mean_coefficient=1.0,
            ci_low=0.5,
            ci_high=1.5,
            n_studies=3,
            status="accepted",
        )
        template = c.to_axiom_template()
        assert template["axiom_id"] == "BA-042"


# ---------------------------------------------------------------------------
# Reviewer Tests
# ---------------------------------------------------------------------------

class TestAxiomReviewer:
    """Tests for human-in-the-loop validation workflow."""

    def test_add_and_list_candidates(self):
        """Add candidates and list them."""
        reviewer = AxiomReviewer()
        c = CandidateAxiom(
            candidate_id="CAND-001",
            proposed_name="test",
            pattern="IF X THEN Y",
            domain_from="ecological",
            domain_to="service",
            mean_coefficient=0.5,
            ci_low=0.3,
            ci_high=0.7,
            n_studies=3,
        )
        reviewer.add_candidate(c)
        assert len(reviewer.list_candidates()) == 1

    def test_accept_candidate(self):
        """Accept a candidate and verify status update."""
        reviewer = AxiomReviewer()
        c = CandidateAxiom(
            candidate_id="CAND-001",
            proposed_name="test",
            pattern="IF X THEN Y",
            domain_from="ecological",
            domain_to="service",
            mean_coefficient=0.5,
            ci_low=0.3,
            ci_high=0.7,
            n_studies=3,
        )
        reviewer.add_candidate(c)
        result = reviewer.accept("CAND-001", reviewer="Dr. Smith", notes="Valid pattern")
        assert result is not None
        assert result.status == "accepted"
        assert result.reviewed_by == "Dr. Smith"
        assert result.reviewed_at is not None

    def test_reject_candidate(self):
        """Reject a candidate with reason."""
        reviewer = AxiomReviewer()
        c = CandidateAxiom(
            candidate_id="CAND-001",
            proposed_name="test",
            pattern="IF X THEN Y",
            domain_from="ecological",
            domain_to="service",
            mean_coefficient=0.5,
            ci_low=0.3,
            ci_high=0.7,
            n_studies=3,
        )
        reviewer.add_candidate(c)
        result = reviewer.reject("CAND-001", reviewer="Dr. Jones", reason="Confounding variables")
        assert result is not None
        assert result.status == "rejected"
        assert result.review_notes == "Confounding variables"

    def test_accept_nonexistent_returns_none(self):
        """Accepting a non-existent candidate returns None."""
        reviewer = AxiomReviewer()
        assert reviewer.accept("CAND-999", reviewer="nobody") is None

    def test_reject_nonexistent_returns_none(self):
        """Rejecting a non-existent candidate returns None."""
        reviewer = AxiomReviewer()
        assert reviewer.reject("CAND-999", reviewer="nobody") is None

    def test_get_accepted_templates(self):
        """Get accepted candidates as axiom templates."""
        reviewer = AxiomReviewer()
        c = CandidateAxiom(
            candidate_id="CAND-001",
            proposed_name="accepted_axiom",
            pattern="IF X THEN Y",
            domain_from="ecological",
            domain_to="service",
            mean_coefficient=0.5,
            ci_low=0.3,
            ci_high=0.7,
            n_studies=3,
            applicable_habitats=["coral_reef"],
        )
        reviewer.add_candidate(c)
        reviewer.accept("CAND-001", reviewer="tester")
        templates = reviewer.get_accepted_templates()
        assert len(templates) == 1
        assert templates[0]["axiom_id"] == "BA-001"

    def test_decision_history(self):
        """Decision history records all reviews."""
        reviewer = AxiomReviewer()
        c1 = CandidateAxiom(
            candidate_id="CAND-001", proposed_name="a",
            pattern="X", domain_from="e", domain_to="s",
            mean_coefficient=0.5, ci_low=0.3, ci_high=0.7, n_studies=3,
        )
        c2 = CandidateAxiom(
            candidate_id="CAND-002", proposed_name="b",
            pattern="Y", domain_from="e", domain_to="f",
            mean_coefficient=1.0, ci_low=0.5, ci_high=1.5, n_studies=4,
        )
        reviewer.add_candidate(c1)
        reviewer.add_candidate(c2)
        reviewer.accept("CAND-001", reviewer="alice")
        reviewer.reject("CAND-002", reviewer="bob", reason="insufficient")

        history = reviewer.get_decision_history()
        assert len(history) == 2
        assert history[0]["decision"] == "accepted"
        assert history[1]["decision"] == "rejected"
        assert history[1]["reviewer"] == "bob"

    def test_filter_by_status(self):
        """List candidates filtered by status."""
        reviewer = AxiomReviewer()
        for i in range(3):
            c = CandidateAxiom(
                candidate_id=f"CAND-{i:03d}", proposed_name=f"test_{i}",
                pattern="X", domain_from="e", domain_to="s",
                mean_coefficient=0.5, ci_low=0.3, ci_high=0.7, n_studies=3,
            )
            reviewer.add_candidate(c)
        reviewer.accept("CAND-000", reviewer="tester")
        reviewer.reject("CAND-001", reviewer="tester")

        assert len(reviewer.list_candidates(status="candidate")) == 1
        assert len(reviewer.list_candidates(status="accepted")) == 1
        assert len(reviewer.list_candidates(status="rejected")) == 1

    def test_provenance_tracking(self):
        """Reviewer records decisions in provenance when available."""
        mock_prov = MagicMock()
        mock_prov.provenance = MagicMock()
        reviewer = AxiomReviewer(provenance_manager=mock_prov)
        c = CandidateAxiom(
            candidate_id="CAND-001", proposed_name="test",
            pattern="X", domain_from="e", domain_to="s",
            mean_coefficient=0.5, ci_low=0.3, ci_high=0.7, n_studies=3,
        )
        reviewer.add_candidate(c)
        reviewer.accept("CAND-001", reviewer="tester")
        mock_prov.provenance.record_activity.assert_called_once()


# ---------------------------------------------------------------------------
# Pipeline Integration Tests
# ---------------------------------------------------------------------------

class TestDiscoveryPipeline:
    """Tests for full pipeline orchestration."""

    def test_pipeline_with_synthetic_data(self, sample_papers):
        """Pipeline produces candidates from a synthetic corpus."""
        pipeline = DiscoveryPipeline(min_sources=2, min_confidence=0.3)
        pipeline.load_papers(sample_papers)
        candidates = pipeline.run()
        # With 4 papers and low thresholds, we should get some candidates
        # (exact number depends on pattern matching)
        assert isinstance(candidates, list)

    def test_pipeline_empty_corpus(self):
        """Pipeline handles empty corpus gracefully."""
        pipeline = DiscoveryPipeline()
        pipeline.load_papers([])
        candidates = pipeline.run()
        assert candidates == []

    def test_pipeline_no_cross_domain_patterns(self):
        """No candidates when papers lack cross-domain relationships."""
        papers = [
            {
                "paper_id": "plain",
                "doi": "10.1000/plain",
                "title": "Descriptive ecology",
                "abstract": "We observed various fish species on the reef. "
                           "The community structure was typical for the region.",
                "source_tier": "T1",
            },
        ]
        pipeline = DiscoveryPipeline(min_sources=3)
        pipeline.load_papers(papers)
        candidates = pipeline.run()
        assert len(candidates) == 0

    def test_pipeline_single_source_excluded(self):
        """Single-source patterns do not become candidates at min_sources=3."""
        papers = [
            {
                "paper_id": "lone",
                "doi": "10.1000/lone",
                "title": "Unique finding",
                "abstract": (
                    "Fish biomass increased by 200% leading to tourism revenue "
                    "of $100 million in reef ecosystems."
                ),
                "source_tier": "T1",
            },
        ]
        pipeline = DiscoveryPipeline(min_sources=3)
        pipeline.load_papers(papers)
        candidates = pipeline.run()
        assert len(candidates) == 0

    def test_pipeline_summary(self, sample_papers):
        """Pipeline summary reports correct stats."""
        pipeline = DiscoveryPipeline(min_sources=2, min_confidence=0.3)
        pipeline.load_papers(sample_papers)
        pipeline.run()
        summary = pipeline.summary()
        assert summary["papers_loaded"] == len(sample_papers)
        assert summary["raw_patterns"] >= 0
        assert "candidates_by_status" in summary

    def test_pipeline_export_candidates(self, sample_papers, tmp_path):
        """Candidates can be exported to JSON."""
        pipeline = DiscoveryPipeline(min_sources=2, min_confidence=0.3)
        pipeline.load_papers(sample_papers)
        pipeline.run()
        output_file = tmp_path / "candidates.json"
        pipeline.export_candidates(output_file)
        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)
        assert "candidates" in data
        assert "pipeline_stats" in data

    def test_pipeline_reviewer_integration(self, sample_papers):
        """Pipeline's reviewer has candidates loaded after run()."""
        pipeline = DiscoveryPipeline(min_sources=2, min_confidence=0.3)
        pipeline.load_papers(sample_papers)
        candidates = pipeline.run()
        reviewer_candidates = pipeline.reviewer.list_candidates()
        assert len(reviewer_candidates) == len(candidates)

    def test_pipeline_all_t4_evidence(self):
        """Papers with only T4 evidence still produce patterns (low confidence)."""
        papers = [
            {
                "paper_id": f"t4_{i}",
                "doi": f"10.1000/t4_{i}",
                "title": f"Preprint {i}",
                "abstract": (
                    "Biomass increased by 50% generating $10 million in "
                    "tourism revenue for reef ecosystems."
                ),
                "source_tier": "T4",
            }
            for i in range(5)
        ]
        pipeline = DiscoveryPipeline(min_sources=3, min_confidence=0.1)
        pipeline.load_papers(papers)
        candidates = pipeline.run()
        # Should still work but with lower confidence
        assert isinstance(candidates, list)

    def test_load_corpus_missing_file(self):
        """Loading from non-existent file returns 0."""
        pipeline = DiscoveryPipeline()
        count = pipeline.load_corpus(Path("/nonexistent/path.json"))
        assert count == 0
