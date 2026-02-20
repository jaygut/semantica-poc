"""Tipping point analyzer for non-linear ESV response at ecological thresholds.

Implements the McClanahan et al. 2011 piecewise function mapping fish biomass
to reef ecosystem function fraction, plus site-level tipping point reports.

Reference: McClanahan et al. 2011 (doi:10.1073/pnas.1106861108)
"""

from __future__ import annotations

import pathlib

from maris.scenario.constants import BIOMASS_THRESHOLDS

# Pre-protection biomass baseline for overfished reefs (kg/ha)
# Aburto-Oropeza et al. 2011 (doi:10.1371/journal.pone.0023601)
_DEFAULT_PRE_PROTECTION_BIOMASS_KG_HA = 200.0

_EXAMPLES_DIR = pathlib.Path(__file__).resolve().parent.parent.parent / "examples"


def compute_reef_function(biomass_kg_ha: float) -> float:
    """Piecewise function mapping fish biomass to reef ecosystem function fraction.

    Based on McClanahan et al. 2011 (doi:10.1073/pnas.1106861108).
    Returns value in [0.0, 1.0].

    Thresholds (kg/ha):
        1500+ -> 1.00 (pristine)
        1130  -> 0.90 (warning)
        600   -> 0.65 (mmsy_upper)
        300   -> 0.30 (mmsy_lower)
        150   -> 0.05 (collapse)
        <150  -> approaches 0
    """
    if biomass_kg_ha >= 1130:
        return 0.90 + 0.10 * min((biomass_kg_ha - 1130) / 370, 1.0)
    elif biomass_kg_ha >= 600:
        return 0.65 + 0.25 * (biomass_kg_ha - 600) / 530
    elif biomass_kg_ha >= 300:
        return 0.30 + 0.35 * (biomass_kg_ha - 300) / 300
    elif biomass_kg_ha >= 150:
        return 0.05 + 0.25 * (biomass_kg_ha - 150) / 150
    else:
        return max(0.005, 0.05 * biomass_kg_ha / 150)


def get_threshold_proximity(biomass_kg_ha: float) -> str:
    """Return human-readable tipping point proximity description.

    Identifies nearest threshold and computes headroom or deficit.
    """
    thresholds = [
        ("collapse", 150),
        ("mmsy_lower", 300),
        ("mmsy_upper", 600),
        ("warning", 1130),
        ("pristine", 1500),
    ]

    current_rf = compute_reef_function(biomass_kg_ha)

    # Find nearest lower threshold
    lower_threshold = None
    for name, kg in thresholds:
        if biomass_kg_ha >= kg:
            lower_threshold = (name, kg)
        else:
            break

    if lower_threshold is None:
        return (
            f"CRITICAL: Biomass {biomass_kg_ha:.0f} kg/ha is below collapse "
            f"threshold (150 kg/ha). Reef function at {current_rf:.1%}."
        )

    lower_name, lower_kg = lower_threshold

    if lower_name == "pristine":
        return (
            f"Pristine condition: biomass {biomass_kg_ha:.0f} kg/ha is above "
            f"all thresholds. Reef function at {current_rf:.1%}."
        )

    headroom_pct = ((biomass_kg_ha - lower_kg) / lower_kg) * 100

    # Find next lower threshold
    next_lower = None
    for name, kg in reversed(thresholds):
        if kg < lower_kg:
            next_lower = (name, kg)
            break

    if next_lower is not None:
        next_name, next_kg = next_lower
        buffer_pct = ((biomass_kg_ha - next_kg) / next_kg) * 100
        return (
            f"Biomass {biomass_kg_ha:.0f} kg/ha is in the '{lower_name}' zone "
            f"({lower_kg} kg/ha). {headroom_pct:.0f}% above '{lower_name}' threshold. "
            f"Reef function at {current_rf:.1%}. "
            f"Next lower threshold: '{next_name}' at {next_kg} kg/ha "
            f"({buffer_pct:.0f}% headroom)."
        )

    return (
        f"Biomass {biomass_kg_ha:.0f} kg/ha is in the '{lower_name}' zone "
        f"({lower_kg} kg/ha). {headroom_pct:.0f}% above threshold. "
        f"Reef function at {current_rf:.1%}."
    )


