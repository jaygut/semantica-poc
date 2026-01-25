#!/usr/bin/env python3
"""
Validate cached PDFs and optionally delete invalid files and HTML leftovers.

Usage:
  python scripts/validate_pdf_cache.py --delete-invalid --delete-html
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from run_manifest import write_run_manifest

BASE_DIR = Path(__file__).resolve().parent.parent
PAPERS_DIR = BASE_DIR / "data/papers"
REPORT_PATH = BASE_DIR / "data/pdf_cache_report.json"
REGISTRY_PATH = BASE_DIR / ".claude/registry/document_index.json"

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    PYPDF_AVAILABLE = False


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate cached PDFs.")
    parser.add_argument("--delete-invalid", action="store_true")
    parser.add_argument("--delete-html", action="store_true")
    parser.add_argument("--require-text", action="store_true")
    parser.add_argument("--allow-non-text", action="store_true")
    parser.add_argument("--min-text-chars", type=int, default=2000)
    parser.add_argument("--check-pages", type=int, default=5)
    parser.add_argument("--require-match", action="store_true")
    parser.add_argument("--allow-mismatch", action="store_true")
    parser.add_argument("--title-match-ratio", type=float, default=0.6)
    parser.add_argument("--update-registry", action="store_true")
    return parser.parse_args()


def main() -> int:
    started_at = datetime.now(timezone.utc)
    args = parse_args()

    if not PAPERS_DIR.exists():
        print(f"Missing papers directory: {PAPERS_DIR}")
        return 1

    html_files = sorted(PAPERS_DIR.glob("*.html"))
    html_removed = []
    if args.delete_html:
        for path in html_files:
            path.unlink(missing_ok=True)
            html_removed.append(str(path))

    pdf_files = sorted(PAPERS_DIR.glob("*.pdf"))
    results = []
    invalid_removed = []

    registry = {}
    if REGISTRY_PATH.exists():
        registry = json.loads(REGISTRY_PATH.read_text()).get("documents", {})

    require_text = True if not args.allow_non_text else args.require_text
    require_match = True if not args.allow_mismatch else args.require_match

    for path in pdf_files:
        doc_id = path.stem
        doc = registry.get(doc_id)
        if require_match and doc is None:
            valid, text_ok, match_ok, error = False, False, False, "doc_id_not_in_registry"
        else:
            valid, text_ok, match_ok, error = validate_pdf_file(
                path,
                require_text=require_text,
                min_text_chars=args.min_text_chars,
                check_pages=args.check_pages,
                expected_title=doc.get("title") if doc else None,
                expected_doi=doc.get("doi") if doc else None,
                require_match=require_match,
                title_match_ratio=args.title_match_ratio,
            )
        results.append(
            {
                "path": str(path),
                "valid": valid,
                "text_extractable": text_ok,
                "match_ok": match_ok,
                "error": error,
                "size_bytes": path.stat().st_size if path.exists() else 0,
                "doc_id": doc_id,
            }
        )
        if not valid and args.delete_invalid:
            path.unlink(missing_ok=True)
            invalid_removed.append(str(path))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pypdf_available": PYPDF_AVAILABLE,
        "pdf_count": len(pdf_files),
        "invalid_count": sum(1 for r in results if not r["valid"]),
        "html_count": len(html_files),
        "require_text": require_text,
        "min_text_chars": args.min_text_chars,
        "check_pages": args.check_pages,
        "require_match": require_match,
        "title_match_ratio": args.title_match_ratio,
        "html_removed": html_removed,
        "invalid_removed": invalid_removed,
        "results": results,
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")

    if args.update_registry and REGISTRY_PATH.exists():
        registry = json.loads(REGISTRY_PATH.read_text())
        documents = registry.get("documents", {})
        updated_at = datetime.now(timezone.utc).isoformat()
        for item in results:
            doc_id = item.get("doc_id")
            if not doc_id or doc_id not in documents:
                continue
            doc = documents[doc_id]
            pdf_cache = doc.get("pdf_cache", {})
            pdf_cache.update(
                {
                    "status": "available" if item["valid"] else "failed",
                    "size_bytes": item.get("size_bytes"),
                    "error": item.get("error"),
                    "text_extractable": item.get("text_extractable"),
                    "match_ok": item.get("match_ok"),
                    "checked_at": updated_at,
                    "validator": "validate_pdf_cache.py",
                }
            )
            doc["pdf_cache"] = pdf_cache
            documents[doc_id] = doc
        registry["documents"] = documents
        registry["updated_at"] = updated_at
        REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n")

    print("PDF CACHE VALIDATION COMPLETE")
    print(f"  PDFs checked: {report['pdf_count']}")
    print(f"  Invalid PDFs: {report['invalid_count']}")
    print(f"  HTML files:   {report['html_count']}")
    print(f"  Report:       {REPORT_PATH}")

    manifest_path = write_run_manifest(
        script_name=Path(__file__).stem,
        args=vars(args),
        inputs={
            "papers_dir": str(PAPERS_DIR),
            "registry_path": str(REGISTRY_PATH),
        },
        outputs={
            "pdf_cache_report": str(REPORT_PATH),
            "invalid_count": report["invalid_count"],
            "deleted_invalid": len(invalid_removed),
            "deleted_html": len(html_removed),
            "registry_updated": bool(args.update_registry),
        },
        started_at=started_at,
        ended_at=datetime.now(timezone.utc),
    )
    print(f"  Run manifest: {manifest_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
