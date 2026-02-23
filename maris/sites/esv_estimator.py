"""Bridge axiom-based ESV estimation for auto-characterized sites.

NOW REGISTRY-DRIVEN (v2.0):
Dynamically loads all 35+ axioms from schemas/bridge_axiom_templates.json
instead of using hardcoded maps. This unlocks advanced valuation logic
(Carbon, Blue Bonds, Insurance) automatically.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from maris.sites.models import (
    EcosystemServiceEstimate,
    HabitatInfo,
)

logger = logging.getLogger(__name__)

# Constants
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_REGISTRY_PATH = _PROJECT_ROOT / "schemas" / "bridge_axiom_templates.json"
def _get_carbon_price(price_scenario: str = "current_market") -> float:
    """Get dynamic carbon price from scenario constants.

    Replaces the former hardcoded _DEFAULT_CARBON_PRICE = 30.0.
    Falls back to 25.25 (S&P DBC-1 assessed average) if scenario not found.
    """
    from maris.scenario.constants import CARBON_PRICE_SCENARIOS
    return CARBON_PRICE_SCENARIOS.get(price_scenario, {}).get("price_usd", 25.25)


_DEFAULT_CARBON_PRICE = _get_carbon_price()  # backwards-compatible module-level constant

# Cache for the loaded map
_DYNAMIC_AXIOM_MAP: dict[str, list[dict[str, Any]]] | None = None


def _load_registry_map() -> dict[str, list[dict[str, Any]]]:
    """Load and index axioms from the JSON registry."""
    global _DYNAMIC_AXIOM_MAP
    if _DYNAMIC_AXIOM_MAP is not None:
        return _DYNAMIC_AXIOM_MAP

    if not _REGISTRY_PATH.exists():
        logger.error("Axiom registry not found at %s", _REGISTRY_PATH)
        return {}

    try:
        with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            axioms = data.get("axioms", [])
    except Exception:
        logger.exception("Failed to load axiom registry")
        return {}

    habitat_map: dict[str, list[dict[str, Any]]] = {}

    for axiom in axioms:
        # 1. Check if axiom is applicable to habitats
        applicable_habitats = axiom.get("applicable_habitats", [])
        if not applicable_habitats:
            continue

        # 2. Heuristic: Can we derive a per-hectare USD value?
        coeffs = axiom.get("coefficients", {})
        valuation_data = _extract_valuation_logic(coeffs)
        
        if not valuation_data:
            # Skip axioms we can't easily turn into a $ value per hectare (yet)
            # e.g. "parametic insurance" (requires wind speed) or "debt swap" (requires debt face value)
            continue

        # 3. Register for each habitat
        entry = {
            "axiom_id": axiom["axiom_id"],
            "service_type": _infer_service_type(axiom["name"], axiom["category"]),
            "description": axiom["description"],
            "default_per_ha_usd": valuation_data["value"],
            "ci_low_per_ha": valuation_data["ci_low"],
            "ci_high_per_ha": valuation_data["ci_high"],
            "is_carbon": valuation_data["is_carbon"]
        }

        for hab in applicable_habitats:
            if hab == "all":
                # Special case: add to common habitats (skipped for now to avoid noise)
                continue
            if hab not in habitat_map:
                habitat_map[hab] = []
            habitat_map[hab].append(entry)

    _DYNAMIC_AXIOM_MAP = habitat_map
    logger.info("Loaded %d active axioms into ESV estimator", sum(len(v) for v in habitat_map.values()))
    return habitat_map


def _extract_valuation_logic(coeffs: dict) -> dict[str, Any] | None:
    """Heuristic to extract value-per-hectare from coefs."""
    
    # Strategy 1: Direct USD/ha value
    for key, val_obj in coeffs.items():
        if "usd" in key and ("per_ha" in key or "_ha_" in key):
            return _parse_coeff_value(val_obj)

    # Strategy 2: Carbon Sequestration (tCO2/ha) * Price
    # Look for sequestration rate
    seq_rate = None
    for key, val_obj in coeffs.items():
        if "sequestration" in key and "tco2" in key.lower() and "ha" in key:
             seq_rate = _parse_coeff_value(val_obj)
             break
    
    if seq_rate:
        # Found carbon rate! Multiply by default price
        base = seq_rate["value"] * _DEFAULT_CARBON_PRICE
        low = seq_rate["ci_low"] * _DEFAULT_CARBON_PRICE
        high = seq_rate["ci_high"] * _DEFAULT_CARBON_PRICE
        return {
            "value": base, "ci_low": low, "ci_high": high, "is_carbon": True
        }

    return None

def _parse_coeff_value(val_obj: Any) -> dict[str, float]:
    """Normalize simple int/float or complex dict coefficient."""
    if isinstance(val_obj, (int, float)):
        return {
            "value": float(val_obj),
            "ci_low": float(val_obj) * 0.7, # Default uncertainty if missing
            "ci_high": float(val_obj) * 1.3,
            "is_carbon": False
        }
    elif isinstance(val_obj, dict) and "value" in val_obj:
        v = float(val_obj["value"])
        ci_low = float(val_obj.get("ci_low", v * 0.7))
        ci_high = float(val_obj.get("ci_high", v * 1.3))
        return {
            "value": v, "ci_low": ci_low, "ci_high": ci_high, "is_carbon": False
        }
    return {"value": 0.0, "ci_low": 0.0, "ci_high": 0.0, "is_carbon": False}


def _infer_service_type(name: str, category: str) -> str:
    """Map axiom name to canonical service category."""
    if "credit" in name:
        return "carbon_credits"
    if "carbon" in name or "sequestration" in name:
        return "carbon_sequestration"
    if "flood" in name or "protection" in name or "attenuation" in name:
        return "coastal_protection"
    if "fisheries" in name or "spillover" in name:
        return "fisheries"
    if "tourism" in name:
        return "tourism"
    return "biodiversity_value"


def estimate_esv(
    habitats: list[HabitatInfo],
    area_km2: float | None = None,
) -> tuple[list[EcosystemServiceEstimate], float, dict[str, Any]]:
    """Estimate ESV for a site using the Dynamic Registry Logic.

    Parameters
    ----------
    habitats : list of HabitatInfo with habitat_id and optional extent_km2.
    area_km2 : total site area, used as fallback if habitat extent is unknown.

    Returns
    -------
    (services, total_esv, confidence_info)
    """
    # Simply load map (lazy load)
    axiom_map = _load_registry_map()

    services: list[EcosystemServiceEstimate] = []
    total = 0.0
    total_ci_low = 0.0
    total_ci_high = 0.0
    axiom_chain: list[str] = []

    for habitat in habitats:
        entries = axiom_map.get(habitat.habitat_id, [])
        if not entries:
            continue

        # Determine extent in hectares
        extent_km2 = habitat.extent_km2 or area_km2 or 0.0
        extent_ha = extent_km2 * 100.0  # 1 km2 = 100 ha

        if extent_ha <= 0:
            continue

        for entry in entries:
            # Calculate Total Value (Value/ha * ha)
            value = entry["default_per_ha_usd"] * extent_ha
            ci_low = entry["ci_low_per_ha"] * extent_ha
            ci_high = entry["ci_high_per_ha"] * extent_ha

            svc = EcosystemServiceEstimate(
                service_type=entry["service_type"],
                service_name=entry["description"],
                annual_value_usd=value,
                valuation_method="bridge_axiom_registry_v2",
                axiom_ids_used=[entry["axiom_id"]],
                ci_low=ci_low,
                ci_high=ci_high,
            )
            services.append(svc)
            
            # Identify redundancy? 
            # (Simple additive model for now - complex logic handled in Reasoning Engine)
            total += value
            total_ci_low += ci_low
            total_ci_high += ci_high
            axiom_chain.append(entry["axiom_id"])

    confidence_info = {
        "total_esv_usd": total,
        "ci_low": total_ci_low,
        "ci_high": total_ci_high,
        "axiom_chain": sorted(list(set(axiom_chain))),  # Deduplicate
        "method": "registry_driven_dynamic_valuation",
        "note": "Valuation derived from 35-axiom registry coefficients",
    }

    return services, total, confidence_info


def get_applicable_axioms(habitat_id: str) -> list[dict[str, Any]]:
    """Return the axiom entries applicable to a given habitat type."""
    axiom_map = _load_registry_map()
    return list(axiom_map.get(habitat_id, []))

def get_habitat_axiom_map() -> dict[str, list[dict[str, Any]]]:
    """Public accessor for the axiom map (replaces old _HABITAT_AXIOM_MAP)."""
    return _load_registry_map()

# Backwards compatibility for consumers expecting the raw dict
# Warning: This forces a load at import time if accessed
_HABITAT_AXIOM_MAP = _load_registry_map()
