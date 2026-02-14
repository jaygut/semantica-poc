"""MARISProvenanceManager - high-level wrapper for the provenance system.

Provides convenience methods that compose the lower-level components
(ProvenanceManager, BridgeAxiomRegistry, IntegrityVerifier, ProvenanceCertificate)
into a single API surface for the rest of the MARIS codebase.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from maris.provenance.bridge_axiom_registry import BridgeAxiomRegistry
from maris.provenance.certificate import ProvenanceCertificate
from maris.provenance.core import ProvenanceAgent, ProvenanceManager
from maris.provenance.integrity import IntegrityVerifier
from maris.provenance.storage import InMemoryStorage

logger = logging.getLogger(__name__)


class MARISProvenanceManager:
    """Unified provenance interface for MARIS.

    Combines provenance tracking, axiom registry, certificate generation,
    and integrity verification into a single entry point.
    """

    def __init__(
        self,
        templates_path: Path | str | None = None,
        evidence_path: Path | str | None = None,
    ) -> None:
        self._storage = InMemoryStorage()
        self._prov = ProvenanceManager(self._storage)
        self._registry = BridgeAxiomRegistry()
        self._certificate = ProvenanceCertificate(self._prov)
        self._verifier = IntegrityVerifier()

        # Register the MARIS system as an agent
        self._prov.register_agent(ProvenanceAgent(
            agent_id="maris:system",
            agent_type="SoftwareAgent",
            name="MARIS v2",
        ))

        # Load axioms if paths provided
        if templates_path:
            self._registry.load(
                Path(templates_path),
                Path(evidence_path) if evidence_path else None,
            )

    @property
    def provenance(self) -> ProvenanceManager:
        """Access the underlying ProvenanceManager."""
        return self._prov

    @property
    def registry(self) -> BridgeAxiomRegistry:
        """Access the BridgeAxiomRegistry."""
        return self._registry

    @property
    def certificate(self) -> ProvenanceCertificate:
        """Access the ProvenanceCertificate generator."""
        return self._certificate

    @property
    def verifier(self) -> IntegrityVerifier:
        """Access the IntegrityVerifier."""
        return self._verifier

    # -- Convenience methods --------------------------------------------------

    def track_extraction(
        self,
        entity_id: str,
        entity_type: str,
        source_doi: str,
        attributes: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Track an entity extracted from a source document.

        Creates the entity and records the extraction activity.
        Returns the entity dict.
        """
        # Track the source document as an entity if not already tracked
        doc_entity_id = f"doc:{source_doi}"
        if not self._prov.get_entity(doc_entity_id):
            self._prov.track_entity(
                entity_id=doc_entity_id,
                entity_type="Document",
                attributes={"doi": source_doi},
            )

        # Track the extracted entity
        entity = self._prov.track_entity(
            entity_id=entity_id,
            entity_type=entity_type,
            attributes=attributes or {},
            derived_from=[doc_entity_id],
            attributed_to="maris:system",
        )

        # Record the extraction activity
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
        """Track the application of a bridge axiom.

        Returns the activity dict, or None if the axiom is not in the registry.
        """
        axiom = self._registry.get(axiom_id)
        if axiom is None:
            logger.warning("Axiom %s not found in registry", axiom_id)
            return None

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

    def get_certificate(self, entity_id: str) -> dict[str, Any]:
        """Generate a provenance certificate for an entity."""
        return self._certificate.generate(entity_id)

    def get_certificate_markdown(self, entity_id: str) -> str:
        """Generate a Markdown provenance certificate for an entity."""
        return self._certificate.generate_markdown(entity_id)

    def get_lineage(self, entity_id: str) -> list[dict[str, Any]]:
        """Get the derivation lineage for an entity."""
        return self._prov.get_lineage(entity_id)

    def summary(self) -> dict[str, Any]:
        """Return a summary of provenance state."""
        prov_summary = self._prov.summary()
        return {
            **prov_summary,
            "axioms_loaded": self._registry.count(),
        }
