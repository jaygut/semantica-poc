from __future__ import annotations

import re
from typing import Any


def _normalize(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def parse_year(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        match = re.search(r"(19|20)\d{2}", value)
        if match:
            try:
                return int(match.group(0))
            except ValueError:
                return None
    return None


def is_recent(year_value: Any, min_year: int, allow_missing_year: bool) -> bool:
    year = parse_year(year_value)
    if year is None:
        return allow_missing_year
    return year >= min_year


def looks_like_asset(entry: dict) -> bool:
    title = (entry.get("title") or "").strip().lower()
    if not title:
        return True

    prefixes = (
        "figure",
        "fig.",
        "table",
        "supplementary",
        "supplemental",
        "appendix",
        "supporting information",
        "data file",
        "dataset",
        "poster",
        "cover image",
    )
    if title.startswith(prefixes):
        return True

    markers = (
        "supplementary information",
        "supplemental information",
        "supporting information",
        "figure s",
        "table s",
        "fig. s",
    )
    if any(marker in title for marker in markers):
        return True

    doi = _normalize(entry.get("doi") or "")
    url = _normalize(entry.get("url") or "")
    patterns = (
        r"/fig(?:ure)?[-_/]",
        r"/table[-_/]",
        r"/supp(?:lement)?[-_/]",
        r"/suppl[-_/]",
    )
    if any(re.search(pattern, doi) for pattern in patterns):
        return True
    if any(re.search(pattern, url) for pattern in patterns):
        return True

    if not entry.get("authors") and not entry.get("year"):
        return True

    return False
