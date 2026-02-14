"""MARIS Axiom Discovery Module - cross-paper pattern detection and candidate axiom formation.

Discovers candidate bridge axioms from the 195-paper library using:
    PatternDetector    - Cross-paper pattern detection for quantitative relationships
    PatternAggregator  - Cross-study aggregation with conflict detection
    CandidateAxiom     - Pydantic model for candidate axioms
    AxiomReviewer      - Human-in-the-loop validation workflow
    DiscoveryPipeline  - Full discovery pipeline orchestration
"""

from maris.discovery.candidate_axiom import CandidateAxiom
from maris.discovery.pattern_detector import CandidatePattern, PatternDetector
from maris.discovery.aggregator import AggregatedPattern, PatternAggregator
from maris.discovery.reviewer import AxiomReviewer
from maris.discovery.pipeline import DiscoveryPipeline

__all__ = [
    "CandidateAxiom",
    "CandidatePattern",
    "PatternDetector",
    "AggregatedPattern",
    "PatternAggregator",
    "AxiomReviewer",
    "DiscoveryPipeline",
]
