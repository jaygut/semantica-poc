"""Provenance endpoint - entity lineage and certificates."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from maris.api.auth import rate_limit_default

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["provenance"], dependencies=[Depends(rate_limit_default)])

# Lazy singleton
_manager: Any = None


def _get_manager() -> Any:
    """Get or create the provenance manager singleton.

    Prefers SemanticaBackedManager (SQLite persistence) when the Semantica SDK
    bridge is available.  Falls back to MARISProvenanceManager (in-memory) if
    the import fails.
    """
    global _manager
    if _manager is None:
        from maris.config import get_config

        cfg = get_config()
        templates_path = cfg.schemas_dir / "bridge_axiom_templates.json"
        evidence_path = cfg.export_dir / "bridge_axioms.json"

        try:
            from maris.semantica_bridge.manager import SemanticaBackedManager

            _manager = SemanticaBackedManager(
                templates_path=templates_path,
                evidence_path=evidence_path,
                db_path=cfg.provenance_db,
            )
            logger.info(
                "Provenance endpoint using SemanticaBackedManager (db=%s)",
                cfg.provenance_db,
            )
        except ImportError:
            from maris.provenance.manager import MARISProvenanceManager

            _manager = MARISProvenanceManager(
                templates_path=templates_path,
                evidence_path=evidence_path,
            )
            logger.info("Provenance endpoint using MARISProvenanceManager (in-memory)")
    return _manager


@router.get("/provenance/{entity_id}")
def get_provenance(entity_id: str) -> dict[str, Any]:
    """Return provenance lineage and certificate for an entity.

    The entity_id can be any tracked entity (e.g., a document DOI,
    an extracted entity, or a bridge axiom identifier).
    """
    manager = _get_manager()

    # Try direct entity lookup
    entity = manager.provenance.get_entity(entity_id)
    if entity is None:
        # Try with doc: prefix for DOIs
        entity = manager.provenance.get_entity(f"doc:{entity_id}")
        if entity is not None:
            entity_id = f"doc:{entity_id}"

    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"Entity '{entity_id}' not found in provenance store",
        )

    certificate = manager.get_certificate(entity_id)
    return certificate


@router.get("/provenance/{entity_id}/markdown")
def get_provenance_markdown(entity_id: str) -> dict[str, str]:
    """Return a Markdown-formatted provenance certificate."""
    manager = _get_manager()

    entity = manager.provenance.get_entity(entity_id)
    if entity is None:
        entity = manager.provenance.get_entity(f"doc:{entity_id}")
        if entity is not None:
            entity_id = f"doc:{entity_id}"

    if entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"Entity '{entity_id}' not found in provenance store",
        )

    markdown = manager.get_certificate_markdown(entity_id)
    return {"entity_id": entity_id, "markdown": markdown}


@router.get("/provenance")
def provenance_summary() -> dict[str, Any]:
    """Return a summary of the provenance store."""
    manager = _get_manager()
    return manager.summary()
