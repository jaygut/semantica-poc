"""JSON-backed site registry for managing characterized MPA sites.

Provides CRUD operations, tier-based filtering, duplicate detection,
and export to case study JSON format.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from maris.sites.models import CharacterizationTier, SiteCharacterization

logger = logging.getLogger(__name__)


class SiteRegistry:
    """Manages a collection of characterized MPA sites persisted as JSON."""

    def __init__(self, registry_path: Path | str | None = None) -> None:
        self._path = Path(registry_path) if registry_path else None
        self._sites: dict[str, SiteCharacterization] = {}

        if self._path and self._path.exists():
            self._load()

    # -- CRUD -----------------------------------------------------------------

    def add_site(self, site: SiteCharacterization) -> None:
        """Add a site to the registry. Raises ValueError on duplicate."""
        key = self._key(site.canonical_name)
        if key in self._sites:
            raise ValueError(f"Site already exists: {site.canonical_name}")
        self._sites[key] = site
        self._save()

    def update_site(self, site: SiteCharacterization) -> None:
        """Update an existing site. Raises KeyError if not found."""
        key = self._key(site.canonical_name)
        if key not in self._sites:
            raise KeyError(f"Site not found: {site.canonical_name}")
        self._sites[key] = site
        self._save()

    def get_site(self, name: str) -> SiteCharacterization | None:
        """Get a site by name, or None if not found."""
        return self._sites.get(self._key(name))

    def remove_site(self, name: str) -> bool:
        """Remove a site by name. Returns True if removed, False if not found."""
        key = self._key(name)
        if key not in self._sites:
            return False
        del self._sites[key]
        self._save()
        return True

    def list_sites(self) -> list[SiteCharacterization]:
        """Return all sites ordered by canonical name."""
        return sorted(self._sites.values(), key=lambda s: s.canonical_name)

    def filter_by_tier(self, tier: CharacterizationTier) -> list[SiteCharacterization]:
        """Return sites at a specific characterization tier."""
        return [s for s in self._sites.values() if s.tier == tier]

    def count(self) -> int:
        return len(self._sites)

    def contains(self, name: str) -> bool:
        return self._key(name) in self._sites

    # -- Validation -----------------------------------------------------------

    def validate_site(self, site: SiteCharacterization) -> list[str]:
        """Validate a site against required fields for its tier. Returns issues."""
        issues: list[str] = []

        if not site.canonical_name:
            issues.append("Missing canonical_name")

        if site.tier in (CharacterizationTier.silver, CharacterizationTier.gold):
            if not site.habitats:
                issues.append(f"{site.tier.value} tier requires at least one habitat")
            if not site.ecosystem_services:
                issues.append(f"{site.tier.value} tier requires ecosystem services")

        if site.tier == CharacterizationTier.gold:
            if site.estimated_esv_usd is None:
                issues.append("Gold tier requires estimated ESV")
            if not site.species:
                issues.append("Gold tier requires species records")

        if site.coordinates:
            if not (-90 <= site.coordinates.latitude <= 90):
                issues.append("Latitude out of range [-90, 90]")
            if not (-180 <= site.coordinates.longitude <= 180):
                issues.append("Longitude out of range [-180, 180]")

        return issues

    # -- Export ---------------------------------------------------------------

    def export_site_json(self, name: str) -> dict[str, Any]:
        """Export a site as a case-study-compatible JSON dict."""
        site = self.get_site(name)
        if site is None:
            raise KeyError(f"Site not found: {name}")
        return site.model_dump(mode="json")

    def get_site_names(self) -> list[str]:
        """Return canonical names of all registered sites."""
        return [s.canonical_name for s in self.list_sites()]

    # -- Persistence ----------------------------------------------------------

    def _save(self) -> None:
        if self._path is None:
            return
        data = {
            "version": "1.0",
            "site_count": len(self._sites),
            "sites": {
                key: site.model_dump(mode="json")
                for key, site in self._sites.items()
            },
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load(self) -> None:
        if self._path is None or not self._path.exists():
            return
        with open(self._path) as f:
            data = json.load(f)
        for key, site_data in data.get("sites", {}).items():
            self._sites[key] = SiteCharacterization.model_validate(site_data)

    @staticmethod
    def _key(name: str) -> str:
        """Normalize a site name to a registry key."""
        return name.strip().lower().replace(" ", "_")
