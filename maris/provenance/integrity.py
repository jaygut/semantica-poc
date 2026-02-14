"""SHA-256 integrity verification for provenance records."""

from __future__ import annotations

import hashlib
import json
from typing import Any


class IntegrityVerifier:
    """Compute and verify SHA-256 checksums for provenance data.

    Provides content-addressable integrity checking for any dict-like
    provenance record. Keys are sorted for deterministic hashing.
    """

    @staticmethod
    def compute_checksum(data: dict[str, Any]) -> str:
        """Compute SHA-256 hex digest of a JSON-serialized dict.

        Keys are sorted for deterministic output regardless of insertion
        order.
        """
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def verify(data: dict[str, Any], expected_checksum: str) -> bool:
        """Verify that a dict matches the expected checksum."""
        actual = IntegrityVerifier.compute_checksum(data)
        return actual == expected_checksum

    @staticmethod
    def compute_checksum_bytes(content: bytes) -> str:
        """Compute SHA-256 hex digest of raw bytes."""
        return hashlib.sha256(content).hexdigest()
