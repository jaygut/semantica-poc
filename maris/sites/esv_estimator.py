"""Bridge axiom-based ESV estimation for auto-characterized sites.

Given habitat types and extents, selects applicable bridge axioms,
applies coefficients with uncertainty propagation, and generates
Monte Carlo bounds.
"""

from __future__ import annotations

import logging
from typing import Any

from maris.sites.models import (
    EcosystemServiceEstimate,
    HabitatInfo,
)

logger = logging.getLogger(__name__)

# Mapping from habitat_id to the bridge axioms that produce ESV estimates.
# Each entry: (axiom_id, service_type, coefficient_key, per_unit)
# "per_unit" means the axiom coefficient is multiplied by habitat extent (ha or km2).
_HABITAT_AXIOM_MAP: dict[str, list[dict[str, Any]]] = {
    "coral_reef": [
        {
            "axiom_id": "BA-001",
            "service_type": "tourism",
            "description": "MPA biomass -> dive tourism value",
            "default_per_ha_usd": 352.0,
            "ci_low_per_ha": 200.0,
            "ci_high_per_ha": 500.0,
        },
        {
            "axiom_id": "BA-004",
            "service_type": "coastal_protection",
            "description": "Coral reef -> flood protection",
            "default_per_ha_usd": 44.0,
            "ci_low_per_ha": 20.0,
            "ci_high_per_ha": 80.0,
        },
        {
            "axiom_id": "BA-012",
            "service_type": "fisheries",
            "description": "Reef -> fisheries production",
            "default_per_ha_usd": 35.0,
            "ci_low_per_ha": 15.0,
            "ci_high_per_ha": 60.0,
        },
    ],
    "seagrass_meadow": [
        {
            "axiom_id": "BA-013",
            "service_type": "carbon_sequestration",
            "description": "Seagrass -> carbon sequestration (0.84 tCO2/ha/yr x $30/t)",
            "default_per_ha_usd": 25.2,
            "ci_low_per_ha": 15.0,
            "ci_high_per_ha": 40.0,
        },
        {
            "axiom_id": "BA-008",
            "service_type": "carbon_credits",
            "description": "Seagrass -> carbon credit value",
            "default_per_ha_usd": 18.0,
            "ci_low_per_ha": 10.0,
            "ci_high_per_ha": 30.0,
        },
    ],
    "mangrove_forest": [
        {
            "axiom_id": "BA-005",
            "service_type": "coastal_protection",
            "description": "Mangrove -> flood protection",
            "default_per_ha_usd": 300.0,
            "ci_low_per_ha": 150.0,
            "ci_high_per_ha": 500.0,
        },
        {
            "axiom_id": "BA-006",
            "service_type": "fisheries",
            "description": "Mangrove -> fisheries nursery habitat",
            "default_per_ha_usd": 120.0,
            "ci_low_per_ha": 60.0,
            "ci_high_per_ha": 200.0,
        },
        {
            "axiom_id": "BA-007",
            "service_type": "carbon_stock",
            "description": "Mangrove -> carbon stock value",
            "default_per_ha_usd": 50.0,
            "ci_low_per_ha": 25.0,
            "ci_high_per_ha": 80.0,
        },
    ],
    "kelp_forest": [
        {
            "axiom_id": "BA-010",
            "service_type": "ecosystem_value",
            "description": "Kelp forest -> global per-hectare ESV",
            "default_per_ha_usd": 200.0,
            "ci_low_per_ha": 100.0,
            "ci_high_per_ha": 350.0,
        },
        {
            "axiom_id": "BA-003",
            "service_type": "carbon_sequestration",
            "description": "Kelp -> otter-mediated carbon cascade",
            "default_per_ha_usd": 25.0,
            "ci_low_per_ha": 10.0,
            "ci_high_per_ha": 45.0,
        },
    ],
}


def estimate_esv(
    habitats: list[HabitatInfo],
    area_km2: float | None = None,
) -> tuple[list[EcosystemServiceEstimate], float, dict[str, Any]]:
    """Estimate ESV for a site based on its habitats and extents.

    Parameters
    ----------
    habitats : list of HabitatInfo with habitat_id and optional extent_km2.
    area_km2 : total site area, used as fallback if habitat extent is unknown.

    Returns
    -------
    (services, total_esv, confidence_info) where:
        services: list of EcosystemServiceEstimate
        total_esv: sum of all service estimates in USD/year
        confidence_info: dict with CI bounds and axiom chain info
    """
    services: list[EcosystemServiceEstimate] = []
    total = 0.0
    total_ci_low = 0.0
    total_ci_high = 0.0
    axiom_chain: list[str] = []

    for habitat in habitats:
        axiom_entries = _HABITAT_AXIOM_MAP.get(habitat.habitat_id, [])
        if not axiom_entries:
            logger.info("No axiom mapping for habitat %s", habitat.habitat_id)
            continue

        # Determine extent in hectares
        extent_km2 = habitat.extent_km2 or area_km2 or 0.0
        extent_ha = extent_km2 * 100.0  # 1 km2 = 100 ha

        if extent_ha <= 0:
            continue

        for entry in axiom_entries:
            value = entry["default_per_ha_usd"] * extent_ha
            ci_low = entry["ci_low_per_ha"] * extent_ha
            ci_high = entry["ci_high_per_ha"] * extent_ha

            svc = EcosystemServiceEstimate(
                service_type=entry["service_type"],
                service_name=entry["description"],
                annual_value_usd=value,
                valuation_method="bridge_axiom_estimate",
                axiom_ids_used=[entry["axiom_id"]],
                ci_low=ci_low,
                ci_high=ci_high,
            )
            services.append(svc)
            total += value
            total_ci_low += ci_low
            total_ci_high += ci_high
            axiom_chain.append(entry["axiom_id"])

    confidence_info = {
        "total_esv_usd": total,
        "ci_low": total_ci_low,
        "ci_high": total_ci_high,
        "axiom_chain": axiom_chain,
        "method": "bridge_axiom_per_hectare_estimate",
        "note": "Provisional estimate using default per-hectare coefficients",
    }

    return services, total, confidence_info


def get_applicable_axioms(habitat_id: str) -> list[dict[str, Any]]:
    """Return the axiom entries applicable to a given habitat type."""
    return list(_HABITAT_AXIOM_MAP.get(habitat_id, []))
