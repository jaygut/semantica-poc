"""Semantica SDK Bridge - adapters that delegate MARIS operations to the real Semantica package.

When the ``semantica`` package (Hawksight-AI) is installed, this bridge lets
MARIS use Semantica's provenance, axiom, storage, and integrity systems under
the hood while preserving MARIS's own API surface.  If ``semantica`` is not
installed the bridge gracefully degrades and MARIS falls back to its native
implementations.

Modules:
    storage_adapter      - SemanticaStorage wrapping semantica.provenance.storage
    axiom_adapter        - Convert between MARIS and Semantica BridgeAxiom objects
    provenance_adapter   - Dual-write ProvenanceManager delegating to Semantica
    integrity_adapter     - Integrity functions backed by Semantica's checksums
    manager              - Enhanced MARISProvenanceManager using Semantica SDK
"""

from __future__ import annotations

import importlib.util

SEMANTICA_AVAILABLE: bool = importlib.util.find_spec("semantica") is not None

from maris.semantica_bridge.storage_adapter import SemanticaStorage  # noqa: E402
from maris.semantica_bridge.axiom_adapter import (  # noqa: E402
    to_semantica_axiom,
    from_semantica_axiom,
    apply_via_semantica,
    create_semantica_chain,
)
from maris.semantica_bridge.provenance_adapter import SemanticaProvenanceAdapter  # noqa: E402
from maris.semantica_bridge.integrity_adapter import SemanticaIntegrityVerifier  # noqa: E402
from maris.semantica_bridge.manager import SemanticaBackedManager  # noqa: E402

__all__ = [
    "SEMANTICA_AVAILABLE",
    "SemanticaStorage",
    "SemanticaProvenanceAdapter",
    "SemanticaIntegrityVerifier",
    "SemanticaBackedManager",
    "to_semantica_axiom",
    "from_semantica_axiom",
    "apply_via_semantica",
    "create_semantica_chain",
]
