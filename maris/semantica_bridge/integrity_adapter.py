"""Integrity adapter - wraps Semantica's integrity functions into MARIS's class interface.

MARIS uses IntegrityVerifier (a class with static methods):
    IntegrityVerifier.compute_checksum(dict) -> str
    IntegrityVerifier.verify(dict, expected) -> bool

Semantica uses module-level functions:
    compute_checksum(ProvenanceEntry) -> str
    verify_checksum(ProvenanceEntry, expected) -> bool
    compute_dict_checksum(dict) -> str
    verify_dict_checksum(dict, expected) -> bool

This adapter creates an IntegrityVerifier that delegates dict checksums to
Semantica's compute_dict_checksum/verify_dict_checksum, and also provides
ProvenanceEntry-level verification through Semantica's native functions.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

try:
    from semantica.provenance.integrity import (
        compute_checksum as _sem_compute,
        verify_checksum as _sem_verify,
        compute_dict_checksum as _sem_dict_checksum,
        verify_dict_checksum as _sem_dict_verify,
    )
    _HAS_SEMANTICA = True
except ImportError:
    _HAS_SEMANTICA = False


class SemanticaIntegrityVerifier:
    """Integrity verifier that delegates to Semantica's checksum functions.

    Drop-in compatible with ``maris.provenance.integrity.IntegrityVerifier``.
    When Semantica is installed, dict checksums use Semantica's implementation
    for consistency with their storage layer.  Falls back to MARIS-native
    JSON-based SHA-256 when Semantica is unavailable.
    """

    @staticmethod
    def compute_checksum(data: dict[str, Any]) -> str:
        """Compute SHA-256 checksum of a dict, using Semantica if available."""
        if _HAS_SEMANTICA:
            try:
                return _sem_dict_checksum(data)
            except Exception:
                pass
        # Fallback: MARIS-native
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def verify(data: dict[str, Any], expected_checksum: str) -> bool:
        """Verify dict checksum, using Semantica if available."""
        if _HAS_SEMANTICA:
            try:
                return _sem_dict_verify(data, expected_checksum)
            except Exception:
                pass
        actual = SemanticaIntegrityVerifier.compute_checksum(data)
        return actual == expected_checksum

    @staticmethod
    def compute_checksum_bytes(content: bytes) -> str:
        """Compute SHA-256 of raw bytes (no Semantica equivalent, always native)."""
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def verify_entry(entry: Any, expected: str | None = None) -> bool:
        """Verify a Semantica ProvenanceEntry's checksum.

        Only works when Semantica is installed. Returns False otherwise.
        """
        if _HAS_SEMANTICA:
            try:
                return _sem_verify(entry, expected)
            except Exception:
                return False
        return False

    @staticmethod
    def compute_entry_checksum(entry: Any) -> str:
        """Compute checksum for a Semantica ProvenanceEntry.

        Returns empty string if Semantica is unavailable.
        """
        if _HAS_SEMANTICA:
            try:
                return _sem_compute(entry)
            except Exception:
                return ""
        return ""
