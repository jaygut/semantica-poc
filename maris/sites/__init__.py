"""Multi-site scaling pipeline for MARIS.

Provides automated MPA characterization at three depth tiers (Bronze/Silver/Gold),
external API clients for marine data sources, ESV estimation via bridge axioms,
and a JSON-backed site registry for managing 30+ MPA sites.
"""

from maris.sites.models import (
    CharacterizationTier,
    CoordinatePair,
    EcosystemServiceEstimate,
    HabitatInfo,
    SiteCharacterization,
    SpeciesRecord,
)
from maris.sites.registry import SiteRegistry

__all__ = [
    "CharacterizationTier",
    "CoordinatePair",
    "EcosystemServiceEstimate",
    "HabitatInfo",
    "SiteCharacterization",
    "SiteRegistry",
    "SpeciesRecord",
]
