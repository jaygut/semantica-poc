"""Compile bridge axioms into inference rules.

Converts MARIS BridgeAxiom objects from the bridge_axiom_templates.json
schema into InferenceRule objects suitable for the forward/backward
chaining engine.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from maris.provenance.bridge_axiom import BridgeAxiom
from maris.reasoning.inference_engine import InferenceRule

logger = logging.getLogger(__name__)


def compile_axiom(axiom: BridgeAxiom) -> InferenceRule:
    """Compile a single bridge axiom into an inference rule.

    Args:
        axiom: A BridgeAxiom instance with axiom_id, input_domain,
            output_domain, rule, and applicable_habitats.

    Returns:
        An InferenceRule with rule_id prefixed by "rule:".
    """
    return InferenceRule(
        rule_id=f"rule:{axiom.axiom_id}",
        axiom=axiom,
        input_domain=axiom.input_domain,
        output_domain=axiom.output_domain,
        condition=axiom.rule,
        applicable_habitats=axiom.applicable_habitats,
    )


def compile_all(axioms: list[BridgeAxiom]) -> dict[str, InferenceRule]:
    """Compile a list of axioms into a rule registry.

    Args:
        axioms: List of BridgeAxiom instances.

    Returns:
        Dict mapping rule_id to InferenceRule.
    """
    rules: dict[str, InferenceRule] = {}
    for axiom in axioms:
        rule = compile_axiom(axiom)
        rules[rule.rule_id] = rule
    return rules


def compile_from_templates(templates_path: str) -> dict[str, InferenceRule]:
    """Load axiom templates from JSON and compile into rules.

    Args:
        templates_path: Path to bridge_axiom_templates.json.

    Returns:
        Dict mapping rule_id to InferenceRule.
    """
    with open(templates_path) as f:
        data = json.load(f)

    axioms: list[BridgeAxiom] = []
    for entry in data.get("axioms", []):
        axiom = _template_entry_to_axiom(entry)
        axioms.append(axiom)

    logger.info("Compiled %d rules from %s", len(axioms), templates_path)
    return compile_all(axioms)


def _template_entry_to_axiom(entry: dict[str, Any]) -> BridgeAxiom:
    """Convert a single axiom template JSON entry to a BridgeAxiom."""
    # Extract the primary coefficient value
    coefficients = entry.get("coefficients", {})
    primary_coeff = 0.0
    ci_low = None
    ci_high = None

    # Use the first coefficient entry as the primary
    for _key, val in coefficients.items():
        if isinstance(val, dict):
            primary_coeff = val.get("value", 0.0)
            ci_low = val.get("ci_low")
            ci_high = val.get("ci_high")
        else:
            primary_coeff = float(val)
        break

    # Extract primary DOI from evidence sources
    evidence = entry.get("evidence_sources", [])
    source_doi = ""
    if evidence:
        source_doi = evidence[0].get("doi", "")

    # Map category to domain pair
    input_domain, output_domain = _category_to_domains(
        entry.get("category", "")
    )

    return BridgeAxiom(
        axiom_id=entry["axiom_id"],
        name=entry.get("name", ""),
        rule=entry.get("pattern", entry.get("description", "")),
        coefficient=primary_coeff,
        input_domain=input_domain,
        output_domain=output_domain,
        source_doi=source_doi,
        confidence=entry.get("confidence", "high"),
        ci_low=ci_low,
        ci_high=ci_high,
        applicable_habitats=entry.get("applicable_habitats", []),
        evidence_sources=evidence,
        caveats=entry.get("caveats", []),
    )


def _category_to_domains(category: str) -> tuple[str, str]:
    """Map an axiom category string to (input_domain, output_domain)."""
    mapping = {
        "ecological_to_service": ("ecological", "service"),
        "service_to_financial": ("service", "financial"),
        "ecological_to_financial": ("ecological", "financial"),
        "risk_to_financial": ("risk", "financial"),
    }
    return mapping.get(category, ("ecological", "service"))
