"""Provenance model objects used across validation and graph population."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DoiVerificationResult:
    """Structured DOI verification result.

    verification_status values:
    - missing
    - placeholder_blocked
    - invalid_format
    - unverified
    - unresolvable
    - verified
    """

    raw_doi: str
    normalized_doi: str
    doi_valid: bool
    verification_status: str
    reason: str
    resolver: str = ""
    resolved_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
