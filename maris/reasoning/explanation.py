"""Human-readable explanation generation for inference chains.

Converts InferenceStep sequences into narrative explanations with DOI
citations at each step, suitable for investor-facing reports and the
Ask MARIS chat panel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from maris.reasoning.inference_engine import InferenceStep


@dataclass
class Explanation:
    """A complete explanation of an inference chain."""

    steps: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    summary: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": self.steps,
            "citations": self.citations,
            "summary": self.summary,
            "confidence": self.confidence,
        }

    def to_markdown(self) -> str:
        """Render the explanation as markdown."""
        lines: list[str] = []
        if self.summary:
            lines.append(f"**Summary:** {self.summary}")
            lines.append("")
        for i, step in enumerate(self.steps, 1):
            lines.append(f"{i}. {step}")
        if self.citations:
            lines.append("")
            lines.append("**Sources:**")
            for cite in self.citations:
                lines.append(f"- {cite}")
        if self.confidence > 0:
            lines.append("")
            lines.append(f"**Confidence:** {self.confidence:.0%}")
        return "\n".join(lines)


class ExplanationGenerator:
    """Generate human-readable explanations from inference chains."""

    def explain(
        self,
        steps: list[InferenceStep],
        question: str = "",
    ) -> Explanation:
        """Generate an explanation from a list of inference steps.

        Each step becomes a sentence: "Because [input_fact] and [axiom],
        we can conclude [output_fact] with [confidence] confidence."
        """
        explanation_steps: list[str] = []
        citations: list[str] = []
        seen_dois: set[str] = set()
        confidences: list[float] = []

        for step in steps:
            conf_str = _format_confidence(step.confidence)
            doi_ref = f" [{step.source_doi}]" if step.source_doi else ""

            sentence = (
                f"Because {step.input_fact} and bridge axiom {step.axiom_id} "
                f"(coefficient={step.coefficient}), "
                f"we can conclude {step.output_fact} "
                f"with {conf_str} confidence.{doi_ref}"
            )
            explanation_steps.append(sentence)

            if step.source_doi and step.source_doi not in seen_dois:
                seen_dois.add(step.source_doi)
                citations.append(f"DOI: {step.source_doi}")

            confidences.append(_confidence_to_float(step.confidence))

        # Overall confidence: minimum of individual steps (weakest link)
        overall_conf = min(confidences) if confidences else 0.0

        summary = _build_summary(steps, question)

        return Explanation(
            steps=explanation_steps,
            citations=citations,
            summary=summary,
            confidence=overall_conf,
        )

    def explain_backward(
        self,
        needed: list[dict[str, Any]],
        target_domain: str,
    ) -> Explanation:
        """Generate an explanation for backward chaining results.

        Describes what evidence is needed to derive the target domain.
        """
        explanation_steps: list[str] = []
        citations: list[str] = []
        seen_dois: set[str] = set()

        for item in needed:
            doi_ref = f" [{item.get('source_doi', '')}]" if item.get("source_doi") else ""
            sentence = (
                f"To derive {item.get('produces_domain', '?')}, "
                f"we need {item.get('needed_domain', '?')} data "
                f"via axiom {item.get('axiom_id', '?')} "
                f"({item.get('axiom_name', '')}).{doi_ref}"
            )
            explanation_steps.append(sentence)

            doi = item.get("source_doi", "")
            if doi and doi not in seen_dois:
                seen_dois.add(doi)
                citations.append(f"DOI: {doi}")

        summary = (
            f"To reach {target_domain} conclusions, "
            f"{len(needed)} axiom application(s) are required."
        )

        return Explanation(
            steps=explanation_steps,
            citations=citations,
            summary=summary,
            confidence=0.0,
        )


def _format_confidence(conf: str | float) -> str:
    """Format a confidence value for display."""
    if isinstance(conf, (int, float)):
        return f"{conf:.0%}"
    return str(conf)


def _confidence_to_float(conf: str | float) -> float:
    """Convert confidence to a float in [0, 1]."""
    if isinstance(conf, (int, float)):
        return float(conf)
    mapping = {"high": 0.9, "medium": 0.7, "low": 0.4}
    return mapping.get(conf.lower(), 0.5)


def _build_summary(steps: list[InferenceStep], question: str) -> str:
    """Build a one-line summary of the inference chain."""
    if not steps:
        return "No inference steps were required."
    domains = []
    if steps:
        first_input = steps[0].input_fact.split(":")[0].split("(")[0].strip()
        domains.append(first_input)
    for step in steps:
        output_domain = step.output_fact.split(" ")[0]
        if output_domain not in domains:
            domains.append(output_domain)
    chain_str = " -> ".join(domains)
    return f"Inference chain: {chain_str} ({len(steps)} step(s))"