def get_tipping_point_site_report(site_data: dict) -> dict:
    """Generate a tipping point report for a given site's case study JSON.

    For coral reef sites, computes current biomass from biomass_multiplier
    and a pre-protection baseline, then evaluates proximity to McClanahan
    thresholds.

    Returns:
        dict with: current_biomass_kg_ha, nearest_threshold, headroom_pct,
        reef_function_current, esv_at_next_threshold, esv_at_collapse,
        habitat_type, site_name. Returns non-applicable dict for non-reef sites.
    """
    habitat = (
        site_data.get("ecological_status", {}).get("primary_habitat", "")
    )

    site_name = site_data.get("site", {}).get("name", "Unknown")

    if habitat != "coral_reef":
        return {
            "site_name": site_name,
            "habitat_type": habitat,
            "applicable": False,
            "reason": "Tipping point analysis applies to coral reef sites only",
        }

    recovery = site_data.get("ecological_recovery", {})
    metrics = recovery.get("metrics", {})
    fish_biomass = metrics.get("fish_biomass", {})
    biomass_ratio = fish_biomass.get("recovery_ratio")

    if biomass_ratio is None:
        return {
            "site_name": site_name,
            "habitat_type": habitat,
            "applicable": False,
            "reason": "No biomass_multiplier data available",
        }

    pre_protection = _DEFAULT_PRE_PROTECTION_BIOMASS_KG_HA
    current_biomass = pre_protection * float(biomass_ratio)
    current_rf = compute_reef_function(current_biomass)

    threshold_names = ["collapse", "mmsy_lower", "mmsy_upper", "warning", "pristine"]
    threshold_values = [
        BIOMASS_THRESHOLDS[t]["kg_ha"] for t in threshold_names
    ]

    nearest_lower_name = None
    nearest_lower_kg = 0
    for name, kg in zip(threshold_names, threshold_values):
        if current_biomass >= kg:
            nearest_lower_name = name
            nearest_lower_kg = kg

    headroom_pct = (
        ((current_biomass - nearest_lower_kg) / nearest_lower_kg) * 100
        if nearest_lower_kg > 0
        else 0
    )

    # Find next lower threshold
    next_lower_kg = None
    for name, kg in reversed(list(zip(threshold_names, threshold_values))):
        if kg < nearest_lower_kg:
            next_lower_kg = kg
            break

    total_esv = site_data.get("ecosystem_services", {}).get("total_annual_value_usd", 0)

    def _esv_at_biomass(target_biomass: float) -> float:
        target_rf = compute_reef_function(target_biomass)
        scale = target_rf / current_rf if current_rf > 0 else 0
        return total_esv * scale

    esv_at_collapse = _esv_at_biomass(150)
    esv_at_next_threshold = (
        _esv_at_biomass(next_lower_kg) if next_lower_kg else None
    )

    proximity_msg = get_threshold_proximity(current_biomass)

    return {
        "site_name": site_name,
        "habitat_type": habitat,
        "applicable": True,
        "current_biomass_kg_ha": round(current_biomass, 1),
        "biomass_multiplier": float(biomass_ratio),
        "nearest_threshold": {
            "name": nearest_lower_name,
            "kg_ha": nearest_lower_kg,
        },
        "headroom_pct": round(headroom_pct, 1),
        "reef_function_current": round(current_rf, 4),
        "esv_current": total_esv,
        "esv_at_next_threshold": round(esv_at_next_threshold, 0) if esv_at_next_threshold else None,
        "esv_at_collapse": round(esv_at_collapse, 0),
        "proximity_description": proximity_msg,
        "source_doi": "10.1073/pnas.1106861108",
    }
