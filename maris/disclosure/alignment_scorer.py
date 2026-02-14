"""TNFD alignment scorer - measures disclosure completeness.

Checks each of the 14 TNFD recommended disclosures against available
MARIS graph data and returns a completeness score with gap analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from maris.disclosure.models import TNFDDisclosure, DisclosureSection


@dataclass
class AlignmentResult:
    """Result of a TNFD alignment assessment."""
    total_disclosures: int = 14
    populated_count: int = 0
    gap_count: int = 0
    score_pct: float = 0.0
    populated_ids: list[str] = field(default_factory=list)
    gap_ids: list[str] = field(default_factory=list)
    gap_details: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_disclosures": self.total_disclosures,
            "populated_count": self.populated_count,
            "gap_count": self.gap_count,
            "score_pct": self.score_pct,
            "populated_ids": self.populated_ids,
            "gap_ids": self.gap_ids,
            "gap_details": self.gap_details,
        }


class AlignmentScorer:
    """Score TNFD disclosure completeness against the 14 recommended disclosures.

    The 14 disclosures are organized across 4 pillars:
    - Governance: GOV-A, GOV-B, GOV-C (3)
    - Strategy: STR-A, STR-B, STR-C, STR-D (4)
    - Risk & Impact Management: RIM-A, RIM-B, RIM-C, RIM-D (4)
    - Metrics & Targets: MT-A, MT-B, MT-C (3)
    """

    EXPECTED_IDS = [
        "GOV-A", "GOV-B", "GOV-C",
        "STR-A", "STR-B", "STR-C", "STR-D",
        "RIM-A", "RIM-B", "RIM-C", "RIM-D",
        "MT-A", "MT-B", "MT-C",
    ]

    def score(self, disclosure: TNFDDisclosure) -> AlignmentResult:
        """Evaluate disclosure completeness.

        Returns an AlignmentResult with populated/gap counts and details.
        """
        all_sections = self._collect_sections(disclosure)
        section_map: dict[str, DisclosureSection] = {
            s.disclosure_id: s for s in all_sections
        }

        populated_ids: list[str] = []
        gap_ids: list[str] = []
        gap_details: dict[str, str] = {}

        for disc_id in self.EXPECTED_IDS:
            section = section_map.get(disc_id)
            if section and section.populated:
                populated_ids.append(disc_id)
            else:
                gap_ids.append(disc_id)
                reason = ""
                if section and section.gap_reason:
                    reason = section.gap_reason
                elif section and not section.content:
                    reason = "No content generated - insufficient graph data"
                elif section is None:
                    reason = "Disclosure section not generated"
                else:
                    reason = "Section exists but marked as unpopulated"
                gap_details[disc_id] = reason

        total = len(self.EXPECTED_IDS)
        populated_count = len(populated_ids)
        gap_count = len(gap_ids)
        score_pct = (populated_count / total * 100) if total > 0 else 0

        return AlignmentResult(
            total_disclosures=total,
            populated_count=populated_count,
            gap_count=gap_count,
            score_pct=round(score_pct, 1),
            populated_ids=populated_ids,
            gap_ids=gap_ids,
            gap_details=gap_details,
        )

    def _collect_sections(
        self, disclosure: TNFDDisclosure
    ) -> list[DisclosureSection]:
        """Collect all disclosure sections from the Prepare phase."""
        prep = disclosure.prepare
        return (
            prep.governance_sections
            + prep.strategy_sections
            + prep.risk_management_sections
            + prep.metrics_targets_sections
        )
