"""Tests for FastAPI API endpoints using TestClient."""

import os
from pathlib import Path

import pytest
from unittest.mock import MagicMock, patch

# Set env vars before any app imports
os.environ["MARIS_NEO4J_PASSWORD"] = "test-password"
os.environ["MARIS_LLM_API_KEY"] = "test-key"
os.environ["MARIS_API_KEY"] = "test-api-key"
os.environ["MARIS_DEMO_MODE"] = "true"

from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """Create a fresh app instance with mocked config."""
    # Reset the config singleton before each test
    import maris.config
    maris.config._config = None

    from maris.api.main import create_app
    return create_app()


@pytest.fixture
def client(app):
    """Test client for the MARIS API."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Valid auth headers for demo mode."""
    return {"Authorization": "Bearer test-api-key"}


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        """Health endpoint should work without auth."""
        with patch("maris.api.routes.health.run_query", return_value=[{"ok": 1}]):
            response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_no_auth_required(self, client):
        """Health endpoint should not require authentication."""
        with patch("maris.api.routes.health.run_query", return_value=[{"ok": 1}]):
            response = client.get("/api/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        """Health response should have status, neo4j_connected, llm_available."""
        with patch("maris.api.routes.health.run_query", return_value=[{"ok": 1}]):
            response = client.get("/api/health")
        data = response.json()
        assert "status" in data
        assert "neo4j_connected" in data
        assert "llm_available" in data

    def test_health_degraded_when_neo4j_down(self, client):
        """Health should report degraded when Neo4j fails."""
        with patch("maris.api.routes.health.run_query", side_effect=Exception("Neo4j down")):
            response = client.get("/api/health")
        data = response.json()
        assert data["neo4j_connected"] is False


class TestQueryEndpoint:
    @patch("maris.api.routes.query._build_inference_trace")
    @patch("maris.api.routes.query._init_components")
    @patch("maris.api.routes.query._classifier")
    @patch("maris.api.routes.query._executor")
    @patch("maris.api.routes.query._generator")
    def test_valid_query(self, mock_gen, mock_exec, mock_cls, mock_init, mock_trace, client, auth_headers):
        """A valid query should return 200 with answer."""
        mock_cls.classify.return_value = {
            "category": "site_valuation",
            "site": "Cabo Pulmo National Park",
            "metrics": [],
            "confidence": 0.9,
            "caveats": [],
        }
        mock_exec.execute_with_strategy.return_value = {
            "results": [{"site": "Cabo Pulmo National Park", "total_esv": 29270000}],
            "record_count": 1,
            "strategy": "deterministic_template",
        }
        mock_exec.get_provenance_edges.return_value = [{
            "from_node": "BA-001",
            "from_type": "BridgeAxiom",
            "relationship": "APPLIES_TO",
            "to_node": "Cabo Pulmo National Park",
            "to_type": "MPA",
        }]
        mock_trace.return_value = ([{
            "step": 1,
            "axiom_id": "BA-001",
            "rule_id": "rule:BA-001",
            "input_fact": "ecological: site=Cabo Pulmo National Park",
            "output_fact": "financial value via BA-001",
            "coefficient": 1.0,
            "confidence": "high",
            "source_doi": "10.1016/j.ecolecon.2024.108163",
            "provisional": False,
        }], "1. BA-001 chain", [])
        mock_gen.generate.return_value = {
            "answer": "The ESV is $29.27M.",
            "confidence": 0.85,
            "evidence": [],
            "axioms_used": ["BA-001"],
            "graph_path": [],
            "caveats": [],
        }
        # Set the module-level refs so _init_components sees them as not-None
        import maris.api.routes.query as qmod
        qmod._llm = MagicMock()
        qmod._classifier = mock_cls
        qmod._executor = mock_exec
        qmod._generator = mock_gen
        qmod._axiom_registry = MagicMock()
        qmod._inference_engine = MagicMock()

        response = client.post(
            "/api/query",
            json={"question": "What is Cabo Pulmo worth?"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "confidence" in data
        assert "evidence_count" in data
        assert "doi_citation_count" in data
        assert "evidence_completeness_score" in data
        assert "provenance_warnings" in data
        assert "provenance_risk" in data
        assert data["query_metadata"]["template_used"].endswith(":deterministic_template")

    @patch("maris.api.routes.query._build_inference_trace")
    @patch("maris.api.routes.query._init_components")
    @patch("maris.api.routes.query._classifier")
    @patch("maris.api.routes.query._executor")
    @patch("maris.api.routes.query._generator")
    def test_query_metrics_follow_visible_evidence_limit(
        self,
        mock_gen,
        mock_exec,
        mock_cls,
        mock_init,
        mock_trace,
        client,
        auth_headers,
    ):
        """Response provenance metrics should reflect the visible evidence payload."""
        mock_cls.classify.return_value = {
            "category": "risk_assessment",
            "site": "Cabo Pulmo National Park",
            "metrics": [],
            "confidence": 0.9,
            "caveats": [],
        }
        mock_exec.execute_with_strategy.return_value = {
            "results": [{"site": "Cabo Pulmo National Park", "risk": "high"}],
            "record_count": 1,
            "strategy": "deterministic_template",
        }
        mock_exec.get_provenance_edges.return_value = [{
            "from_node": "BA-001",
            "from_type": "BridgeAxiom",
            "relationship": "APPLIES_TO",
            "to_node": "Cabo Pulmo National Park",
            "to_type": "MPA",
        }]
        mock_trace.return_value = ([{
            "step": 1,
            "axiom_id": "BA-001",
            "rule_id": "rule:BA-001",
            "input_fact": "ecological: site=Cabo Pulmo National Park",
            "output_fact": "financial value via BA-001",
            "coefficient": 1.0,
            "confidence": "high",
            "source_doi": "10.1016/j.ecolecon.2024.108163",
            "provisional": False,
        }], "1. BA-001 chain", [])
        mock_gen.generate.return_value = {
            "answer": "Risk context synthesized.",
            "confidence": 0.9,
            "evidence": [
                {
                    "doi": f"10.1000/example{i}",
                    "title": f"Evidence {i}",
                    "year": 2024,
                    "tier": "T1",
                }
                for i in range(1, 9)
            ],
            "axioms_used": ["BA-001"],
            "graph_path": [],
            "caveats": [],
        }

        import maris.api.routes.query as qmod
        qmod._llm = MagicMock()
        qmod._classifier = mock_cls
        qmod._executor = mock_exec
        qmod._generator = mock_gen
        qmod._axiom_registry = MagicMock()
        qmod._inference_engine = MagicMock()

        response = client.post(
            "/api/query",
            json={
                "question": "What are the key risks for Cabo Pulmo National Park?",
                "max_evidence_sources": 5,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["evidence"]) == 5
        assert data["evidence_count"] == 5
        assert data["doi_citation_count"] == 5
        assert data["evidence_completeness_score"] == 1.0
        assert data["confidence_breakdown"]["citation_coverage_factor"] == 1.0

    def test_query_without_question_returns_422(self, client, auth_headers):
        """Missing question field should fail validation."""
        response = client.post("/api/query", json={}, headers=auth_headers)
        assert response.status_code == 422

    @patch("maris.api.routes.query._init_components")
    @patch("maris.api.routes.query._classifier")
    @patch("maris.api.routes.query._executor")
    @patch("maris.api.routes.query._generator")
    @patch("maris.api.routes.query._build_inference_trace")
    def test_portfolio_scope_without_site_routes_to_open_domain(
        self,
        mock_trace,
        mock_gen,
        mock_exec,
        mock_cls,
        mock_init,
        client,
        auth_headers,
    ):
        """Portfolio-wide prompts should avoid site-required 422 and use open-domain strategy."""
        mock_cls.classify.return_value = {
            "category": "site_valuation",
            "site": None,
            "metrics": [],
            "confidence": 0.6,
            "caveats": [],
        }
        mock_exec.execute_with_strategy.return_value = {
            "template": "open_domain",
            "results": [{"name": "Portfolio insight", "score": 1.0}],
            "record_count": 1,
            "strategy": "safe_open_domain_retrieval",
        }
        mock_exec.get_provenance_edges.return_value = []
        mock_gen.generate.return_value = {
            "answer": "Portfolio context available.",
            "confidence": 0.3,
            "evidence": [],
            "axioms_used": [],
            "graph_path": [],
            "caveats": [],
        }
        mock_trace.return_value = ([], "", [])

        import maris.api.routes.query as qmod
        qmod._llm = MagicMock()
        qmod._classifier = mock_cls
        qmod._executor = mock_exec
        qmod._generator = mock_gen
        qmod._axiom_registry = MagicMock()
        qmod._inference_engine = MagicMock()

        response = client.post(
            "/api/query",
            json={"question": "What is the combined investment potential of all characterized sites?"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        called_category = mock_exec.execute_with_strategy.call_args.args[0]
        assert called_category == "open_domain"

    @patch("maris.api.routes.query._init_components")
    @patch("maris.api.routes.query._classifier")
    @patch("maris.api.routes.query._executor")
    @patch("maris.api.routes.query._generator")
    def test_site_query_without_site_is_rejected(
        self,
        mock_gen,
        mock_exec,
        mock_cls,
        mock_init,
        client,
        auth_headers,
    ):
        """Strict mode should reject site-required categories without explicit site context."""
        mock_cls.classify.return_value = {
            "category": "site_valuation",
            "site": None,
            "metrics": [],
            "confidence": 0.8,
            "caveats": [],
        }
        import maris.api.routes.query as qmod
        qmod._llm = MagicMock()
        qmod._classifier = mock_cls
        qmod._executor = mock_exec
        qmod._generator = mock_gen
        qmod._axiom_registry = MagicMock()
        qmod._inference_engine = MagicMock()

        response = client.post(
            "/api/query",
            json={"question": "What is it worth?"},
            headers=auth_headers,
        )
        assert response.status_code == 422
        assert "requires a specific site" in response.json()["detail"]

    @patch("maris.api.routes.query._init_components")
    @patch("maris.api.routes.query._classifier")
    @patch("maris.api.routes.query._executor")
    @patch("maris.api.routes.query._generator")
    def test_open_domain_no_results_returns_safe_insufficiency_response(
        self,
        mock_gen,
        mock_exec,
        mock_cls,
        mock_init,
        client,
        auth_headers,
    ):
        """Open-domain no-results should return explicit insufficiency response with 200."""
        mock_cls.classify.return_value = {
            "category": "open_domain",
            "site": None,
            "metrics": [],
            "confidence": 0.2,
            "caveats": [],
        }
        mock_exec.execute_with_strategy.return_value = {
            "template": "open_domain",
            "error_type": "no_results",
            "error": "Insufficient graph-grounded context for this query.",
            "results": [],
        }
        import maris.api.routes.query as qmod
        qmod._llm = MagicMock()
        qmod._classifier = mock_cls
        qmod._executor = mock_exec
        qmod._generator = mock_gen
        qmod._axiom_registry = MagicMock()
        qmod._inference_engine = MagicMock()

        response = client.post(
            "/api/query",
            json={"question": "Tell me something interesting"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "Insufficient citation-grade graph context" in data["answer"]
        assert data["confidence"] == 0.0
        assert data["evidence_count"] == 0
        assert data["provenance_risk"] == "high"


class TestSiteEndpoint:
    def test_site_endpoint_returns_data(self, client, auth_headers):
        """Site endpoint should return structured site data."""
        import maris.api.routes.graph as gmod
        mock_executor = MagicMock()
        mock_executor.execute.return_value = {
            "results": [{
                "site": "Cabo Pulmo National Park",
                "total_esv": 29270000,
                "biomass_ratio": 4.63,
                "neoli_score": 4,
                "asset_rating": "AAA",
                "services": [],
                "evidence": [],
            }],
            "record_count": 1,
        }
        gmod._executor = mock_executor
        gmod._axiom_engine = MagicMock()

        response = client.get("/api/site/Cabo Pulmo National Park", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["site"] == "Cabo Pulmo National Park"

    def test_site_not_found_returns_404(self, client, auth_headers):
        """Non-existent site should return 404."""
        import maris.api.routes.graph as gmod
        mock_executor = MagicMock()
        mock_executor.execute.return_value = {"results": [], "record_count": 0}
        gmod._executor = mock_executor
        gmod._axiom_engine = MagicMock()

        response = client.get("/api/site/Nonexistent Site", headers=auth_headers)
        assert response.status_code == 404


class TestRuntimeSiteRegistration:
    def test_register_runtime_sites_discovers_and_registers(self):
        """Runtime registration should discover sites and register dynamic patterns."""
        import maris.api.routes.query as qmod

        qmod._dynamic_sites_registered = False
        with (
            patch.object(qmod, "get_config") as mock_cfg,
            patch.object(qmod, "discover_case_study_paths", return_value=["a.json", "b.json"]),
            patch.object(
                qmod,
                "discover_site_names",
                return_value=[
                    ("Raja Ampat Marine Park", "a.json"),
                    ("Cispata Bay Mangrove Conservation Area", "b.json"),
                ],
            ),
            patch.object(qmod, "register_dynamic_sites", return_value=2) as mock_register,
        ):
            mock_cfg.return_value = MagicMock(project_root="/tmp/project")
            qmod._register_runtime_sites()

        mock_register.assert_called_once_with([
            "Cispata Bay Mangrove Conservation Area",
            "Raja Ampat Marine Park",
        ])
        assert qmod._dynamic_sites_registered is True
        qmod._dynamic_sites_registered = False

    def test_register_runtime_sites_handles_empty_discovery(self):
        """When no sites are discovered, registration should no-op safely."""
        import maris.api.routes.query as qmod

        qmod._dynamic_sites_registered = False
        with (
            patch.object(qmod, "get_config") as mock_cfg,
            patch.object(qmod, "discover_case_study_paths", return_value=[]),
            patch.object(qmod, "discover_site_names", return_value=[]),
            patch.object(qmod, "register_dynamic_sites") as mock_register,
        ):
            mock_cfg.return_value = MagicMock(project_root="/tmp/project")
            qmod._register_runtime_sites()

        mock_register.assert_not_called()
        assert qmod._dynamic_sites_registered is True
        qmod._dynamic_sites_registered = False

    def test_init_components_invokes_runtime_registration(self):
        """_init_components should always invoke runtime site registration."""
        import maris.api.routes.query as qmod

        qmod._llm = None
        qmod._classifier = None
        qmod._executor = None
        qmod._generator = None
        qmod._axiom_registry = None
        qmod._inference_engine = None
        qmod._dynamic_sites_registered = False

        with (
            patch.object(qmod, "_register_runtime_sites") as mock_runtime_register,
            patch.object(qmod, "get_config") as mock_cfg,
            patch.object(qmod, "LLMAdapter", return_value=MagicMock()),
            patch.object(qmod, "QueryClassifier", return_value=MagicMock()),
            patch.object(qmod, "QueryExecutor", return_value=MagicMock()),
            patch.object(qmod, "ResponseGenerator", return_value=MagicMock()),
            patch.object(qmod, "BridgeAxiomRegistry", return_value=MagicMock()),
            patch.object(qmod, "InferenceEngine", return_value=MagicMock()),
        ):
            mock_cfg.return_value = MagicMock(
                schemas_dir=Path("/tmp"),
                export_dir=Path("/tmp"),
            )
            qmod._init_components()

        mock_runtime_register.assert_called_once()


class TestAxiomEndpoint:
    def test_axiom_valid_id(self, client, auth_headers):
        """Valid axiom ID should return data."""
        import maris.api.routes.graph as gmod
        mock_executor = MagicMock()
        mock_executor.execute.return_value = {
            "results": [{"applicable_sites": ["Cabo Pulmo National Park"], "translated_services": ["Tourism"]}],
            "record_count": 1,
        }
        mock_engine = MagicMock()
        mock_engine.get_axiom.return_value = {
            "axiom_id": "BA-001",
            "name": "mpa_biomass_dive_tourism_value",
            "category": "ecological_to_service",
            "description": "Test axiom",
            "coefficients": {},
            "sources": [{"doi": "10.1016/j.ecolecon.2024.108163", "citation": "Test", "finding": "Test finding"}],
        }
        gmod._executor = mock_executor
        gmod._axiom_engine = mock_engine

        response = client.get("/api/axiom/BA-001", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["axiom_id"] == "BA-001"

    def test_axiom_not_found(self, client, auth_headers):
        """Non-existent axiom should return 404."""
        import maris.api.routes.graph as gmod
        mock_executor = MagicMock()
        mock_engine = MagicMock()
        mock_engine.get_axiom.return_value = None
        gmod._executor = mock_executor
        gmod._axiom_engine = mock_engine

        response = client.get("/api/axiom/BA-999", headers=auth_headers)
        assert response.status_code == 404


class TestRequestIdHeader:
    def test_response_has_request_id(self, client):
        """All responses should include X-Request-ID header."""
        with patch("maris.api.routes.health.run_query", return_value=[{"ok": 1}]):
            response = client.get("/api/health")
        assert "x-request-id" in response.headers
