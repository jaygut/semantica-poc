#!/usr/bin/env python3
"""
MARIS Document Fetcher
======================
Fetches all documents listed in the MARIS registry and saves them locally.
Generates a fetch report with success/failure details.

Usage:
    python scripts/fetch_documents.py
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
REGISTRY_PATH = "/Users/jaygut/Desktop/semantica-poc/.claude/registry/document_index.json"
OUTPUT_DIR = "/Users/jaygut/Desktop/semantica-poc/data/papers"
REPORT_PATH = "/Users/jaygut/Desktop/semantica-poc/data/fetch_report.json"

USER_AGENT = "SemanticaMARISFetcher/1.0 (+https://github.com/Hawksight-AI/semantica; mailto:green-intel@technetium-ia.com)"
TIMEOUT = 30
CHUNK_SIZE = 128 * 1024  # 128KB chunks


def create_session() -> requests.Session:
    """Create a requests session with retry logic for transient failures."""
    retry_strategy = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"],
        raise_on_status=False
    )
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/pdf,text/html,application/xml,application/json,text/plain,*/*"
    })
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def infer_extension(content_type: str, url: str) -> str:
    """Infer file extension from Content-Type header or URL."""
    ext = ".bin"

    if content_type:
        content_type = content_type.lower()
        if "pdf" in content_type:
            ext = ".pdf"
        elif "html" in content_type:
            ext = ".html"
        elif "xml" in content_type:
            ext = ".xml"
        elif "json" in content_type:
            ext = ".json"
        elif "text/plain" in content_type:
            ext = ".txt"

    # Fallback to URL extension if Content-Type didn't help
    if ext == ".bin" and url:
        match = re.search(r"\.([a-zA-Z0-9]{2,5})(?:\?|#|$)", url)
        if match:
            url_ext = match.group(1).lower()
            if url_ext in ["pdf", "html", "xml", "json", "txt", "htm"]:
                ext = f".{url_ext}"
                if ext == ".htm":
                    ext = ".html"

    return ext


def safe_filename(doc_id: str, content_type: str, url: str) -> str:
    """Generate a safe filename from document ID and detected type."""
    # Sanitize doc_id to remove problematic characters
    safe_id = re.sub(r'[^\w\-_]', '_', doc_id)
    ext = infer_extension(content_type, url)
    return f"{safe_id}{ext}"


def fetch_with_head_then_get(session: requests.Session, url: str) -> tuple:
    """
    Fetch a URL using HEAD to detect content type, then GET to download.
    Returns (response, content_type) or raises on failure.
    """
    # First, try HEAD to get content type without downloading
    try:
        head_resp = session.head(url, allow_redirects=True, timeout=TIMEOUT)
        content_type = head_resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    except requests.RequestException:
        # HEAD failed, try GET directly
        content_type = ""

    # Now GET the actual content
    get_resp = session.get(url, allow_redirects=True, timeout=TIMEOUT, stream=True)

    # Update content_type from GET response if HEAD didn't provide it
    if not content_type:
        content_type = get_resp.headers.get("Content-Type", "").split(";")[0].strip().lower()

    return get_resp, content_type


def extract_citation_pdf_url(html_text: str) -> str | None:
    """Extract citation_pdf_url meta content from HTML, if present."""
    if not html_text:
        return None
    match = re.search(
        r'citation_pdf_url\"\\s+content=\"([^\"]+)\"',
        html_text,
        flags=re.IGNORECASE
    )
    if match:
        return match.group(1).strip()
    return None


def fetch_pdf_from_html(
    session: requests.Session,
    html_path: str,
    base_url: str,
    doc_id: str
) -> dict:
    """Attempt to fetch a PDF from citation_pdf_url found in HTML."""
    result = {
        "pdf_attempted": False,
        "pdf_url": None,
        "pdf_status": None,
        "pdf_content_type": None,
        "pdf_size_bytes": None,
        "pdf_path": None,
        "pdf_error": None,
    }

    try:
        html_text = Path(html_path).read_text(errors="ignore")
    except OSError as exc:
        result["pdf_error"] = f"read_html_failed: {str(exc)[:100]}"
        return result

    pdf_url = extract_citation_pdf_url(html_text)
    if not pdf_url:
        result["pdf_error"] = "citation_pdf_url_not_found"
        return result

    result["pdf_attempted"] = True
    result["pdf_url"] = urljoin(base_url, pdf_url)

    try:
        response, content_type = fetch_with_head_then_get(session, result["pdf_url"])
        result["pdf_status"] = response.status_code
        result["pdf_content_type"] = content_type or "unknown"

        if response.status_code >= 400:
            result["pdf_error"] = f"pdf_http_{response.status_code}"
            return result

        if "pdf" not in (content_type or ""):
            result["pdf_error"] = f"non_pdf_content_type:{content_type or 'unknown'}"
            return result

        filename = safe_filename(doc_id, content_type, result["pdf_url"])
        out_path = os.path.join(OUTPUT_DIR, filename)

        bytes_written = 0
        with open(out_path, "wb") as out_file:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    out_file.write(chunk)
                    bytes_written += len(chunk)

        result["pdf_size_bytes"] = bytes_written
        result["pdf_path"] = out_path
        return result
    except requests.Timeout:
        result["pdf_error"] = "pdf_timeout"
    except requests.ConnectionError as exc:
        result["pdf_error"] = f"pdf_connection_error:{str(exc)[:100]}"
    except requests.RequestException as exc:
        result["pdf_error"] = f"pdf_request_error:{str(exc)[:100]}"
    except OSError as exc:
        result["pdf_error"] = f"pdf_file_error:{str(exc)[:100]}"
    except Exception as exc:
        result["pdf_error"] = f"pdf_unexpected_error:{str(exc)[:100]}"

    return result


def fetch_documents():
    """Main function to fetch all documents from the registry."""

    # Create output directory
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # Initialize report
    report = {
        "fetch_started": datetime.now(timezone.utc).isoformat(),
        "fetch_completed": None,
        "total_documents": 0,
        "fetched_count": 0,
        "failed_count": 0,
        "fetched": [],
        "failed": []
    }

    # Load registry
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Registry not found at {REGISTRY_PATH}")
        return
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in registry: {e}")
        return

    documents = registry.get("documents", {})
    report["total_documents"] = len(documents)

    print(f"Found {len(documents)} documents in registry")
    print(f"Output directory: {OUTPUT_DIR}")
    print("-" * 60)

    # Create session with retry logic
    session = create_session()

    # Process each document
    for idx, (doc_id, doc) in enumerate(documents.items(), 1):
        url = doc.get("url")
        doi = doc.get("doi")
        title = doc.get("title", "Unknown")[:50]

        # Build list of URLs to try
        candidates = []
        if url:
            candidates.append(url)
        if doi:
            # DOI resolver as fallback
            candidates.append(f"https://doi.org/{doi}")

        if not candidates:
            report["failed"].append({
                "id": doc_id,
                "url": None,
                "doi": doi,
                "error": "No URL or DOI available",
                "attempted_at": datetime.now(timezone.utc).isoformat()
            })
            report["failed_count"] += 1
            print(f"[{idx}/{len(documents)}] SKIP: {doc_id} - No URL or DOI")
            continue

        # Try each candidate URL
        success = False
        last_error = None

        for candidate_url in candidates:
            try:
                print(f"[{idx}/{len(documents)}] Fetching: {doc_id}...", end=" ", flush=True)

                response, content_type = fetch_with_head_then_get(session, candidate_url)

                if response.status_code >= 400:
                    last_error = f"HTTP {response.status_code}"
                    print(f"FAILED ({last_error})")
                    continue

                # Generate filename and save
                filename = safe_filename(doc_id, content_type, candidate_url)
                out_path = os.path.join(OUTPUT_DIR, filename)

                # Stream content to file
                bytes_written = 0
                with open(out_path, "wb") as out_file:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            out_file.write(chunk)
                            bytes_written += len(chunk)

                # Record success
                report["fetched"].append({
                    "id": doc_id,
                    "url": candidate_url,
                    "status": response.status_code,
                    "content_type": content_type or "unknown",
                    "size_bytes": bytes_written,
                    "path": out_path,
                    "retrieved_at": datetime.now(timezone.utc).isoformat()
                })
                report["fetched_count"] += 1
                success = True

                # If HTML, try to fetch the linked PDF when available.
                if "html" in (content_type or ""):
                    pdf_result = fetch_pdf_from_html(
                        session=session,
                        html_path=out_path,
                        base_url=candidate_url,
                        doc_id=doc_id
                    )
                    report["fetched"][-1].update(pdf_result)

                print(f"OK ({filename}, {bytes_written:,} bytes)")
                break

            except requests.Timeout:
                last_error = "Request timeout"
                print(f"TIMEOUT")
            except requests.ConnectionError as e:
                last_error = f"Connection error: {str(e)[:100]}"
                print(f"CONNECTION ERROR")
            except requests.RequestException as e:
                last_error = f"Request failed: {str(e)[:100]}"
                print(f"REQUEST ERROR")
            except IOError as e:
                last_error = f"File write error: {str(e)[:100]}"
                print(f"FILE ERROR")
            except Exception as e:
                last_error = f"Unexpected error: {str(e)[:100]}"
                print(f"ERROR")

        # Record failure if no candidate succeeded
        if not success:
            report["failed"].append({
                "id": doc_id,
                "url": url,
                "doi": doi,
                "error": last_error or "Unknown error",
                "attempted_at": datetime.now(timezone.utc).isoformat()
            })
            report["failed_count"] += 1

        # Small delay to be respectful to servers
        time.sleep(0.5)

    # Finalize report
    report["fetch_completed"] = datetime.now(timezone.utc).isoformat()

    # Write report
    report_dir = Path(REPORT_PATH).parent
    report_dir.mkdir(parents=True, exist_ok=True)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("-" * 60)
    print(f"Fetch complete!")
    print(f"  Fetched: {report['fetched_count']}/{report['total_documents']}")
    print(f"  Failed:  {report['failed_count']}/{report['total_documents']}")
    print(f"  Report:  {REPORT_PATH}")


if __name__ == "__main__":
    fetch_documents()
