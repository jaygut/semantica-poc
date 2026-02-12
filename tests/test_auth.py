"""Tests for API authentication, rate limiting, and input validation."""

import os
import pytest
from unittest.mock import patch, MagicMock

# Must set env vars BEFORE app imports
os.environ["MARIS_NEO4J_PASSWORD"] = "test-password"
os.environ["MARIS_LLM_API_KEY"] = "test-key"
os.environ["MARIS_API_KEY"] = "test-api-key"
os.environ["MARIS_DEMO_MODE"] = "false"

from fastapi import HTTPException
from fastapi.testclient import TestClient
from maris.api.auth import (
    validate_question,
    validate_site_name,
    validate_axiom_id,
    _check_rate_limit,
    _rate_buckets,
)


@pytest.fixture(autouse=True)
def _reset_config_and_env():
    """Reset config singleton and set auth-enforced env before each test."""
    import maris.config
    maris.config._config = None
    os.environ["MARIS_DEMO_MODE"] = "false"
    os.environ["MARIS_API_KEY"] = "test-api-key"
    yield
    # Restore demo mode for other test files
    os.environ["MARIS_DEMO_MODE"] = "true"
    maris.config._config = None


@pytest.fixture
def app():
    """Create fresh app with auth enforced (demo_mode=false)."""
    import maris.config
    maris.config._config = None
    from maris.api.main import create_app
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-api-key"}


# ---- Input validation (standalone, no app needed) ----


class TestInputValidation:
    def test_validate_question_rejects_long(self):
        """validate_question with 501-char string raises HTTPException(400)."""
        with pytest.raises(HTTPException) as exc_info:
            validate_question("x" * 501)
        assert exc_info.value.status_code == 400

    def test_validate_question_accepts_normal(self):
        """validate_question accepts a normal-length question."""
        result = validate_question("What is Cabo Pulmo worth?")
        assert result == "What is Cabo Pulmo worth?"

    def test_validate_site_name_rejects_injection(self):
        """validate_site_name rejects SQL injection attempts."""
        with pytest.raises(HTTPException) as exc_info:
            validate_site_name("'; DROP TABLE --")
        assert exc_info.value.status_code == 400

    def test_validate_site_name_accepts_valid(self):
        """validate_site_name accepts a valid site name."""
        result = validate_site_name("Cabo Pulmo National Park")
        assert result == "Cabo Pulmo National Park"

    def test_validate_axiom_id_rejects_invalid(self):
        """validate_axiom_id rejects non-matching IDs."""
        with pytest.raises(HTTPException) as exc_info:
            validate_axiom_id("BA-999x")
        assert exc_info.value.status_code == 400

    def test_validate_axiom_id_accepts_valid(self):
        """validate_axiom_id accepts BA-001."""
        result = validate_axiom_id("BA-001")
        assert result == "BA-001"


# ---- Health endpoint (no auth required) ----


class TestHealthNoAuth:
    def test_health_no_auth_required(self, client):
        """GET /api/health returns 200 without any auth header."""
        with patch("maris.api.routes.health.run_query", return_value=[{"ok": 1}]):
            response = client.get("/api/health")
        assert response.status_code == 200


# ---- Auth enforcement on protected endpoints ----


class TestAuthEnforcement:
    def test_query_401_without_token(self, client):
        """POST /api/query returns 401 without auth header."""
        response = client.post(
            "/api/query",
            json={"question": "What is Cabo Pulmo worth?"},
        )
        assert response.status_code == 401

    def test_query_401_wrong_token(self, client):
        """POST /api/query with wrong Bearer token returns 401."""
        response = client.post(
            "/api/query",
            json={"question": "What is Cabo Pulmo worth?"},
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert response.status_code == 401

    def test_query_200_with_correct_token(self, client, auth_headers):
        """POST /api/query with correct token returns 200."""
        import maris.api.routes.query as qmod

        mock_cls = MagicMock()
        mock_cls.classify.return_value = {
            "category": "site_valuation",
            "site": "Cabo Pulmo National Park",
            "metrics": [],
            "confidence": 0.9,
            "caveats": [],
        }
        mock_exec = MagicMock()
        mock_exec.execute.return_value = {
            "results": [{"site": "Cabo Pulmo National Park", "total_esv": 29270000}],
            "record_count": 1,
        }
        mock_exec.get_provenance_edges.return_value = []
        mock_gen = MagicMock()
        mock_gen.generate.return_value = {
            "answer": "The ESV is $29.27M.",
            "confidence": 0.85,
            "evidence": [],
            "axioms_used": [],
            "graph_path": [],
            "caveats": [],
        }

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

    def test_site_401_without_token(self, client):
        """GET /api/site/Test returns 401 without auth."""
        response = client.get("/api/site/Test")
        assert response.status_code == 401

    def test_axiom_401_without_token(self, client):
        """GET /api/axiom/BA-001 returns 401 without auth."""
        response = client.get("/api/axiom/BA-001")
        assert response.status_code == 401


# ---- Rate limiting ----


class TestRateLimiting:
    def test_rate_limit_429(self):
        """_check_rate_limit raises 429 after exceeding max requests."""
        # Use a unique key to avoid cross-test contamination
        test_key = "test_rate_limit_429_key"
        _rate_buckets.pop(test_key, None)

        # Fill the bucket to max
        for _ in range(30):
            _check_rate_limit(test_key, max_requests=30, window_seconds=60)

        # 31st request should raise 429
        with pytest.raises(HTTPException) as exc_info:
            _check_rate_limit(test_key, max_requests=30, window_seconds=60)
        assert exc_info.value.status_code == 429

        # Clean up
        _rate_buckets.pop(test_key, None)
