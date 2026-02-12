"""Bridge axiom evaluation engine."""

import json
import logging
from pathlib import Path

from maris.config import get_config

logger = logging.getLogger(__name__)


def _extract_coeff_value(coeff):
    """Extract the numeric value from a coefficient that may be a dict with uncertainty or a scalar."""
    if isinstance(coeff, dict) and "value" in coeff:
        return coeff["value"]
    if isinstance(coeff, (int, float)):
        return coeff
    return None


def _extract_coeff_bounds(coeff):
    """Extract (value, ci_low, ci_high) from a coefficient. Returns None for ci bounds if unavailable."""
    if isinstance(coeff, dict):
        if "value" in coeff:
            return (
                coeff["value"],
                coeff.get("ci_low"),
                coeff.get("ci_high"),
            )
        if "min" in coeff and "max" in coeff:
            mid = (coeff["min"] + coeff["max"]) / 2
            return (mid, coeff["min"], coeff["max"])
    if isinstance(coeff, (int, float)):
        return (coeff, None, None)
    return (None, None, None)


class BridgeAxiomEngine:
    """Load and evaluate bridge axiom templates."""

    def __init__(self, templates_path: Path | None = None):
        if templates_path is None:
            templates_path = get_config().schemas_dir / "bridge_axiom_templates.json"

        with open(templates_path) as f:
            data = json.load(f)

        self._axioms: dict[str, dict] = {}
        for axiom in data.get("axioms", []):
            self._axioms[axiom["axiom_id"]] = axiom

        logger.info("Loaded %d bridge axioms from %s", len(self._axioms), templates_path)

    def get_axiom(self, axiom_id: str) -> dict | None:
        """Return a single axiom template by ID."""
        return self._axioms.get(axiom_id)

    def list_all(self) -> list[dict]:
        """Return all axiom templates."""
        return list(self._axioms.values())

    def list_applicable(self, habitat: str) -> list[dict]:
        """Return axioms applicable to a given habitat type."""
        results = []
        for axiom in self._axioms.values():
            habitats = axiom.get("applicable_habitats", [])
            if "all" in habitats or habitat in habitats:
                results.append(axiom)
        return results

    def evaluate(self, axiom_id: str, inputs: dict) -> dict:
        """Apply axiom coefficients to inputs and compute a value with CI.

        Handles both scalar coefficients and structured uncertainty coefficients
        (dicts with value, ci_low, ci_high fields).
        """
        axiom = self._axioms.get(axiom_id)
        if axiom is None:
            return {"error": f"Unknown axiom: {axiom_id}"}

        coefficients = axiom.get("coefficients", {})
        caveats = axiom.get("caveats", [])

        result_value = 0.0
        ci_low = 0.0
        ci_high = 0.0
        applied: list[str] = []
        has_uncertainty = False

        for key, input_val in inputs.items():
            if not isinstance(input_val, (int, float)):
                continue

            coeff = coefficients.get(key)
            if coeff is None:
                continue

            val, lo, hi = _extract_coeff_bounds(coeff)
            if val is None:
                continue

            result_value += input_val * val
            applied.append(key)

            if lo is not None and hi is not None:
                ci_low += input_val * lo
                ci_high += input_val * hi
                has_uncertainty = True
            else:
                ci_low += input_val * val
                ci_high += input_val * val

        # If confidence_interval_95 is present and we have no other CI, use it
        ci95 = coefficients.get("confidence_interval_95")
        if isinstance(ci95, list) and len(ci95) == 2 and not has_uncertainty:
            ci_low = ci95[0]
            ci_high = ci95[1]

        # Collect uncertainty metadata
        uncertainty_types = set()
        for key in applied:
            coeff = coefficients.get(key)
            if isinstance(coeff, dict):
                utype = coeff.get("uncertainty_type", "unknown")
                uncertainty_types.add(utype)

        return {
            "axiom_id": axiom_id,
            "value": result_value,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "coefficients_applied": applied,
            "caveats": caveats,
            "uncertainty_types": list(uncertainty_types),
        }
