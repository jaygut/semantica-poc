"""TNFD LEAP disclosure generator - v4 extension with dynamic site discovery.

Extends the base LEAPGenerator with auto-discovered case study files.
Drop-in replacement: import LEAPGeneratorV4 instead of LEAPGenerator.

IMPORTANT: This module does NOT modify the original leap_generator.py.
It imports and extends the base class with dynamic case study discovery.
"""

from __future__ import annotations

from pathlib import Path

from maris.config_v4 import discover_case_study_paths, discover_site_names
from maris.disclosure.leap_generator import LEAPGenerator, _CASE_STUDY_FILES


def _discover_case_study_files(
    project_root: Path | None = None,
) -> dict[str, str]:
    """Build the full case study files mapping from auto-discovery.

    Merges the base _CASE_STUDY_FILES with all discovered case studies
    from examples/*_case_study.json. Discovery results take precedence
    for overlapping site names.
    """
    result = dict(_CASE_STUDY_FILES)

    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent.parent

    paths = discover_case_study_paths(project_root)
    sites = discover_site_names(paths)

    for name, path in sites:
        # Store as relative path from project root (matching base format)
        try:
            rel = path.relative_to(project_root)
        except ValueError:
            rel = path
        result[name] = str(rel)

    return result


class LEAPGeneratorV4(LEAPGenerator):
    """LEAP generator with auto-discovered case study sites.

    Overrides the site lookup to include all case study files found in
    examples/*_case_study.json, not just the hardcoded Cabo Pulmo and
    Shark Bay entries.
    """

    def __init__(self, project_root: Path | str | None = None) -> None:
        super().__init__(project_root)
        self._v4_case_files = _discover_case_study_files(self._root)

    def generate(self, site_name: str):
        """Generate TNFD LEAP disclosure for any discovered site.

        Uses the extended v4 case study mapping which includes all
        auto-discovered sites alongside the original two.
        """
        import json

        case_file = self._v4_case_files.get(site_name)
        if case_file is None:
            raise ValueError(
                f"No case study available for '{site_name}'. "
                f"Available sites: {list(self._v4_case_files.keys())}"
            )

        case_path = self._root / case_file
        with open(case_path) as f:
            case_data = json.load(f)

        axiom_path = self._root / "schemas" / "bridge_axiom_templates.json"
        with open(axiom_path) as f:
            axiom_data = json.load(f)

        return self.generate_from_data(site_name, case_data, axiom_data)

    @property
    def available_sites(self) -> list[str]:
        """Return all available site names for LEAP generation."""
        return list(self._v4_case_files.keys())


# Module-level convenience for the extended mapping
CASE_STUDY_FILES_V4 = _discover_case_study_files()
