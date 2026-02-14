"""Cross-domain reasoning engine for MARIS.

Provides hybrid GraphRAG retrieval, rule-based inference using bridge axioms,
and human-readable explanation generation. Extends the existing 5-template
Cypher system with open-domain queries via forward/backward chaining.
"""

from maris.reasoning.context_builder import ContextNode, ContextEdge, ContextGraph
from maris.reasoning.hybrid_retriever import HybridRetriever, RetrievalResult
from maris.reasoning.inference_engine import InferenceEngine, InferenceStep
from maris.reasoning.explanation import ExplanationGenerator

__all__ = [
    "ContextNode",
    "ContextEdge",
    "ContextGraph",
    "HybridRetriever",
    "RetrievalResult",
    "InferenceEngine",
    "InferenceStep",
    "ExplanationGenerator",
]
