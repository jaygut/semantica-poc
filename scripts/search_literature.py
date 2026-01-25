#!/usr/bin/env python3
"""
API-backed literature search runner for MARIS registry.

Supports OpenAlex and Crossref, optional URL verification, and registry updates.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from run_manifest import write_run_manifest
from registry_filters import is_recent, looks_like_asset

BASE_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PATH = BASE_DIR / ".claude/registry/document_index.json"
KEYWORD_CANDIDATES = [
    BASE_DIR / "data/keywords/search_keywords.md",
    BASE_DIR / ".claude/skills/literature-scout/references/search_keywords.md",
]
OUTPUT_DIR = BASE_DIR / "data/search_results"

OPENALEX_URL = "https://api.openalex.org/works"
CROSSREF_URL = "https://api.crossref.org/works"
USER_AGENT = "MARIS-LiteratureSearch/1.0 (+https://github.com/Hawksight-AI/semantica)"
MAILTO = "green-intel@technetium-ia.com"


def get_session() -> requests.Session:
    retry_strategy = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def resolve_keywords_path() -> Path:
    for candidate in KEYWORD_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Missing search keywords. Expected data/keywords/search_keywords.md."
    )


def load_keywords() -> str:
    return resolve_keywords_path().read_text()


def parse_queries(domain: str) -> list[str]:
    raw = load_keywords().splitlines()
    queries: list[str] = []

    domain_aliases = {
        "ecological": ["ecological foundations"],
        "trophic": ["trophic & network ecology"],
        "connectivity": ["connectivity & spatial dynamics"],
        "services": ["ecosystem services"],
        "blue-finance": ["blue finance"],
        "conservation-finance": ["conservation finance"],
        "disclosure": ["disclosure & reporting"],
        "edna": ["data modalities", "edna"],
        "remote-sensing": ["remote sensing"],
        "all": [],
    }

    target = [d.lower() for d in domain_aliases.get(domain, [])]
    current_section = ""
    in_code = False

    for line in raw:
        line = line.rstrip()
        if line.startswith("## "):
            current_section = line[3:].strip().lower()
            continue
        if line.startswith("### "):
            current_section = line[4:].strip().lower()
            continue
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            continue
        if not line.strip() or line.strip().startswith("#"):
            continue
        if domain != "all" and target:
            if not any(tag in current_section for tag in target):
                continue
        queries.append(line.strip())

    if domain != "all" and not queries:
        # Fallback to all queries if the domain filter fails to match sections.
        return parse_queries("all")

    return queries


def depth_config(depth: str) -> dict:
    if depth == "shallow":
        return {"per_query": 5, "max_queries": 6}
    if depth == "deep":
        return {"per_query": 20, "max_queries": 20}
    return {"per_query": 10, "max_queries": 12}


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def generate_doc_id(authors: list[str], year: int | None, title: str) -> str:
    author = authors[0] if authors else "unknown"
    author_slug = re.sub(r"[^a-z0-9]+", "_", author.lower()).strip("_")[:20]
    title_slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:30]
    year_str = str(year) if year else "unknown"
    return f"{author_slug}_{year_str}_{title_slug}"


def openalex_search(session: requests.Session, query: str, per_page: int) -> list[dict]:
    params = {"search": query, "per-page": per_page, "mailto": MAILTO}
    response = session.get(OPENALEX_URL, params=params, timeout=20)
    if response.status_code != 200:
        return []
    data = response.json()
    results = []
    for item in data.get("results", []):
        title = item.get("display_name")
        doi = (item.get("doi") or "").replace("https://doi.org/", "")
        year = item.get("publication_year")
        authors = [
            author.get("author", {}).get("display_name")
            for author in item.get("authorships", [])
            if author.get("author")
        ]
        primary = item.get("primary_location", {}) or {}
        url = primary.get("landing_page_url") or item.get("id")
        journal = (item.get("host_venue") or {}).get("display_name")
        if not title or not url:
            continue
        results.append(
            {
                "title": title,
                "doi": doi or None,
                "year": year,
                "authors": [a for a in authors if a],
                "url": url,
                "journal": journal,
                "source": "openalex",
                "query": query,
            }
        )
    return results


def crossref_search(session: requests.Session, query: str, rows: int) -> list[dict]:
    params = {"query": query, "rows": rows, "mailto": MAILTO}
    response = session.get(CROSSREF_URL, params=params, timeout=20)
    if response.status_code != 200:
        return []
    data = response.json()
    results = []
    for item in data.get("message", {}).get("items", []):
        title_list = item.get("title") or []
        title = title_list[0] if title_list else None
        doi = item.get("DOI")
        url = item.get("URL")
        year = None
        issued = item.get("issued", {}).get("date-parts", [])
        if issued and issued[0]:
            year = issued[0][0]
        authors = []
        for author in item.get("author", []):
            name = " ".join(filter(None, [author.get("given"), author.get("family")]))
            if name:
                authors.append(name)
        journal = None
        container = item.get("container-title") or []
        if container:
            journal = container[0]
        if not title or not url:
            continue
        results.append(
            {
                "title": title,
                "doi": doi,
                "year": year,
                "authors": authors,
                "url": url,
                "journal": journal,
                "source": "crossref",
                "query": query,
            }
        )
    return results


def load_verify_helpers() -> tuple[callable, callable]:
    verify_module_path = BASE_DIR / ".claude/skills/literature-scout/scripts/verify_url.py"
    if not verify_module_path.exists():
        return None, None
    spec = __import__("importlib.util").util.spec_from_file_location("verify_url", verify_module_path)
    module = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify_url, module.determine_source_tier


def dedup_results(results: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for item in results:
        doi = (item.get("doi") or "").lower()
        title = normalize_title(item.get("title") or "")
        key = doi or title
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def update_registry(entries: list[dict], domain: str, search_meta: dict) -> int:
    if not REGISTRY_PATH.exists():
        print(f"Missing registry: {REGISTRY_PATH}")
        return 0
    registry = json.loads(REGISTRY_PATH.read_text())
    documents = registry.get("documents", {})
    added = 0

    existing_dois = {doc.get("doi") for doc in documents.values() if doc.get("doi")}
    existing_titles = {normalize_title(doc.get("title", "")) for doc in documents.values()}

    for entry in entries:
        doi = entry.get("doi")
        title = entry.get("title", "")
        if doi and doi in existing_dois:
            continue
        if normalize_title(title) in existing_titles:
            continue
        doc_id = generate_doc_id(entry.get("authors", []), entry.get("year"), title)
        if doc_id in documents:
            continue
        documents[doc_id] = {
            "title": title,
            "url": entry.get("url"),
            "doi": doi,
            "authors": entry.get("authors", []),
            "year": entry.get("year"),
            "journal": entry.get("journal"),
            "source_tier": entry.get("source_tier", "T1"),
            "document_type": entry.get("document_type", "peer-reviewed"),
            "domain_tags": list({domain, entry.get("source")} - {None}),
            "added_at": datetime.now(timezone.utc).isoformat(),
            "notes": f"auto-import via search_literature ({entry.get('source')})",
            "search_provenance": search_meta | {
                "source": entry.get("source"),
                "query": entry.get("query"),
                "verified": entry.get("verification") is not None,
            },
        }
        added += 1

    registry["documents"] = documents

    # Recalculate statistics using existing helper if available
    try:
        from validate_registry import recalculate_statistics
        registry = recalculate_statistics(registry)
    except Exception:
        pass

    registry["updated_at"] = datetime.now(timezone.utc).isoformat()
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n")
    return added


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search literature and optionally update registry.")
    parser.add_argument("domain", type=str, help="Domain or 'all'")
    parser.add_argument("--depth", type=str, default="medium", choices=["shallow", "medium", "deep"])
    parser.add_argument("--tiers", type=str, default="T1,T2")
    parser.add_argument("--sources", type=str, default="openalex,crossref")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--update-registry", action="store_true")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--min-year", type=int, default=2018)
    parser.add_argument("--allow-missing-year", action="store_true")
    return parser.parse_args()


def main() -> int:
    started_at = datetime.now(timezone.utc)
    args = parse_args()
    cfg = depth_config(args.depth)
    queries = parse_queries(args.domain)
    if not queries:
        print("No queries found for domain.")
        return 1

    queries = queries[: cfg["max_queries"]]
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    per_query = cfg["per_query"]
    tiers = {t.strip() for t in args.tiers.split(",") if t.strip()}

    verify_url_fn, tier_fn = load_verify_helpers()
    session = get_session()
    results: list[dict] = []

    def run_query(query: str, source: str) -> list[dict]:
        if source == "openalex":
            return openalex_search(session, query, per_query)
        if source == "crossref":
            return crossref_search(session, query, per_query)
        return []

    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(run_query, query, source)
            for query in queries
            for source in sources
        ]
        for future in as_completed(futures):
            results.extend(future.result())

    results = dedup_results(results)

    search_meta = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "domain": args.domain,
        "depth": args.depth,
        "tiers": sorted(tiers),
        "sources": sources,
        "min_year": args.min_year,
        "allow_missing_year": args.allow_missing_year,
        "queried_at": datetime.now(timezone.utc).isoformat(),
        "keywords_path": str(resolve_keywords_path()),
    }

    filtered = []
    skipped_assets = 0
    skipped_old = 0
    for entry in results:
        if looks_like_asset(entry):
            skipped_assets += 1
            continue
        if not is_recent(entry.get("year"), args.min_year, args.allow_missing_year):
            skipped_old += 1
            continue
        url = entry.get("url")
        entry["query"] = entry.get("query") or None
        if tier_fn:
            entry["source_tier"] = tier_fn(url) if url else "T4"
        else:
            entry["source_tier"] = entry.get("source_tier") or "T1"
        if args.verify and verify_url_fn and url:
            verification = verify_url_fn(url)
            entry["verification"] = verification
            entry["source_tier"] = verification["extracted_metadata"]["source_tier"]
        if entry.get("source_tier") not in tiers:
            continue
        filtered.append(entry)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = OUTPUT_DIR / f"{args.domain}_{timestamp}.json"
    output_path.write_text(
        json.dumps({"metadata": search_meta, "results": filtered}, indent=2) + "\n"
    )

    added = 0
    if args.update_registry and filtered:
        added = update_registry(filtered, args.domain, search_meta)

    manifest_path = write_run_manifest(
        script_name=Path(__file__).stem,
        args=vars(args),
        inputs={
            "registry_path": str(REGISTRY_PATH),
            "keywords_path": str(resolve_keywords_path()),
        },
        outputs={
            "search_results": str(output_path),
            "registry_updated": bool(args.update_registry),
            "added_entries": added,
        },
        started_at=started_at,
        ended_at=datetime.now(timezone.utc),
    )

    print("SEARCH COMPLETE")
    print(f"  Queries:     {len(queries)}")
    print(f"  Results:     {len(results)}")
    print(f"  Skipped:     {skipped_assets}")
    print(f"  Skipped old: {skipped_old}")
    print(f"  Filtered:    {len(filtered)}")
    print(f"  Output:      {output_path}")
    print(f"  Run manifest: {manifest_path}")
    if args.update_registry:
        print(f"  Added docs:  {added}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
