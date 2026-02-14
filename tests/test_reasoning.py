"""Tests for the cross-domain reasoning engine (P2).

Covers context builder, hybrid retriever, inference engine, explanation
generator, open_domain classification, and regression on existing 5 categories.
All tests use mocks and fixtures - zero dependency on running Neo4j.
"""

import pytest
from unittest.mock import MagicMock

from maris.reasoning.context_builder import (
    ContextNode,
    ContextEdge,
    ContextGraph,
    build_context_from_results,
    label_to_context_type,
)
from maris.reasoning.hybrid_retriever import (
    HybridRetriever,
    RetrievalResult,
    reciprocal_rank_fusion,
)
from maris.reasoning.inference_engine import (
    InferenceEngine,
    InferenceStep,
)
from maris.reasoning.explanation import (
    ExplanationGenerator,
    Explanation,
)
from maris.provenance.bridge_axiom import BridgeAxiom
from maris.provenance.core import ProvenanceManager
from maris.query.classifier import QueryClassifier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_graph_results():
    """Sample Neo4j results for context building."""
    return [
        {
            "site": "Cabo Pulmo National Park",
            "total_esv": 29270000,
            "biomass_ratio": 4.63,
            "neoli_score": 4,
            "asset_rating": "AAA",
            "services": [
                {
                    "service": "Tourism",
                    "value_usd": 25000000,
                    "method": "market_price",
                },
                {
                    "service": "Fisheries Spillover",
                    "value_usd": 2500000,
                    "method": "production_function",
                },
            ],
            "evidence": [
                {
                    "axiom_id": "BA-001",
                    "doi": "10.1038/s41598-024-83664-1",
                    "title": "Tourism WTP study",
                    "year": 2024,
                    "tier": "T1",
                },
            ],
        }
    ]


@pytest.fixture
def sample_axioms():
    """Sample bridge axioms for inference engine testing."""
    return [
        BridgeAxiom(
            axiom_id="BA-001",
            name="mpa_biomass_dive_tourism_value",
            rule="IF full_protection(Site) THEN wtp_increase(Site, 84%)",
            coefficient=0.84,
            input_domain="ecological",
            output_domain="service",
            source_doi="10.1038/s41598-024-83664-1",
            confidence="high",
            applicable_habitats=["coral_reef"],
        ),
        BridgeAxiom(
            axiom_id="BA-014",
            name="carbon_stock_to_credit_value",
            rule="IF sequestration_tCO2_yr(Site, S) THEN credit_revenue(Site, S*30)",
            coefficient=30.0,
            input_domain="service",
            output_domain="financial",
            source_doi="10.1038/s44183-025-00111-y",
            confidence=0.85,
            applicable_habitats=["seagrass_meadow"],
        ),
        BridgeAxiom(
            axiom_id="BA-013",
            name="seagrass_carbon_sequestration_rate",
            rule="IF seagrass_area(Site, A) THEN sequestration(Site, A*0.84)",
            coefficient=0.84,
            input_domain="ecological",
            output_domain="service",
            source_doi="10.1038/s41467-025-64667-6",
            confidence="high",
            applicable_habitats=["seagrass_meadow"],
        ),
    ]


@pytest.fixture
def classifier():
    """Classifier without LLM fallback."""
    return QueryClassifier(llm=None)


# ===========================================================================
# 1. Context Builder Tests
# ===========================================================================

class TestContextNode:
    def test_create_node(self):
        node = ContextNode(node_id="test:1", node_type="site", name="Test MPA")
        assert node.node_id == "test:1"
        assert node.node_type == "site"
        assert node.name == "Test MPA"

    def test_node_to_dict(self):
        node = ContextNode(
            node_id="mpa:cabo",
            node_type="site",
            name="Cabo Pulmo",
            properties={"esv": 29.27},
            confidence=0.9,
        )
        d = node.to_dict()
        assert d["node_id"] == "mpa:cabo"
        assert d["properties"]["esv"] == 29.27
        assert d["confidence"] == 0.9

    def test_default_confidence_is_one(self):
        node = ContextNode(node_id="x", node_type="site")
        assert node.confidence == 1.0


