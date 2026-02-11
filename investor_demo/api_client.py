"""API client with automatic fallback to static precomputed data."""

import json
import logging
from pathlib import Path
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

_DEFAULT_API = "http://localhost:8000"
_PRECOMPUTED_PATH = Path(__file__).parent / "precomputed_responses.json"


class LiveAPIClient:
    """Connects to the MARIS FastAPI backend."""

    def __init__(self, base_url: str = _DEFAULT_API):
        self.base_url = base_url.rstrip("/")
        self.is_live = True

    def query(self, question: str, site: str | None = None) -> dict:
        import requests

        payload = {"question": question, "site": site, "include_graph_path": True}
        resp = requests.post(f"{self.base_url}/api/query", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_health(self) -> dict:
        import requests

        resp = requests.get(f"{self.base_url}/api/health", timeout=5)
        resp.raise_for_status()
        return resp.json()

    def get_axiom(self, axiom_id: str) -> dict:
        import requests

        resp = requests.get(f"{self.base_url}/api/axiom/{axiom_id}", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_site(self, site_name: str) -> dict:
        import requests

        resp = requests.get(f"{self.base_url}/api/site/{site_name}", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def compare(self, sites: list[str]) -> dict:
        import requests

        resp = requests.post(
            f"{self.base_url}/api/compare",
            json={"site_names": sites},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


class StaticBundleClient:
    """Fallback using precomputed responses when the API is unavailable."""

    def __init__(self, precomputed_path: str | Path = _PRECOMPUTED_PATH):
        self.is_live = False
        self._path = Path(precomputed_path)
        self._data: dict = {}
        if self._path.exists():
            with open(self._path) as f:
                self._data = json.load(f)

    def _match(self, question: str) -> dict:
        """Find the closest precomputed response via fuzzy matching."""
        responses = self._data.get("responses", {})
        if not responses:
            return self._fallback()

        best_key = None
        best_score = 0.0
        q_lower = question.lower()
        for key in responses:
            score = SequenceMatcher(None, q_lower, key.lower()).ratio()
            if score > best_score:
                best_score = score
                best_key = key

        if best_key and best_score > 0.35:
            return responses[best_key]
        return self._fallback()

    @staticmethod
    def _fallback() -> dict:
        return {
            "answer": "I don't have a precomputed answer for that question. Start the MARIS API for live responses.",
            "confidence": 0.0,
            "evidence": [],
            "axioms_used": [],
            "graph_path": [],
            "caveats": ["Running in static fallback mode - live API not available"],
        }

    def query(self, question: str, site: str | None = None) -> dict:
        return self._match(question)

    def get_health(self) -> dict:
        return {"status": "static", "neo4j_connected": False, "llm_available": False, "graph_stats": {}}

    def get_axiom(self, axiom_id: str) -> dict:
        return {"axiom_id": axiom_id, "name": "", "description": "Static fallback - start API for details."}

    def get_site(self, site_name: str) -> dict:
        return {"site": site_name, "total_esv_usd": None}

    def compare(self, sites: list[str]) -> dict:
        return {"sites": []}


def get_client() -> LiveAPIClient | StaticBundleClient:
    """Try the live API; fall back to the static bundle."""
    try:
        import requests

        resp = requests.get(f"{_DEFAULT_API}/api/health", timeout=3)
        if resp.status_code == 200:
            logger.info("Connected to MARIS API at %s", _DEFAULT_API)
            return LiveAPIClient()
    except Exception:
        pass

    logger.info("MARIS API unavailable - using static bundle fallback")
    return StaticBundleClient()
