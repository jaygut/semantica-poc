"""
Scenario intelligence constants.
All values sourced from peer-reviewed literature or verified market data.
"""

# IPCC AR6 WG2 Ch.3 + Nature 2025 (doi:10.1038/s41586-025-09439-4)
SSP_SCENARIOS: dict[str, dict] = {
    "SSP1-2.6": {
        "label": "Low emissions (Paris-aligned, 1.8C by 2100)",
        "warming_2100_c": 1.8,
        "sea_level_rise_m_range": (0.32, 0.62),
        "coral_loss_pct_by_2050": (30, 50),
        "coral_loss_pct_by_2100": (70, 90),
        "mangrove_sea_level_risk": "low_moderate",
    },
    "SSP2-4.5": {
        "label": "Intermediate (current trajectory, 2.7C by 2100)",
        "warming_2100_c": 2.7,
        "sea_level_rise_m_range": (0.44, 0.76),
        "coral_loss_pct_by_2050": (50, 70),
        "coral_loss_pct_by_2100": (90, 99),
        "mangrove_sea_level_risk": "moderate",
    },
    "SSP5-8.5": {
        "label": "Very high emissions (4.4C by 2100)",
        "warming_2100_c": 4.4,
        "sea_level_rise_m_range": (0.63, 1.88),
        "coral_loss_pct_by_2050": (70, 90),
        "coral_loss_pct_by_2100": (99, 100),
        "mangrove_sea_level_risk": "high",
    },
}

# McClanahan et al. 2011 (doi:10.1073/pnas.1106861108)
# Fish biomass thresholds in kg/ha where ecosystem metrics undergo discontinuous change
BIOMASS_THRESHOLDS: dict[str, dict] = {
    "pristine":   {"kg_ha": 1500, "reef_function_pct": 1.00, "label": "Pristine/fully protected"},
    "warning":    {"kg_ha": 1130, "reef_function_pct": 0.90, "label": "Early warning - macroalgal variance increasing"},
    "mmsy_upper": {"kg_ha": 600,  "reef_function_pct": 0.65, "label": "Upper sustainable yield (B_MMSY upper)"},
    "mmsy_lower": {"kg_ha": 300,  "reef_function_pct": 0.30, "label": "Multiple metrics degrading simultaneously"},
    "collapse":   {"kg_ha": 150,  "reef_function_pct": 0.05, "label": "Hard coral and calcification approach zero"},
}

# S&P Global Commodity Insights, Verra VCS, Blue Carbon Initiative (2024-2025)
CARBON_PRICE_SCENARIOS: dict[str, dict] = {
    "conservative":   {"price_usd": 15.0, "label": "Conservative (Cispata Bay 2021 issuance)"},
    "current_market": {"price_usd": 25.25, "label": "S&P DBC-1 assessed average (Dec 2024)"},
    "premium":        {"price_usd": 29.30, "label": "S&P DBC-1 record high (Aug 2025)"},
    "2030_projection":{"price_usd": 45.0,  "label": "15x market growth projection by 2030"},
    "high_integrity": {"price_usd": 65.0,  "label": "CORSIA-eligible high-integrity credit"},
}

# Blue Carbon Initiative + Nature 2022 (doi:10.1038/s41598-022-11716-5)
# Sequestration rates in tCO2e per hectare per year
BLUE_CARBON_SEQUESTRATION: dict[str, dict] = {
    "mangrove_global":    {"tco2_ha_yr_low": 6.0,  "tco2_ha_yr_high": 8.0,  "source": "Blue Carbon Initiative"},
    "mangrove_sundarbans":{"tco2_ha_yr_low": 17.0, "tco2_ha_yr_high": 24.0, "source": "doi:10.1038/s41598-022-11716-5"},
    "seagrass_global":    {"tco2_ha_yr_low": 3.0,  "tco2_ha_yr_high": 5.0,  "source": "Blue Carbon Initiative"},
}

# Service sensitivity to reef quality (fraction of ESV retained at each threshold level)
# Derived from axiom chain analysis: tourism (BA-001) most sensitive, carbon least
SERVICE_REEF_SENSITIVITY: dict[str, dict] = {
    "tourism":            {"warning": 0.95, "mmsy_upper": 0.70, "mmsy_lower": 0.30, "collapse": 0.05},
    "fisheries":          {"warning": 0.92, "mmsy_upper": 0.75, "mmsy_lower": 0.40, "collapse": 0.10},
    "coastal_protection": {"warning": 0.88, "mmsy_upper": 0.60, "mmsy_lower": 0.25, "collapse": 0.05},
    "carbon_sequestration":{"warning":0.98, "mmsy_upper": 0.85, "mmsy_lower": 0.60, "collapse": 0.20},
}

# Confidence penalties for scenario extrapolation
SCENARIO_CONFIDENCE_PENALTIES: dict[str, dict] = {
    "temporal_extrapolation": {"penalty_per_decade": 0.10, "max_penalty": 0.40},
    "ssp_uncertainty":        {"SSP1-2.6": 0.05, "SSP2-4.5": 0.10, "SSP5-8.5": 0.15},
    "threshold_proximity":    {"within_10pct": 0.15, "within_20pct": 0.10},
    "missing_site_calibration": {"penalty": 0.20},
}
