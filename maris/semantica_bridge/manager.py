"""Semantica-backed MARISProvenanceManager.

Enhanced version of maris.provenance.manager.MARISProvenanceManager that uses
the Semantica SDK under the hood for provenance tracking, axiom application,
integrity verification, and persistent storage.

This is the primary integration point - MARIS code that currently uses
MARISProvenanceManager can switch to SemanticaBackedManager for full Semantica
SDK integration with zero API changes.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from maris.provenance.bridge_axiom_registry import BridgeAxiomRegistry
from maris.provenance.certificate import ProvenanceCertificate
from maris.provenance.core import ProvenanceAgent
from maris.semantica_bridge.axiom_adapter import apply_via_semantica, create_semantica_chain
from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier
from maris.semantica_bridge.provenance_adapter import SemanticaProvenanceAdapter
from maris.semantica_bridge.storage_adapter import SemanticaStorage

logger = logging.getLogger(__name__)

try:
    import semantica.provenance.manager  # noqa: F401

    _HAS_SEMANTICA = True
except ImportError:
    _HAS_SEMANTICA = False


class SemanticaBackedManager:
    """Full MARIS provenance manager backed by the Semantica SDK.

    API-compatible with ``maris.provenance.manager.MARISProvenanceManager``.
    All provenance operations are dual-written to both MARIS's fast local
    storage and Semantica's persistent backend.

    New capabilities over MARISProvenanceManager:
        - SQLite-persistent provenance (via Semantica's SQLiteStorage)
        - Semantica-native lineage tracing with W3C PROV-O compliance
        - Bridge axiom application tracked through Semantica's chain system
        - Integrity verification via Semantica's checksum functions
        - Full audit trail accessible through Semantica's API

    Usage:
        manager = SemanticaBackedManager(
            templates_path="schemas/bridge_axiom_templates.json",
            db_path="provenance.db",
        )
        manager.track_extraction("cabo_pulmo_esv", "EcosystemService", "10.1371/...")
        cert = manager.get_certificate("cabo_pulmo_esv")
    """

    def __init__(
        self,
        templates_path: Path | str | None = None,
        evidence_path: Path | str | None = None,
        db_path: str | None = None,
    ) -> None:
        # Use Semantica-backed storage
        self._storage = SemanticaStorage(db_path=db_path)

        # Use Semantica-backed provenance manager
        self._prov = SemanticaProvenanceAdapter(
            storage=self._storage,
            db_path=db_path,
        )

        # Registry and certificate use MARIS native (no Semantica equivalent)
        self._registry = BridgeAxiomRegistry()
        self._certificate = ProvenanceCertificate(self._prov)
        self._verifier = SemanticaIntegrityVerifier()

        # Register MARIS system agent
        self._prov.register_agent(ProvenanceAgent(
            agent_id="maris:system",
            agent_type="SoftwareAgent",
            name="MARIS v2 (Semantica-backed)",
        ))

        # Load axioms if paths provided
        if templates_path:
            self._registry.load(
                Path(templates_path),
                Path(evidence_path) if evidence_path else None,
            )

        logger.info(
            "SemanticaBackedManager initialized (semantica=%s, db=%s, axioms=%d)",
            _HAS_SEMANTICA,
            db_path or "in-memory",
            self._registry.count(),
        )

    @property
    def provenance(self) -> SemanticaProvenanceAdapter:
        return self._prov

    @property
    def registry(self) -> BridgeAxiomRegistry:
        return self._registry

    @property
    def certificate(self) -> ProvenanceCertificate:
        return self._certificate

    @property
    def verifier(self) -> SemanticaIntegrityVerifier:
        return self._verifier

    @property
    def semantica_available(self) -> bool:
        return _HAS_SEMANTICA

    # -- Convenience methods (matching MARISProvenanceManager API) -------------

    def track_extraction(
        self,
        entity_id: str,
        entity_type: str,
        source_doi: str,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Track an entity extracted from a source document.

        Dual-writes to both MARIS and Semantica backends.
        """
        doc_entity_id = f"doc:{source_doi}"
        if not self._prov.get_entity(doc_entity_id):
            self._prov.track_entity(
                entity_id=doc_entity_id,
                entity_type="Document",
                attributes={"doi": source_doi},
            )

        entity = self._prov.track_entity(
            entity_id=entity_id,
            entity_type=entity_type,
            attributes=attributes or {},
            derived_from=[doc_entity_id],
            attributed_to="maris:system",
        )

        self._prov.record_activity(
            activity_type="extraction",
            used=[doc_entity_id],
            generated=[entity_id],
            associated_with="maris:system",
            attributes={"source_doi": source_doi},
        )

        return entity.to_dict()

    def track_axiom_application(
        self,
        axiom_id: str,
        input_entity_id: str,
        output_entity_id: str,
        input_value: float,
        output_value: float,
    ) -> dict[str, Any] | None:
        """Track axiom application through both MARIS and Semantica.

        When Semantica is available, uses apply_via_semantica() for the axiom
        application to get full provenance tracking in Semantica's backend.
        """
        axiom = self._registry.get(axiom_id)
        if axiom is None:
            logger.warning("Axiom %s not found in registry", axiom_id)
            return None

        # Apply via Semantica for provenance tracking
        apply_via_semantica(
            maris_axiom=axiom,
            input_entity=input_entity_id,
            input_value=input_value,
            prov_manager=self._prov.semantica_manager,
        )

        # Record activity in MARIS
        activity = self._prov.record_activity(
            activity_type="axiom_application",
            used=[input_entity_id],
            generated=[output_entity_id],
            associated_with="maris:system",
            attributes={
                "axiom_id": axiom_id,
                "axiom_name": axiom.name,
                "input_value": input_value,
                "output_value": output_value,
                "source_doi": axiom.source_doi,
            },
        )
        return activity.to_dict()

    def execute_chain(
        self,
        axiom_ids: list[str],
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a translation chain through Semantica's chain system.

        Builds a chain from axiom IDs and runs it through Semantica's
        create_translation_chain() for full provenance.
        """
        axioms = []
        for aid in axiom_ids:
            axiom = self._registry.get(aid)
            if axiom is None:
                raise ValueError(f"Axiom {aid} not found in registry")
            axioms.append(axiom)

        return create_semantica_chain(
            maris_axioms=axioms,
            input_data=input_data,
            prov_manager=self._prov.semantica_manager,
        )

    def get_certificate(self, entity_id: str) -> dict[str, Any]:
        return self._certificate.generate(entity_id)

    def get_certificate_markdown(self, entity_id: str) -> str:
        return self._certificate.generate_markdown(entity_id)

    def get_lineage(self, entity_id: str) -> list[dict[str, Any]]:
        return self._prov.get_lineage(entity_id)

    def get_semantica_lineage(self, entity_id: str) -> dict[str, Any]:
        """Get lineage directly from Semantica's backend."""
        return self._prov.get_semantica_lineage(entity_id)

    def summary(self) -> dict[str, Any]:
        prov_summary = self._prov.summary()
        sem_stats = self._prov.get_semantica_statistics()
        return {
            **prov_summary,
            "axioms_loaded": self._registry.count(),
            "semantica_available": _HAS_SEMANTICA,
            "semantica_entries": sem_stats.get("total_entries", 0),
            "semantica_unique_sources": sem_stats.get("unique_sources", 0),
        }
