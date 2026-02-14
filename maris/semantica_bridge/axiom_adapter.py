"""Bridge axiom adapter - convert between MARIS and Semantica BridgeAxiom objects.

MARIS BridgeAxiom.apply(input_value) takes 1 arg and returns a result dict.
Semantica BridgeAxiom.apply(input_entity, input_value) takes 2 args and also
optionally tracks provenance through a ProvenanceManager.

This adapter transparently converts between the two representations and
enables MARIS to use Semantica's axiom application with full provenance tracking.
"""

from __future__ import annotations

import logging
from typing import Any

from maris.provenance.bridge_axiom import BridgeAxiom as MARISAxiom

logger = logging.getLogger(__name__)

try:
    from semantica.provenance.bridge_axiom import (
        BridgeAxiom as SemanticaAxiom,
        create_translation_chain as _create_chain,
    )

    _HAS_SEMANTICA = True
except ImportError:
    _HAS_SEMANTICA = False


def to_semantica_axiom(maris_axiom: MARISAxiom) -> Any:
    """Convert a MARIS BridgeAxiom to a Semantica BridgeAxiom.

    Returns a ``semantica.provenance.bridge_axiom.BridgeAxiom`` instance,
    or ``None`` if the semantica package is not installed.
    """
    if not _HAS_SEMANTICA:
        return None

    # Map MARIS confidence (string or float) to Semantica confidence (float)
    confidence = maris_axiom.confidence
    if isinstance(confidence, str):
        confidence = {"high": 0.9, "medium": 0.7, "low": 0.4}.get(confidence, 0.7)

    return SemanticaAxiom(
        axiom_id=maris_axiom.axiom_id,
        name=maris_axiom.name,
        rule=maris_axiom.rule,
        coefficient=maris_axiom.coefficient,
        source_doi=maris_axiom.source_doi,
        source_page=maris_axiom.source_page or "",
        source_quote=maris_axiom.source_quote or None,
        confidence=confidence,
        input_domain=maris_axiom.input_domain,
        output_domain=maris_axiom.output_domain,
        metadata={
            "ci_low": maris_axiom.ci_low,
            "ci_high": maris_axiom.ci_high,
            "applicable_habitats": maris_axiom.applicable_habitats,
            "evidence_sources": maris_axiom.evidence_sources,
            "caveats": maris_axiom.caveats,
        },
    )


def from_semantica_axiom(sem_axiom: Any) -> MARISAxiom:
    """Convert a Semantica BridgeAxiom to a MARIS BridgeAxiom.

    Works with any object exposing the SemanticaAxiom interface.
    """
    meta = getattr(sem_axiom, "metadata", {}) or {}
    return MARISAxiom(
        axiom_id=sem_axiom.axiom_id,
        name=sem_axiom.name,
        rule=sem_axiom.rule,
        coefficient=sem_axiom.coefficient,
        input_domain=sem_axiom.input_domain,
        output_domain=sem_axiom.output_domain,
        source_doi=sem_axiom.source_doi,
        source_page=getattr(sem_axiom, "source_page", ""),
        source_quote=getattr(sem_axiom, "source_quote", "") or "",
        confidence=sem_axiom.confidence,
        ci_low=meta.get("ci_low"),
        ci_high=meta.get("ci_high"),
        applicable_habitats=meta.get("applicable_habitats", []),
        evidence_sources=meta.get("evidence_sources", []),
        caveats=meta.get("caveats", []),
    )


def apply_via_semantica(
    maris_axiom: MARISAxiom,
    input_entity: str,
    input_value: float,
    prov_manager: Any | None = None,
) -> dict[str, Any]:
    """Apply a MARIS axiom through Semantica's BridgeAxiom.apply() with provenance.

    This is the key integration point: it converts the MARIS axiom to a
    Semantica axiom, applies it using Semantica's implementation (which
    optionally tracks provenance), and converts the result back to MARIS
    format.

    Falls back to MARIS-native apply() if semantica is not installed.
    """
    if not _HAS_SEMANTICA:
        # Fallback: use MARIS native apply
        result = maris_axiom.apply(input_value)
        result["input_entity"] = input_entity
        result["output_entity"] = f"{input_entity}_transformed_{maris_axiom.axiom_id}"
        return result

    sem_axiom = to_semantica_axiom(maris_axiom)
    result = sem_axiom.apply(
        input_entity=input_entity,
        input_value=input_value,
        prov_manager=prov_manager,
    )

    # Enrich with MARIS-specific CI if available
    if maris_axiom.ci_low is not None and maris_axiom.ci_high is not None:
        result["ci_low"] = input_value * maris_axiom.ci_low
        result["ci_high"] = input_value * maris_axiom.ci_high

    return result


def create_semantica_chain(
    maris_axioms: list[MARISAxiom],
    input_data: dict[str, Any],
    prov_manager: Any | None = None,
) -> dict[str, Any]:
    """Execute a MARIS axiom chain through Semantica's create_translation_chain().

    Converts MARIS axioms to Semantica axioms, runs the chain via Semantica's
    orchestration, and returns a MARIS-compatible result dict.

    Falls back to MARIS-native TranslationChain.execute() if semantica is not
    installed.
    """
    if not _HAS_SEMANTICA:
        from maris.provenance.bridge_axiom import TranslationChain

        chain = TranslationChain(maris_axioms)
        return chain.execute(input_data.get("value", 0.0))

    sem_axioms = [to_semantica_axiom(a) for a in maris_axioms]
    chain = _create_chain(input_data, sem_axioms, prov_manager)

    # Convert Semantica TranslationChain result to MARIS format
    return {
        "chain_id": chain.chain_id,
        "initial_value": input_data.get("value"),
        "final_value": chain.layers[-1].get("value") if chain.layers else None,
        "layers": chain.layers,
        "confidence": chain.confidence,
        "axiom_count": len(maris_axioms),
        "source_dois": [a.source_doi for a in maris_axioms if a.source_doi],
    }
