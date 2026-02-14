"""Thin wrappers for external marine data APIs.

Each client is fully mockable and uses configurable timeouts, retry logic,
and rate limiting. No real HTTP calls are made in tests.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_DELAY = 1.0


class _BaseClient:
    """Shared HTTP plumbing for external API clients."""

    def __init__(
        self,
        base_url: str,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        retry_delay: float = _DEFAULT_RETRY_DELAY,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict | list:
        """Issue a GET request with retry logic."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_exc: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                resp = httpx.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                # HTTP 204 No Content (and any response with empty body)
                # has no JSON to parse - return empty list.
                if resp.status_code == 204 or not resp.content:
                    return []
                try:
                    return resp.json()
                except (json.JSONDecodeError, ValueError):
                    logger.warning(
                        "Non-JSON response from %s (status %d)",
                        url, resp.status_code,
                    )
                    return []
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_exc = exc
                logger.warning(
                    "Request to %s failed (attempt %d/%d): %s",
                    url, attempt + 1, self.max_retries, exc,
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))

        raise ConnectionError(
            f"Failed to reach {url} after {self.max_retries} attempts"
        ) from last_exc


class OBISClient(_BaseClient):
    """Client for the Ocean Biogeographic Information System (OBIS) API.

    Docs: https://api.obis.org/v3
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(base_url="https://api.obis.org/v3", **kwargs)

    def get_occurrences(
        self,
        geometry: str | None = None,
        taxon_id: int | None = None,
        mpa_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query species occurrence records.

        Parameters
        ----------
        geometry : WKT polygon string for spatial filtering.
        taxon_id : WoRMS AphiaID to filter by taxon.
        mpa_name : Free-text MPA name search.
        limit : Maximum records to return.
        """
        params: dict[str, Any] = {"size": limit}
        if geometry:
            params["geometry"] = geometry
        if taxon_id:
            params["taxonid"] = taxon_id
        if mpa_name:
            params["areaid"] = mpa_name

        result = self._get("occurrence", params=params)
        if isinstance(result, dict):
            return result.get("results", [])
        return result

    def get_checklist(
        self,
        geometry: str | None = None,
        mpa_name: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Get unique species checklist for a geographic area.

        More efficient than raw occurrences because OBIS deduplicates
        server-side, returning one record per species.

        Parameters
        ----------
        geometry : WKT polygon for spatial filtering.
        mpa_name : Free-text MPA / area name.
        limit : Maximum species to return (default 500).
        """
        params: dict[str, Any] = {"size": limit}
        if geometry:
            params["geometry"] = geometry
        if mpa_name:
            params["areaid"] = mpa_name

        result = self._get("checklist", params=params)
        if isinstance(result, dict):
            return result.get("results", [])
        return result


class WoRMSClient(_BaseClient):
    """Client for the World Register of Marine Species (WoRMS) API.

    Docs: https://www.marinespecies.org/rest/
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(base_url="https://www.marinespecies.org/rest", **kwargs)

    def get_record(self, aphia_id: int) -> dict[str, Any]:
        """Get a full AphiaRecord by AphiaID."""
        result = self._get(f"AphiaRecordByAphiaID/{aphia_id}")
        return result if isinstance(result, dict) else {}

    def search_by_name(self, scientific_name: str) -> list[dict[str, Any]]:
        """Search for taxa by scientific name."""
        result = self._get("AphiaRecordsByName/" + scientific_name)
        return result if isinstance(result, list) else [result] if result else []

    def get_classification(self, aphia_id: int) -> dict[str, Any]:
        """Get the full taxonomic classification for an AphiaID.

        Returns a nested dict with keys like ``scientificname``, ``rank``,
        and ``child`` (recursive).  Flattened ranks (kingdom, phylum, class,
        order, family, genus) are extracted by :func:`flatten_classification`.
        """
        result = self._get(f"AphiaClassificationByAphiaID/{aphia_id}")
        return result if isinstance(result, dict) else {}

    def get_attributes(self, aphia_id: int) -> list[dict[str, Any]]:
        """Get biological attributes for an AphiaID.

        The WoRMS ``/AphiaAttributesByAphiaID/{id}`` endpoint returns a
        list of attribute dicts, each with ``measurementType`` and
        ``measurementValue`` fields (e.g. functional group, body size).
        """
        result = self._get(f"AphiaAttributesByAphiaID/{aphia_id}")
        return result if isinstance(result, list) else []


def flatten_classification(node: dict[str, Any]) -> dict[str, str]:
    """Walk a nested WoRMS classification response and return a flat dict.

    The WoRMS ``/AphiaClassificationByAphiaID`` endpoint returns a tree
    like ``{"rank": "Kingdom", "scientificname": "Animalia", "child": {...}}``.
    This helper walks the tree and returns::

        {"Kingdom": "Animalia", "Phylum": "Cnidaria", ...}
    """
    flat: dict[str, str] = {}
    current: dict[str, Any] | None = node
    while current:
        rank = current.get("rank", "")
        name = current.get("scientificname", "")
        if rank and name:
            flat[rank] = name
        current = current.get("child")
    return flat


class MarineRegionsClient(_BaseClient):
    """Client for the Marine Regions Gazetteer API.

    Docs: https://www.marineregions.org/gazetteer.php?p=webservices
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            base_url="https://www.marineregions.org/rest",
            **kwargs,
        )

    def search_by_name(self, name: str, type_id: int | None = None) -> list[dict[str, Any]]:
        """Search gazetteer records by name.

        Parameters
        ----------
        name : Place name to search.
        type_id : Optional placetype filter (e.g., 27 = MPA).
        """
        params: dict[str, Any] = {"like": "true", "offset": 0}
        if type_id is not None:
            params["typeID"] = type_id

        result = self._get(f"getGazetteerRecordsByName.json/{name}", params=params)
        return result if isinstance(result, list) else []

    def get_by_mrgid(self, mrgid: int) -> dict[str, Any]:
        """Get a gazetteer record by MRGID."""
        result = self._get(f"getGazetteerRecordByMRGID.json/{mrgid}")
        return result if isinstance(result, dict) else {}

    def get_geometry(self, mrgid: int) -> dict[str, Any]:
        """Get the geometry (WKT) for a gazetteer record."""
        result = self._get(f"getGazetteerGeometries.json/{mrgid}")
        if isinstance(result, list) and result:
            return result[0]
        return result if isinstance(result, dict) else {}
