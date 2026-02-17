"""Site discovery service for ingestion pipeline."""

import json
from pathlib import Path


def discover_case_study_paths(project_root: Path) -> list[Path]:
    """Auto-discover all case study JSONs from examples/*_case_study.json."""
    pattern = project_root / "examples" / "*_case_study.json"
    return sorted(pattern.parent.glob(pattern.name))


def discover_site_names(case_study_paths: list[Path]) -> list[tuple[str, Path]]:
    """Extract canonical site names from case study JSON files.

    Returns:
        List of (canonical_name, file_path) tuples.
    """
    results: list[tuple[str, Path]] = []
    for path in case_study_paths:
        try:
            with open(path) as f:
                data = json.load(f)
            # Prefer site.name, fall back to top-level site_name, then derived
            name = (
                data.get("site", {}).get("name")
                or data.get("site_name")
                or _name_from_filename(path)
            )
            if name:
                results.append((name, path))
        except (json.JSONDecodeError, OSError):
            continue
    return results


def _name_from_filename(path: Path) -> str:
    """Derive a readable site name from a case study filename."""
    stem = path.stem.replace("_case_study", "")
    return stem.replace("_", " ").title()
