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
    """v4 configuration extending base config with dynamic site discovery.

    Overrides Neo4j connection to target a separate v4 database and replaces
    hardcoded case_study_paths with dynamic glob-based discovery.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Override Neo4j settings for v4 (separate database)
        # Use MARIS_NEO4J_URI_V4 if set; otherwise default to port 7688
        # to avoid accidentally targeting the production database.
        self.neo4j_uri = getenv(
            "MARIS_NEO4J_URI_V4",
            "bolt://localhost:7688",
        )
        self.neo4j_database = getenv(
            "MARIS_NEO4J_DATABASE_V4",
            "neo4j",
        )

    @property
    def case_study_paths(self) -> list[Path]:
        """All case study files, auto-discovered from examples/."""
        return discover_case_study_paths(Path(self.project_root))

    @property
    def discovered_sites(self) -> list[tuple[str, Path]]:
        """All (canonical_name, path) tuples from discovered case studies."""
        return discover_site_names(self.case_study_paths)


# Singleton for v4 config
_config_v4: MARISConfigV4 | None = None


def get_config_v4() -> MARISConfigV4:
    """Return the singleton v4 config instance."""
    global _config_v4  # noqa: PLW0603
    if _config_v4 is None:
        _config_v4 = MARISConfigV4()
    return _config_v4
