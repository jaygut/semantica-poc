"""Phase 6 Integration Tests: LLM Discovery Pipeline Validation.

Tests the LLMPatternDetector and DiscoveryPipeline against a real LLM
(DeepSeek by default) with actual paper abstracts from the registry.

Requirements:
    - MARIS_LLM_API_KEY must be set in .env
    - Network access to the LLM provider

Run with:
    pytest tests/integration/test_phase6_llm_discovery.py -v --tb=long
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
REGISTRY_PATH = PROJECT_ROOT / ".claude" / "registry" / "document_index.json"

# Force-reload .env so the real API key overrides any "test-key" set by
# conftest.py or other test modules during collection.
load_dotenv(PROJECT_ROOT / ".env", override=True)

_has_llm_key = bool(os.environ.get("MARIS_LLM_API_KEY", ""))
# Treat the dummy "test-key" value (set by conftest.py) as not configured
if os.environ.get("MARIS_LLM_API_KEY", "") == "test-key":
    _has_llm_key = False

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _has_llm_key, reason="MARIS_LLM_API_KEY not configured"),
]


def _get_adapter():
    """Create a real LLMAdapter from a fresh config."""
    import maris.config as _cfg_mod
    from maris.llm.adapter import LLMAdapter
    # Force-reload .env and reset singleton so real API key is used
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    _cfg_mod._config = None
    cfg = _cfg_mod.get_config()
    return LLMAdapter(config=cfg)


def _get_test_papers(n: int = 5) -> list[dict]:
    """Load n papers with abstracts from the registry."""
    with open(REGISTRY_PATH) as f:
        registry = json.load(f)

    documents = registry.get("documents", {})
    papers = []
    for paper_id, doc in documents.items():
        abstract = doc.get("abstract", "")
        if not abstract or len(abstract) < 100:
            continue
        papers.append({
            "paper_id": paper_id,
            "doi": doc.get("doi", ""),
            "title": doc.get("title", ""),
            "abstract": abstract,
            "source_tier": doc.get("source_tier", "T1"),
            "domain_tags": doc.get("domain_tags", []),
        })
        if len(papers) >= n:
            break

    return papers


# ---------------------------------------------------------------------------
# T6.1: LLM Adapter Connectivity
# ---------------------------------------------------------------------------

class TestT61LLMConnectivity:
    """Verify the LLM adapter can reach the configured provider."""

    def test_llm_returns_response(self):
        adapter = _get_adapter()
        response = adapter.complete(
            messages=[{"role": "user", "content": "Return exactly: {\"test\": true}"}],
            temperature=0.0,
        )
        assert isinstance(response, str)
        assert len(response) > 0

    def test_llm_returns_valid_json(self):
        adapter = _get_adapter()
        response = adapter.complete(
            messages=[{"role": "user", "content": "Return exactly: {\"test\": true}"}],
            temperature=0.0,
        )
        parsed = json.loads(response)
        assert parsed.get("test") is True


# ---------------------------------------------------------------------------
# T6.2: Extraction Prompt Produces Parseable Output
# ---------------------------------------------------------------------------

class TestT62ExtractionPrompt:
    """Validate AXIOM_DISCOVERY_PROMPT against real abstracts."""

    def test_extraction_returns_json_array(self):
        """LLM returns parseable JSON array for a real abstract."""
        from maris.llm.prompts import AXIOM_DISCOVERY_PROMPT
        from maris.discovery.llm_detector import _parse_json_array

        adapter = _get_adapter()
        papers = _get_test_papers(1)
        assert len(papers) >= 1, "No papers with abstracts found"

        paper = papers[0]
        prompt = AXIOM_DISCOVERY_PROMPT.format(
            doi=paper["doi"],
            abstract=paper["abstract"],
        )
        raw = adapter.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        result = _parse_json_array(raw)
        # Should be a list (possibly empty), not None (parse failure)
        assert result is not None, f"Failed to parse LLM output: {raw[:200]}"

    def test_extraction_items_have_required_fields(self):
        """Extracted items contain expected field names."""
        from maris.llm.prompts import AXIOM_DISCOVERY_PROMPT
        from maris.discovery.llm_detector import _parse_json_array

        adapter = _get_adapter()
        # Use beck_2018 which we know has quantitative relationships
        with open(REGISTRY_PATH) as f:
            registry = json.load(f)
        doc = registry["documents"].get("beck_2018_coral_flood_protection", {})
        if not doc.get("abstract"):
            pytest.skip("beck_2018 paper not found or has no abstract")

        prompt = AXIOM_DISCOVERY_PROMPT.format(
            doi=doc.get("doi", ""),
            abstract=doc["abstract"],
        )
        raw = adapter.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        items = _parse_json_array(raw)
        assert items is not None
        assert len(items) > 0, "Expected at least one pattern from beck_2018"

        required_fields = {"ecological_metric", "financial_metric", "coefficient"}
        for item in items:
            for field in required_fields:
                assert field in item, f"Missing field '{field}' in item: {item}"


# ---------------------------------------------------------------------------
# T6.3: LLMPatternDetector End-to-End
# ---------------------------------------------------------------------------

class TestT63LLMPatternDetector:
    """Test LLMPatternDetector with real LLM and real abstracts."""

    def test_detector_extracts_patterns(self):
        """LLMPatternDetector produces CandidatePattern objects."""
        from maris.discovery.llm_detector import LLMPatternDetector
        from maris.discovery.pattern_detector import CandidatePattern

        adapter = _get_adapter()
        papers = _get_test_papers(3)
        assert len(papers) >= 1

        detector = LLMPatternDetector(llm_adapter=adapter, min_confidence=0.3)
        patterns = detector.detect_patterns(papers)

        assert isinstance(patterns, list)
        assert all(isinstance(p, CandidatePattern) for p in patterns)

    def test_detector_no_crashes_on_diverse_abstracts(self):
        """Pipeline handles diverse abstracts without crashing."""
        from maris.discovery.llm_detector import LLMPatternDetector

        adapter = _get_adapter()
        papers = _get_test_papers(5)

        detector = LLMPatternDetector(llm_adapter=adapter, min_confidence=0.3)
        # This should complete without raising
        patterns = detector.detect_patterns(papers)
        assert isinstance(patterns, list)


# ---------------------------------------------------------------------------
# T6.4: Full Pipeline Smoke Test
# ---------------------------------------------------------------------------

class TestT64PipelineSmoke:
    """Smoke test for the full DiscoveryPipeline with real LLM."""

    def test_pipeline_runs_without_crash(self):
        """Pipeline loads corpus and runs detection without errors."""
        from maris.discovery.pipeline import DiscoveryPipeline

        adapter = _get_adapter()
        pipeline = DiscoveryPipeline(
            min_sources=2,
            min_confidence=0.3,
            llm_adapter=adapter,
        )

        # Load a small subset for speed
        papers = _get_test_papers(5)
        pipeline.load_papers(papers)
        candidates = pipeline.run()

        assert isinstance(candidates, list)
        summary = pipeline.summary()
        assert summary["papers_loaded"] == len(papers)
        assert summary["raw_patterns"] >= 0
