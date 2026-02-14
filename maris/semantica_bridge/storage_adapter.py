"""Storage adapter - wraps Semantica's ProvenanceStorage behind MARIS's InMemoryStorage API.

MARIS's InMemoryStorage uses a generic (record_type, record_id) -> dict model.
Semantica's storage uses ProvenanceEntry objects keyed by entity_id.

This adapter bridges both: MARIS code keeps calling .put()/.get()/.find() etc.,
while provenance-type records are persisted through Semantica's SQLiteStorage
for durability and W3C PROV-O compliance.
"""

from __future__ import annotations

import copy
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

try:
    from semantica.provenance.storage import (
        SQLiteStorage as _SemanticaSQLiteStorage,
        InMemoryStorage as _SemanticaInMemoryStorage,
    )
    from semantica.provenance.schemas import ProvenanceEntry as _SemanticaEntry

    _HAS_SEMANTICA = True
except ImportError:
    _HAS_SEMANTICA = False


class SemanticaStorage:
    """Drop-in replacement for maris.provenance.storage.InMemoryStorage that
    persists provenance-type records through Semantica's SQLiteStorage.

    Records whose type is ``entity``, ``activity``, or ``agent`` are also
    mirrored into a Semantica ProvenanceEntry for lineage tracing and
    persistent audit.  All other record types are stored in a local dict
    exactly like the original InMemoryStorage.

    API-compatible with ``maris.provenance.storage.InMemoryStorage``.
    """

    def __init__(self, db_path: str | None = None) -> None:
        self._local: dict[tuple[str, str], dict[str, Any]] = {}
        self._lock = threading.Lock()

        # Initialise Semantica backend
        if _HAS_SEMANTICA and db_path:
            self._semantica = _SemanticaSQLiteStorage(db_path)
            logger.info("SemanticaStorage: using SQLite backend at %s", db_path)
        elif _HAS_SEMANTICA:
            self._semantica = _SemanticaInMemoryStorage()
            logger.info("SemanticaStorage: using Semantica in-memory backend")
        else:
            self._semantica = None
            logger.info("SemanticaStorage: semantica not installed, local-only mode")

    @property
    def semantica_backend(self) -> Any:
        """Direct access to the underlying Semantica storage (for tests)."""
        return self._semantica

    # -- CRUD (MARIS-compatible) -----------------------------------------------

    def put(self, record_type: str, record_id: str, data: dict[str, Any]) -> None:
        with self._lock:
            self._local[(record_type, record_id)] = copy.deepcopy(data)

        # Mirror to Semantica storage for provenance-typed records
        if self._semantica is not None and record_type in ("entity", "activity", "agent"):
            try:
                entry = _dict_to_semantica_entry(record_type, record_id, data)
                self._semantica.store(entry)
            except Exception:
                logger.debug("SemanticaStorage: failed to mirror %s/%s", record_type, record_id, exc_info=True)

    def get(self, record_type: str, record_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._local.get((record_type, record_id))
            return copy.deepcopy(record) if record is not None else None

    def delete(self, record_type: str, record_id: str) -> bool:
        with self._lock:
            return self._local.pop((record_type, record_id), None) is not None

    def exists(self, record_type: str, record_id: str) -> bool:
        with self._lock:
            return (record_type, record_id) in self._local

    # -- Queries ---------------------------------------------------------------

    def list_by_type(self, record_type: str) -> list[dict[str, Any]]:
        with self._lock:
            return [
                copy.deepcopy(v)
                for (rt, _), v in self._local.items()
                if rt == record_type
            ]

    def find(self, record_type: str, **attrs: Any) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        with self._lock:
            for (rt, _), v in self._local.items():
                if rt != record_type:
                    continue
                if all(v.get(k) == val for k, val in attrs.items()):
                    results.append(copy.deepcopy(v))
        return results

    def count(self, record_type: str | None = None) -> int:
        with self._lock:
            if record_type is None:
                return len(self._local)
            return sum(1 for (rt, _) in self._local if rt == record_type)

    def clear(self) -> None:
        with self._lock:
            self._local.clear()
        if self._semantica is not None:
            try:
                self._semantica.clear()
            except Exception:
                pass

    # -- Semantica-specific queries --------------------------------------------

    def trace_lineage(self, entity_id: str) -> list[dict[str, Any]]:
        """Trace lineage through Semantica's BFS traversal.

        Falls back to a local derived_from walk if Semantica is unavailable.
        """
        if self._semantica is not None:
            try:
                entries = self._semantica.trace_lineage(entity_id)
                return [e.to_dict() for e in entries]
            except Exception:
                pass

        # Fallback: local BFS on derived_from chains
        visited: set[str] = set()
        chain: list[dict[str, Any]] = []
        queue = [entity_id]
        while queue:
            eid = queue.pop(0)
            if eid in visited:
                continue
            visited.add(eid)
            record = self.get("entity", eid)
            if record is not None:
                chain.append(record)
                for parent_id in record.get("derived_from", []):
                    if parent_id not in visited:
                        queue.append(parent_id)
        return chain

    def retrieve_semantica_entry(self, entity_id: str) -> Any | None:
        """Retrieve the raw Semantica ProvenanceEntry for an entity."""
        if self._semantica is not None:
            try:
                return self._semantica.retrieve(entity_id)
            except Exception:
                return None
        return None


# -- Helpers -------------------------------------------------------------------

def _dict_to_semantica_entry(
    record_type: str, record_id: str, data: dict[str, Any]
) -> "_SemanticaEntry":
    """Convert a MARIS dict record into a Semantica ProvenanceEntry."""
    return _SemanticaEntry(
        entity_id=record_id,
        entity_type=data.get("entity_type", record_type),
        activity_id=data.get("activity_id", data.get("generated_by", record_type + "_tracking")),
        agent_id=data.get("attributed_to", "maris:system"),
        source_document=data.get("attributes", {}).get("doi", data.get("source_doi", "")),
        source_location=data.get("attributes", {}).get("source_page"),
        source_quote=data.get("attributes", {}).get("source_quote"),
        confidence=data.get("confidence", 1.0) if isinstance(data.get("confidence"), (int, float)) else 1.0,
        parent_entity_id=data.get("derived_from", [None])[0] if data.get("derived_from") else None,
        used_entities=data.get("used", []),
        metadata=data.get("attributes", {}),
    )
