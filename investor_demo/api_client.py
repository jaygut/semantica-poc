"""API client with automatic fallback to static precomputed data."""

import json
import logging
import math
import re
from pathlib import Path

logger = logging.getLogger(__name__)

_DEFAULT_API = "http://localhost:8000"
_PRECOMPUTED_PATH = Path(__file__).parent / "precomputed_responses.json"

# Stopwords to ignore during keyword matching
_STOPWORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "about", "between",
    "through", "during", "before", "after", "above", "below", "up", "down",
    "out", "off", "over", "under", "again", "further", "then", "once",
    "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
    "neither", "each", "every", "all", "any", "few", "more", "most",
    "other", "some", "such", "no", "only", "own", "same", "than", "too",
    "very", "just", "also", "this", "that", "these", "those", "it", "its",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "they",
    "them", "his", "her", "their", "what", "which", "who", "whom",
    "how", "when", "where", "why", "if", "because", "while",
    "tell", "show", "give", "much", "many",
})


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

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text into lowercase keywords, removing stopwords."""
        tokens = re.findall(r"[a-z0-9][\w\-]*", text.lower())
        return [t for t in tokens if t not in _STOPWORDS]

    def _match(self, question: str) -> dict:
        """Find the closest precomputed response via TF-IDF-style keyword overlap."""
        responses = self._data.get("responses", {})
        if not responses:
            return self._fallback()

        q_tokens = self._tokenize(question)
        if not q_tokens:
            return self._fallback()

        # Build document frequency across all keys
        all_keys = list(responses.keys())
        key_token_sets = []
        for key in all_keys:
            key_token_sets.append(set(self._tokenize(key)))

        # Document frequency: how many keys contain each token
        df: dict[str, int] = {}
        for token_set in key_token_sets:
            for token in token_set:
                df[token] = df.get(token, 0) + 1

        n_docs = len(all_keys)
        q_token_set = set(q_tokens)

        best_key = None
        best_score = 0.0

        for idx, key in enumerate(all_keys):
            k_tokens = key_token_sets[idx]
            if not k_tokens:
                continue

            # Compute weighted overlap: sum of IDF for matching tokens
            overlap = q_token_set & k_tokens
            if not overlap:
                continue

            # TF-IDF inspired score: sum(1/df) for overlapping tokens,
            # normalized by geometric mean of set sizes
            score = 0.0
            for token in overlap:
                idf = math.log(n_docs / (1 + df.get(token, 0))) + 1.0
                score += idf

            # Normalize by geometric mean of query and key token counts
            normalizer = math.sqrt(len(q_token_set) * len(k_tokens))
            if normalizer > 0:
                score /= normalizer

            if score > best_score:
                best_score = score
                best_key = key

        if best_key and best_score > 0.3:
            return responses[best_key]
        return self._fallback()

    @staticmethod
    def _fallback() -> dict:
        return {
            "answer": "I don't have enough information to answer that question in static mode. Try rephrasing your question, or start the MARIS API (uvicorn maris.api.main:app) for live responses that can query the full knowledge graph.",
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
