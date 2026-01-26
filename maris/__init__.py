"""
MARIS (Marine Asset Risk Intelligence System) POC
Semantica × MARIS Knowledge Graph Implementation
"""

__version__ = "0.1.0"
__author__ = "MARIS POC Team"

from maris.config import Config, get_config
from maris.semantica_integration import SemanticaClient
from maris.entity_extractor import EntityExtractor
from maris.relationship_extractor import RelationshipExtractor
from maris.bridge_axiom_engine import BridgeAxiomEngine
from maris.query_engine import QueryEngine
from maris.graph_builder import GraphBuilder

__all__ = [
    "Config",
    "get_config",
    "SemanticaClient",
    "EntityExtractor",
    "RelationshipExtractor",
    "BridgeAxiomEngine",
    "QueryEngine",
    "GraphBuilder",
]
