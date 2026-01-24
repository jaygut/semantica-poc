#!/usr/bin/env python3
"""
Abstract Enrichment Script for MARIS Registry

Implements a 5-tier cascade strategy to fetch abstracts for all documents:
  Tier 1: CrossRef API → OpenAlex API → Semantic Scholar API
  Tier 2: HTML meta tag extraction
  Tier 3: WebFetch (stub - requires manual invocation)
  Tier 4: WebSearch (stub)
  Tier 5: PDF first-page parsing

Usage:
    python scripts/enrich_abstracts.py
    python scripts/enrich_abstracts.py --dry-run
    python scripts/enrich_abstracts.py --limit 10
"""

import json
import re
import html
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import sys

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("WARNING: requests library not available. Install with: pip install requests")

# Configuration
REGISTRY_PATH = Path(__file__).parent.parent / ".claude/registry/document_index.json"
PAPERS_DIR = Path(__file__).parent.parent / "data/papers"

USER_AGENT = "MARIS/1.0 (mailto:green-intel@technetium-ia.com)"
TIMEOUT = 15
DELAY_BETWEEN_REQUESTS = 0.5  # Be respectful to APIs


def create_session() -> "requests.Session":
    """Create a requests session with retry logic."""
    if not REQUESTS_AVAILABLE:
        return None

    retry_strategy = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"]
    )
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def load_index() -> dict:
    """Load the document index."""
    return json.loads(REGISTRY_PATH.read_text())


def save_index(index: dict):
    """Save the document index."""
    index['updated_at'] = datetime.now(timezone.utc).isoformat()
    REGISTRY_PATH.write_text(json.dumps(index, indent=2))


# =============================================================================
# Tier 1: DOI-Based API Fetching
# =============================================================================

