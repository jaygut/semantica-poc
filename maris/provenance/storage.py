"""In-memory storage backend for provenance records."""

from __future__ import annotations

import copy
import threading
from typing import Any


class InMemoryStorage:
    """Thread-safe dict-based storage for provenance records.

    Records are stored by (record_type, record_id) tuples. Supports
    basic CRUD operations and queries by type or attribute value.
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], dict[str, Any]] = {}
        self._lock = threading.Lock()

    # -- CRUD -----------------------------------------------------------------

    def put(self, record_type: str, record_id: str, data: dict[str, Any]) -> None:
        """Store or overwrite a record."""
        with self._lock:
            self._store[(record_type, record_id)] = copy.deepcopy(data)

    def get(self, record_type: str, record_id: str) -> dict[str, Any] | None:
        """Retrieve a record, or None if not found."""
        with self._lock:
            record = self._store.get((record_type, record_id))
            return copy.deepcopy(record) if record is not None else None

    def delete(self, record_type: str, record_id: str) -> bool:
        """Delete a record. Returns True if it existed."""
        with self._lock:
            return self._store.pop((record_type, record_id), None) is not None

    def exists(self, record_type: str, record_id: str) -> bool:
        """Check whether a record exists."""
        with self._lock:
            return (record_type, record_id) in self._store

    # -- Queries --------------------------------------------------------------

    def list_by_type(self, record_type: str) -> list[dict[str, Any]]:
        """Return all records of a given type."""
        with self._lock:
            return [
                copy.deepcopy(v)
                for (rt, _), v in self._store.items()
                if rt == record_type
            ]

    def find(self, record_type: str, **attrs: Any) -> list[dict[str, Any]]:
        """Return records of *record_type* matching all given attribute values."""
        results: list[dict[str, Any]] = []
        with self._lock:
            for (rt, _), v in self._store.items():
                if rt != record_type:
                    continue
                if all(v.get(k) == val for k, val in attrs.items()):
                    results.append(copy.deepcopy(v))
        return results

    def count(self, record_type: str | None = None) -> int:
        """Count records, optionally filtered by type."""
        with self._lock:
            if record_type is None:
                return len(self._store)
            return sum(1 for (rt, _) in self._store if rt == record_type)

    def clear(self) -> None:
        """Remove all records."""
        with self._lock:
            self._store.clear()
