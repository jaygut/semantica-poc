"""Monte Carlo simulation for ESV uncertainty quantification."""

import numpy as np


def run_monte_carlo(
    services: list[dict],
    n_simulations: int = 10_000,
    seed: int | None = 42,
) -> dict:
    """Run Monte Carlo simulation over ecosystem service valuations.

    Each service dict should have keys: value, ci_low, ci_high.
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