def fetch_crossref_abstract(session, doi: str) -> Optional[str]:
    """Fetch abstract from CrossRef API."""
    if not session or not doi:
        return None

    url = f"https://api.crossref.org/works/{doi}"

    try:
        response = session.get(url, timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            abstract = data.get("message", {}).get("abstract", "")
            if abstract:
                # CrossRef abstracts often have JATS XML tags - strip them
                clean = re.sub(r'<[^>]+>', '', abstract).strip()
                if len(clean) > 100:
                    return clean
    except Exception as e:
        pass  # Silent fail, try next source

    return None


def reconstruct_openalex_abstract(inverted_index: dict) -> str:
    """Reconstruct abstract from OpenAlex inverted index format."""
    if not inverted_index:
        return ""

    words = []
    for word, positions in inverted_index.items():
        for pos in positions:
            words.append((pos, word))
    words.sort()
    return " ".join(w[1] for w in words)


def fetch_openalex_abstract(session, doi: str) -> Optional[str]:
    """Fetch abstract from OpenAlex API."""
    if not session or not doi:
        return None

    url = f"https://api.openalex.org/works/doi:{doi}"

    try:
        response = session.get(url, timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            abstract_index = data.get("abstract_inverted_index", {})
            if abstract_index:
                abstract = reconstruct_openalex_abstract(abstract_index)
                if len(abstract) > 100:
                    return abstract
    except Exception as e:
        pass

    return None


def fetch_semantic_scholar_abstract(session, doi: str) -> Optional[str]:
    """Fetch abstract from Semantic Scholar API."""
    if not session or not doi:
        return None

    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
    params = {"fields": "abstract"}

    try:
        response = session.get(url, params=params, timeout=TIMEOUT)
        if response.status_code == 200:
            abstract = response.json().get("abstract")
            if abstract and len(abstract) > 100:
                return abstract
    except Exception as e:
        pass

    return None


# =============================================================================
# Tier 2: HTML Meta Tag Extraction
# =============================================================================

def extract_abstract_from_html(html_content: str) -> Optional[str]:
    """Extract abstract from HTML meta tags in priority order."""
    if not html_content:
        return None

    # Priority 1: Standard meta tags
    patterns = [
        (r'<meta\s+name=["\']citation_abstract["\']\s+content=["\']([^"\']+)["\']', 'citation_abstract'),
        (r'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']citation_abstract["\']', 'citation_abstract'),
        (r'<meta\s+name=["\']dc\.description["\']\s+content=["\']([^"\']+)["\']', 'dc.description'),
        (r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', 'description'),
        (r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']+)["\']', 'og:description'),
    ]

    for pattern, tag_name in patterns:
        match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
        if match:
            abstract = html.unescape(match.group(1)).strip()
            # Filter out short descriptions or login prompts
            if len(abstract) > 150 and not is_paywall_text(abstract):
                return abstract

    # Priority 2: Structured data (JSON-LD)
    jsonld_pattern = r'<script\s+type=["\']application/ld\+json["\']>([^<]+)</script>'
    for match in re.finditer(jsonld_pattern, html_content, re.IGNORECASE):
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict):
                abstract = data.get("abstract") or data.get("description")
                if abstract and len(abstract) > 150 and not is_paywall_text(abstract):
                    return abstract
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        abstract = item.get("abstract") or item.get("description")
                        if abstract and len(abstract) > 150 and not is_paywall_text(abstract):
                            return abstract
        except json.JSONDecodeError:
            pass

    return None


def is_paywall_text(text: str) -> bool:
    """Check if text appears to be paywall/login content rather than abstract."""
    paywall_indicators = [
        'login', 'subscribe', 'access denied', 'cookie',
        'sign in', 'register', 'purchase', 'buy now',
        'institutional access', 'pay per view'
    ]
    text_lower = text.lower()
    return any(indicator in text_lower for indicator in paywall_indicators)


# =============================================================================
# Tier 5: PDF First-Page Parsing
# =============================================================================

def extract_abstract_from_pdf(pdf_path: str) -> Optional[str]:
    """Extract abstract from PDF first 2 pages."""
    try:
        import pymupdf
    except ImportError:
        return None  # PyMuPDF not available

    try:
        doc = pymupdf.open(pdf_path)
        text = ""
        for page_num in range(min(2, len(doc))):
            text += doc[page_num].get_text()

        # Look for abstract section
        abstract_patterns = [
            r'Abstract[:\s]*\n?(.*?)(?:Introduction|Keywords|Background|1\.|1\s)',
            r'Summary[:\s]*\n?(.*?)(?:Introduction|Keywords|1\.)',
            r'ABSTRACT[:\s]*\n?(.*?)(?:INTRODUCTION|KEYWORDS|1\.)',
        ]

        for pattern in abstract_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Clean up whitespace
                abstract = re.sub(r'\s+', ' ', abstract)
                if 100 < len(abstract) < 3000:
                    return abstract

        return None
    except Exception:
        return None


# =============================================================================
# Validation
# =============================================================================

def validate_abstract(abstract: str) -> tuple[bool, str]:
    """Validate abstract quality."""
    if not abstract:
        return False, "empty"
    if len(abstract) < 100:
        return False, "too_short"
    if len(abstract) > 5000:
        return False, "too_long"
    if abstract.count(" ") < 20:
        return False, "insufficient_words"
    if is_paywall_text(abstract):
        return False, "paywall_text"
    if abstract.startswith("http"):
        return False, "url_not_abstract"

    return True, "valid"


# =============================================================================
# Main Enrichment Function
# =============================================================================

def enrich_abstracts(dry_run: bool = False, limit: int = None):
    """Add abstracts to all documents using cascade strategy."""

    if not REQUESTS_AVAILABLE:
        print("ERROR: requests library required. Install with: pip install requests")
        return

    index = load_index()
    session = create_session()

    stats = {
        "total": 0,
        "already_has_abstract": 0,
        "crossref": 0,
        "openalex": 0,
        "semantic_scholar": 0,
        "html_meta": 0,
        "pdf_parse": 0,
        "failed": 0
    }

    documents = list(index["documents"].items())
    if limit:
        documents = documents[:limit]

    print(f"Processing {len(documents)} documents...")
    print("-" * 60)

    for idx, (doc_id, doc) in enumerate(documents, 1):
        stats["total"] += 1

        # Skip if already has abstract
        if doc.get("abstract"):
            stats["already_has_abstract"] += 1
            continue

        abstract = None
        source = None
        doi = doc.get("doi")

        print(f"[{idx}/{len(documents)}] {doc_id[:40]}...", end=" ", flush=True)

        # Tier 1a: CrossRef API
        if doi and not abstract:
            abstract = fetch_crossref_abstract(session, doi)
            if abstract:
                source = "crossref_api"
                print("CrossRef ✓")

        # Tier 1b: OpenAlex API
        if doi and not abstract:
            time.sleep(DELAY_BETWEEN_REQUESTS)
            abstract = fetch_openalex_abstract(session, doi)
            if abstract:
                source = "openalex_api"
                print("OpenAlex ✓")

        # Tier 1c: Semantic Scholar API
        if doi and not abstract:
            time.sleep(DELAY_BETWEEN_REQUESTS)
            abstract = fetch_semantic_scholar_abstract(session, doi)
            if abstract:
                source = "semantic_scholar_api"
                print("SemanticScholar ✓")

        # Tier 2: HTML meta tags (if we have downloaded HTML)
        if not abstract:
            html_path = PAPERS_DIR / f"{doc_id}.html"
            if html_path.exists():
                try:
                    html_content = html_path.read_text(errors='ignore')
                    abstract = extract_abstract_from_html(html_content)
                    if abstract:
                        source = "html_meta"
                        print("HTML ✓")
                except Exception:
                    pass

        # Tier 5: PDF parsing (if we have downloaded PDF)
        if not abstract:
            pdf_path = PAPERS_DIR / f"{doc_id}.pdf"
            if pdf_path.exists():
                abstract = extract_abstract_from_pdf(str(pdf_path))
                if abstract:
                    source = "pdf_parse"
                    print("PDF ✓")

        # Validate and save
        if abstract:
            is_valid, reason = validate_abstract(abstract)
            if is_valid:
                if not dry_run:
                    doc["abstract"] = abstract
                    doc["abstract_source"] = source
                    doc["abstract_captured_at"] = datetime.now(timezone.utc).isoformat()

                stats[source.replace("_api", "")] += 1
            else:
                print(f"Invalid ({reason})")
                stats["failed"] += 1
        else:
            print("Not found")
            stats["failed"] += 1

        time.sleep(DELAY_BETWEEN_REQUESTS)

    # Save index
    if not dry_run:
        save_index(index)

    # Print summary
    print("-" * 60)
    print("Enrichment Summary:")
    print(f"  Total processed: {stats['total']}")
    print(f"  Already had abstract: {stats['already_has_abstract']}")
    print(f"  CrossRef: {stats['crossref']}")
    print(f"  OpenAlex: {stats['openalex']}")
    print(f"  Semantic Scholar: {stats['semantic_scholar']}")
    print(f"  HTML meta: {stats['html_meta']}")
    print(f"  PDF parse: {stats['pdf_parse']}")
    print(f"  Failed: {stats['failed']}")

    success_count = stats['crossref'] + stats['openalex'] + stats['semantic_scholar'] + stats['html_meta'] + stats['pdf_parse']
    processable = stats['total'] - stats['already_has_abstract']
    if processable > 0:
        coverage = (success_count / processable) * 100
        print(f"  Coverage: {coverage:.1f}% of documents without abstracts")

    if dry_run:
        print("\n[DRY RUN - No changes saved]")

    return stats


def main():
    dry_run = '--dry-run' in sys.argv
    limit = None

    if '--limit' in sys.argv:
        idx = sys.argv.index('--limit')
        if idx + 1 < len(sys.argv):
            limit = int(sys.argv[idx + 1])

    enrich_abstracts(dry_run=dry_run, limit=limit)


if __name__ == "__main__":
    main()
