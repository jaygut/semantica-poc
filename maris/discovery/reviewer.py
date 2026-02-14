"""Human-in-the-loop validation for candidate axioms.

Provides an accept/reject interface for CandidateAxiom objects. When accepted,
converts candidates to bridge axiom template format. All decisions are recorded
with timestamps and reviewer identity for audit provenance.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from maris.discovery.candidate_axiom import CandidateAxiom

logger = logging.getLogger(__name__)


class AxiomReviewer:
    """Review and validate candidate axioms with full audit trail.

    Maintains an internal list of candidates and a decision history log.
    When a candidate is accepted, it is converted to bridge axiom template
    format compatible with schemas/bridge_axiom_templates.json.
    """

    def __init__(self, provenance_manager: Any = None) -> None:
        self._candidates: dict[str, CandidateAxiom] = {}
        self._history: list[dict[str, Any]] = []
        self._provenance = provenance_manager

    def add_candidate(self, candidate: CandidateAxiom) -> None:
        """Add a candidate axiom for review."""
        self._candidates[candidate.candidate_id] = candidate

    def add_candidates(self, candidates: list[CandidateAxiom]) -> int:
        """Add multiple candidates. Returns count added."""
        for c in candidates:
            self.add_candidate(c)
        return len(candidates)

    def get_candidate(self, candidate_id: str) -> CandidateAxiom | None:
        """Get a candidate by ID."""
        return self._candidates.get(candidate_id)

    def list_candidates(
        self, status: str | None = None
    ) -> list[CandidateAxiom]:
        """List candidates, optionally filtered by status."""
        candidates = list(self._candidates.values())
        if status:
            candidates = [c for c in candidates if c.status == status]
        return candidates

    def accept(
        self,
        candidate_id: str,
        reviewer: str,
        notes: str = "",
    ) -> CandidateAxiom | None:
        """Accept a candidate axiom.

        Updates the candidate status and records the decision.
        Returns the updated candidate, or None if not found.
        """
        candidate = self._candidates.get(candidate_id)
        if candidate is None:
            logger.warning("Candidate %s not found", candidate_id)
            return None

        now = datetime.now(timezone.utc).isoformat()
        candidate.status = "accepted"
        candidate.reviewed_by = reviewer
        candidate.reviewed_at = now
        candidate.review_notes = notes

        self._record_decision(candidate_id, "accepted", reviewer, notes, now)
        logger.info("Accepted candidate %s by %s", candidate_id, reviewer)

        return candidate

    def reject(
        self,
        candidate_id: str,
        reviewer: str,
        reason: str = "",
    ) -> CandidateAxiom | None:
        """Reject a candidate axiom.

        Updates the candidate status and records the decision.
        Returns the updated candidate, or None if not found.
        """
        candidate = self._candidates.get(candidate_id)
        if candidate is None:
            logger.warning("Candidate %s not found", candidate_id)
            return None

        now = datetime.now(timezone.utc).isoformat()
        candidate.status = "rejected"
        candidate.reviewed_by = reviewer
        candidate.reviewed_at = now
        candidate.review_notes = reason

        self._record_decision(candidate_id, "rejected", reviewer, reason, now)
        logger.info("Rejected candidate %s by %s: %s", candidate_id, reviewer, reason)

        return candidate

    def get_accepted_templates(self) -> list[dict]:
        """Get all accepted candidates converted to axiom template format."""
        templates = []
        for candidate in self._candidates.values():
            if candidate.status == "accepted":
                templates.append(candidate.to_axiom_template())
        return templates

    def get_decision_history(self) -> list[dict[str, Any]]:
        """Return the full decision history for audit."""
        return list(self._history)

    def _record_decision(
        self,
        candidate_id: str,
        decision: str,
        reviewer: str,
        notes: str,
        timestamp: str,
    ) -> None:
        """Record a review decision in the history log."""
        record = {
            "candidate_id": candidate_id,
            "decision": decision,
            "reviewer": reviewer,
            "notes": notes,
            "timestamp": timestamp,
        }
        self._history.append(record)

        # Track in provenance system if available
        if self._provenance is not None:
            try:
                self._provenance.provenance.record_activity(
                    activity_type="axiom_review",
                    attributes={
                        "candidate_id": candidate_id,
                        "decision": decision,
                        "reviewer": reviewer,
                        "notes": notes,
                    },
                )
            except Exception:
                logger.warning("Failed to record review in provenance", exc_info=True)
