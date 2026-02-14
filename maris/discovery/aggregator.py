"""Cross-study pattern aggregation with conflict detection.

Groups CandidatePattern objects by relationship type using fuzzy matching,
computes aggregate statistics, and flags conflicting coefficients.
"""

from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from maris.discovery.candidate_axiom import CandidateAxiom
from maris.discovery.pattern_detector import CandidatePattern

logger = logging.getLogger(__name__)

# Similarity threshold for fuzzy grouping of relationship types
_SIMILARITY_THRESHOLD = 0.6

# Number of standard deviations to flag as outlier
_OUTLIER_SD_THRESHOLD = 2.0


@dataclass
class AggregatedPattern:
    """A group of CandidatePatterns representing the same relationship."""

    relationship_type: str
    patterns: list[CandidatePattern] = field(default_factory=list)
    mean_coefficient: float = 0.0
    std_dev: float = 0.0
    ci_low: float = 0.0
    ci_high: float = 0.0
    n_studies: int = 0
    unique_dois: list[str] = field(default_factory=list)
    applicable_habitats: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    evidence_tiers: dict[str, int] = field(default_factory=dict)


class PatternAggregator:
    """Aggregate CandidatePatterns by relationship type and detect conflicts.

    Groups patterns using fuzzy string matching on relationship descriptions,
    computes mean coefficient and CI from independent studies, and flags
    outliers (>2 SD from mean) as conflicts.
    """

    def __init__(
        self,
        similarity_threshold: float = _SIMILARITY_THRESHOLD,
        outlier_sd_threshold: float = _OUTLIER_SD_THRESHOLD,
    ) -> None:
        self._similarity_threshold = similarity_threshold
        self._outlier_sd_threshold = outlier_sd_threshold

    def aggregate(self, patterns: list[CandidatePattern]) -> list[AggregatedPattern]:
        """Group patterns by relationship type and compute aggregate stats.

        Args:
            patterns: List of CandidatePattern objects from PatternDetector.

        Returns:
            List of AggregatedPattern objects with statistics and conflicts.
        """
        if not patterns:
            return []

        groups = self._group_patterns(patterns)
        aggregated = []

        for rel_type, group_patterns in groups.items():
            agg = self._compute_statistics(rel_type, group_patterns)
            aggregated.append(agg)

        logger.info(
            "Aggregated %d patterns into %d groups",
            len(patterns),
            len(aggregated),
        )
        return aggregated

    def filter_by_min_sources(
        self,
        aggregated: list[AggregatedPattern],
        min_sources: int = 3,
    ) -> list[AggregatedPattern]:
        """Filter aggregated patterns to only those with minimum source count."""
        return [a for a in aggregated if a.n_studies >= min_sources]

    def form_candidates(
        self,
        aggregated: list[AggregatedPattern],
        start_id: int = 17,
    ) -> list[CandidateAxiom]:
        """Convert aggregated patterns into CandidateAxiom objects.

        Args:
            aggregated: List of AggregatedPattern objects (already filtered).
            start_id: Starting number for CAND-NNN IDs.

        Returns:
            List of CandidateAxiom objects ready for human review.
        """
        candidates = []
        for i, agg in enumerate(aggregated):
            if not agg.patterns:
                continue

            # Derive domain info from first pattern
            first = agg.patterns[0]
            candidate_id = f"CAND-{start_id + i:03d}"

            candidate = CandidateAxiom(
                candidate_id=candidate_id,
                proposed_name=agg.relationship_type,
                pattern=f"IF {first.domain_from}_metric(Site, X) THEN {first.domain_to}_outcome(Site, X * {agg.mean_coefficient:.4f})",
                domain_from=first.domain_from,
                domain_to=first.domain_to,
                mean_coefficient=agg.mean_coefficient,
                ci_low=agg.ci_low,
                ci_high=agg.ci_high,
                n_studies=agg.n_studies,
                supporting_dois=agg.unique_dois,
                applicable_habitats=agg.applicable_habitats,
                conflicts=agg.conflicts,
            )
            candidates.append(candidate)

        return candidates

    def _group_patterns(
        self, patterns: list[CandidatePattern]
    ) -> dict[str, list[CandidatePattern]]:
        """Group patterns by fuzzy-matching relationship types."""
        groups: dict[str, list[CandidatePattern]] = {}

        for pattern in patterns:
            matched = False
            for existing_key in list(groups.keys()):
                similarity = SequenceMatcher(
                    None, pattern.relationship_type, existing_key
                ).ratio()
                if similarity >= self._similarity_threshold:
                    groups[existing_key].append(pattern)
                    matched = True
                    break

            if not matched:
                groups[pattern.relationship_type] = [pattern]

        return groups

    def _compute_statistics(
        self, rel_type: str, patterns: list[CandidatePattern]
    ) -> AggregatedPattern:
        """Compute aggregate statistics for a group of patterns."""
        # Deduplicate by DOI (use one coefficient per study)
        doi_coefficients: dict[str, float] = {}
        all_habitats: set[str] = set()
        evidence_tiers: dict[str, int] = {}

        for p in patterns:
            key = p.source_doi if p.source_doi else p.paper_id
            if key and key not in doi_coefficients:
                doi_coefficients[key] = p.coefficient_value
            if p.habitat:
                all_habitats.add(p.habitat)

        coefficients = list(doi_coefficients.values())
        unique_dois = [d for d in doi_coefficients.keys() if d]
        n_studies = len(coefficients)

        if n_studies == 0:
            return AggregatedPattern(
                relationship_type=rel_type,
                patterns=patterns,
            )

        mean_coeff = statistics.mean(coefficients)
        std_dev = statistics.stdev(coefficients) if n_studies >= 2 else 0.0

        # CI: mean +/- 1.96 * (SD / sqrt(n)) if n >= 2, else use +/- 20%
        if n_studies >= 2 and std_dev > 0:
            se = std_dev / math.sqrt(n_studies)
            ci_low = mean_coeff - 1.96 * se
            ci_high = mean_coeff + 1.96 * se
        else:
            ci_low = mean_coeff * 0.8
            ci_high = mean_coeff * 1.2

        # Conflict detection: flag DOIs with coefficients > 2 SD from mean
        conflicts: list[str] = []
        if std_dev > 0:
            for doi, coeff in doi_coefficients.items():
                if abs(coeff - mean_coeff) > self._outlier_sd_threshold * std_dev:
                    conflicts.append(doi)

        return AggregatedPattern(
            relationship_type=rel_type,
            patterns=patterns,
            mean_coefficient=mean_coeff,
            std_dev=std_dev,
            ci_low=ci_low,
            ci_high=ci_high,
            n_studies=n_studies,
            unique_dois=unique_dois,
            applicable_habitats=sorted(all_habitats),
            conflicts=conflicts,
            evidence_tiers=evidence_tiers,
        )