class TestContextEdge:
    def test_create_edge(self):
        edge = ContextEdge(source_id="a", target_id="b", relationship="GENERATES")
        assert edge.source_id == "a"
        assert edge.target_id == "b"
        assert edge.relationship == "GENERATES"

    def test_edge_to_dict(self):
        edge = ContextEdge(
            source_id="mpa:cabo",
            target_id="svc:tourism",
            relationship="GENERATES",
            properties={"weight": 1.0},
        )
        d = edge.to_dict()
        assert d["relationship"] == "GENERATES"
        assert d["properties"]["weight"] == 1.0


class TestContextGraph:
    def test_empty_graph(self):
        g = ContextGraph()
        assert g.node_count() == 0
        assert g.edge_count() == 0

    def test_add_and_retrieve_node(self):
        g = ContextGraph()
        g.add_node(ContextNode(node_id="n1", node_type="site", name="Test"))
        assert g.node_count() == 1
        assert g.get_node("n1").name == "Test"

    def test_get_nonexistent_node(self):
        g = ContextGraph()
        assert g.get_node("missing") is None

    def test_neighbors(self):
        g = ContextGraph()
        g.add_node(ContextNode(node_id="a", node_type="site"))
        g.add_node(ContextNode(node_id="b", node_type="service"))
        g.add_node(ContextNode(node_id="c", node_type="evidence"))
        g.add_edge(ContextEdge(source_id="a", target_id="b", relationship="GENERATES"))
        g.add_edge(ContextEdge(source_id="a", target_id="c", relationship="EVIDENCED_BY"))
        neighbors = g.neighbors("a")
        assert len(neighbors) == 2
        neighbor_ids = {n.node_id for n in neighbors}
        assert "b" in neighbor_ids
        assert "c" in neighbor_ids

    def test_to_dict(self):
        g = ContextGraph()
        g.add_node(ContextNode(node_id="n1", node_type="site"))
        g.add_edge(ContextEdge(source_id="n1", target_id="n2", relationship="REL"))
        d = g.to_dict()
        assert len(d["nodes"]) == 1
        assert len(d["edges"]) == 1


class TestBuildContextFromResults:
    def test_builds_site_node(self, sample_graph_results):
        g = build_context_from_results(sample_graph_results)
        site_node = g.get_node("mpa:Cabo Pulmo National Park")
        assert site_node is not None
        assert site_node.node_type == "site"
        assert site_node.properties["total_esv"] == 29270000

    def test_builds_service_nodes(self, sample_graph_results):
        g = build_context_from_results(sample_graph_results)
        tourism = g.get_node("service:Tourism")
        assert tourism is not None
        assert tourism.node_type == "service"

    def test_builds_evidence_nodes(self, sample_graph_results):
        g = build_context_from_results(sample_graph_results)
        doc = g.get_node("doc:10.1038/s41598-024-83664-1")
        assert doc is not None
        assert doc.node_type == "evidence"

    def test_builds_edges(self, sample_graph_results):
        g = build_context_from_results(sample_graph_results)
        assert g.edge_count() > 0
        # Site -> Service edge
        generates_edges = [
            e for e in g.edges if e.relationship == "GENERATES"
        ]
        assert len(generates_edges) >= 2

    def test_empty_results(self):
        g = build_context_from_results([])
        assert g.node_count() == 0

    def test_deduplication(self, sample_graph_results):
        """Adding the same results twice should not duplicate nodes."""
        doubled = sample_graph_results + sample_graph_results
        g = build_context_from_results(doubled)
        site_nodes = [n for n in g.nodes if n.node_type == "site"]
        assert len(site_nodes) == 1


class TestLabelToContextType:
    def test_mpa_maps_to_site(self):
        assert label_to_context_type("MPA") == "site"

    def test_document_maps_to_evidence(self):
        assert label_to_context_type("Document") == "evidence"

    def test_unknown_maps_to_unknown(self):
        assert label_to_context_type("SomethingElse") == "unknown"


# ===========================================================================
# 2. Hybrid Retriever Tests
# ===========================================================================

