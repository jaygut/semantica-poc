"""CandidateAxiom Pydantic model for discovered axiom candidates."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CandidateAxiom(BaseModel):
    """A candidate bridge axiom discovered from cross-paper pattern aggregation.

    Candidates are formed when 3+ independent papers report a consistent
    quantitative relationship between an ecological metric and a financial
    or service outcome. They require human review before being accepted
    into the bridge axiom registry.
    """

    candidate_id: str = Field(description="Unique ID, e.g. 'CAND-017'")
    proposed_name: str = Field(description="Descriptive name for the axiom")
    pattern: str = Field(description="IF-THEN format translation rule")
    domain_from: str = Field(description="Source domain (e.g. 'ecological')")
    domain_to: str = Field(description="Target domain (e.g. 'service', 'financial')")
    mean_coefficient: float = Field(description="Mean coefficient across studies")
    ci_low: float = Field(description="Lower confidence interval bound")
    ci_high: float = Field(description="Upper confidence interval bound")
    n_studies: int = Field(description="Number of independent supporting studies")
    supporting_dois: list[str] = Field(default_factory=list, description="DOIs of supporting papers")
    applicable_habitats: list[str] = Field(default_factory=list, description="Applicable habitat types")
    conflicts: list[str] = Field(default_factory=list, description="DOIs with outlier coefficients")
    status: Literal["candidate", "accepted", "rejected"] = Field(default="candidate")
    review_notes: str | None = Field(default=None, description="Reviewer notes")
    reviewed_by: str | None = Field(default=None, description="Reviewer identifier")
    reviewed_at: str | None = Field(default=None, description="ISO datetime of review")

    def to_axiom_template(self) -> dict:
        """Convert accepted candidate to bridge axiom template format.

        Returns a dict compatible with schemas/bridge_axiom_templates.json structure.
        Raises ValueError if the candidate has not been accepted.
        """
        if self.status != "accepted":
            raise ValueError(
                f"Cannot convert candidate {self.candidate_id} to template: "
                f"status is '{self.status}', must be 'accepted'"
            )

        return {
            "axiom_id": self.candidate_id.replace("CAND-", "BA-"),
            "name": self.proposed_name,
            "category": f"{self.domain_from}_to_{self.domain_to}",
            "description": self.pattern,
            "pattern": self.pattern,
            "coefficients": {
                "primary_coefficient": {
                    "value": self.mean_coefficient,
                    "ci_low": self.ci_low,
                    "ci_high": self.ci_high,
                    "distribution": "triangular",
                    "study_sample_size": self.n_studies,
                    "effect_size_type": "ratio",
                    "uncertainty_type": "research_grounded",
                }
            },
            "applicable_habitats": self.applicable_habitats,
            "evidence_tier": "T1",
            "sources": [
                {"doi": doi, "citation": "", "finding": ""}
                for doi in self.supporting_dois
            ],
            "caveats": [
                f"Derived from {self.n_studies} independent studies",
                f"Coefficient range: {self.ci_low} - {self.ci_high}",
            ],
        }
