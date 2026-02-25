"""API client with automatic fallback to static precomputed data."""

import json
import logging
import math
import os
import re
from pathlib import Path
from typing import Any

from maris.sites.models import EcosystemServiceEstimate

# Import the new registry-driven logic for "Holographic" local RAG
try:
    from maris.sites.esv_estimator import estimate_esv, get_applicable_axioms, HabitatInfo
    _HAS_LOGIC_ENGINE = True
except ImportError:
    _HAS_LOGIC_ENGINE = False

logger = logging.getLogger(__name__)

_DEFAULT_API = "http://localhost:8000"
_PRECOMPUTED_PATH = Path(__file__).parent / "precomputed_responses_v4.json"

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

    def __init__(self, base_url: str = _DEFAULT_API, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.is_live = True
        self._api_key = api_key or os.environ.get("MARIS_API_KEY", "")

    def _headers(self) -> dict:
        h: dict[str, str] = {}
        if self._api_key:
            h["Authorization"] = f"Bearer {self._api_key}"
        return h

    def query(self, question: str, site: str | None = None) -> dict:
        import requests

        payload: dict = {"question": question, "include_graph_path": True}
        if site:
            payload["site"] = site
        resp = requests.post(f"{self.base_url}/api/query", json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_health(self) -> dict:
        import requests

        try:
            resp = requests.get(f"{self.base_url}/api/health", headers=self._headers(), timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            # Fallback to offline if API dies mid-session
            return {"status": "offline"}

    def get_axiom(self, axiom_id: str) -> dict:
        import requests
        resp = requests.get(f"{self.base_url}/api/axiom/{axiom_id}", headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_site(self, site_name: str) -> dict:
        import requests
        resp = requests.get(f"{self.base_url}/api/site/{site_name}", headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

    def compare(self, sites: list[str]) -> dict:
        import requests
        resp = requests.post(
            f"{self.base_url}/api/compare",
            json={"site_names": sites},
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


class StaticBundleClient:
    """Fallback using dynamic local logic + precomputed responses."""

    def __init__(self, precomputed_path: str | Path = _PRECOMPUTED_PATH):
        self.is_live = False
        self._path = Path(precomputed_path)
        self._data: dict = {}
        
        # Load precomputed chat responses
        if self._path.exists():
            with open(self._path) as f:
                self._data = json.load(f)
                
        # Cache for loaded site JSONs (for holographic RAG)
        self._site_cache: dict[str, Any] = {}

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text into lowercase keywords, removing stopwords."""
        tokens = re.findall(r"[a-z0-9][\w\-]*", text.lower())
        return [t for t in tokens if t not in _STOPWORDS]

    def _load_site_json(self, site_name: str) -> dict | None:
        """Load local case study JSON for a specific site."""
        if site_name in self._site_cache:
            return self._site_cache[site_name]
            
        # Try to find matching file in examples/
        root = Path(__file__).resolve().parent.parent
        examples_dir = root / "examples"
        
        # Simple fuzzy match on filename
        slug = site_name.lower().replace(" ", "_").split("_")[0] # e.g. "cabo" from "Cabo Pulmo"
        
        for f in examples_dir.glob("*_case_study.json"):
            if slug in f.name.lower():
                try:
                    with open(f) as fh:
                        data = json.load(fh)
                        self._site_cache[site_name] = data
                        return data
                except Exception:
                    continue
        return None

    def _run_holographic_rag(self, question: str, site_name: str) -> dict | None:
        """Attempt to answer dynamically using local JSON + Axiom Logic."""
        if not _HAS_LOGIC_ENGINE:
            return None

        # Scenario and concept queries must use the precomputed responses.
        # Holographic RAG only handles direct site valuation/carbon intents.
        _q = question.lower()
        _BYPASS_PHRASES = (
            # Scenario patterns
            "without protection",
            "tipping point",
            "carbon revenue",
            "under ssp",
            # Financial mechanism concept queries - precomputed have richer answers
            "debt-for-nature",
            "debt for nature",
            "blue bond",
            "reef insurance",
            "parametric insurance",
            "nature bond",
            "mpa bond",
            "relate to",
        )
        if any(phrase in _q for phrase in _BYPASS_PHRASES):
            return None

        site_data = self._load_site_json(site_name)
        if not site_data:
            return None

        q_lower = question.lower()
        
        # INTENT: Valuation / Worth
        if "value" in q_lower or "worth" in q_lower or "economic" in q_lower:
            # Re-run the esv_estimator logic live
            habitats = []
            for h in site_data.get("habitats", []):
                habitats.append(HabitatInfo(
                    habitat_id=h["habitat_id"], 
                    extent_km2=h.get("extent_km2"),
                    name=h.get("name", "")
                ))
            
            services, total, conf = estimate_esv(habitats, area_km2=site_data.get("area_km2"))

            # No services computed (e.g. empty habitats array) - fall through to
            # precomputed cache which has the correct site-specific answer
            if total == 0.0 and not services:
                return None

            # Format answer
            answer = f"Based on the **Bridge Axiom Registry v2.0**, {site_name} generates an estimated **${total:,.0f} per year** in ecosystem services.\n\n"
            answer += "**Breakdown by Service:**\n"
            for s in services:
                answer += f"- **{s.service_name}**: ${s.annual_value_usd:,.0f}/yr (via {', '.join(s.axiom_ids_used)})\n"
            
            answer += f"\n**Methodology:** This valuation was computed locally using {len(conf['axiom_chain'])} active axioms from the registry."
            
            return {
                "answer": answer,
                "confidence": 0.95,
                "evidence": [{"title": "Dynamic Registry Calculation", "tier": "T1", "doi": "Local Compute"}],
                "axioms_used": conf["axiom_chain"],
                "graph_path": [],
                "caveats": ["Computed instantly in Demo Mode using local Python logic engine."]
            }
            
        # INTENT: Carbon / Sequestration
        if "carbon" in q_lower or "sequestration" in q_lower:
            # Find carbon axioms
            habitats = site_data.get("habitats", [])
            lines = []
            axioms_triggered = []
            
            for h in habitats:
                hid = h["habitat_id"]
                # Get axioms for this habitat
                # We need to manually match since we don't have the full graph
                if "seagrass" in hid:
                    lines.append(f"- **Seagrass**: Uses BA-013 (Sequestration Rate) and BA-008 (Credit Value).")
                    axioms_triggered.extend(["BA-013", "BA-008"])
                if "mangrove" in hid:
                    lines.append(f"- **Mangroves**: Uses BA-017 (Sequestration) and BA-009 (Restoration BCR).")
                    axioms_triggered.extend(["BA-017", "BA-009"])
            
            if lines:
                answer = f"{site_name} includes key blue carbon habitats:\n\n" + "\n".join(lines)
                answer += "\n\nThese are valued using Tier 2 financial bridge axioms found in the registry."
                return {
                    "answer": answer,
                    "confidence": 0.90,
                    "evidence": [],
                    "axioms_used": list(set(axioms_triggered)),
                    "graph_path": [],
                    "caveats": ["Holographic lookup from local site JSON."]
                }

        return None

    def _match(self, question: str, site: str | None = None) -> dict:
        """Find best response: Holographic RAG -> Precomputed -> Fallback."""
        
        # 1. Try Holographic RAG (Dynamic Logic)
        if site:
            holographic_response = self._run_holographic_rag(question, site)
            if holographic_response:
                return holographic_response

        # 2. Try Precomputed (Static Cache)
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

        # Document frequency
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
            if not k_tokens: continue

            overlap = q_token_set & k_tokens
            if not overlap: continue

            # TF-IDF scoring
            score = 0.0
            for token in overlap:
                idf = math.log(n_docs / (1 + df.get(token, 0))) + 1.0
                score += idf

            normalizer = math.sqrt(len(q_token_set) * len(k_tokens))
            if normalizer > 0:
                score /= normalizer

            if score > best_score:
                best_score = score
                best_key = key

        # Lower threshold for match
        if best_key and best_score > 0.25:
            return responses[best_key]
            
        return self._fallback()

    @staticmethod
    def _fallback() -> dict:
        return {
            "answer": "I don't have enough information to answer that. " 
                      "In **Demo Mode**, I can dynamically calculate valuations or answer pre-cached questions. "
                      "Start the **Live API** to query the full knowledge graph.",
            "confidence": 0.0,
            "evidence": [],
            "axioms_used": [],
            "graph_path": [],
            "caveats": ["Demo Mode limit reached"],
        }

    def query(self, question: str, site: str | None = None) -> dict:
        # If site context is known, try site-specific query first
        base_match = self._match(question, site)
        
        # If confidence is high (e.g. from Holographic RAG), return immediately
        if base_match.get("confidence", 0) > 0.8:
            return base_match
            
        # Otherwise try variations
        if site and site.lower() not in question.lower():
            for variant in [
                f"{question.rstrip('?')} for {site}?",
                f"{question.rstrip('?')} {site}?",
            ]:
                candidate = self._match(variant, site)
                if candidate.get("confidence", 0) > base_match.get("confidence", 0):
                    return candidate
                    
        return base_match

    def get_health(self) -> dict:
        return {"status": "static", "neo4j_connected": False, "llm_available": False, "graph_stats": {}}

    def get_axiom(self, axiom_id: str) -> dict:
        return {"axiom_id": axiom_id, "name": "", "description": "Static fallback."}

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
            return LiveAPIClient(api_key=os.environ.get("MARIS_API_KEY", ""))
    except Exception:
        pass

    return StaticBundleClient()