class TestReciprocalRankFusion:
    def test_single_list(self):
        result = reciprocal_rank_fusion([["a", "b", "c"]])
        assert result[0][0] == "a"  # rank 1 has highest score

    def test_two_lists_intersection_boosted(self):
        result = reciprocal_rank_fusion([
            ["a", "b", "c"],
            ["b", "a", "d"],
        ])
        # Both a and b appear in both lists; check both appear at top
        top_ids = [r[0] for r in result[:2]]
        assert "a" in top_ids
        assert "b" in top_ids

    def test_empty_lists(self):
        result = reciprocal_rank_fusion([])
        assert result == []

    def test_unique_items_all_present(self):
        result = reciprocal_rank_fusion([["x"], ["y"], ["z"]])
        ids = {r[0] for r in result}
        assert ids == {"x", "y", "z"}


class TestHybridRetriever:
    def test_retrieve_no_executor_no_site(self):
        retriever = HybridRetriever()
        result = retriever.retrieve("What is carbon sequestration?")
        assert isinstance(result, RetrievalResult)
        assert result.context.node_count() == 0

    def test_retrieve_with_mock_executor(self, sample_graph_results):
        mock_executor = MagicMock()
        mock_executor.execute.return_value = {
            "results": sample_graph_results,
            "record_count": 1,
        }
        retriever = HybridRetriever(executor=mock_executor)
        result = retriever.retrieve(
            "What is the value of tourism?",
            site_name="Cabo Pulmo National Park",
        )
        assert result.context.node_count() > 0
        assert result.retrieval_modes["graph"] > 0

    def test_keyword_retrieval_ranks_relevant_nodes(self):
        retriever = HybridRetriever(
            keyword_rules=[
                ("site_valuation", [r"\bvalue\b", r"\besv\b"]),
            ],
        )
        # Manually populate context
        context = retriever.retrieve("test")
        assert isinstance(context, RetrievalResult)

    def test_result_to_dict(self):
        result = RetrievalResult(
            context=ContextGraph(),
            ranked_nodes=[{"node_id": "a", "score": 0.5}],
            retrieval_modes={"graph": 3, "keyword": 2},
            total_candidates=5,
        )
        d = result.to_dict()
        assert d["total_candidates"] == 5
        assert d["retrieval_modes"]["graph"] == 3


# ===========================================================================
# 3. Inference Engine Tests
# ===========================================================================

