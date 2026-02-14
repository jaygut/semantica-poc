"""Full axiom discovery pipeline orchestration.

Coordinates the end-to-end flow:
  1. Load paper corpus (abstracts + entities from document_index.json)
  2. Run pattern detector across all papers
  3. Aggregate patterns by relationship type
  4. Filter for 3+ independent sources
  5. Form candidate axioms
  6. Run conflict detection
  7. Output candidates for human review
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from maris.discovery.aggregator import AggregatedPattern, PatternAggregator
from maris.discovery.candidate_axiom import CandidateAxiom
from maris.discovery.pattern_detector import CandidatePattern, PatternDetector
from maris.discovery.reviewer import AxiomReviewer

logger = logging.getLogger(__name__)


class DiscoveryPipeline:
    """Orchestrates the full axiom discovery pipeline.

    Loads the document corpus, detects cross-domain patterns, aggregates
    across studies, forms candidate axioms, and prepares them for human review.
    """

    def __init__(
        self,
        min_sources: int = 3,
        min_confidence: float = 0.3,
        registry_path: Path | str | None = None,
    ) -> None:
        self._min_sources = min_sources
        self._detector = PatternDetector(min_confidence=min_confidence)
        self._aggregator = PatternAggregator()
        self._reviewer = AxiomReviewer()
        self._registry_path = Path(registry_path) if registry_path else None

        # Pipeline state
        self._papers: list[dict[str, Any]] = []
        self._patterns: list[CandidatePattern] = []
        self._aggregated: list[AggregatedPattern] = []
        self._candidates: list[CandidateAxiom] = []

    @property
    def papers(self) -> list[dict[str, Any]]:
        return list(self._papers)

    @property
    def patterns(self) -> list[CandidatePattern]:
        return list(self._patterns)

    @property
    def aggregated(self) -> list[AggregatedPattern]:
        return list(self._aggregated)

    @property
    def candidates(self) -> list[CandidateAxiom]:
        return list(self._candidates)

    @property
    def reviewer(self) -> AxiomReviewer:
        return self._reviewer

    def load_corpus(self, registry_path: Path | str | None = None) -> int:
        """Load the paper corpus from document_index.json.

        Args:
            registry_path: Path to document_index.json. Falls back to
                constructor arg or default location.

        Returns:
            Number of papers loaded.
        """
        path = Path(registry_path) if registry_path else self._registry_path
        if path is None:
            path = Path(__file__).parent.parent.parent / ".claude" / "registry" / "document_index.json"

        if not path.exists():
            logger.warning("Registry not found at %s", path)
            return 0

        with open(path) as f:
            data = json.load(f)

        documents = data.get("documents", {})
        self._papers = []

        for paper_id, doc in documents.items():
            self._papers.append({
                "paper_id": paper_id,
                "doi": doc.get("doi", ""),
                "title": doc.get("title", ""),
                "abstract": doc.get("abstract", ""),
                "source_tier": doc.get("source_tier", "T1"),
                "domain_tags": doc.get("domain_tags", []),
            })

        logger.info("Loaded %d papers from %s", len(self._papers), path)
        return len(self._papers)

    def load_papers(self, papers: list[dict[str, Any]]) -> int:
        """Load papers directly (for testing without file I/O).

        Args:
            papers: List of paper dicts with keys matching load_corpus format.

        Returns:
            Number of papers loaded.
        """
        self._papers = list(papers)
        return len(self._papers)

    def run(self) -> list[CandidateAxiom]:
        """Execute the full discovery pipeline.

        Returns:
            List of CandidateAxiom objects ready for human review.
        """
        if not self._papers:
            logger.warning("No papers loaded - call load_corpus() or load_papers() first")
            return []

        # Step 1: Detect patterns
        logger.info("Step 1: Detecting patterns across %d papers...", len(self._papers))
        self._patterns = self._detector.detect_patterns(self._papers)
        logger.info("Found %d raw patterns", len(self._patterns))

        if not self._patterns:
            logger.info("No patterns detected - pipeline complete")
            return []

        # Step 2: Aggregate by relationship type
        logger.info("Step 2: Aggregating patterns...")
        self._aggregated = self._aggregator.aggregate(self._patterns)
        logger.info("Formed %d aggregated groups", len(self._aggregated))

        # Step 3: Filter for minimum sources
        logger.info("Step 3: Filtering for %d+ independent sources...", self._min_sources)
        filtered = self._aggregator.filter_by_min_sources(
            self._aggregated, self._min_sources
        )
        logger.info("%d groups pass minimum source threshold", len(filtered))

        if not filtered:
            logger.info("No groups meet the minimum source threshold - pipeline complete")
            self._candidates = []
            return []

        # Step 4: Form candidate axioms
        logger.info("Step 4: Forming candidate axioms...")
        self._candidates = self._aggregator.form_candidates(filtered)
        logger.info("Formed %d candidate axioms", len(self._candidates))

        # Step 5: Add to reviewer
        self._reviewer.add_candidates(self._candidates)

        return self._candidates

    def export_candidates(self, output_path: Path | str) -> int:
        """Export candidates to a JSON file.

        Args:
            output_path: Path to write candidates JSON.

        Returns:
            Number of candidates exported.
        """
        output = Path(output_path)
        data = {
            "candidates": [c.model_dump() for c in self._candidates],
            "pipeline_stats": {
                "papers_processed": len(self._papers),
                "raw_patterns": len(self._patterns),
                "aggregated_groups": len(self._aggregated),
                "candidates_formed": len(self._candidates),
                "min_sources": self._min_sources,
            },
        }

        with open(output, "w") as f:
            json.dump(data, f, indent=2)

        logger.info("Exported %d candidates to %s", len(self._candidates), output)
        return len(self._candidates)

    def summary(self) -> dict[str, Any]:
        """Return a summary of pipeline state."""
        return {
            "papers_loaded": len(self._papers),
            "raw_patterns": len(self._patterns),
            "aggregated_groups": len(self._aggregated),
            "candidates": len(self._candidates),
            "min_sources": self._min_sources,
            "candidates_by_status": {
                "candidate": len([c for c in self._candidates if c.status == "candidate"]),
                "accepted": len([c for c in self._candidates if c.status == "accepted"]),
                "rejected": len([c for c in self._candidates if c.status == "rejected"]),
            },
        }
