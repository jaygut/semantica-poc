"""Dynamic axiom display registry - reads directly from bridge_axiom_templates.json.

Replaces the hardcoded ``AXIOM_INFO`` dict in intelligence_brief.py and the
hardcoded ``_AXIOM_DISPLAY`` dict in site_intelligence.py.

All 40 axioms (BA-001 through BA-040) are available automatically. When new
axioms are added to the JSON file they appear in the dashboard immediately on
the next API/app restart - no code changes required.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from maris.axioms.engine import BridgeAxiomEngine  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton - loaded once on first import
# ---------------------------------------------------------------------------

_engine: BridgeAxiomEngine | None = None


def _get_engine() -> BridgeAxiomEngine:
    global _engine
    if _engine is None:
        _engine = BridgeAxiomEngine()
        logger.info(
            "axiom_registry: loaded %d axioms from bridge_axiom_templates.json",
            len(_engine.list_all()),
        )
    return _engine


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _human_name(snake: str) -> str:
    """Convert a snake_case axiom name to a Title Case display label.

    Example: 'mpa_biomass_dive_tourism_value' -> 'Mpa Biomass Dive Tourism Value'
    Handles the common '_to_' connector: 'ecological_to_service' stays readable.
    """
    return snake.replace("_", " ").title()


def _coefficient_summary(coefficients: dict) -> str:
    """Return a short human-readable string for the primary (first) coefficient.

    Formats based on ``effect_size_type``:
        percent_change  -> "84% change"
        ratio           -> "6.7x ratio"
        usd_value       -> "$1,200" / "$500M" / "$272B"
        rate            -> "0.84/yr"
        mass            -> "1023 Mg C/ha"
        count           -> "n=200000"
    Falls back to the raw value for any unrecognised type.
    Returns empty string if no numeric coefficient is found.
    """
    for _coeff_name, coeff in coefficients.items():
        if not isinstance(coeff, dict) or "value" not in coeff:
            continue
        val = coeff.get("value")
        est = coeff.get("effect_size_type", "")
        if val is None:
            continue
        try:
            if est == "percent_change":
                return f"{val}% change"
            elif est == "ratio":
                return f"{val}x ratio"
            elif est == "usd_value":
                fval = float(val)
                if fval >= 1_000_000_000:
                    return f"${fval / 1e9:.1f}B"
                elif fval >= 1_000_000:
                    return f"${fval / 1e6:.0f}M"
                elif fval >= 1_000:
                    return f"${fval:,.0f}"
                else:
                    return f"${fval:.2f}"
            elif est == "rate":
                return f"{val:.2g}/yr"
            elif est == "mass":
                return f"{val:g} Mg C/ha"
            elif est == "count":
                return f"n={int(val)}"
            elif est == "area":
                return f"{val} km²"
            else:
                return str(val)
        except (TypeError, ValueError):
            return str(val)
    return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_axiom_display(axiom_id: str) -> dict:
    """Return display metadata for a single axiom, read live from the registry.

    The returned dict is **backwards-compatible** with the old hardcoded
    ``AXIOM_INFO`` (intelligence_brief.py) and ``_AXIOM_DISPLAY``
    (site_intelligence.py) entries:

    Key            | intelligence_brief usage  | site_intelligence usage
    ---------------|---------------------------|-------------------------
    meaning        | AXIOM_INFO['meaning']     | -
    citation       | AXIOM_INFO['citation']    | -
    doi            | AXIOM_INFO['doi']         | -
    name           | -                         | _AXIOM_DISPLAY['name']
    translation    | -                         | _AXIOM_DISPLAY['translation']
    coefficient    | -                         | _AXIOM_DISPLAY['coefficient']

    Additional keys available for richer display:
        all_sources   - list of all source dicts [{citation, doi, finding}]
        category      - axiom category string
        evidence_tier - T1/T2/T3/T4
        caveats       - list of caveat strings
        pattern       - IF-THEN logic pattern
        description   - full plain-English description (same as 'meaning')

    Returns an empty dict if the axiom_id is not found.
    """
    engine = _get_engine()
    axiom = engine.get_axiom(axiom_id)
    if not axiom:
        logger.warning("axiom_registry: unknown axiom_id %r", axiom_id)
        return {}

    sources = axiom.get("sources", [])
    primary_source = sources[0] if sources else {}
    coefficients = axiom.get("coefficients", {})
    description = axiom.get("description", "")

    return {
        # intelligence_brief.py compatibility
        "meaning": description,
        "citation": primary_source.get("citation", ""),
        "doi": primary_source.get("doi", ""),
        # site_intelligence.py compatibility
        "name": _human_name(axiom.get("name", axiom_id)),
        "translation": description,
        "coefficient": _coefficient_summary(coefficients),
        # extended fields for richer display
        "description": description,
        "all_sources": sources,
        "category": axiom.get("category", ""),
        "evidence_tier": axiom.get("evidence_tier", ""),
        "caveats": axiom.get("caveats", []),
        "pattern": axiom.get("pattern", ""),
        "applicable_habitats": axiom.get("applicable_habitats", []),
    }


def get_total_axiom_count() -> int:
    """Return the number of axioms currently in bridge_axiom_templates.json."""
    return len(_get_engine().list_all())


def get_all_axiom_display() -> dict[str, dict]:
    """Return a dict of {axiom_id: display_metadata} for all axioms.

    Useful when a component needs to display all axioms (e.g. a full axiom
    catalogue tab) rather than looking up by individual ID.
    """
    engine = _get_engine()
    return {axiom["axiom_id"]: get_axiom_display(axiom["axiom_id"]) for axiom in engine.list_all()}
