#!/usr/bin/env python3
"""
Normalize cached PDF filenames by matching PDF content to registry entries.

Defaults to dry-run. Use --apply to rename files.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_manifest import write_run_manifest

BASE_DIR = Path(__file__).resolve().parent.parent
PAPERS_DIR = BASE_DIR / "data/papers"
REPORT_PATH = BASE_DIR / "data/pdf_filename_report.json"
REGISTRY_PATH = BASE_DIR / ".claude/registry/document_index.json"

try:
    from pypdf import PdfReader

    PYPDF_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    PYPDF_AVAILABLE = False


def safe_filename(doc_id: str) -> str:
    safe_id = re.sub(r"[^\w\-_]", "_", doc_id)
    return f"{safe_id}.pdf"


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


def title_match_score(text: str, title: str) -> float:
    if not text or not title:
        return 0.0
    norm_text = normalize_text(text)
    norm_title = normalize_text(title)
    if not norm_title:
        return 0.0
    if norm_title in norm_text:
        return 1.0
    title_tokens = [t for t in norm_title.split() if len(t) > 3]
    if len(title_tokens) < 4:
        return 0.0
    text_tokens = set(norm_text.split())
    overlap = sum(1 for t in title_tokens if t in text_tokens)
    return overlap / len(title_tokens)


def extract_pdf_signals(path: Path, check_pages: int) -> tuple[str, list[str], str | None, str | None]:
    if not path.exists():
        return "", [], None, "missing_file"
    if path.stat().st_size < 1024:
        return "", [], None, "too_small"
    try:
        with open(path, "rb") as handle:
            header = handle.read(5)
        if not header.startswith(b"%PDF"):
            return "", [], None, "bad_header"
    except OSError as exc:
        return "", [], None, f"io_error:{str(exc)[:120]}"

    if not PYPDF_AVAILABLE:
        return "", [], None, "pypdf_missing"

    try:
        reader = PdfReader(str(path), strict=False)
        if not reader.pages:
            return "", [], None, "no_pages"
        page_limit = min(check_pages, len(reader.pages))
        text_chunks = []
        for idx in range(page_limit):
            text_chunks.append(reader.pages[idx].extract_text() or "")
        text = "\n".join(text_chunks)

        meta_title = None
        metadata = reader.metadata or {}
        if hasattr(metadata, "title"):
            meta_title = metadata.title
        if not meta_title and isinstance(metadata, dict):
            meta_title = metadata.get("/Title")
        if meta_title:
            meta_title = meta_title.strip()
        if meta_title and meta_title.lower().startswith("untitled"):
            meta_title = None

        return text, extract_dois(text), meta_title, None
    except Exception as exc:
        return "", [], None, f"pypdf_error:{str(exc)[:120]}"


def infer_doc_id(
    *,
    text: str,
    meta_title: str | None,
    doi_candidates: list[str],
    documents: dict[str, Any],
    doi_index: dict[str, str],
    title_match_ratio: float,
    min_text_chars: int,
) -> tuple[str | None, str | None]:
    for doi in doi_candidates:
        doc_id = doi_index.get(doi)
        if doc_id:
            return doc_id, f"doi:{doi}"

    match_text = text if len(text.strip()) >= min_text_chars else ""
    if not match_text and meta_title:
        match_text = meta_title

    if not match_text:
        return None, "no_text"

    best_id = None
    best_score = 0.0
    for doc_id, doc in documents.items():
        title = doc.get("title") or ""
        score = title_match_score(match_text, title)
        if score > best_score:
            best_score = score
            best_id = doc_id

    if best_id and best_score >= title_match_ratio:
        return best_id, f"title:{best_score:.2f}"

    return None, "no_match"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize cached PDF filenames.")
    parser.add_argument("--check-pages", type=int, default=5)
    parser.add_argument("--min-text-chars", type=int, default=2000)
    parser.add_argument("--title-match-ratio", type=float, default=0.6)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> int:
    started_at = datetime.now(timezone.utc)
    args = parse_args()

    if not PAPERS_DIR.exists():
        print(f"Missing papers directory: {PAPERS_DIR}")
        return 1
    if not REGISTRY_PATH.exists():
        print(f"Missing registry: {REGISTRY_PATH}")
        return 1

    registry = json.loads(REGISTRY_PATH.read_text())
    documents = registry.get("documents", {})
    doi_index = {
        doc.get("doi").lower().strip(): doc_id
        for doc_id, doc in documents.items()
        if doc.get("doi")
    }

    pdf_files = sorted(PAPERS_DIR.glob("*.pdf"))
    results = []
    renamed = 0
    would_rename = 0
    conflicts = 0
    errors = 0

    for path in pdf_files:
        doc_id = path.stem
        text, dois, meta_title, error = extract_pdf_signals(path, args.check_pages)
        action = "ok"
        reason = None
        target_path = None
        inferred_id = None

        if error:
            action = "error"
            reason = error
            errors += 1
        else:
            inferred_id, reason = infer_doc_id(
                text=text,
                meta_title=meta_title,
                doi_candidates=dois,
                documents=documents,
                doi_index=doi_index,
                title_match_ratio=args.title_match_ratio,
                min_text_chars=args.min_text_chars,
            )
            if inferred_id is None:
                action = "no_match"
            elif inferred_id == doc_id:
                action = "ok"
            else:
                target_path = PAPERS_DIR / safe_filename(inferred_id)
                if target_path.exists():
                    action = "conflict"
                    conflicts += 1
                elif args.apply:
                    path.rename(target_path)
                    action = "renamed"
                    renamed += 1
                else:
                    action = "would_rename"
                    would_rename += 1

        results.append(
            {
                "path": str(path),
                "doc_id": doc_id,
                "inferred_doc_id": inferred_id,
                "action": action,
                "reason": reason,
                "meta_title": meta_title,
                "doi_candidates": dois,
                "target_path": str(target_path) if target_path else None,
                "text_chars": len(text or ""),
            }
        )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pypdf_available": PYPDF_AVAILABLE,
        "pdf_count": len(pdf_files),
        "renamed": renamed,
        "would_rename": would_rename,
        "conflicts": conflicts,
        "errors": errors,
        "applied": bool(args.apply),
        "results": results,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")

    manifest_path = write_run_manifest(
        script_name=Path(__file__).stem,
        args=vars(args),
        inputs={
            "papers_dir": str(PAPERS_DIR),
            "registry_path": str(REGISTRY_PATH),
        },
        outputs={
            "filename_report": str(REPORT_PATH),
            "renamed": renamed,
            "would_rename": would_rename,
            "conflicts": conflicts,
        },
        started_at=started_at,
        ended_at=datetime.now(timezone.utc),
    )

    print("PDF FILENAME NORMALIZATION COMPLETE")
    print(f"  PDFs checked:  {len(pdf_files)}")
    print(f"  Renamed:       {renamed}")
    print(f"  Would rename:  {would_rename}")
    print(f"  Conflicts:     {conflicts}")
    print(f"  Report:        {REPORT_PATH}")
    print(f"  Run manifest:  {manifest_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
