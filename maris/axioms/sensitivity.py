"""One-at-a-time (OAT) sensitivity analysis for ESV Monte Carlo simulations.

Methodology: OAT was selected over Sobol indices because the ESV model is
additive (ecosystem service values are summed), so parameter interactions
are minimal. OAT with 12 parameters requires only 49 model runs, and
produces tornado plot data directly interpretable by investors and
underwriters. See ai_docs/research/sensitivity_methods.md for full
justification.
"""

import logging
from copy import deepcopy

from maris.axioms.monte_carlo import run_monte_carlo

logger = logging.getLogger(__name__)


def run_sensitivity_analysis(
    services: list[dict],
    perturbations: list[float] | None = None,
    n_simulations: int = 10_000,
    seed: int | None = 42,
) -> dict:
    """Run OAT sensitivity analysis on ecosystem service parameters.

    Varies each service's value by the given perturbation percentages while
    holding all others at baseline, then records the impact on total ESV.

    Parameters
    ----------
    services : list[dict]
        Service dicts with keys: value, ci_low, ci_high, service_name.
    perturbations : list[float]
        Perturbation levels as fractions (e.g., [0.10, 0.20] for 10%, 20%).
        Defaults to [0.10, 0.20].
    n_simulations : int
        Number of Monte Carlo runs per scenario.
    seed : int | None
        Random seed for reproducibility.

    Returns
    -------
    dict with keys:
        baseline_esv: float - baseline median ESV
        sensitivity_results: list[dict] - per-parameter sensitivity data
        dominant_parameter: str - most sensitive parameter name
        methodology: str - "OAT"
        methodology_justification: str
        tornado_plot_data: list[dict] - sorted data for tornado chart
    """
    if perturbations is None:
        perturbations = [0.10, 0.20]

    # Run baseline
    baseline = run_monte_carlo(services, n_simulations=n_simulations, seed=seed)
    baseline_esv = baseline["median"]

    results = []

    for i, svc in enumerate(services):
        svc_name = svc.get("service_name", svc.get("service_type", f"service_{i}"))
        base_value = float(svc.get("value", 0))

        if base_value == 0:
            continue

        param_results = {
            "parameter_name": svc_name,
            "base_value": base_value,
            "base_esv": baseline_esv,
        }

        max_impact_pct = 0.0

        for pct in perturbations:
            # Perturb high
            services_high = deepcopy(services)
            services_high[i]["value"] = base_value * (1 + pct)
            high_result = run_monte_carlo(
                services_high, n_simulations=n_simulations, seed=seed
            )
            high_esv = high_result["median"]

            # Perturb low
            services_low = deepcopy(services)
            services_low[i]["value"] = base_value * (1 - pct)
            low_result = run_monte_carlo(
                services_low, n_simulations=n_simulations, seed=seed
            )
            low_esv = low_result["median"]

            pct_label = int(pct * 100)
            param_results[f"low_{pct_label}_esv"] = low_esv
            param_results[f"high_{pct_label}_esv"] = high_esv

            impact = abs(high_esv - low_esv) / baseline_esv * 100
            param_results[f"impact_{pct_label}_pct"] = round(impact, 2)
            max_impact_pct = max(max_impact_pct, impact)

        param_results["max_impact_pct"] = round(max_impact_pct, 2)
        results.append(param_results)

    # Sort by max impact (descending) and assign ranks
    results.sort(key=lambda x: x["max_impact_pct"], reverse=True)
    for rank, r in enumerate(results, 1):
        r["sensitivity_rank"] = rank

    dominant = results[0]["parameter_name"] if results else "none"

    # Build tornado plot data (sorted by impact at largest perturbation)
    largest_pct = int(max(perturbations) * 100) if perturbations else 20
    tornado_data = []
    for r in results:
        tornado_data.append({
            "parameter_name": r["parameter_name"],
            "low_esv": r.get(f"low_{largest_pct}_esv", baseline_esv),
            "high_esv": r.get(f"high_{largest_pct}_esv", baseline_esv),
            "base_esv": baseline_esv,
            "sensitivity_rank": r["sensitivity_rank"],
        })

    return {
        "baseline_esv": baseline_esv,
        "sensitivity_results": results,
        "dominant_parameter": dominant,
        "methodology": "OAT",
        "methodology_justification": (
            "One-at-a-time (OAT) analysis selected for additive ESV model with "
            f"{len(services)} parameters. OAT captures >95% of variance in additive "
            "models and produces tornado plots directly interpretable by investors. "
            "Sobol indices would show near-zero interaction terms for this model structure."
        ),
        "tornado_plot_data": tornado_data,
        "perturbation_levels": [int(p * 100) for p in perturbations],
        "n_simulations_per_scenario": n_simulations,
    }
