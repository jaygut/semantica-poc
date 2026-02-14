"""MARIS Provenance Module - W3C PROV-O compatible provenance tracking.

Provides self-contained provenance infrastructure implementing the interfaces
expected by the Semantica framework. All classes are standalone (no external
semantica dependency required) so that downstream P1-P4 modules can code
against a stable API regardless of whether the Hawksight-AI semantica package
is installed.

Core components:
    InMemoryStorage        - Dict-based provenance record storage
    ProvenanceManager      - W3C PROV-O style entity/activity/agent tracking
    BridgeAxiom            - Dataclass representing a single translation rule
    TranslationChain       - Sequences multiple BridgeAxiom applications
    IntegrityVerifier      - SHA-256 content checksums
    BridgeAxiomRegistry    - Loads 16 axioms from JSON, builds TranslationChains
    ProvenanceCertificate  - Generates JSON + Markdown provenance certificates
"""

from maris.provenance.storage import InMemoryStorage
from maris.provenance.core import (
    ProvenanceEntity,
    ProvenanceActivity,
    ProvenanceAgent,
    ProvenanceManager,
)
from maris.provenance.bridge_axiom import BridgeAxiom, TranslationChain
from maris.provenance.integrity import IntegrityVerifier
from maris.provenance.bridge_axiom_registry import BridgeAxiomRegistry
from maris.provenance.certificate import ProvenanceCertificate

__all__ = [
    "InMemoryStorage",
    "ProvenanceEntity",
    "ProvenanceActivity",
    "ProvenanceAgent",
    "ProvenanceManager",
    "BridgeAxiom",
    "TranslationChain",
    "IntegrityVerifier",
    "BridgeAxiomRegistry",
    "ProvenanceCertificate",
]
