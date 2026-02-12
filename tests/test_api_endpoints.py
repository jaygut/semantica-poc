"""Tests for FastAPI API endpoints using TestClient."""

import os

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
    @patch("maris.api.routes.query._init_components")
    @patch("maris.api.routes.query._classifier")
    @patch("maris.api.routes.query._executor")
    @patch("maris.api.routes.query._generator")
    def test_valid_query(self, mock_gen, mock_exec, mock_cls, mock_init, client, auth_headers):
        """A valid query should return 200 with answer."""
        mock_cls.classify.return_value = {
            "category": "site_valuation",
            "site": "Cabo Pulmo National Park",
            "metrics": [],
            "confidence": 0.9,
            "caveats": [],
        }
        mock_exec.execute.return_value = {
            "results": [{"site": "Cabo Pulmo National Park", "total_esv": 29270000}],
            "record_count": 1,
        }
        mock_exec.get_provenance_edges.return_value = []
        mock_gen.generate.return_value = {
            "answer": "The ESV is $29.27M.",
            "confidence": 0.85,
            "evidence": [],
            "axioms_used": [],
            "graph_path": [],
            "caveats": [],
        }
        # Set the module-level refs so _init_components sees them as not-None
        import maris.api.routes.query as qmod
        qmod._llm = MagicMock()
        qmod._classifier = mock_cls
        qmod._executor = mock_exec
        qmod._generator = mock_gen

        response = client.post(
            "/api/query",
            json={"question": "What is Cabo Pulmo worth?"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "confidence" in data

    def test_query_without_question_returns_422(self, client, auth_headers):
        """Missing question field should fail validation."""
        response = client.post("/api/query", json={}, headers=auth_headers)
        assert response.status_code == 422


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
