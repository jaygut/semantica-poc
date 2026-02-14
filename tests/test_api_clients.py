"""Unit tests for _BaseClient HTTP edge cases in maris/sites/api_clients.py.

Covers:
  - WoRMS returning HTTP 204 No Content (empty body)
  - External APIs returning HTML error pages instead of JSON
  - OBIS returning empty result sets
  - Marine Regions returning 204 No Content
  - Empty response body on 200 OK

All tests use unittest.mock - no real HTTP calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from maris.sites.api_clients import (
    MarineRegionsClient,
    OBISClient,
    WoRMSClient,
    _BaseClient,
)


def _make_mock_response(
    status_code: int = 200,
    content: bytes = b"",
    json_data: dict | list | None = None,
) -> MagicMock:
    """Build a mock httpx.Response with the given status, content, and json."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.content = content
    resp.raise_for_status = MagicMock()
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        # Simulate JSONDecodeError for empty or non-JSON content
        import json
        resp.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    return resp


# ---------------------------------------------------------------------------
# 1. _BaseClient._get() - HTTP 204 No Content
# ---------------------------------------------------------------------------
class TestBaseClientHttp204:
    """_BaseClient._get() should return [] when the server returns 204."""

    def test_204_returns_empty_list(self) -> None:
        resp = _make_mock_response(status_code=204, content=b"")
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = _BaseClient(base_url="https://example.com")
            result = client._get("/test")
        assert result == []

    def test_200_with_empty_body_returns_empty_list(self) -> None:
        resp = _make_mock_response(status_code=200, content=b"")
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = _BaseClient(base_url="https://example.com")
            result = client._get("/test")
        assert result == []


# ---------------------------------------------------------------------------
# 2. _BaseClient._get() - malformed JSON (HTML error pages)
# ---------------------------------------------------------------------------
class TestBaseClientMalformedJson:
    """_BaseClient._get() should return [] for non-JSON response bodies."""

    def test_html_error_page_returns_empty_list(self) -> None:
        html = b"<html><body>503 Service Unavailable</body></html>"
        resp = _make_mock_response(status_code=200, content=html)
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = _BaseClient(base_url="https://example.com")
            result = client._get("/test")
        assert result == []

    def test_valid_json_still_works(self) -> None:
        resp = _make_mock_response(
            status_code=200,
            content=b'[{"id": 1}]',
            json_data=[{"id": 1}],
        )
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = _BaseClient(base_url="https://example.com")
            result = client._get("/test")
        assert result == [{"id": 1}]


# ---------------------------------------------------------------------------
# 3. WoRMS client - 204 for non-existent species
# ---------------------------------------------------------------------------
class TestWoRMS204:
    """WoRMS returns 204 for species not found - client should not crash."""

    def test_search_by_name_204_returns_empty_list(self) -> None:
        resp = _make_mock_response(status_code=204, content=b"")
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = WoRMSClient(max_retries=1)
            results = client.search_by_name("Nonexistus fakeus")
        assert results == []

    def test_get_record_204_returns_empty_dict(self) -> None:
        resp = _make_mock_response(status_code=204, content=b"")
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = WoRMSClient(max_retries=1)
            result = client.get_record(999999999)
        # _get returns []; get_record checks isinstance(result, dict) -> False -> {}
        assert result == {}

    def test_get_classification_204_returns_empty_dict(self) -> None:
        resp = _make_mock_response(status_code=204, content=b"")
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = WoRMSClient(max_retries=1)
            result = client.get_classification(999999999)
        assert result == {}

    def test_search_by_name_html_error_returns_empty_list(self) -> None:
        html = b"<html><body>WoRMS maintenance</body></html>"
        resp = _make_mock_response(status_code=200, content=html)
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = WoRMSClient(max_retries=1)
            results = client.search_by_name("Acropora")
        assert results == []


# ---------------------------------------------------------------------------
# 4. OBIS client - empty result handling
# ---------------------------------------------------------------------------
class TestOBISEmptyResults:
    """OBIS edge cases for empty/missing data."""

    def test_obis_empty_results_dict(self) -> None:
        resp = _make_mock_response(
            status_code=200,
            content=b'{"results": []}',
            json_data={"results": []},
        )
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = OBISClient(max_retries=1)
            results = client.get_occurrences(mpa_name="Nonexistent")
        assert results == []

    def test_obis_204_returns_empty_list(self) -> None:
        resp = _make_mock_response(status_code=204, content=b"")
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = OBISClient(max_retries=1)
            results = client.get_occurrences(mpa_name="Nonexistent")
        # _get returns []; get_occurrences: isinstance([], dict) -> False -> returns []
        assert results == []


# ---------------------------------------------------------------------------
# 5. Marine Regions client - 204 handling
# ---------------------------------------------------------------------------
class TestMarineRegions204:
    """Marine Regions edge cases."""

    def test_search_by_name_204_returns_empty_list(self) -> None:
        resp = _make_mock_response(status_code=204, content=b"")
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = MarineRegionsClient(max_retries=1)
            results = client.search_by_name("Nonexistent")
        assert results == []

    def test_get_by_mrgid_204_returns_empty_dict(self) -> None:
        resp = _make_mock_response(status_code=204, content=b"")
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = MarineRegionsClient(max_retries=1)
            result = client.get_by_mrgid(999999999)
        assert result == {}

    def test_get_geometry_204_returns_empty_dict(self) -> None:
        resp = _make_mock_response(status_code=204, content=b"")
        with patch("maris.sites.api_clients.httpx.get", return_value=resp):
            client = MarineRegionsClient(max_retries=1)
            result = client.get_geometry(999999999)
        assert result == {}
