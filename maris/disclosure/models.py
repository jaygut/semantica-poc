"""Pydantic v2 models for TNFD LEAP disclosure generation.

Models the four phases of the TNFD LEAP framework (Locate, Evaluate,
Assess, Prepare) and the 14 recommended disclosures across the four
pillars (Governance, Strategy, Risk & Impact Management, Metrics & Targets).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Supporting types
# ---------------------------------------------------------------------------

class HabitatDescriptor(BaseModel):
    """A habitat type with optional extent data."""
    habitat_id: str
    name: str = ""
    extent_km2: float | None = None
    condition: str = ""


class SpeciesDependency(BaseModel):
    """A species relevant to ecosystem service delivery."""
    scientific_name: str
    common_name: str = ""
    role: str = ""
    dependency_type: str = ""


class ServiceDependency(BaseModel):
    """An ecosystem service the site depends on or generates."""
    service_type: str
    annual_value_usd: float | None = None
    valuation_method: str = ""
    share_of_total_esv_pct: float | None = None
    bridge_axioms_used: list[str] = Field(default_factory=list)


class ImpactPathway(BaseModel):
    """A pathway through which activities impact nature or nature impacts finance."""
    pathway_type: str = ""
    description: str = ""
    direction: str = ""
    magnitude: str = ""
    bridge_axiom_id: str | None = None
    source_doi: str | None = None


class RiskAssessment(BaseModel):
    """A nature-related risk with severity and likelihood."""
    risk_type: str
    category: str = ""
    severity: str = ""
    likelihood: str = ""
    time_horizon: str = ""
    financial_impact_description: str = ""
    source_doi: str | None = None


class Opportunity(BaseModel):
    """A nature-related financial opportunity."""
    opportunity_type: str
    description: str = ""
    estimated_value_range: str = ""
    time_horizon: str = ""
    enabling_axioms: list[str] = Field(default_factory=list)


class MetricEntry(BaseModel):
    """A disclosure metric with value and provenance."""
    metric_name: str
    value: Any = None
    unit: str = ""
    measurement_year: int | None = None
    source_doi: str | None = None
    methodology: str = ""


class TargetEntry(BaseModel):
    """A nature-related target aligned with GBF/TNFD guidance."""
    target_name: str
    baseline_value: Any = None
    target_value: Any = None
    target_year: int | None = None
    aligned_framework: str = ""
    status: str = ""


class ProvenanceEntry(BaseModel):
    """A provenance record linking a disclosure element to its evidence."""
    claim: str
    bridge_axiom_id: str | None = None
    source_doi: str | None = None
    evidence_tier: str = ""
    confidence: float | None = None


class DisclosureSection(BaseModel):
    """One of the 14 TNFD recommended disclosures."""
    disclosure_id: str
    pillar: str
    title: str
    content: str = ""
    populated: bool = False
    gap_reason: str = ""


# ---------------------------------------------------------------------------
# LEAP phase models
# ---------------------------------------------------------------------------

class TNFDLocate(BaseModel):
    """Phase 1 - Locate: Identify nature interface locations."""
    site_name: str
    country: str = ""
    coordinates: dict[str, float] = Field(default_factory=dict)
    area_km2: float | None = None
    biome: str = ""
    habitats: list[HabitatDescriptor] = Field(default_factory=list)
    priority_biodiversity_area: bool = False
    world_heritage_status: bool = False
    designation_year: int | None = None
    management_authority: str = ""
    indigenous_partnership: str = ""


class TNFDEvaluate(BaseModel):
    """Phase 2 - Evaluate: Dependencies, impacts, and ecosystem services."""
    total_esv_usd: float | None = None
    services: list[ServiceDependency] = Field(default_factory=list)
    primary_dependency: str = ""
    species_dependencies: list[SpeciesDependency] = Field(default_factory=list)
    impact_pathways: list[ImpactPathway] = Field(default_factory=list)
    bridge_axioms_applied: list[str] = Field(default_factory=list)


class TNFDAssess(BaseModel):
    """Phase 3 - Assess: Material risks and opportunities."""
    physical_risks: list[RiskAssessment] = Field(default_factory=list)
    transition_risks: list[RiskAssessment] = Field(default_factory=list)
    systemic_risks: list[RiskAssessment] = Field(default_factory=list)
    opportunities: list[Opportunity] = Field(default_factory=list)
    neoli_score: int | None = None
    asset_rating: str = ""
    composite_score: float | None = None
    monte_carlo_summary: dict[str, Any] = Field(default_factory=dict)


class TNFDPrepare(BaseModel):
    """Phase 4 - Prepare: Strategy, targets, metrics, disclosures."""
    governance_sections: list[DisclosureSection] = Field(default_factory=list)
    strategy_sections: list[DisclosureSection] = Field(default_factory=list)
    risk_management_sections: list[DisclosureSection] = Field(default_factory=list)
    metrics_targets_sections: list[DisclosureSection] = Field(default_factory=list)
    metrics: list[MetricEntry] = Field(default_factory=list)
    targets: list[TargetEntry] = Field(default_factory=list)
    provenance_chain: list[ProvenanceEntry] = Field(default_factory=list)
    recommendation: str = ""


# ---------------------------------------------------------------------------
# Top-level disclosure model
# ---------------------------------------------------------------------------

class TNFDDisclosure(BaseModel):
    """Complete TNFD LEAP disclosure for an MPA site."""
    site_name: str
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    framework_version: str = "TNFD v1.0"
    locate: TNFDLocate
    evaluate: TNFDEvaluate
    assess: TNFDAssess
    prepare: TNFDPrepare
