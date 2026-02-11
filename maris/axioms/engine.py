"""Bridge axiom evaluation engine."""

import json
import logging
from pathlib import Path

from maris.config import get_config

logger = logging.getLogger(__name__)


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

        This is a simplified evaluator for the POC.  It looks up the axiom,
        multiplies relevant input values by coefficients, and returns the
        result together with any available confidence interval.
        """
        axiom = self._axioms.get(axiom_id)
        if axiom is None:
            return {"error": f"Unknown axiom: {axiom_id}"}

        coefficients = axiom.get("coefficients", {})
        caveats = axiom.get("caveats", [])

        # Generic evaluation: multiply each numeric input by matching coefficient
        result_value = 0.0
        ci_low = 0.0
        ci_high = 0.0
        applied: list[str] = []

        for key, input_val in inputs.items():
            if not isinstance(input_val, (int, float)):
                continue

            # Look for a matching coefficient
            coeff = coefficients.get(key)
            if isinstance(coeff, (int, float)):
                result_value += input_val * coeff
                applied.append(key)
            elif isinstance(coeff, dict):
                # Range-based coefficient: {min: x, max: y}
                lo = coeff.get("min", 0)
                hi = coeff.get("max", 0)
                mid = (lo + hi) / 2
                result_value += input_val * mid
                ci_low += input_val * lo
                ci_high += input_val * hi
                applied.append(key)

        # If confidence_interval_95 is present, use it for the primary CI
        ci95 = coefficients.get("confidence_interval_95")
        if isinstance(ci95, list) and len(ci95) == 2:
            ci_low = ci_low or ci95[0]
            ci_high = ci_high or ci95[1]

        return {
            "axiom_id": axiom_id,
            "value": result_value,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "coefficients_applied": applied,
            "caveats": caveats,
        }
