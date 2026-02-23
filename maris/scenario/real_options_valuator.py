"""Real options valuation for conservation investment.

Computes the option value of conservation investment above static NPV
using Monte Carlo simulation. The real options approach captures the
value of management flexibility (ability to adapt strategy as ecosystem
responds to protection).

Source: Speir et al. 2015 (doi:10.3389/fmars.2015.00101)

ESV volatility estimated from confidence interval bounds in case study data:
- market_price method: 20% annual volatility
- avoided_cost method: 30% annual volatility
- regional_analogue method: 50% annual volatility
"""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

# Volatility by valuation method (annualized, from CI convention)
_METHOD_VOLATILITY: dict[str, float] = {
    "market_price": 0.20,
    "avoided_cost": 0.30,
    "regional_analogue": 0.50,
    "regional_analogue_estimate": 0.50,
    "expenditure_method": 0.30,
}

# Counterfactual retention fraction: unprotected site retains this
# fraction of protected-site ESV (generic assumption)
_COUNTERFACTUAL_RETENTION = 0.40


def _estimate_esv_volatility(site_data: dict) -> float:
    """Estimate blended ESV volatility from the valuation methods used.

    Weight volatility by each service's share of total ESV.
    """
    services = site_data.get("ecosystem_services", {}).get("services", [])
    total_esv = site_data.get("ecosystem_services", {}).get("total_annual_value_usd", 0.0)

    if not services or total_esv <= 0:
        return 0.30  # Default moderate volatility

    weighted_vol = 0.0
    for svc in services:
        value = svc.get("annual_value_usd", 0.0)
        method = svc.get("valuation_method", "avoided_cost")
        vol = _METHOD_VOLATILITY.get(method, 0.30)
        weighted_vol += (value / total_esv) * vol

    return weighted_vol


def compute_conservation_option_value(
    site_data: dict,
    investment_cost_usd: float,
    time_horizon_years: int = 20,
    discount_rate: float = 0.04,
    n_simulations: int = 10_000,
    seed: int = 42,
) -> dict:
    """Compute option value of conservation investment using Monte Carlo simulation.

    Real options approach (Speir et al. 2015, doi:10.3389/fmars.2015.00101):
    Option_Value = E[max(NPV_protected - NPV_unprotected - investment_cost, 0)]

    Parameters
    ----------
    site_data : dict
        Full case study JSON data for the site.
    investment_cost_usd : float
        Upfront conservation investment cost.
    time_horizon_years : int
        Time horizon for NPV computation.
    discount_rate : float
        Annual discount rate.
    n_simulations : int
        Number of Monte Carlo paths.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    dict with: static_npv, option_value, total_value, option_premium_pct,
    esv_volatility, bcr, payback_years, p5_npv, p50_npv, p95_npv.

    Validation (Cispata Bay mangrove restoration at $5M):
    - BCR target: [6.0, 16.0]
    - Option premium: 15-40% above static NPV
    """
    total_esv = site_data.get("ecosystem_services", {}).get("total_annual_value_usd", 0.0)
    volatility = _estimate_esv_volatility(site_data)

    rng = np.random.default_rng(seed)

    # Discount factors
    years = np.arange(1, time_horizon_years + 1)
    discount_factors = 1.0 / (1.0 + discount_rate) ** years

    # Static NPV (deterministic)
    # Annual benefit = ESV_protected - ESV_unprotected
    annual_net_benefit = total_esv * (1.0 - _COUNTERFACTUAL_RETENTION)
    static_npv = float(np.sum(annual_net_benefit * discount_factors)) - investment_cost_usd

    # Monte Carlo simulation with geometric Brownian motion
    # Protected ESV follows: ESV(t) = ESV_0 * exp((mu - 0.5*sigma^2)*t + sigma*W(t))
    # Unprotected ESV follows independent GBM with same vol but at lower level
    mu = 0.0  # No real ESV growth assumed
    dt = 1.0  # Annual steps

    # Generate two independent sets of paths for protected and unprotected
    dW_protected = rng.standard_normal((n_simulations, time_horizon_years))
    dW_unprotected = rng.standard_normal((n_simulations, time_horizon_years))

    # Protected site paths
    log_returns_p = (mu - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * dW_protected
    cum_log_p = np.cumsum(log_returns_p, axis=1)
    esv_protected_paths = total_esv * np.exp(cum_log_p)

    # Unprotected site: starts at retention fraction, independent uncertainty
    unprotected_esv_0 = total_esv * _COUNTERFACTUAL_RETENTION
    log_returns_u = (mu - 0.5 * volatility**2) * dt + volatility * np.sqrt(dt) * dW_unprotected
    cum_log_u = np.cumsum(log_returns_u, axis=1)
    esv_unprotected_paths = unprotected_esv_0 * np.exp(cum_log_u)

    # Net benefit paths (conservation premium each year)
    net_benefit_paths = esv_protected_paths - esv_unprotected_paths  # (n_sims, T)

    # NPV of each simulation
    npv_paths = np.sum(net_benefit_paths * discount_factors[np.newaxis, :], axis=1) - investment_cost_usd

    # Option value: E[max(NPV, 0)] - max(static_npv, 0)
    # The option value captures the asymmetric payoff from uncertainty:
    # with flexibility, you can abandon if NPV < 0 (limit downside)
    # The premium comes from Jensen's inequality on the convex payoff max(x, 0)
    option_payoffs = np.maximum(npv_paths, 0.0)
    option_value = float(np.mean(option_payoffs)) - max(static_npv, 0.0)

    # Total value
    total_value = static_npv + option_value

    # Option premium percentage
    option_premium_pct = (option_value / abs(static_npv) * 100.0) if static_npv != 0 else 0.0

    # BCR: expected NPV of benefits (before investment) / investment
    expected_gross_npv = float(np.mean(
        np.sum(net_benefit_paths * discount_factors[np.newaxis, :], axis=1)
    ))
    bcr = expected_gross_npv / investment_cost_usd if investment_cost_usd > 0 else 0.0

    # Payback period: when cumulative discounted net benefit exceeds investment
    cumulative_benefit = annual_net_benefit * np.cumsum(discount_factors)
    payback_mask = cumulative_benefit >= investment_cost_usd
    if np.any(payback_mask):
        payback_years = float(years[payback_mask][0])
    else:
        payback_years = float(time_horizon_years + 1)  # Beyond horizon

    # Percentiles
    p5_npv = float(np.percentile(npv_paths, 5))
    p50_npv = float(np.percentile(npv_paths, 50))
    p95_npv = float(np.percentile(npv_paths, 95))

    return {
        "static_npv": static_npv,
        "option_value": option_value,
        "total_value": total_value,
        "option_premium_pct": option_premium_pct,
        "esv_volatility": volatility,
        "bcr": bcr,
        "payback_years": payback_years,
        "p5_npv": p5_npv,
        "p50_npv": p50_npv,
        "p95_npv": p95_npv,
        "investment_cost_usd": investment_cost_usd,
        "time_horizon_years": time_horizon_years,
        "discount_rate": discount_rate,
        "n_simulations": n_simulations,
    }
