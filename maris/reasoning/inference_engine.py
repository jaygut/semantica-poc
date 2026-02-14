"""Rule-based inference engine using bridge axioms.

Supports forward chaining (ecological facts -> financial conclusions) and
backward chaining (financial query -> needed ecological evidence). Tracks
provenance through the ProvenanceManager from P0.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from maris.provenance.bridge_axiom import BridgeAxiom

logger = logging.getLogger(__name__)


@dataclass
class InferenceRule:
    """A rule derived from a bridge axiom for the inference engine.

    input_domain and output_domain define the domain transition (e.g.,
    ecological -> service -> financial). The condition is a human-readable
    description of when the rule applies.
    """

    rule_id: str
    axiom: BridgeAxiom
    input_domain: str
    output_domain: str
    condition: str = ""
    applicable_habitats: list[str] = field(default_factory=list)


@dataclass
class InferenceStep:
    """A single step in an inference chain."""

    rule_id: str
    axiom_id: str
    input_fact: str
    output_fact: str
    coefficient: float
    confidence: str | float
    source_doi: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "axiom_id": self.axiom_id,
            "input_fact": self.input_fact,
            "output_fact": self.output_fact,
            "coefficient": self.coefficient,
            "confidence": self.confidence,
            "source_doi": self.source_doi,
        }


class InferenceEngine:
    """Rule-based reasoning engine using MARIS bridge axioms.

    Registers axioms as inference rules, then supports:
    - Forward chaining: given ecological facts, derive financial conclusions
    - Backward chaining: given a financial query, identify needed evidence
    """

    def __init__(self, provenance_manager: Any = None) -> None:
        self._rules: dict[str, InferenceRule] = {}
        self._provenance = provenance_manager

    def register_axiom(self, axiom: BridgeAxiom) -> str:
        """Register a bridge axiom as an inference rule.

        Returns the rule_id.
        """
        rule_id = f"rule:{axiom.axiom_id}"
        self._rules[rule_id] = InferenceRule(
            rule_id=rule_id,
            axiom=axiom,
            input_domain=axiom.input_domain,
            output_domain=axiom.output_domain,
            condition=axiom.rule,
            applicable_habitats=axiom.applicable_habitats,
        )
        return rule_id

    def register_axioms(self, axioms: list[BridgeAxiom]) -> int:
        """Register multiple axioms. Returns count registered."""
        for axiom in axioms:
            self.register_axiom(axiom)
        return len(axioms)

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def get_rule(self, rule_id: str) -> InferenceRule | None:
        return self._rules.get(rule_id)

    def forward_chain(
        self,
        facts: dict[str, Any],
        max_steps: int = 10,
    ) -> list[InferenceStep]:
        """Forward chaining: derive conclusions from known facts.

        Args:
            facts: Dict of known facts. Keys are domain names (e.g.,
                "ecological", "service"), values are dicts of metric->value.
            max_steps: Maximum inference steps to prevent infinite loops.

        Returns list of InferenceSteps representing the derivation chain.
        """
        steps: list[InferenceStep] = []
        derived_domains: set[str] = set(facts.keys())
        used_rules: set[str] = set()

        for _ in range(max_steps):
            progress = False
            for rule_id, rule in self._rules.items():
                if rule_id in used_rules:
                    continue
                if rule.input_domain not in derived_domains:
                    continue

                # Apply the rule
                input_facts = facts.get(rule.input_domain, {})
                input_desc = _format_facts(rule.input_domain, input_facts)
                output_desc = (
                    f"{rule.output_domain} value via {rule.axiom.name} "
                    f"(coeff={rule.axiom.coefficient})"
                )

                step = InferenceStep(
                    rule_id=rule_id,
                    axiom_id=rule.axiom.axiom_id,
                    input_fact=input_desc,
                    output_fact=output_desc,
                    coefficient=rule.axiom.coefficient,
                    confidence=rule.axiom.confidence,
                    source_doi=rule.axiom.source_doi,
                )
                steps.append(step)
                used_rules.add(rule_id)

                # Add derived domain to available facts
                if rule.output_domain not in derived_domains:
                    derived_domains.add(rule.output_domain)
                    facts[rule.output_domain] = {}
                progress = True

                # Record provenance if manager available
                if self._provenance:
                    self._record_inference_provenance(step)

            if not progress:
                break

        return steps

    def backward_chain(
        self,
        target_domain: str,
        max_depth: int = 5,
    ) -> list[dict[str, Any]]:
        """Backward chaining: identify what evidence is needed to derive a target.

        Args:
            target_domain: The domain we want to reach (e.g., "financial").
            max_depth: Maximum backward steps.

        Returns list of required evidence dicts, each with rule_id, axiom_id,
        needed_domain, needed_facts description, and source_doi.
        """
        needed: list[dict[str, Any]] = []
        visited_domains: set[str] = set()
        targets = [target_domain]

        for _ in range(max_depth):
            if not targets:
                break
            next_targets: list[str] = []
            for domain in targets:
                if domain in visited_domains:
                    continue
                visited_domains.add(domain)

                # Find rules that produce this domain
                for rule_id, rule in self._rules.items():
                    if rule.output_domain != domain:
                        continue
                    needed.append({
                        "rule_id": rule_id,
                        "axiom_id": rule.axiom.axiom_id,
                        "axiom_name": rule.axiom.name,
                        "needed_domain": rule.input_domain,
                        "produces_domain": rule.output_domain,
                        "source_doi": rule.axiom.source_doi,
                        "condition": rule.condition,
                    })
                    if rule.input_domain not in visited_domains:
                        next_targets.append(rule.input_domain)

            targets = next_targets

        return needed

    def find_rules_for_habitat(self, habitat: str) -> list[InferenceRule]:
        """Return all rules applicable to a specific habitat."""
        return [
            r for r in self._rules.values()
            if "all" in r.applicable_habitats or habitat in r.applicable_habitats
        ]

    def find_chain(
        self,
        input_domain: str,
        output_domain: str,
    ) -> list[InferenceRule]:
        """Find a sequence of rules connecting input_domain to output_domain.

        Uses BFS to find the shortest chain. Returns empty list if no path.
        """
        if input_domain == output_domain:
            return []

        # BFS
        queue: list[tuple[str, list[InferenceRule]]] = [(input_domain, [])]
        visited: set[str] = {input_domain}

        while queue:
            current_domain, path = queue.pop(0)
            for rule in self._rules.values():
                if rule.input_domain != current_domain:
                    continue
                new_path = path + [rule]
                if rule.output_domain == output_domain:
                    return new_path
                if rule.output_domain not in visited:
                    visited.add(rule.output_domain)
                    queue.append((rule.output_domain, new_path))

        return []

    def _record_inference_provenance(self, step: InferenceStep) -> None:
        """Record an inference step in the provenance manager."""
        try:
            self._provenance.record_activity(
                activity_type="inference",
                used=[step.axiom_id],
                attributes={
                    "rule_id": step.rule_id,
                    "input_fact": step.input_fact,
                    "output_fact": step.output_fact,
                    "coefficient": step.coefficient,
                    "source_doi": step.source_doi,
                },
            )
        except Exception:
            logger.warning("Failed to record inference provenance", exc_info=True)


def _format_facts(domain: str, facts: dict[str, Any]) -> str:
    """Format facts dict into a human-readable string."""
    if not facts:
        return f"{domain} (domain present)"
    parts = [f"{k}={v}" for k, v in facts.items()]
    return f"{domain}: {', '.join(parts)}"