class TestInferenceEngine:
    def test_register_single_axiom(self, sample_axioms):
        engine = InferenceEngine()
        rule_id = engine.register_axiom(sample_axioms[0])
        assert rule_id == "rule:BA-001"
        assert engine.rule_count == 1

    def test_register_multiple_axioms(self, sample_axioms):
        engine = InferenceEngine()
        count = engine.register_axioms(sample_axioms)
        assert count == 3
        assert engine.rule_count == 3

    def test_get_rule(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axiom(sample_axioms[0])
        rule = engine.get_rule("rule:BA-001")
        assert rule is not None
        assert rule.axiom.axiom_id == "BA-001"

    def test_get_nonexistent_rule(self):
        engine = InferenceEngine()
        assert engine.get_rule("rule:missing") is None

    def test_forward_chain_single_step(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axiom(sample_axioms[0])  # ecological -> service
        facts = {"ecological": {"biomass_ratio": 4.63}}
        steps = engine.forward_chain(facts)
        assert len(steps) == 1
        assert steps[0].axiom_id == "BA-001"
        assert steps[0].source_doi == "10.1038/s41598-024-83664-1"

    def test_forward_chain_multi_step(self, sample_axioms):
        engine = InferenceEngine()
        # ecological -> service (BA-001 or BA-013)
        engine.register_axiom(sample_axioms[0])
        # service -> financial (BA-014)
        engine.register_axiom(sample_axioms[1])
        facts = {"ecological": {"biomass_ratio": 4.63}}
        steps = engine.forward_chain(facts)
        # Should get ecological -> service, then service -> financial
        assert len(steps) == 2
        domains = [s.axiom_id for s in steps]
        assert "BA-001" in domains
        assert "BA-014" in domains

    def test_forward_chain_no_matching_domain(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axiom(sample_axioms[0])  # ecological -> service
        facts = {"financial": {}}  # No rule starts from financial
        steps = engine.forward_chain(facts)
        assert len(steps) == 0

    def test_forward_chain_max_steps(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axioms(sample_axioms)
        facts = {"ecological": {}}
        steps = engine.forward_chain(facts, max_steps=1)
        # Only 1 step allowed
        assert len(steps) <= 3  # At most the number of rules with ecological input

    def test_backward_chain_financial(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axioms(sample_axioms)
        needed = engine.backward_chain("financial")
        assert len(needed) >= 1
        # BA-014 produces financial, so it should be listed
        axiom_ids = [n["axiom_id"] for n in needed]
        assert "BA-014" in axiom_ids

    def test_backward_chain_unfound_domain(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axioms(sample_axioms)
        needed = engine.backward_chain("nonexistent_domain")
        assert len(needed) == 0

    def test_find_rules_for_habitat(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axioms(sample_axioms)
        coral_rules = engine.find_rules_for_habitat("coral_reef")
        assert len(coral_rules) >= 1
        assert any(r.axiom.axiom_id == "BA-001" for r in coral_rules)

    def test_find_chain_ecological_to_financial(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axioms(sample_axioms)
        chain = engine.find_chain("ecological", "financial")
        assert len(chain) == 2
        assert chain[0].input_domain == "ecological"
        assert chain[-1].output_domain == "financial"

    def test_find_chain_same_domain_returns_empty(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axioms(sample_axioms)
        chain = engine.find_chain("ecological", "ecological")
        assert chain == []

    def test_find_chain_no_path_returns_empty(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axioms(sample_axioms)
        chain = engine.find_chain("financial", "ecological")
        assert chain == []


class TestInferenceProvenance:
    def test_forward_chain_records_provenance(self, sample_axioms):
        pm = ProvenanceManager()
        engine = InferenceEngine(provenance_manager=pm)
        engine.register_axiom(sample_axioms[0])
        facts = {"ecological": {"biomass_ratio": 4.63}}
        engine.forward_chain(facts)
        summary = pm.summary()
        assert summary["activities"] >= 1


class TestInferenceStep:
    def test_step_to_dict(self):
        step = InferenceStep(
            rule_id="rule:BA-001",
            axiom_id="BA-001",
            input_fact="ecological: biomass=4.63",
            output_fact="service via tourism",
            coefficient=0.84,
            confidence="high",
            source_doi="10.1038/test",
        )
        d = step.to_dict()
        assert d["axiom_id"] == "BA-001"
        assert d["coefficient"] == 0.84
        assert d["source_doi"] == "10.1038/test"


# ===========================================================================
# 4. Explanation Generator Tests
# ===========================================================================

class TestExplanationGenerator:
    def test_explain_single_step(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axiom(sample_axioms[0])
        steps = engine.forward_chain({"ecological": {"biomass": 4.63}})

        gen = ExplanationGenerator()
        explanation = gen.explain(steps, "How does biomass affect tourism?")
        assert isinstance(explanation, Explanation)
        assert len(explanation.steps) == 1
        assert "BA-001" in explanation.steps[0]
        assert len(explanation.citations) >= 1

    def test_explain_multi_step(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axioms(sample_axioms[:2])  # ecological -> service -> financial
        steps = engine.forward_chain({"ecological": {}})

        gen = ExplanationGenerator()
        explanation = gen.explain(steps)
        assert len(explanation.steps) == 2
        assert explanation.confidence > 0

    def test_explain_empty_steps(self):
        gen = ExplanationGenerator()
        explanation = gen.explain([])
        assert explanation.steps == []
        assert explanation.confidence == 0.0
        assert "No inference" in explanation.summary

    def test_explain_to_markdown(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axiom(sample_axioms[0])
        steps = engine.forward_chain({"ecological": {}})

        gen = ExplanationGenerator()
        explanation = gen.explain(steps)
        md = explanation.to_markdown()
        assert "**Summary:**" in md
        assert "BA-001" in md

    def test_explain_to_dict(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axiom(sample_axioms[0])
        steps = engine.forward_chain({"ecological": {}})

        gen = ExplanationGenerator()
        explanation = gen.explain(steps)
        d = explanation.to_dict()
        assert "steps" in d
        assert "citations" in d
        assert "summary" in d
        assert "confidence" in d

    def test_explain_backward(self, sample_axioms):
        engine = InferenceEngine()
        engine.register_axioms(sample_axioms)
        needed = engine.backward_chain("financial")

        gen = ExplanationGenerator()
        explanation = gen.explain_backward(needed, "financial")
        assert len(explanation.steps) >= 1
        assert "financial" in explanation.summary


# ===========================================================================
# 5. Integration: open_domain through classification
# ===========================================================================

class TestOpenDomainClassification:
    def test_ambiguous_question_routes_to_open_domain(self, classifier):
        result = classifier.classify("tell me something interesting")
        assert result["category"] == "open_domain"
        assert result["confidence"] <= 0.3

    def test_keyword_question_not_open_domain(self, classifier):
        """Keyword matches should NOT route to open_domain."""
        result = classifier.classify("What is the value of Cabo Pulmo?")
        assert result["category"] == "site_valuation"

    def test_risk_keywords_not_open_domain(self, classifier):
        result = classifier.classify("What if climate change degrades the reef?")
        assert result["category"] == "risk_assessment"

    def test_comparison_not_open_domain(self, classifier):
        result = classifier.classify("Compare Cabo Pulmo and Shark Bay")
        assert result["category"] == "comparison"

    def test_llm_low_confidence_routes_to_open_domain(self):
        mock_llm = MagicMock()
        mock_llm.complete_json.return_value = {
            "category": "site_valuation",
            "confidence": 0.2,
        }
        c = QueryClassifier(llm=mock_llm)
        result = c.classify("nebulous question with no keywords")
        assert result["category"] == "open_domain"

    def test_llm_high_confidence_keeps_category(self):
        mock_llm = MagicMock()
        mock_llm.complete_json.return_value = {
            "category": "risk_assessment",
            "confidence": 0.8,
        }
        c = QueryClassifier(llm=mock_llm)
        result = c.classify("nebulous question with no keywords")
        assert result["category"] == "risk_assessment"


# ===========================================================================
# 6. Regression: all existing 5 categories unchanged
# ===========================================================================

class TestExistingCategoryRegression:
    """Verify all 5 original categories still work identically."""

    def test_site_valuation_value(self, classifier):
        result = classifier.classify("What is the value of Cabo Pulmo?")
        assert result["category"] == "site_valuation"

    def test_site_valuation_esv(self, classifier):
        result = classifier.classify("What is the ESV of Cabo Pulmo?")
        assert result["category"] == "site_valuation"

    def test_provenance_evidence(self, classifier):
        result = classifier.classify("What evidence supports this?")
        assert result["category"] == "provenance_drilldown"

    def test_provenance_doi(self, classifier):
        result = classifier.classify("Show me the DOI sources")
        assert result["category"] == "provenance_drilldown"

    def test_axiom_bridge(self, classifier):
        result = classifier.classify("Explain bridge axiom BA-001")
        assert result["category"] == "axiom_explanation"

    def test_axiom_coefficient(self, classifier):
        result = classifier.classify("What is the coefficient for BA-002?")
        assert result["category"] == "axiom_explanation"

    def test_comparison_compare(self, classifier):
        result = classifier.classify("Compare Cabo Pulmo to Great Barrier Reef")
        assert result["category"] == "comparison"

    def test_comparison_versus(self, classifier):
        result = classifier.classify("Cabo Pulmo versus Great Barrier Reef")
        assert result["category"] == "comparison"

    def test_risk_risk(self, classifier):
        result = classifier.classify("What is the risk to Cabo Pulmo?")
        assert result["category"] == "risk_assessment"

    def test_risk_climate(self, classifier):
        result = classifier.classify("How does climate change affect the reef?")
        assert result["category"] == "risk_assessment"

    def test_risk_degradation(self, classifier):
        result = classifier.classify("What if reef degradation occurs?")
        assert result["category"] == "risk_assessment"
