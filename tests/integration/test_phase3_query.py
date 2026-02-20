"""Phase 3 Integration Tests: End-to-End Query Pipeline (T3.1-T3.6).

These tests validate the complete query pipeline: classifier regression,
open_domain category, forward chaining, provenance endpoint, and open-domain
execution. Tests work in two modes:
  - If the API server is running: test via HTTP calls
  - If the API server is NOT running: test classifier and executor directly

All tests use the @pytest.mark.integration marker and can be run via:
    pytest tests/integration/test_phase3_query.py -v
"""

from __future__ import annotations

import importlib.util
import os
import urllib.request
import urllib.error
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent

# ---------------------------------------------------------------------------
# Detect live API availability
# ---------------------------------------------------------------------------

API_BASE = os.environ.get("MARIS_API_URL", "http://localhost:8000")
API_KEY = os.environ.get("MARIS_API_KEY", "test-key")

def _api_is_running() -> bool:
    """Check if the MARIS API server is reachable."""
    try:
        req = urllib.request.Request(f"{API_BASE}/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


_API_AVAILABLE = _api_is_running()

# Check Neo4j availability via graph connection
def _neo4j_is_running() -> bool:
    try:
        from maris.graph.connection import run_query
        result = run_query("RETURN 1 AS n", {})
        return len(result) > 0
    except Exception:
        return False


_NEO4J_AVAILABLE = _neo4j_is_running()

# Check if HybridRetriever exists
_HAS_HYBRID_RETRIEVER = importlib.util.find_spec("maris.reasoning.hybrid_retriever") is not None

requires_api = pytest.mark.skipif(
    not _API_AVAILABLE,
    reason="MARIS API not running at " + API_BASE,
)

requires_neo4j = pytest.mark.skipif(
    not _NEO4J_AVAILABLE,
    reason="Neo4j not reachable",
)


def _api_post(path: str, json_body: dict) -> dict:
    """POST JSON to the API and return parsed response."""
    import json
    data = json.dumps(json_body).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _api_get(path: str) -> dict:
    """GET from the API and return parsed response."""
    import json
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {API_KEY}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# T3.1: Regression - 5 Original Categories via Live API
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT31RegressionOriginalCategories:
    """T3.1: Test all 5 original categories through the live API.

    Each query should return HTTP 200 with answer, confidence, and evidence.
    """

    CATEGORY_QUERIES = [
        ("site_valuation", "What is Cabo Pulmo worth?"),
        ("provenance_drilldown", "What is the evidence for the biomass recovery at Cabo Pulmo?"),
        ("axiom_explanation", "How does bridge axiom BA-001 work?"),
        ("comparison", "Compare Cabo Pulmo and Shark Bay"),
        ("risk_assessment", "What are the risks to Shark Bay if seagrass is lost?"),
    ]

    @requires_api
    @pytest.mark.parametrize("expected_category,question", CATEGORY_QUERIES)
    def test_category_via_api(self, expected_category, question):
        """Each original category returns a valid response through the API."""
        result = _api_post("/api/query", {"question": question})

        # Basic response shape
        assert "answer" in result, f"No 'answer' field in response for: {question}"
        assert result["answer"], f"Empty answer for: {question}"
        assert "confidence" in result
        assert 0 <= result["confidence"] <= 1

        # Classification should match expected category
        metadata = result.get("query_metadata", {})
        actual_category = metadata.get("category", "")
        assert actual_category == expected_category, (
            f"Category mismatch for '{question}': "
            f"expected {expected_category}, got {actual_category}"
        )

    @pytest.mark.parametrize("expected_category,question", CATEGORY_QUERIES)
    def test_category_via_classifier_direct(self, expected_category, question):
        """Fallback: test classifier directly without API."""
        from maris.query.classifier import QueryClassifier

        clf = QueryClassifier()  # no LLM - keyword only
        result = clf.classify(question)
        actual = result["category"]
        assert actual == expected_category, (
            f"Classifier mismatch for '{question}': "
            f"expected {expected_category}, got {actual}"
        )

    @requires_api
    def test_no_category_routes_to_open_domain_unexpectedly(self):
        """Regression check: original categories must NOT route to open_domain."""
        from maris.query.classifier import QueryClassifier

        clf = QueryClassifier()
        for expected_category, question in self.CATEGORY_QUERIES:
            result = clf.classify(question)
            assert result["category"] != "open_domain", (
                f"REGRESSION: '{question}' should be '{expected_category}' "
                f"but routed to 'open_domain'"
            )


# ---------------------------------------------------------------------------
# T3.2: Classifier Regression - Direct Classification (MOST IMPORTANT)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT32ClassifierRegression:
    """T3.2: The single most important test - 10 known queries must classify correctly.

    These queries MUST still classify as their original categories. If any
    regress to open_domain, the classifier change broke core functionality.
    """

    # Queries that currently classify correctly via keyword matching
    PASSING_QUERIES = [
        ("What is Cabo Pulmo worth?", "site_valuation"),
        ("What is the ESV of Shark Bay?", "site_valuation"),
        ("Show me the evidence for biomass recovery", "provenance_drilldown"),
        ("Explain bridge axiom BA-001", "axiom_explanation"),
        ("How does seagrass sequester carbon?", "axiom_explanation"),
        ("Compare Cabo Pulmo and Shark Bay", "comparison"),
        ("What are the climate risks?", "risk_assessment"),
        ("What happens if coral cover declines?", "risk_assessment"),
    ]

    # Queries with known classifier regex gaps (documented as findings)
    KNOWN_GAPS = [
        # BUG: BA-\d{3} regex is case-sensitive but classifier lowercases input,
        # so "ba-013" never matches. Also "DOIs" (plural) doesn't match \bdoi\b,
        # and "support" doesn't match "supporting".
        ("What DOIs support BA-013?", "provenance_drilldown", "open_domain",
         "BUG: BA-\\d{3} case-sensitive + 'DOIs'/'support' not matched"),
        # BUG: "rank" matches comparison (1 hit) and "esv" matches site_valuation
        # (1 hit). Tie-break favors site_valuation because it appears first in
        # _KEYWORD_RULES. Should prefer comparison when "rank" is present.
        ("Rank the MPAs by ESV", "comparison", "site_valuation",
         "BUG: tie-break in _KEYWORD_RULES favors site_valuation over comparison"),
    ]

    @pytest.fixture(scope="class")
    def classifier(self):
        from maris.query.classifier import QueryClassifier
        return QueryClassifier()  # no LLM - pure keyword classification

    @pytest.mark.parametrize("question,expected", PASSING_QUERIES)
    def test_known_query_classification(self, classifier, question, expected):
        """Each known query must classify to its expected category."""
        result = classifier.classify(question)
        actual = result["category"]
        assert actual == expected, (
            f"REGRESSION: '{question}' classified as '{actual}', expected '{expected}'. "
            f"Confidence: {result.get('confidence')}, Site: {result.get('site')}"
        )

    @pytest.mark.parametrize("question,expected,actual_result,reason", KNOWN_GAPS)
    def test_known_gap_classification(self, classifier, question, expected, actual_result, reason):
        """Document known classifier gaps as xfail.

        These are real bugs in the keyword regex patterns. The classifier
        returns the wrong category due to case sensitivity, missing word
        forms, or tie-breaking issues.
        """
        result = classifier.classify(question)
        actual = result["category"]
        if actual == expected:
            # Bug was fixed - great!
            pass
        else:
            assert actual == actual_result, (
                f"Unexpected result for '{question}': got '{actual}', "
                f"expected either '{expected}' (correct) or '{actual_result}' (known gap)"
            )
            pytest.xfail(f"CLASSIFIER GAP: {reason}")

    @pytest.mark.parametrize("question,expected", PASSING_QUERIES)
    def test_known_query_never_open_domain(self, classifier, question, expected):
        """No passing query should ever route to open_domain."""
        result = classifier.classify(question)
        assert result["category"] != "open_domain", (
            f"REGRESSION: '{question}' fell through to 'open_domain' "
            f"(expected '{expected}')"
        )

    @pytest.mark.parametrize("question,expected", PASSING_QUERIES)
    def test_known_query_has_confidence(self, classifier, question, expected):
        """Each known query should have reasonable classification confidence."""
        result = classifier.classify(question)
        assert result["confidence"] >= 0.5, (
            f"Low confidence {result['confidence']} for '{question}'"
        )

    def test_site_resolution_cabo_pulmo(self, classifier):
        """Cabo Pulmo resolves to canonical name."""
        result = classifier.classify("What is Cabo Pulmo worth?")
        assert result["site"] == "Cabo Pulmo National Park"

    def test_site_resolution_shark_bay(self, classifier):
        """Shark Bay resolves to canonical name."""
        result = classifier.classify("What is the ESV of Shark Bay?")
        assert result["site"] == "Shark Bay World Heritage Area"

    def test_multi_site_forces_comparison(self, classifier):
        """Mentioning two sites forces comparison category."""
        result = classifier.classify("Compare Cabo Pulmo and Shark Bay")
        assert result["category"] == "comparison"
        assert "sites" in result
        assert len(result["sites"]) >= 2

    def test_axiom_id_extraction_with_explicit_axiom_keyword(self, classifier):
        """BA-NNN patterns trigger axiom_explanation when 'axiom' keyword is also present."""
        result = classifier.classify("Explain bridge axiom BA-013")
        assert result["category"] == "axiom_explanation"

    def test_axiom_id_alone_is_case_sensitive_gap(self, classifier):
        """BUG: BA-\\d{3} regex is case-sensitive - 'ba-013' (lowered) doesn't match.

        The classifier lowercases input for matching, but the BA-\\d{3} pattern
        uses uppercase 'BA'. This means axiom IDs are only matched when accompanied
        by other keywords like 'axiom' or 'bridge'.
        """
        result = classifier.classify("What DOIs support BA-013?")
        if result["category"] in ("provenance_drilldown", "axiom_explanation"):
            pass  # Fixed
        else:
            pytest.xfail(
                "CLASSIFIER GAP: BA-\\d{3} is case-sensitive; lowered input "
                "'ba-013' doesn't match. Also 'DOIs' != 'doi', 'support' != 'supporting'"
            )

    def test_seagrass_carbon_routes_to_axiom(self, classifier):
        """Seagrass carbon keywords route to axiom_explanation."""
        result = classifier.classify("How does seagrass sequester carbon?")
        assert result["category"] == "axiom_explanation"


# ---------------------------------------------------------------------------
# T3.3: Open Domain - New Query Types
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT33OpenDomain:
    """T3.3: Test queries that should route to open_domain.

    The open_domain category exists when queries don't match the 5 core
    categories. This requires no LLM to be configured (falls through keyword
    matching to open_domain default).
    """

    OPEN_DOMAIN_QUERIES = [
        "How does the MARIS system work?",
        "What data sources does this system use?",
        "Tell me about the team behind this project",
    ]

    @pytest.fixture(scope="class")
    def classifier_no_llm(self):
        from maris.query.classifier import QueryClassifier
        return QueryClassifier()  # no LLM - ambiguous queries fall to open_domain

    @pytest.mark.parametrize("question", OPEN_DOMAIN_QUERIES)
    def test_ambiguous_query_routes_to_open_domain(self, classifier_no_llm, question):
        """Queries that don't match any keyword should route to open_domain (no LLM)."""
        result = classifier_no_llm.classify(question)
        # Without LLM, these should fall through to open_domain
        assert result["category"] == "open_domain", (
            f"Expected 'open_domain' for '{question}', got '{result['category']}'"
        )

    @pytest.mark.parametrize("question", OPEN_DOMAIN_QUERIES)
    def test_open_domain_has_low_confidence(self, classifier_no_llm, question):
        """Open domain queries should have lower confidence than keyword-matched."""
        result = classifier_no_llm.classify(question)
        if result["category"] == "open_domain":
            assert result["confidence"] <= 0.5, (
                f"open_domain should have low confidence, got {result['confidence']}"
            )

    def test_open_domain_category_recognized_by_generator(self):
        """The response generator recognizes open_domain in its hop count map."""
        from maris.query.generator import _CATEGORY_HOPS
        assert "open_domain" in _CATEGORY_HOPS, (
            "GAP: open_domain not in _CATEGORY_HOPS - generator won't know hop count"
        )

    def test_executor_has_execute_open_domain(self):
        """Verify execute_open_domain() method exists on QueryExecutor."""
        from maris.query.executor import QueryExecutor
        executor = QueryExecutor()
        assert hasattr(executor, "execute_open_domain"), (
            "GAP: QueryExecutor.execute_open_domain() not found"
        )

    def test_hybrid_retriever_importable(self):
        """HybridRetriever module should be importable."""
        if not _HAS_HYBRID_RETRIEVER:
            pytest.skip("GAP: maris.reasoning.hybrid_retriever not found")
        from maris.reasoning.hybrid_retriever import HybridRetriever
        assert HybridRetriever is not None

    def test_open_domain_cypher_templates_exist(self):
        """Open domain Cypher templates (graph_neighborhood, semantic_search) exist."""
        from maris.query.cypher_templates import get_template
        neighborhood = get_template("graph_neighborhood")
        semantic = get_template("semantic_search")
        assert neighborhood is not None, "GAP: graph_neighborhood template not found"
        assert semantic is not None, "GAP: semantic_search template not found"


# ---------------------------------------------------------------------------
# T3.4: Forward Chaining Through Live API
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT34ForwardChaining:
    """T3.4: Test a forward chaining query via API or direct classification.

    The query 'If coral cover declined 30%, what happens to tourism?' should
    trigger risk_assessment and the response should reference relevant axioms.
    """

    FORWARD_CHAIN_QUERY = (
        "If coral cover at Cabo Pulmo declined 30%, "
        "what would happen to tourism revenue?"
    )

    def test_forward_chain_classifies_as_risk(self):
        """Forward chaining scenario should classify as risk_assessment.

        BUG: Three regex gaps prevent matching:
        1. \\bdecline\\b doesn't match 'declined' (past tense)
        2. \\bwhat\\b.*\\bif\\b expects 'what...if' order, but query is 'if...what'
        3. \\bwhat\\s+happens\\b doesn't match 'what would happen'
        """
        from maris.query.classifier import QueryClassifier

        clf = QueryClassifier()
        result = clf.classify(self.FORWARD_CHAIN_QUERY)
        if result["category"] == "risk_assessment":
            pass  # Fixed
        else:
            pytest.xfail(
                "CLASSIFIER GAP: 'declined' not matched by \\bdecline\\b, "
                "'if...what' order not matched by \\bwhat\\b.*\\bif\\b, "
                "'what would happen' not matched by \\bwhat\\s+happens\\b. "
                f"Got '{result['category']}' instead of 'risk_assessment'"
            )

    def test_forward_chain_detects_cabo_pulmo(self):
        """The query should resolve Cabo Pulmo site."""
        from maris.query.classifier import QueryClassifier

        clf = QueryClassifier()
        result = clf.classify(self.FORWARD_CHAIN_QUERY)
        assert result["site"] == "Cabo Pulmo National Park"

    def test_forward_chain_extracts_tourism_metric(self):
        """The query should extract 'tourism' as a metric."""
        from maris.query.classifier import QueryClassifier

        clf = QueryClassifier()
        result = clf.classify(self.FORWARD_CHAIN_QUERY)
        assert "tourism" in result.get("metrics", []), (
            f"Expected 'tourism' in metrics, got {result.get('metrics')}"
        )

    @requires_api
    def test_forward_chain_via_api(self):
        """Full API round-trip for forward chaining query.

        Due to classifier gaps (see test_forward_chain_classifies_as_risk),
        this may not route to risk_assessment. We verify the API doesn't crash
        and returns a valid response regardless of category.
        """
        result = _api_post("/api/query", {"question": self.FORWARD_CHAIN_QUERY})
        assert "answer" in result
        assert result["answer"], "Empty answer for forward chaining query"
        assert result.get("confidence", 0) >= 0

        metadata = result.get("query_metadata", {})
        category = metadata.get("category", "")
        if category != "risk_assessment":
            pytest.xfail(
                f"Forward chaining query classified as '{category}' instead of "
                "'risk_assessment' due to classifier regex gaps (see T3.4 findings)"
            )

    @requires_neo4j
    def test_risk_template_returns_results_for_cabo_pulmo(self):
        """Direct executor: risk_assessment template for Cabo Pulmo returns data."""
        from maris.query.executor import QueryExecutor

        executor = QueryExecutor()
        result = executor.execute(
            "risk_assessment",
            {"site_name": "Cabo Pulmo National Park"},
        )
        assert result.get("record_count", 0) > 0, (
            "risk_assessment template returned no results for Cabo Pulmo"
        )
        assert not result.get("error"), f"Query error: {result.get('error')}"


# ---------------------------------------------------------------------------
# T3.5: Provenance Endpoint with Semantica Persistence
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT35ProvenanceEndpoint:
    """T3.5: Verify the /api/provenance/summary endpoint.

    Check that:
    - The endpoint exists and responds
    - Returns JSON with entity/activity/agent counts
    - Determine if SemanticaBackedManager or original MARISProvenanceManager is used
    """

    @requires_api
    def test_provenance_summary_endpoint_exists(self):
        """GET /api/provenance returns a response.

        The provenance router is defined in maris/api/routes/provenance.py
        and registered in main.py, but the running API server may be from
        a different branch/version that doesn't include it.
        """
        try:
            result = _api_get("/api/provenance")
            assert isinstance(result, dict), "Provenance summary should return a dict"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                pytest.xfail(
                    "INTEGRATION GAP: /api/provenance endpoint returns 404. "
                    "The provenance router exists in code (maris/api/routes/provenance.py) "
                    "and is registered in main.py, but the running API server "
                    "may not include it (different branch or older version)."
                )
            raise

    @requires_api
    def test_provenance_summary_has_counts(self):
        """Provenance summary includes entity, activity, and agent counts."""
        try:
            result = _api_get("/api/provenance")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                pytest.xfail("Provenance endpoint not available (see T3.5 findings)")
            raise
        assert "entities" in result, "Missing 'entities' count"
        assert "activities" in result, "Missing 'activities' count"
        assert "agents" in result, "Missing 'agents' count"
        # axioms_loaded comes from MARISProvenanceManager.summary()
        assert "axioms_loaded" in result, "Missing 'axioms_loaded' count"

    @requires_api
    def test_provenance_axioms_loaded(self):
        """Provenance should report at least 35 axioms loaded (40 after DB re-population with BA-036-040)."""
        try:
            result = _api_get("/api/provenance")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                pytest.xfail("Provenance endpoint not available (see T3.5 findings)")
            raise
        axioms = result.get("axioms_loaded", 0)
        assert axioms >= 35, f"Expected at least 35 axioms loaded, got {axioms}"

    def test_provenance_route_uses_maris_manager(self):
        """Check if the provenance route uses MARISProvenanceManager (not SemanticaBackedManager).

        This documents whether the Semantica bridge is wired into the API.
        """
        route_path = PROJECT_ROOT / "maris" / "api" / "routes" / "provenance.py"
        source = route_path.read_text()

        uses_semantica = "SemanticaBackedManager" in source
        uses_maris_native = "MARISProvenanceManager" in source

        if uses_semantica:
            # Bridge is wired in
            pass
        elif uses_maris_native:
            # Integration gap: bridge exists but API uses native manager
            pytest.xfail(
                "INTEGRATION GAP: Provenance route uses MARISProvenanceManager, "
                "not SemanticaBackedManager. Dual-write provenance is available "
                "but not wired into the API endpoint."
            )
        else:
            pytest.fail("Provenance route uses neither known manager class")

    def test_semantica_provenance_adapter_importable(self):
        """SemanticaProvenanceAdapter should be importable."""
        try:
            from maris.semantica_bridge.provenance_adapter import (
                SemanticaProvenanceAdapter,
            )
            assert SemanticaProvenanceAdapter is not None
        except ImportError:
            pytest.xfail("SemanticaProvenanceAdapter not importable")


# ---------------------------------------------------------------------------
# T3.6: Open Domain Execution Path
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestT36OpenDomainExecution:
    """T3.6: Test the open-domain execution path through HybridRetriever.

    If execute_open_domain() and HybridRetriever exist, test them against
    real Neo4j. If they don't exist, document as GAP and skip.
    """

    @requires_api
    def test_open_domain_via_api_no_crash(self):
        """An open-domain-style query through the API should not crash.

        Note: the query may be classified as something other than open_domain
        if keyword rules match. The key test is that it doesn't 500.
        """
        try:
            result = _api_post(
                "/api/query",
                {"question": "What is the combined investment potential of all characterized sites?"},
            )
            assert "answer" in result
        except urllib.error.HTTPError as e:
            if e.code == 500:
                body = e.read().decode("utf-8", errors="replace")
                pytest.fail(f"API returned 500 for open-domain query: {body}")
            raise

    @requires_neo4j
    def test_execute_open_domain_direct(self):
        """Direct test of QueryExecutor.execute_open_domain() against live Neo4j."""
        from maris.query.executor import QueryExecutor

        executor = QueryExecutor()
        if not hasattr(executor, "execute_open_domain"):
            pytest.skip("GAP: execute_open_domain() not found on QueryExecutor")

        try:
            result = executor.execute_open_domain(
                question="What ecosystem services does Cabo Pulmo provide?",
                site_name="Cabo Pulmo National Park",
            )
        except ImportError as e:
            pytest.xfail(f"execute_open_domain import dependency missing: {e}")
        except Exception as e:
            pytest.fail(f"execute_open_domain crashed: {type(e).__name__}: {e}")

        assert isinstance(result, dict)
        assert "results" in result or "ranked_nodes" in result
        assert result.get("template") == "open_domain"

    @requires_neo4j
    def test_hybrid_retriever_direct(self):
        """Direct test of HybridRetriever against live Neo4j."""
        if not _HAS_HYBRID_RETRIEVER:
            pytest.skip("GAP: HybridRetriever module not found")

        from maris.reasoning.hybrid_retriever import HybridRetriever
        from maris.query.classifier import _KEYWORD_RULES
        from maris.query.executor import QueryExecutor

        executor = QueryExecutor()
        retriever = HybridRetriever(
            executor=executor,
            keyword_rules=_KEYWORD_RULES,
        )

        try:
            result = retriever.retrieve(
                question="What ecosystem services does seagrass provide?",
                site_name="Shark Bay World Heritage Area",
                max_hops=2,
                top_k=10,
            )
        except Exception as e:
            pytest.fail(f"HybridRetriever.retrieve() crashed: {type(e).__name__}: {e}")

        assert result is not None
        assert hasattr(result, "ranked_nodes")
        assert hasattr(result, "retrieval_modes")
        # Graph mode should have found some nodes (if Neo4j has data)
        modes = result.retrieval_modes
        assert "graph" in modes
        assert "keyword" in modes

    @requires_neo4j
    def test_all_five_templates_execute_against_neo4j(self):
        """Smoke test: all 5 core Cypher templates execute without error against live Neo4j."""
        from maris.query.executor import QueryExecutor

        executor = QueryExecutor()
        templates_and_params = [
            ("site_valuation", {"site_name": "Cabo Pulmo National Park"}),
            ("provenance_drilldown", {"site_name": "Cabo Pulmo National Park"}),
            ("axiom_explanation", {"axiom_id": "BA-001"}),
            ("comparison", {"site_names": ["Cabo Pulmo National Park", "Shark Bay World Heritage Area"]}),
            ("risk_assessment", {"site_name": "Shark Bay World Heritage Area"}),
        ]

        for template_name, params in templates_and_params:
            result = executor.execute(template_name, params)
            assert not result.get("error"), (
                f"Template '{template_name}' failed: {result.get('error')}"
            )
            assert result.get("record_count", 0) >= 0

    @requires_neo4j
    def test_site_valuation_returns_data_for_both_sites(self):
        """Both fully characterized sites should return ESV data."""
        from maris.query.executor import QueryExecutor

        executor = QueryExecutor()
        for site in ["Cabo Pulmo National Park", "Shark Bay World Heritage Area"]:
            result = executor.execute("site_valuation", {"site_name": site})
            assert not result.get("error"), f"Error for {site}: {result.get('error')}"
            assert result.get("record_count", 0) > 0, (
                f"No results for site_valuation on {site}"
            )
