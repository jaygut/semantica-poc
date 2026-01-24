#!/usr/bin/env python3
"""
Batch PDF fetcher for MARIS registry.

Goals:
- Build a robust local PDF cache for downstream ingestion.
- Prioritize T1 papers.
- Use multiple discovery strategies (direct URL, DOI landing, Unpaywall OA).
- Record outcomes in a PDF registry report.
"""

from __future__ import annotations

import argparse
import json
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_DIR = Path(__file__).resolve().parent.parent
REGISTRY_PATH = BASE_DIR / ".claude/registry/document_index.json"
OUTPUT_DIR = BASE_DIR / "data/papers"
REPORT_PATH = BASE_DIR / "data/pdf_registry.json"

USER_AGENT = "SemanticaMARISFetcher/1.1 (+https://github.com/Hawksight-AI/semantica; mailto:green-intel@technetium-ia.com)"
UNPAYWALL_EMAIL = "green-intel@technetium-ia.com"
TIMEOUT = 30
CHUNK_SIZE = 128 * 1024

_thread_local = threading.local()

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    PYPDF_AVAILABLE = False


def get_session() -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None:
        retry_strategy = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            raise_on_status=False,
        )
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        _thread_local.session = session
    return session


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text())


def safe_filename(doc_id: str) -> str:
    safe_id = re.sub(r"[^\w\-_]", "_", doc_id)
    return f"{safe_id}.pdf"


def is_pdf_response(response: requests.Response, url: str) -> bool:
    content_type = response.headers.get("Content-Type", "").lower()
    if "pdf" in content_type:
        return True
    return url.lower().endswith(".pdf")


def extract_pdf_links(html_text: str, base_url: str) -> list[str]:
    if not html_text:
        return []

    patterns = [
        r'citation_pdf_url"[^>]*content="([^"]+)"',
        r"citation_pdf_url'[^>]*content='([^']+)'",
        r'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']application/pdf["\'][^>]+href=["\']([^"\']+)["\']',
        r'href=["\']([^"\']+\.pdf[^"\']*)["\']',
    ]

    links: list[str] = []
    for pattern in patterns:
        for match in re.findall(pattern, html_text, flags=re.IGNORECASE):
            link = match.strip()
            if link:
                links.append(urljoin(base_url, link))

    # Deduplicate while preserving order
    seen = set()
    ordered: list[str] = []
    for link in links:
        if link in seen:
            continue
        seen.add(link)
        ordered.append(link)

    return ordered[:5]


def unpaywall_pdf_url(session: requests.Session, doi: str | None) -> str | None:
    if not doi:
        return None
    url = f"https://api.unpaywall.org/v2/{doi}?email={UNPAYWALL_EMAIL}"
    try:
        response = session.get(url, timeout=TIMEOUT)
        if response.status_code != 200:
            return None
        data = response.json()
    except (requests.RequestException, ValueError):
        return None

    locations = []
    best = data.get("best_oa_location") or {}
    if best:
        locations.append(best)
    locations.extend(data.get("oa_locations", []))

    for loc in locations:
        pdf_url = loc.get("url_for_pdf")
        if pdf_url:
            return pdf_url
        url = loc.get("url")
        if url and url.lower().endswith(".pdf"):
            return url

    return None


