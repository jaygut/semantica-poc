"""Blue carbon revenue computation for mangrove and seagrass sites.

Computes annual blue carbon credit revenue based on habitat area,
sequestration rates from peer-reviewed literature, and carbon price
scenarios from the voluntary carbon market.

Sources:
- Blue Carbon Initiative global rates
- Sani et al. 2022 (doi:10.1038/s41598-022-11716-5) for Sundarbans
- S&P Global Commodity Insights DBC-1 for carbon prices
- Verra VCS Vida Manglar actuals for Cispata Bay validation
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from maris.scenario.constants import (
    BLUE_CARBON_SEQUESTRATION,
    CARBON_PRICE_SCENARIOS,
)

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_EXAMPLES_DIR = _PROJECT_ROOT / "examples"

# Mapping from site primary_habitat to sequestration key in constants
_HABITAT_SEQ_KEY: dict[str, str] = {
    "mangrove_forest": "mangrove_global",
    "seagrass_meadow": "seagrass_global",
}

# Sundarbans gets site-specific higher sequestration rates
_SITE_SEQ_OVERRIDE: dict[str, str] = {
    "Sundarbans Reserve Forest": "mangrove_sundarbans",
}


def _detect_habitat_and_area(site_data: dict) -> tuple[str, float]:
    """Detect the primary blue carbon habitat type and its area in hectares.

    Searches ecological_status.primary_habitat first, then falls back to
    site-level fields (mangrove_extent_ha, seagrass_extent_km2).

    Returns (habitat_type, area_ha) or ("unknown", 0.0) if not found.
    """
    eco = site_data.get("ecological_status", {})
    primary_habitat = eco.get("primary_habitat", "")
    site = site_data.get("site", {})

    # Mangrove sites
    if primary_habitat == "mangrove_forest":
        # Prefer vida_manglar_project_ha for Cispata (VCS credit area)
        vida_ha = site.get("vida_manglar_project_ha")
        if vida_ha:
            return "mangrove_forest", float(vida_ha)
        # Then mangrove_extent_ha
        mangrove_ha = site.get("mangrove_extent_ha")
        if mangrove_ha:
            return "mangrove_forest", float(mangrove_ha)
        # Then mangrove_extent_km2 converted to ha
        mangrove_km2 = site.get("mangrove_extent_km2")
        if mangrove_km2:
            return "mangrove_forest", float(mangrove_km2) * 100.0
        # Fallback to area_km2
        area_km2 = site.get("area_km2", 0)
        return "mangrove_forest", float(area_km2) * 100.0

    # Seagrass sites
    if primary_habitat == "seagrass_meadow":
        seagrass_km2 = site.get("seagrass_extent_km2")
        if seagrass_km2:
            return "seagrass_meadow", float(seagrass_km2) * 100.0
        area_km2 = site.get("area_km2", 0)
        return "seagrass_meadow", float(area_km2) * 100.0

    # Coral reef sites may have mangrove components (e.g., Belize, Aldabra)
    # Check bridge_axiom_applications for mangrove_area references
    baa = site_data.get("bridge_axiom_applications", [])
    for ba in baa:
        calc = ba.get("calculation", {})
        mangrove_ha = calc.get("mangrove_area_ha")
        if mangrove_ha:
            return "mangrove_forest", float(mangrove_ha)
        mangrove_km2 = calc.get("mangrove_area_km2")
        if mangrove_km2:
            return "mangrove_forest", float(mangrove_km2) * 100.0

    return "unknown", 0.0


def compute_blue_carbon_revenue(
    site_name: str,
    site_data: dict,
    price_scenario: str = "current_market",
    target_year: int = 2030,
    verra_verified_fraction: float = 0.60,
) -> dict:
    """Compute annual blue carbon credit revenue for a site.

    Parameters
    ----------
    site_name : str
        Display name of the site.
    site_data : dict
        Full case study JSON data for the site.
    price_scenario : str
        Key into CARBON_PRICE_SCENARIOS from constants.py.
        One of: conservative, current_market, premium, 2030_projection, high_integrity.
    target_year : int
        Target year for the projection (informational).
    verra_verified_fraction : float
        Fraction of gross sequestration that achieves VCS verification.
        Default 0.60 is conservative. Cispata Bay actuals imply ~0.44.

    Returns
    -------
    dict with: site_name, price_scenario, price_usd, habitat_area_ha,
    seq_rate_tco2_ha_yr (mid), annual_credits, annual_revenue_usd,
    annual_revenue_range (low/high), target_year, habitat_type.

    Validation anchor (Cispata Bay at $15/credit, 0.60 verified):
    7,500 ha * 7.0 tCO2/ha/yr * 0.60 * $15 = $472,500
    Range: [7500*6*0.60*15, 7500*8*0.60*15] = [$405K, $540K]
    Vida Manglar actuals: ~$300K first issuance at 0.44 fraction.
    """
    habitat_type, area_ha = _detect_habitat_and_area(site_data)

    if habitat_type == "unknown" or area_ha <= 0:
        return {
            "site_name": site_name,
            "error": "no_blue_carbon_habitat_detected",
            "habitat_type": habitat_type,
            "habitat_area_ha": area_ha,
        }

    # Get carbon price
    price_info = CARBON_PRICE_SCENARIOS.get(price_scenario, CARBON_PRICE_SCENARIOS["current_market"])
    price_usd = price_info["price_usd"]

    # Get sequestration rate - check for site-specific override first
    seq_key = _SITE_SEQ_OVERRIDE.get(site_name, _HABITAT_SEQ_KEY.get(habitat_type, ""))
    seq_data = BLUE_CARBON_SEQUESTRATION.get(seq_key)

    if seq_data is None:
        return {
            "site_name": site_name,
            "error": f"no_sequestration_data_for_{habitat_type}",
            "habitat_type": habitat_type,
            "habitat_area_ha": area_ha,
        }

    seq_low = seq_data["tco2_ha_yr_low"]
    seq_high = seq_data["tco2_ha_yr_high"]
    seq_mid = (seq_low + seq_high) / 2.0

    # Compute annual credits and revenue
    annual_credits_mid = area_ha * seq_mid * verra_verified_fraction
    annual_credits_low = area_ha * seq_low * verra_verified_fraction
    annual_credits_high = area_ha * seq_high * verra_verified_fraction

    annual_revenue = annual_credits_mid * price_usd
    annual_revenue_low = annual_credits_low * price_usd
    annual_revenue_high = annual_credits_high * price_usd

    return {
        "site_name": site_name,
        "price_scenario": price_scenario,
        "price_usd": price_usd,
        "habitat_type": habitat_type,
        "habitat_area_ha": area_ha,
        "seq_rate_tco2_ha_yr": seq_mid,
        "seq_rate_low": seq_low,
        "seq_rate_high": seq_high,
        "verra_verified_fraction": verra_verified_fraction,
        "annual_credits": annual_credits_mid,
        "annual_revenue_usd": annual_revenue,
        "annual_revenue_range": {
            "low": annual_revenue_low,
            "high": annual_revenue_high,
        },
        "target_year": target_year,
        "source": seq_data.get("source", "Blue Carbon Initiative"),
    }


def load_site_data(site_json_path: str | Path) -> dict:
    """Load a case study JSON file."""
    with open(site_json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_portfolio_blue_carbon(
    price_scenario: str = "current_market",
    target_year: int = 2030,
    verra_verified_fraction: float = 0.60,
) -> dict:
    """Compute blue carbon revenue for all sites in the portfolio.

    Returns dict with per-site results and portfolio totals.
    """
    results: dict[str, dict] = {}
    total_revenue = 0.0
    total_revenue_low = 0.0
    total_revenue_high = 0.0

    for json_path in sorted(_EXAMPLES_DIR.glob("*_case_study.json")):
        site_data = load_site_data(json_path)
        site_name = site_data.get("site", {}).get("name", json_path.stem)

        result = compute_blue_carbon_revenue(
            site_name=site_name,
            site_data=site_data,
            price_scenario=price_scenario,
            target_year=target_year,
            verra_verified_fraction=verra_verified_fraction,
        )
        results[site_name] = result

        if "error" not in result:
            total_revenue += result["annual_revenue_usd"]
            rev_range = result["annual_revenue_range"]
            total_revenue_low += rev_range["low"]
            total_revenue_high += rev_range["high"]

    return {
        "sites": results,
        "portfolio_total_revenue_usd": total_revenue,
        "portfolio_revenue_range": {
            "low": total_revenue_low,
            "high": total_revenue_high,
        },
        "price_scenario": price_scenario,
        "target_year": target_year,
    }
