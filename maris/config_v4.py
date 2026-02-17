"""MARIS v4 Configuration Overlay - Dynamic site discovery for global scaling.

Extends the base MARISConfig with:
- Dynamic case study discovery via glob on examples/*_case_study.json
- v4-specific Neo4j database connection (separate from production)
- Auto-discovery of canonical site names from case study files

IMPORTANT: This module targets a SEPARATE Neo4j database for v4.
Do NOT use it against the production v2/v3 database.
"""

import json
from os import getenv
from pathlib import Path

from maris.settings import settings
from maris.config import MARISConfig


def discover_case_study_paths(project_root: Path | None = None) -> list[Path]:
    """Auto-discover all case study JSONs from examples/*_case_study.json.

    Returns a sorted list of absolute Path objects for every file matching
    the naming convention. This replaces the hardcoded two-file list in
    the base config.
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent
    pattern = project_root / "examples" / "*_case_study.json"
    return sorted(pattern.parent.glob(pattern.name))


def discover_site_names(case_study_paths: list[Path]) -> list[tuple[str, Path]]:
    """Extract canonical site names from case study JSON files.

    Reads each file's site.name (or falls back to the top-level site_name
    field) and returns a list of (canonical_name, file_path) tuples.
    """
    results: list[tuple[str, Path]] = []
    for path in case_study_paths:
        try:
            with open(path) as f:
                data = json.load(f)
            # Prefer site.name, fall back to top-level site_name, then derive from filename
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
    """Derive a readable site name from a case study filename.

    e.g., belize_bbrrs_case_study.json -> Belize Bbrrs
    """
    stem = path.stem.replace("_case_study", "")
    return stem.replace("_", " ").title()


class MARISConfigV4(MARISConfig):
    """Wrapper to make type checkers happy.
    
    Actual implementation is just a configured instance of MARISSettings.
    """
    pass

# Singleton for v4 config
_config_v4: MARISConfigV4 | None = None


def get_config_v4() -> MARISConfigV4:
    """Return the v4 config instance (settings configured for v4 DB)."""
    global _config_v4  # noqa: PLW0603
    if _config_v4 is None:
        # Create a copy of settings with v4 overrides
        v4_settings = settings.model_copy(deep=True)
        
        # Override Neo4j connection details
        if v4_settings.neo4j_uri_v4:
            v4_settings.neo4j_uri = v4_settings.neo4j_uri_v4
        else:
            # Fallback to local port 7688 if not specified
            v4_settings.neo4j_uri = "bolt://localhost:7688"
            
        if v4_settings.neo4j_database_v4:
            v4_settings.neo4j_database = v4_settings.neo4j_database_v4
            
        _config_v4 = v4_settings  # type: ignore
        
    return _config_v4