def normalize_text(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def extract_dois(text: str) -> list[str]:
    if not text:
        return []
    matches = re.findall(r"10\.\d{4,9}/[^\s\"<>]+", text, flags=re.IGNORECASE)
    cleaned = []
    for match in matches:
        cleaned.append(match.rstrip(").,;:").lower())
    return cleaned


def title_matches(text: str, title: str, min_ratio: float) -> bool:
    if not text or not title:
        return False
    norm_text = normalize_text(text)
    norm_title = normalize_text(title)
    if not norm_title:
        return False
    if norm_title in norm_text:
        return True
    title_tokens = [t for t in norm_title.split() if len(t) > 3]
    if len(title_tokens) < 4:
        return False
    text_tokens = set(norm_text.split())
    overlap = sum(1 for t in title_tokens if t in text_tokens)
    return (overlap / len(title_tokens)) >= min_ratio


def looks_like_access_notice(text: str) -> bool:
    norm = normalize_text(text)
    if not norm:
        return True
    phrases = [
        "access denied",
        "sign in",
        "log in",
        "purchase",
        "buy this article",
        "get access",
        "institutional access",
        "your access",
        "subscribe",
        "download pdf",
        "downloaded from",
        "terms of use",
        "rights and permissions",
    ]
    if any(phrase in norm for phrase in phrases):
        word_count = len(norm.split())
        return word_count < 800
    return False


def validate_pdf_file(
    path: Path,
    *,
    require_text: bool,
    min_text_chars: int,
    check_pages: int,
    expected_title: str | None = None,
    expected_doi: str | None = None,
    require_match: bool = True,
    title_match_ratio: float = 0.6,
) -> tuple[bool, bool, bool, str | None]:
    if not path.exists():
        return False, False, False, "missing_file"

    if path.stat().st_size < 1024:
        return False, False, False, "too_small"

    try:
        with open(path, "rb") as handle:
            header = handle.read(5)
        if not header.startswith(b"%PDF"):
            return False, False, False, "bad_header"
    except OSError as exc:
        return False, False, False, f"io_error:{str(exc)[:120]}"

    if not PYPDF_AVAILABLE:
        if require_text or require_match:
            return False, False, False, "pypdf_missing"
        return True, False, False, None

    try:
        reader = PdfReader(str(path), strict=False)
        if not reader.pages:
            return False, False, False, "no_pages"
        page_limit = min(check_pages, len(reader.pages))
        text_chunks = []
        for idx in range(page_limit):
            text_chunks.append(reader.pages[idx].extract_text() or "")
        text = "\n".join(text_chunks)
        text_ok = len(text.strip()) >= min_text_chars

        doi_ok = False
        title_ok = False
        if expected_doi:
            expected = expected_doi.lower().strip()
            doi_ok = expected in extract_dois(text)
        if expected_title:
            title_ok = title_matches(text, expected_title, title_match_ratio)

        if expected_title:
            match_ok = title_ok
        elif expected_doi:
            match_ok = doi_ok
        else:
            match_ok = True

        if require_text and not text_ok:
            return False, text_ok, match_ok, "text_not_extractable"
        if looks_like_access_notice(text) and not match_ok:
            return False, text_ok, match_ok, "access_notice"
        if require_match and not match_ok:
            return False, text_ok, match_ok, "content_mismatch"

        return True, text_ok, match_ok, None
    except Exception as exc:
        return False, False, False, f"pypdf_error:{str(exc)[:120]}"


def fetch_pdf(
    session: requests.Session,
    url: str,
    out_path: Path,
    *,
    require_text: bool,
    min_text_chars: int,
    check_pages: int,
    expected_title: str | None,
    expected_doi: str | None,
    require_match: bool,
    title_match_ratio: float,
) -> tuple[bool, str | None, int]:
    try:
        response = session.get(url, allow_redirects=True, timeout=TIMEOUT, stream=True)
    except requests.RequestException as exc:
        return False, f"request_error:{str(exc)[:120]}", 0

    if response.status_code >= 400:
        return False, f"http_{response.status_code}", 0

    if not is_pdf_response(response, url):
        return False, "non_pdf", 0

    bytes_written = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as out_file:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                out_file.write(chunk)
                bytes_written += len(chunk)

    valid, _, _, error = validate_pdf_file(
        out_path,
        require_text=require_text,
        min_text_chars=min_text_chars,
        check_pages=check_pages,
        expected_title=expected_title,
        expected_doi=expected_doi,
        require_match=require_match,
        title_match_ratio=title_match_ratio,
    )
    if not valid:
        out_path.unlink(missing_ok=True)
        return False, error or "invalid_pdf", bytes_written

    return True, None, bytes_written


def attempt_document_pdf(
    doc_id: str,
    doc: dict,
    delay_s: float,
    *,
    require_text: bool,
    min_text_chars: int,
    check_pages: int,
    require_match: bool,
    title_match_ratio: float,
) -> dict:
    session = get_session()
    filename = safe_filename(doc_id)
    out_path = OUTPUT_DIR / filename

    if out_path.exists() and out_path.stat().st_size > 0:
        valid, text_ok, match_ok, error = validate_pdf_file(
            out_path,
            require_text=require_text,
            min_text_chars=min_text_chars,
            check_pages=check_pages,
            expected_title=doc.get("title"),
            expected_doi=doc.get("doi"),
            require_match=require_match,
            title_match_ratio=title_match_ratio,
        )
        if valid:
            return {
                "doc_id": doc_id,
                "status": "exists",
                "pdf_path": str(out_path),
                "source_url": None,
                "size_bytes": out_path.stat().st_size,
                "text_extractable": text_ok,
                "match_ok": match_ok,
            }
        out_path.unlink(missing_ok=True)

    doi = doc.get("doi")
    url = doc.get("url")
    candidates: list[str] = []

    oa_pdf = unpaywall_pdf_url(session, doi)
    if oa_pdf:
        candidates.append(oa_pdf)

    if url:
        candidates.append(url)
    if doi:
        candidates.append(f"https://doi.org/{doi}")

    last_error = None
    for candidate_url in candidates:
        try:
            response = session.get(candidate_url, allow_redirects=True, timeout=TIMEOUT)
        except requests.RequestException as exc:
            last_error = f"request_error:{str(exc)[:120]}"
            continue

        if response.status_code >= 400:
            last_error = f"http_{response.status_code}"
            continue

        if is_pdf_response(response, candidate_url):
            ok, err, size = fetch_pdf(
                session,
                candidate_url,
                out_path,
                require_text=require_text,
                min_text_chars=min_text_chars,
                check_pages=check_pages,
                expected_title=doc.get("title"),
                expected_doi=doc.get("doi"),
                require_match=require_match,
                title_match_ratio=title_match_ratio,
            )
            if ok:
                valid, text_ok, match_ok, _ = validate_pdf_file(
                    out_path,
                    require_text=require_text,
                    min_text_chars=min_text_chars,
                    check_pages=check_pages,
                    expected_title=doc.get("title"),
                    expected_doi=doc.get("doi"),
                    require_match=require_match,
                    title_match_ratio=title_match_ratio,
                )
                time.sleep(delay_s)
                return {
                    "doc_id": doc_id,
                    "status": "success",
                    "pdf_path": str(out_path),
                    "source_url": candidate_url,
                    "size_bytes": size,
                    "method": "direct_pdf",
                    "text_extractable": text_ok,
                    "match_ok": match_ok,
                }
            last_error = err
            continue

        content_type = response.headers.get("Content-Type", "").lower()
        html_text = response.text if "html" in content_type or "<html" in response.text[:2000].lower() else ""
        if html_text:
            pdf_links = extract_pdf_links(html_text, candidate_url)
            for pdf_url in pdf_links:
                ok, err, size = fetch_pdf(
                    session,
                    pdf_url,
                    out_path,
                    require_text=require_text,
                    min_text_chars=min_text_chars,
                    check_pages=check_pages,
                    expected_title=doc.get("title"),
                    expected_doi=doc.get("doi"),
                    require_match=require_match,
                    title_match_ratio=title_match_ratio,
                )
                if ok:
                    valid, text_ok, match_ok, _ = validate_pdf_file(
                        out_path,
                        require_text=require_text,
                        min_text_chars=min_text_chars,
                        check_pages=check_pages,
                        expected_title=doc.get("title"),
                        expected_doi=doc.get("doi"),
                        require_match=require_match,
                        title_match_ratio=title_match_ratio,
                    )
                    time.sleep(delay_s)
                    return {
                        "doc_id": doc_id,
                        "status": "success",
                        "pdf_path": str(out_path),
                        "source_url": pdf_url,
                        "size_bytes": size,
                        "method": "html_pdf_link",
                        "text_extractable": text_ok,
                        "match_ok": match_ok,
                    }
                last_error = err

    time.sleep(delay_s)
    return {
        "doc_id": doc_id,
        "status": "failed",
        "error": last_error or "no_pdf_found",
    }


def select_documents(
    documents: dict,
    tiers: Iterable[str],
    max_docs: int,
) -> list[tuple[str, dict]]:
    tier_rank = {"T1": 0, "T2": 1, "T3": 2, "T4": 3}
    allowed = set(tiers)

    items = []
    for doc_id, doc in documents.items():
        tier = doc.get("source_tier", "T4")
        if tier not in allowed:
            continue
        items.append((doc_id, doc))

    items.sort(
        key=lambda item: (
            tier_rank.get(item[1].get("source_tier", "T4"), 4),
            0 if item[1].get("doi") else 1,
            0 if item[1].get("url") else 1,
        )
    )

    return items[:max_docs]


def build_report(results: list[dict], args: argparse.Namespace) -> dict:
    successes = [r for r in results if r["status"] in {"success", "exists"}]
    failures = [r for r in results if r["status"] == "failed"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_pdfs": args.target_pdfs,
        "max_docs": args.max_docs,
        "tiers": args.tiers,
        "workers": args.workers,
        "require_text": True if not args.allow_non_text else args.require_text,
        "min_text_chars": args.min_text_chars,
        "check_pages": args.check_pages,
        "require_match": True if not args.allow_mismatch else args.require_match,
        "title_match_ratio": args.title_match_ratio,
        "update_registry": not args.no_update_registry,
        "attempted_docs": len(results),
        "pdfs_found": len(successes),
        "successes": successes,
        "failures": failures,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch PDF fetcher for MARIS registry.")
    parser.add_argument("--target-pdfs", type=int, default=60)
    parser.add_argument("--max-docs", type=int, default=120)
    parser.add_argument("--tiers", type=str, default="T1,T2")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--delay-s", type=float, default=0.4)
    parser.add_argument("--require-text", action="store_true")
    parser.add_argument("--allow-non-text", action="store_true")
    parser.add_argument("--min-text-chars", type=int, default=2000)
    parser.add_argument("--check-pages", type=int, default=5)
    parser.add_argument("--require-match", action="store_true")
    parser.add_argument("--allow-mismatch", action="store_true")
    parser.add_argument("--title-match-ratio", type=float, default=0.6)
    parser.add_argument("--no-update-registry", action="store_true")
    return parser.parse_args()


def update_registry_pdf_status(results: list[dict]) -> None:
    if not REGISTRY_PATH.exists():
        return
    registry = json.loads(REGISTRY_PATH.read_text())
    documents = registry.get("documents", {})
    updated_at = datetime.now(timezone.utc).isoformat()

    for result in results:
        doc_id = result.get("doc_id")
        if not doc_id or doc_id not in documents:
            continue
        doc = documents[doc_id]
        pdf_cache = doc.get("pdf_cache", {})
        status = result.get("status")
        pdf_cache.update(
            {
                "status": "available" if status in {"success", "exists"} else "failed",
                "source_url": result.get("source_url"),
                "size_bytes": result.get("size_bytes"),
                "error": result.get("error"),
                "text_extractable": result.get("text_extractable"),
                "match_ok": result.get("match_ok"),
                "checked_at": updated_at,
                "validator": "fetch_pdfs_batch.py",
            }
        )
        doc["pdf_cache"] = pdf_cache
        documents[doc_id] = doc

    registry["documents"] = documents
    registry["updated_at"] = updated_at
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n")


def main() -> int:
    args = parse_args()
    tiers = [t.strip() for t in args.tiers.split(",") if t.strip()]
    args.tiers = tiers

    registry = load_registry()
    documents = registry.get("documents", {})
    selection = select_documents(documents, tiers=tiers, max_docs=args.max_docs)

    require_text = True if not args.allow_non_text else args.require_text
    require_match = True if not args.allow_mismatch else args.require_match

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    lock = threading.Lock()

    def runner(doc_id: str, doc: dict) -> dict:
        result = attempt_document_pdf(
            doc_id,
            doc,
            delay_s=args.delay_s,
            require_text=require_text,
            min_text_chars=args.min_text_chars,
            check_pages=args.check_pages,
            require_match=require_match,
            title_match_ratio=args.title_match_ratio,
        )
        with lock:
            results.append(result)
        return result

    # ThreadPoolExecutor kept simple for clarity.
    from concurrent.futures import ThreadPoolExecutor, as_completed

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(runner, doc_id, doc) for doc_id, doc in selection]
        for _ in as_completed(futures):
            pass

    report = build_report(results, args)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")

    if not args.no_update_registry:
        update_registry_pdf_status(results)

    print("PDF FETCH COMPLETE")
    print(f"  Attempted docs: {report['attempted_docs']}")
    print(f"  PDFs found:     {report['pdfs_found']}")
    print(f"  Report:         {REPORT_PATH}")

    if report["pdfs_found"] < args.target_pdfs:
        print("WARNING: Target PDF count not met.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
