"""Hybrid retrieval combining graph traversal, keyword matching, and RRF ranking.

The HybridRetriever reuses existing MARIS keyword rules from the classifier
and graph traversal from the executor, then merges results via Reciprocal
Rank Fusion (RRF) for unified ranking.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from maris.reasoning.context_builder import (
    ContextGraph,
    build_context_from_results,
)

logger = logging.getLogger(__name__)

# RRF constant (standard value from Cormack et al.)
_RRF_K = 60


@dataclass
class RetrievalResult:
    """Result from hybrid retrieval with ranked context items."""

    context: ContextGraph
    ranked_nodes: list[dict[str, Any]] = field(default_factory=list)
    retrieval_modes: dict[str, int] = field(default_factory=dict)
    total_candidates: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ranked_nodes": self.ranked_nodes,
            "retrieval_modes": self.retrieval_modes,
            "total_candidates": self.total_candidates,
            "node_count": self.context.node_count(),
            "edge_count": self.context.edge_count(),
        }


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    k: int = _RRF_K,
) -> list[tuple[str, float]]:
    """Combine multiple ranked lists of node IDs into a unified ranking.

    Uses Reciprocal Rank Fusion: for each item, score = sum(1 / (k + rank_i))
    across all lists where the item appears. Higher score = more relevant.
    """
    scores: dict[str, float] = {}
    for ranked_list in ranked_lists:
        for rank, node_id in enumerate(ranked_list, start=1):
            scores[node_id] = scores.get(node_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


class HybridRetriever:
    """Hybrid retrieval combining graph traversal and keyword matching.

    Accepts an executor for graph queries and optional keyword rules.
    Graph traversal results and keyword-matched results are merged via RRF.
    """

    def __init__(
        self,
        executor: Any = None,
        keyword_rules: list[tuple[str, list[str]]] | None = None,
    ) -> None:
        self._executor = executor
        self._keyword_rules = keyword_rules or []

    def retrieve(
        self,
        question: str,
        site_name: str | None = None,
        max_hops: int = 3,
        top_k: int = 20,
    ) -> RetrievalResult:
        """Run hybrid retrieval for an open-domain question.

        Returns a RetrievalResult with ranked context nodes.
        """
        graph_ranked: list[str] = []
        keyword_ranked: list[str] = []
        context = ContextGraph()
        modes: dict[str, int] = {"graph": 0, "keyword": 0}

        # 1. Graph traversal (if executor and site available)
        if self._executor and site_name:
            graph_results = self._graph_retrieve(site_name, max_hops)
            graph_context = build_context_from_results(graph_results)
            for node in graph_context.nodes:
                context.add_node(node)
            for edge in graph_context.edges:
                context.add_edge(edge)
            graph_ranked = [n.node_id for n in graph_context.nodes]
            modes["graph"] = len(graph_ranked)

        # 2. Keyword matching against context nodes
        keyword_ranked = self._keyword_retrieve(question, context)
        modes["keyword"] = len(keyword_ranked)

        # 3. RRF fusion
        ranked_lists = [rl for rl in [graph_ranked, keyword_ranked] if rl]
        if ranked_lists:
            fused = reciprocal_rank_fusion(ranked_lists)
        else:
            fused = []

        # Build ranked output
        ranked_nodes: list[dict[str, Any]] = []
        for node_id, score in fused[:top_k]:
            node = context.get_node(node_id)
            if node:
                ranked_nodes.append({
                    "node_id": node_id,
                    "name": node.name,
                    "node_type": node.node_type,
                    "score": round(score, 6),
                    "properties": node.properties,
                })

        return RetrievalResult(
            context=context,
            ranked_nodes=ranked_nodes,
            retrieval_modes=modes,
            total_candidates=context.node_count(),
        )

    def _graph_retrieve(self, site_name: str, max_hops: int) -> list[dict[str, Any]]:
        """Retrieve graph neighborhood via executor."""
        try:
            result = self._executor.execute(
                "graph_traverse",
                {"start_name": site_name, "max_hops": max_hops},
            )
            return result.get("results", [])
        except Exception:
            logger.exception("Graph retrieval failed for site=%s", site_name)
            return []

    def _keyword_retrieve(
        self,
        question: str,
        context: ContextGraph,
    ) -> list[str]:
        """Rank context nodes by keyword match relevance to the question."""
        q_lower = question.lower()
        scored: list[tuple[str, int]] = []

        for node in context.nodes:
            score = 0
            node_text = f"{node.name} {' '.join(str(v) for v in node.properties.values())}".lower()

            # Check keyword rules
            for _category, patterns in self._keyword_rules:
                for pat in patterns:
                    if re.search(pat, q_lower):
                        # Boost if the pattern also matches node content
                        if re.search(pat, node_text):
                            score += 2
                        else:
                            score += 1

            # Direct term overlap
            q_words = set(q_lower.split())
            node_words = set(node_text.split())
            overlap = len(q_words & node_words)
            score += overlap

            if score > 0:
                scored.append((node.node_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [node_id for node_id, _ in scored]
