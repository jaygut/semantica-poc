"""Provenance adapter - delegates MARIS provenance tracking to Semantica's ProvenanceManager.

This adapter wraps MARIS's ProvenanceManager (which uses InMemoryStorage with
a (type, id) -> dict model) and mirrors all provenance operations into
Semantica's ProvenanceManager (which uses ProvenanceEntry + SQLite).

The result is dual-write provenance: MARIS's fast local storage for the query
pipeline, plus Semantica's persistent W3C PROV-O-compliant storage for audits,
lineage tracing, and regulatory compliance.
"""

from __future__ import annotations

import logging
from typing import Any

from maris.provenance.core import (
    ProvenanceEntity,
    ProvenanceManager as MARISProvenanceManager,
)
from maris.provenance.storage import InMemoryStorage as MARISStorage

logger = logging.getLogger(__name__)

try:
    from semantica.provenance.manager import ProvenanceManager as SemanticaPM
    from semantica.provenance.storage import (
        SQLiteStorage as SemanticaSQLite,
        InMemoryStorage as SemanticaMemory,
    )
    _HAS_SEMANTICA = True
except ImportError:
    _HAS_SEMANTICA = False


class SemanticaProvenanceAdapter(MARISProvenanceManager):
    """Extended ProvenanceManager that dual-writes to Semantica's backend.

    Inherits from maris.provenance.core.ProvenanceManager so all existing MARIS
    code works unchanged.  Additionally mirrors every track_entity(),
    record_activity(), and register_agent() call into a Semantica
    ProvenanceManager backed by SQLite for persistent audit trails.

    Usage:
        adapter = SemanticaProvenanceAdapter(db_path="provenance.db")
        entity = adapter.track_entity("cabo_pulmo_esv", entity_type="valuation")
        lineage = adapter.get_lineage("cabo_pulmo_esv")  # queries both backends
    """

    def __init__(
        self,
        storage: MARISStorage | None = None,
        db_path: str | None = None,
    ) -> None:
        super().__init__(storage=storage)

        # Initialize Semantica backend
        self._sem_pm: Any = None
        if _HAS_SEMANTICA:
            if db_path:
                sem_storage = SemanticaSQLite(db_path)
            else:
                sem_storage = SemanticaMemory()
            self._sem_pm = SemanticaPM(storage=sem_storage)
            logger.info(
                "SemanticaProvenanceAdapter: Semantica backend active (%s)",
                "SQLite" if db_path else "in-memory",
            )
        else:
            logger.info("SemanticaProvenanceAdapter: semantica not installed, MARIS-only mode")

    @property
    def semantica_manager(self) -> Any:
        """Direct access to the underlying Semantica ProvenanceManager."""
        return self._sem_pm

    # -- Entity tracking (dual-write) ------------------------------------------

    def track_entity(
        self,
        entity_id: str,
        entity_type: str = "",
        attributes: dict[str, Any] | None = None,
        generated_by: str | None = None,
        derived_from: list[str] | None = None,
        attributed_to: str | None = None,
    ) -> ProvenanceEntity:
        """Track an entity in both MARIS and Semantica backends."""
        # MARIS native tracking (always)
        entity = super().track_entity(
            entity_id=entity_id,
            entity_type=entity_type,
            attributes=attributes,
            generated_by=generated_by,
            derived_from=derived_from,
            attributed_to=attributed_to,
        )

        # Mirror to Semantica
        if self._sem_pm is not None:
            try:
                source = (attributes or {}).get("doi", "")
                if not source and derived_from:
                    source = derived_from[0]
                self._sem_pm.track_entity(
                    entity_id=entity_id,
                    source=source or entity_type,
                    metadata=attributes,
                    entity_type=entity_type,
                    parent_entity_id=derived_from[0] if derived_from else None,
                    confidence=_extract_confidence(attributes),
                )
            except Exception:
                logger.debug("Semantica mirror failed for entity %s", entity_id, exc_info=True)

        return entity

    # -- Activity recording (dual-write) ---------------------------------------

    def record_activity(
        self,
        activity_type: str = "",
        used: list[str] | None = None,
        generated: list[str] | None = None,
        associated_with: str | None = None,
        attributes: dict[str, Any] | None = None,
        activity_id: str | None = None,
    ) -> Any:
        """Record an activity in both MARIS and Semantica backends."""
        activity = super().record_activity(
            activity_type=activity_type,
            used=used,
            generated=generated,
            associated_with=associated_with,
            attributes=attributes,
            activity_id=activity_id,
        )

        # Mirror to Semantica as a relationship tracking
        if self._sem_pm is not None:
            try:
                self._sem_pm.track_relationship(
                    relationship_id=activity.activity_id,
                    source=(attributes or {}).get("source_doi", activity_type),
                    metadata={
                        "activity_type": activity_type,
                        "used": used or [],
                        "generated": generated or [],
                        **(attributes or {}),
                    },
                )
            except Exception:
                logger.debug("Semantica mirror failed for activity %s", activity.activity_id, exc_info=True)

        return activity

    # -- Lineage queries (enhanced with Semantica) -----------------------------

    def get_lineage(self, entity_id: str, max_depth: int = 10) -> list[dict[str, Any]]:
        """Get lineage, preferring Semantica's BFS trace when available."""
        # Always get MARIS native lineage
        maris_lineage = super().get_lineage(entity_id, max_depth)

        # Enrich with Semantica lineage if available
        if self._sem_pm is not None:
            try:
                sem_lineage = self._sem_pm.get_lineage(entity_id)
                if sem_lineage and sem_lineage.get("lineage_chain"):
                    # Add Semantica-specific metadata to MARIS lineage entries
                    sem_sources = sem_lineage.get("source_documents", [])
                    if sem_sources and maris_lineage:
                        maris_lineage[0]["_semantica_sources"] = sem_sources
                        maris_lineage[0]["_semantica_entity_count"] = sem_lineage.get("entity_count", 0)
            except Exception:
                logger.debug("Semantica lineage enrichment failed for %s", entity_id, exc_info=True)

        return maris_lineage

    # -- Semantica-specific queries --------------------------------------------

    def get_semantica_lineage(self, entity_id: str) -> dict[str, Any]:
        """Get lineage directly from Semantica's ProvenanceManager.

        Returns an empty dict if Semantica is unavailable.
        """
        if self._sem_pm is not None:
            try:
                return self._sem_pm.get_lineage(entity_id)
            except Exception:
                pass
        return {}

    def get_semantica_statistics(self) -> dict[str, Any]:
        """Get statistics from the Semantica backend."""
        if self._sem_pm is not None:
            try:
                return self._sem_pm.get_statistics()
            except Exception:
                pass
        return {"total_entries": 0, "entity_types": {}, "unique_sources": 0}

    def get_all_semantica_sources(self, entity_id: str) -> list[dict[str, Any]]:
        """Get all sources from Semantica's source tracker."""
        if self._sem_pm is not None:
            try:
                return self._sem_pm.get_all_sources(entity_id)
            except Exception:
                pass
        return []


def _extract_confidence(attributes: dict[str, Any] | None) -> float:
    """Extract a numeric confidence value from attributes."""
    if not attributes:
        return 1.0
    conf = attributes.get("confidence", 1.0)
    if isinstance(conf, (int, float)):
        return float(conf)
    if isinstance(conf, str):
        return {"high": 0.9, "medium": 0.7, "low": 0.4}.get(conf, 0.7)
    return 1.0
