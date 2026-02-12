"""Monte Carlo simulation for ESV uncertainty quantification.

Triangular Distribution Rationale
----------------------------------
The triangular distribution is used because:
1. It requires only three parameters (min, mode, max) - matching the data
   available from ecosystem service valuation literature, which typically
   reports point estimates and ranges rather than full distribution parameters.
2. It does not assume symmetry (unlike normal), accommodating the right-skewed
   nature of many ESV estimates.
3. It naturally bounds the output (unlike normal, which is unbounded),
   preventing physically impossible negative ESV values.
4. It is the standard choice in risk analysis when only range and best estimate
   are known (TEEB Valuation Database Manual, 2013).
5. Alternative distributions (lognormal, beta) require mean and variance
   parameters that most ESV primary studies do not report.

When individual axiom coefficients specify a different distribution type
(e.g., lognormal for biomass ratios), the triangular distribution serves
as a conservative approximation. Future versions may support per-coefficient
distribution selection.
"""

import numpy as np


def run_monte_carlo(
    services: list[dict],
    n_simulations: int = 10_000,
    seed: int | None = 42,
) -> dict:
    """Run Monte Carlo simulation over ecosystem service valuations.

    Each service dict should have keys: value, ci_low, ci_high.
    Optionally: service_name, service_type for sensitivity labeling.
    Samples from a triangular distribution per service and sums.

    Returns dict with median, mean, p5, p95, and the raw simulations array.
    """
    rng = np.random.default_rng(seed)
    totals = np.zeros(n_simulations)

    for svc in services:
        value = float(svc.get("value", 0))
        ci_low = float(svc.get("ci_low", value * 0.7))
        ci_high = float(svc.get("ci_high", value * 1.3))

        # Clamp: ensure left <= mode <= right
        left = min(ci_low, value)
        right = max(ci_high, value)
        mode = max(left, min(value, right))

        if left == right:
            samples = np.full(n_simulations, value)
        else:
            samples = rng.triangular(left, mode, right, size=n_simulations)

        totals += samples

    return {
        "median": float(np.median(totals)),
        "mean": float(np.mean(totals)),
        "p5": float(np.percentile(totals, 5)),
        "p95": float(np.percentile(totals, 95)),
        "std": float(np.std(totals)),
        "n_simulations": n_simulations,
        "simulations": totals,
    }


def run_monte_carlo_with_sensitivity(
    services: list[dict],
    n_simulations: int = 10_000,
    seed: int | None = 42,
    perturbations: list[float] | None = None,
) -> dict:
    """Run Monte Carlo simulation with integrated OAT sensitivity analysis.

    Combines the standard Monte Carlo output with a tornado-plot sensitivity
    ranking showing which parameters drive ESV uncertainty most.
    """
    mc_result = run_monte_carlo(services, n_simulations=n_simulations, seed=seed)

    from maris.axioms.sensitivity import run_sensitivity_analysis
    sensitivity = run_sensitivity_analysis(
        services,
        perturbations=perturbations,
        n_simulations=n_simulations,
        seed=seed,
    )

    # Merge results (exclude raw simulations array from sensitivity)
    result = {
        "median": mc_result["median"],
        "mean": mc_result["mean"],
        "p5": mc_result["p5"],
        "p95": mc_result["p95"],
        "std": mc_result["std"],
        "n_simulations": n_simulations,
        "simulations": mc_result["simulations"],
        "sensitivity_ranking": [
            {
                "param": r["parameter_name"],
                "impact_pct": r["max_impact_pct"],
                "rank": r["sensitivity_rank"],
            }
            for r in sensitivity["sensitivity_results"]
        ],
        "dominant_parameter": sensitivity["dominant_parameter"],
        "tornado_plot_data": sensitivity["tornado_plot_data"],
        "sensitivity_methodology": sensitivity["methodology"],
        "sensitivity_justification": sensitivity["methodology_justification"],
    }

    return result
