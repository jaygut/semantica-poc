"""Portfolio-level Nature VaR with correlated stress scenarios.

Uses Cholesky decomposition on a habitat-based correlation matrix to
generate correlated Monte Carlo draws for ESV degradation across sites.

Correlation structure (between ESV shocks across sites):
- Same habitat type: 0.50-0.70 (coral reefs most correlated)
- Cross-habitat: 0.25-0.40 (moderate - regional climate linkage)

Sources:
- IPCC AR6 WG2 Ch.3 for SSP degradation anchors
- McClanahan et al. 2011 (doi:10.1073/pnas.1106861108) for reef thresholds
- Habitat correlations derived from observed co-occurrence of thermal stress events
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_EXAMPLES_DIR = _PROJECT_ROOT / "examples"

# Habitat correlation matrix for ESV shock co-movement
# Higher values = shocks are more correlated between sites with that habitat pair
HABITAT_CORRELATION: dict[tuple[str, str], float] = {
    ("coral_reef", "coral_reef"): 0.70,
    ("mangrove_forest", "mangrove_forest"): 0.55,
    ("seagrass_meadow", "seagrass_meadow"): 0.50,
    ("coral_reef", "mangrove_forest"): 0.30,
    ("coral_reef", "seagrass_meadow"): 0.25,
    ("mangrove_forest", "seagrass_meadow"): 0.40,
}

# Mean degradation fraction by habitat under each SSP by target year
# Derived from IPCC AR6 WG2 Ch.3 anchor points, linearly interpolated from 2025
_DEGRADATION_ANCHORS: dict[str, dict[str, dict[int, tuple[float, float]]]] = {
    "coral_reef": {
        "SSP1-2.6": {2050: (0.30, 0.50), 2100: (0.70, 0.90)},
        "SSP2-4.5": {2050: (0.50, 0.70), 2100: (0.90, 0.99)},
        "SSP5-8.5": {2050: (0.70, 0.90), 2100: (0.99, 1.00)},
    },
    "mangrove_forest": {
        "SSP1-2.6": {2050: (0.03, 0.08), 2100: (0.08, 0.15)},
        "SSP2-4.5": {2050: (0.05, 0.15), 2100: (0.15, 0.30)},
        "SSP5-8.5": {2050: (0.10, 0.25), 2100: (0.30, 0.50)},
    },
    "seagrass_meadow": {
        "SSP1-2.6": {2050: (0.10, 0.20), 2100: (0.20, 0.40)},
        "SSP2-4.5": {2050: (0.15, 0.30), 2100: (0.30, 0.50)},
        "SSP5-8.5": {2050: (0.25, 0.45), 2100: (0.50, 0.70)},
    },
}


def _interpolate_degradation(
    habitat: str, ssp: str, target_year: int,
) -> tuple[float, float]:
    """Linearly interpolate degradation fraction between 2025 (0%) and anchor years.

    Returns (degradation_low, degradation_high).
    """
    anchors = _DEGRADATION_ANCHORS.get(habitat, {}).get(ssp, {})
    if not anchors:
        # Unknown habitat/ssp - use moderate defaults
        return (0.10, 0.30)

    # Sort anchor years
    anchor_years = sorted(anchors.keys())

    if target_year <= 2025:
        return (0.0, 0.0)

    # Find bracketing anchors
    base_year = 2025
    for i, yr in enumerate(anchor_years):
        if target_year <= yr:
            if i == 0:
                # Between 2025 and first anchor
                frac = (target_year - base_year) / (yr - base_year)
                low_anchor, high_anchor = anchors[yr]
                return (frac * low_anchor, frac * high_anchor)
            else:
                # Between two anchors
                prev_yr = anchor_years[i - 1]
                prev_low, prev_high = anchors[prev_yr]
                curr_low, curr_high = anchors[yr]
                frac = (target_year - prev_yr) / (yr - prev_yr)
                return (
                    prev_low + frac * (curr_low - prev_low),
                    prev_high + frac * (curr_high - prev_high),
                )

    # Beyond last anchor - extrapolate from last segment (capped at 1.0)
    last_yr = anchor_years[-1]
    last_low, last_high = anchors[last_yr]
    return (min(last_low, 1.0), min(last_high, 1.0))


def _get_habitat_correlation(hab_a: str, hab_b: str) -> float:
    """Look up pairwise habitat correlation, handling symmetry."""
    if hab_a == hab_b:
        return HABITAT_CORRELATION.get((hab_a, hab_b), 0.50)
    # Try both orderings
    corr = HABITAT_CORRELATION.get((hab_a, hab_b))
    if corr is not None:
        return corr
    corr = HABITAT_CORRELATION.get((hab_b, hab_a))
    if corr is not None:
        return corr
    # Default for unknown habitat pairs
    return 0.20


def _build_correlation_matrix(habitats: list[str]) -> np.ndarray:
    """Build NxN correlation matrix from habitat list."""
    n = len(habitats)
    corr = np.eye(n)
    for i in range(n):
        for j in range(i + 1, n):
            c = _get_habitat_correlation(habitats[i], habitats[j])
            corr[i, j] = c
            corr[j, i] = c
    return corr


def load_portfolio_esv() -> dict[str, dict]:
    """Load all 9 case study JSONs and return site_esv_map.

    Returns:
        {site_name: {"total_esv": float, "habitat": str, "services": list}}
    """
    result: dict[str, dict] = {}
    for json_path in sorted(_EXAMPLES_DIR.glob("*_case_study.json")):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        site_name = data.get("site", {}).get("name", json_path.stem)
        esv_bundle = data.get("ecosystem_services", {})
        total_esv = esv_bundle.get("total_annual_value_usd", 0.0)
        habitat = data.get("ecological_status", {}).get("primary_habitat", "coral_reef")
        services = []
        for svc in esv_bundle.get("services", []):
            services.append({
                "service_type": svc.get("service_type", "unknown"),
                "annual_value_usd": svc.get("annual_value_usd", 0.0),
                "valuation_method": svc.get("valuation_method", "unknown"),
            })
        result[site_name] = {
            "total_esv": float(total_esv),
            "habitat": habitat,
            "services": services,
        }
    return result


def run_portfolio_stress_test(
    site_esv_map: dict[str, dict] | None = None,
    stress_scenario: str = "thermal",
    ssp_scenario: str = "SSP2-4.5",
    target_year: int = 2050,
    n_simulations: int = 10_000,
    seed: int = 42,
) -> dict:
    """Portfolio Nature VaR computation with habitat-based correlation structure.

    Parameters
    ----------
    site_esv_map : dict
        {site_name: {"total_esv": float, "habitat": str, "services": list}}.
        If None, loads from case study JSONs automatically.
    stress_scenario : str
        Stress type: "thermal", "policy", "fisheries", "compound".
        "compound" applies full SSP degradation; others use partial factors.
    ssp_scenario : str
        "SSP1-2.6", "SSP2-4.5", or "SSP5-8.5".
    target_year : int
        Projection year (2030, 2040, 2050, 2075, 2100).
    n_simulations : int
        Number of Monte Carlo draws.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    dict with portfolio_baseline_esv, scenario_median_esv, nature_var_95,
    nature_var_99, site_var_contributions, correlation_matrix,
    dominant_risk_habitat, n_simulations.

    Validation: Under SSP2-4.5 compound by 2050, nature_var_95 should be
    in [$400M, $900M] for the 9-site $1.62B portfolio.
    """
    if site_esv_map is None:
        site_esv_map = load_portfolio_esv()

    rng = np.random.default_rng(seed)

    # Extract site data into parallel arrays
    site_names = list(site_esv_map.keys())
    n_sites = len(site_names)
    baseline_esvs = np.array([site_esv_map[s]["total_esv"] for s in site_names])
    habitats = [site_esv_map[s].get("habitat", "coral_reef") for s in site_names]
    portfolio_baseline = float(np.sum(baseline_esvs))

    # Build correlation matrix and Cholesky factor
    corr_matrix = _build_correlation_matrix(habitats)

    # Ensure positive definiteness (add small diagonal if needed)
    min_eig = np.min(np.linalg.eigvalsh(corr_matrix))
    if min_eig < 1e-6:
        corr_matrix += np.eye(n_sites) * (1e-6 - min_eig)

    chol = np.linalg.cholesky(corr_matrix)

    # Get per-site degradation parameters
    deg_params = []
    for habitat in habitats:
        deg_low, deg_high = _interpolate_degradation(habitat, ssp_scenario, target_year)
        # For non-compound scenarios, scale down the degradation
        if stress_scenario == "thermal":
            # Thermal stress primarily affects coral reefs
            if habitat == "coral_reef":
                pass  # Full degradation
            else:
                deg_low *= 0.5
                deg_high *= 0.5
        elif stress_scenario == "policy":
            deg_low *= 0.3
            deg_high *= 0.3
        elif stress_scenario == "fisheries":
            deg_low *= 0.4
            deg_high *= 0.4
        # "compound" uses full degradation
        deg_mean = (deg_low + deg_high) / 2.0
        deg_std = (deg_high - deg_low) / 4.0  # ~95% of draws within range
        deg_std = max(deg_std, 0.01)  # Minimum variance
        deg_params.append((deg_mean, deg_std))

    # Monte Carlo with correlated draws
    # Generate standard normal draws and correlate via Cholesky
    z = rng.standard_normal((n_simulations, n_sites))
    correlated_z = z @ chol.T  # (n_sims, n_sites) correlated normal draws

    # Convert to degradation fractions (clipped to [0, 1])
    stressed_esvs = np.zeros((n_simulations, n_sites))
    for i in range(n_sites):
        deg_mean, deg_std = deg_params[i]
        degradation = deg_mean + deg_std * correlated_z[:, i]
        degradation = np.clip(degradation, 0.0, 0.95)  # Cap at 95% loss
        stressed_esvs[:, i] = baseline_esvs[i] * (1.0 - degradation)

    # Portfolio-level results
    portfolio_stressed = np.sum(stressed_esvs, axis=1)
    p5_portfolio = float(np.percentile(portfolio_stressed, 5))
    p1_portfolio = float(np.percentile(portfolio_stressed, 1))
    median_portfolio = float(np.median(portfolio_stressed))

    nature_var_95 = portfolio_baseline - p5_portfolio
    nature_var_99 = portfolio_baseline - p1_portfolio

    # Per-site VaR contributions
    site_var_contributions: dict[str, float] = {}
    for i, name in enumerate(site_names):
        site_p5 = float(np.percentile(stressed_esvs[:, i], 5))
        site_var_contributions[name] = float(baseline_esvs[i]) - site_p5

    # Dominant risk habitat (habitat with largest aggregate VaR contribution)
    habitat_var: dict[str, float] = {}
    for i, name in enumerate(site_names):
        h = habitats[i]
        habitat_var[h] = habitat_var.get(h, 0.0) + site_var_contributions[name]

    dominant_risk_habitat = max(habitat_var, key=habitat_var.get) if habitat_var else "unknown"

    return {
        "portfolio_baseline_esv": portfolio_baseline,
        "scenario_median_esv": median_portfolio,
        "nature_var_95": nature_var_95,
        "nature_var_99": nature_var_99,
        "site_var_contributions": site_var_contributions,
        "correlation_matrix": corr_matrix.tolist(),
        "dominant_risk_habitat": dominant_risk_habitat,
        "n_simulations": n_simulations,
        "ssp_scenario": ssp_scenario,
        "target_year": target_year,
        "stress_scenario": stress_scenario,
    }
