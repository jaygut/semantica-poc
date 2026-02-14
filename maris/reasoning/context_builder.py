"""Build context graphs from MARIS Neo4j query results.

Converts raw Neo4j node/edge records into lightweight ContextNode and
ContextEdge objects suitable for reasoning, retrieval ranking, and
explanation generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Map MARIS Neo4j labels to semantic context types used by the reasoning engine.
_LABEL_TO_TYPE: dict[str, str] = {
    "MPA": "site",
    "BridgeAxiom": "axiom",
    "Document": "evidence",
    "EcosystemService": "service",
    "Habitat": "habitat",
    "Species": "species",
    "TrophicLevel": "trophic",
    "Concept": "concept",
    "FinancialInstrument": "financial",
    "Framework": "framework",
}


@dataclass
class ContextNode:
    """A node in the reasoning context graph."""

    node_id: str
    node_type: str
    name: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "properties": self.properties,
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass
class ContextEdge:
    """An edge in the reasoning context graph."""

    source_id: str
    target_id: str
    relationship: str
    properties: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "properties": self.properties,
        }


class ContextGraph:
    """Lightweight graph of context nodes and edges for reasoning."""

    def __init__(self) -> None:
        self._nodes: dict[str, ContextNode] = {}
        self._edges: list[ContextEdge] = []

    @property
    def nodes(self) -> list[ContextNode]:
        return list(self._nodes.values())

    @property
    def edges(self) -> list[ContextEdge]:
        return list(self._edges)

    def add_node(self, node: ContextNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, edge: ContextEdge) -> None:
        self._edges.append(edge)

    def get_node(self, node_id: str) -> ContextNode | None:
        return self._nodes.get(node_id)

    def neighbors(self, node_id: str) -> list[ContextNode]:
        """Return all nodes connected to the given node."""
        neighbor_ids: set[str] = set()
        for edge in self._edges:
            if edge.source_id == node_id:
                neighbor_ids.add(edge.target_id)
            elif edge.target_id == node_id:
                neighbor_ids.add(edge.source_id)
        return [self._nodes[nid] for nid in neighbor_ids if nid in self._nodes]

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
        }


def label_to_context_type(neo4j_label: str) -> str:
    """Map a Neo4j node label to a reasoning context type."""
    return _LABEL_TO_TYPE.get(neo4j_label, "unknown")


def build_context_from_results(results: list[dict[str, Any]]) -> ContextGraph:
    """Convert Neo4j query result records into a ContextGraph.

    Supports result dicts that contain node-like fields (name, labels, doi,
    axiom_id, service_name) and nested evidence/service lists. Each unique
    entity is added once; duplicates are merged by node_id.
    """
    graph = ContextGraph()

    for record in results:
        # Extract the primary node from the record
        _extract_primary_node(record, graph)
        # Extract nested evidence items
        _extract_nested_items(record, graph)

    return graph


def _extract_primary_node(record: dict[str, Any], graph: ContextGraph) -> None:
    """Extract a primary node from a top-level result record."""
    # Site/MPA node
    site = record.get("site")
    if site:
        node_id = f"mpa:{site}"
        if graph.get_node(node_id) is None:
            props = {}
            for key in ("total_esv", "biomass_ratio", "neoli_score", "asset_rating"):
                if record.get(key) is not None:
                    props[key] = record[key]
            graph.add_node(ContextNode(
                node_id=node_id,
                node_type="site",
                name=site,
                properties=props,
            ))

    # Axiom node
    axiom_id = record.get("axiom_id")
    if axiom_id:
        node_id = f"axiom:{axiom_id}"
        if graph.get_node(node_id) is None:
            props = {}
            for key in ("axiom_name", "category", "description", "coefficients"):
                if record.get(key) is not None:
                    props[key] = record[key]
            graph.add_node(ContextNode(
                node_id=node_id,
                node_type="axiom",
                name=record.get("axiom_name", axiom_id),
                properties=props,
            ))

    # Services from record
    services = record.get("services")
    if isinstance(services, list):
        for svc in services:
            if not isinstance(svc, dict):
                continue
            svc_name = svc.get("service") or svc.get("service_name")
            if not svc_name:
                continue
            svc_id = f"service:{svc_name}"
            if graph.get_node(svc_id) is None:
                graph.add_node(ContextNode(
                    node_id=svc_id,
                    node_type="service",
                    name=svc_name,
                    properties={k: v for k, v in svc.items() if v is not None},
                ))
            # Link site -> service
            if site:
                graph.add_edge(ContextEdge(
                    source_id=f"mpa:{site}",
                    target_id=svc_id,
                    relationship="GENERATES",
                ))


def _extract_nested_items(record: dict[str, Any], graph: ContextGraph) -> None:
    """Extract evidence and axiom items from nested lists."""
    evidence = record.get("evidence")
    site = record.get("site")
    if isinstance(evidence, list):
        for item in evidence:
            if not isinstance(item, dict):
                continue
            doi = item.get("doi")
            if not doi:
                continue
            doc_id = f"doc:{doi}"
            if graph.get_node(doc_id) is None:
                graph.add_node(ContextNode(
                    node_id=doc_id,
                    node_type="evidence",
                    name=item.get("title", doi),
                    properties={k: v for k, v in item.items() if v is not None},
                    confidence=1.0 if item.get("tier") == "T1" else 0.8,
                ))
            # Link axiom -> evidence
            ax_id = item.get("axiom_id")
            if ax_id:
                graph.add_edge(ContextEdge(
                    source_id=f"axiom:{ax_id}",
                    target_id=doc_id,
                    relationship="EVIDENCED_BY",
                ))
            # Link axiom -> site
            if ax_id and site:
                graph.add_edge(ContextEdge(
                    source_id=f"axiom:{ax_id}",
                    target_id=f"mpa:{site}",
                    relationship="APPLIES_TO",
                ))
