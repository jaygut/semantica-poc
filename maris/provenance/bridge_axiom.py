"""Bridge axiom dataclass and translation chain.

A BridgeAxiom represents a single ecological-to-financial translation rule
with full provenance metadata. A TranslationChain sequences multiple axiom
applications and tracks cumulative confidence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BridgeAxiom:
    """A single bridge axiom with provenance metadata.

    Attributes:
        axiom_id: Unique identifier (e.g., "BA-001")
        name: Human-readable name
        rule: Description of the translation rule
        coefficient: Primary numeric coefficient
        input_domain: Source domain (e.g., "ecological")
        output_domain: Target domain (e.g., "financial")
        source_doi: Primary DOI source
        source_page: Page reference in source
        source_quote: Supporting quote from source
        confidence: Confidence level ("high", "medium", "low") or float
        ci_low: Lower confidence interval bound for coefficient
        ci_high: Upper confidence interval bound for coefficient
        applicable_habitats: List of habitats this axiom applies to
        evidence_sources: List of evidence source dicts
        caveats: List of caveat strings
    """

    axiom_id: str
    name: str = ""
    rule: str = ""
    coefficient: float = 0.0
    input_domain: str = ""
    output_domain: str = ""
    source_doi: str = ""
    source_page: str = ""
    source_quote: str = ""
    confidence: str | float = "high"
    ci_low: float | None = None
    ci_high: float | None = None
    applicable_habitats: list[str] = field(default_factory=list)
    evidence_sources: list[dict[str, Any]] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    def apply(self, input_value: float) -> dict[str, Any]:
        """Apply this axiom to an input value.

        Returns a dict with the output value, confidence interval, and
        provenance metadata.
        """
        output_value = input_value * self.coefficient

        result: dict[str, Any] = {
            "axiom_id": self.axiom_id,
            "input_value": input_value,
            "output_value": output_value,
            "coefficient": self.coefficient,
            "source_doi": self.source_doi,
            "confidence": self.confidence,
        }

        if self.ci_low is not None and self.ci_high is not None:
            result["ci_low"] = input_value * self.ci_low
            result["ci_high"] = input_value * self.ci_high

        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "axiom_id": self.axiom_id,
            "name": self.name,
            "rule": self.rule,
            "coefficient": self.coefficient,
            "input_domain": self.input_domain,
            "output_domain": self.output_domain,
            "source_doi": self.source_doi,
            "source_page": self.source_page,
            "source_quote": self.source_quote,
            "confidence": self.confidence,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "applicable_habitats": self.applicable_habitats,
            "evidence_sources": self.evidence_sources,
            "caveats": self.caveats,
        }


class TranslationChain:
    """Sequences multiple BridgeAxiom applications with cumulative provenance.

    Confidence intervals are propagated multiplicatively when axioms
    are chained (each step's relative uncertainty compounds).
    """

    def __init__(self, axioms: list[BridgeAxiom] | None = None) -> None:
        self._axioms: list[BridgeAxiom] = list(axioms) if axioms else []
        self._steps: list[dict[str, Any]] = []

    @property
    def axioms(self) -> list[BridgeAxiom]:
        return list(self._axioms)

    @property
    def steps(self) -> list[dict[str, Any]]:
        return list(self._steps)

    def add(self, axiom: BridgeAxiom) -> None:
        """Add an axiom to the chain."""
        self._axioms.append(axiom)

    def execute(self, initial_value: float) -> dict[str, Any]:
        """Execute the full chain on an initial value.

        Returns the final output plus per-step provenance and cumulative
        confidence interval (propagated multiplicatively).
        """
        self._steps = []
        current_value = initial_value
        cumulative_rel_sq_low = 0.0
        cumulative_rel_sq_high = 0.0
        all_dois: list[str] = []
        all_caveats: list[str] = []

        for axiom in self._axioms:
            step = axiom.apply(current_value)
            self._steps.append(step)

            if axiom.source_doi:
                all_dois.append(axiom.source_doi)
            all_caveats.extend(axiom.caveats)

            # Propagate relative CI
            if current_value != 0 and "ci_low" in step and "ci_high" in step:
                rel_low = (step["output_value"] - step["ci_low"]) / abs(step["output_value"]) if step["output_value"] != 0 else 0
                rel_high = (step["ci_high"] - step["output_value"]) / abs(step["output_value"]) if step["output_value"] != 0 else 0
                cumulative_rel_sq_low += rel_low ** 2
                cumulative_rel_sq_high += rel_high ** 2

            current_value = step["output_value"]

        # Build cumulative CI
        combined_rel_low = math.sqrt(cumulative_rel_sq_low)
        combined_rel_high = math.sqrt(cumulative_rel_sq_high)

        result: dict[str, Any] = {
            "initial_value": initial_value,
            "final_value": current_value,
            "steps": self._steps,
            "axiom_count": len(self._axioms),
            "source_dois": all_dois,
            "caveats": all_caveats,
        }

        if current_value != 0:
            result["ci_low"] = current_value * (1 - combined_rel_low)
            result["ci_high"] = current_value * (1 + combined_rel_high)

        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "axioms": [a.to_dict() for a in self._axioms],
            "steps": self._steps,
        }
