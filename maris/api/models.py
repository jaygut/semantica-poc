"""Pydantic request/response models for the MARIS API."""

import re

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    doi: str | None = None
    doi_url: str | None = None
    doi_valid: bool | None = None
    doi_verification_status: str | None = None
    doi_verification_reason: str | None = None
    doi_resolver: str | None = None
    title: str = ""
    year: int | None = None
    tier: str = "N/A"
    page_ref: str | None = None
    quote: str = ""

    @field_validator("title", "quote", mode="before")
    @classmethod
    def coerce_none_to_empty(cls, v):
        return v if v is not None else ""

    @field_validator("tier", mode="before")
    @classmethod
    def normalise_tier(cls, v):
        if v is None:
            return "N/A"
        value = str(v).strip().upper()
        if value in {"T1", "T2", "T3", "T4"}:
            return value
        return "N/A"


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    site: str | None = Field(default=None, max_length=100)
    include_graph_path: bool = True
    max_evidence_sources: int = Field(default=5, ge=1, le=20)

    @field_validator("site")
    @classmethod
    def validate_site(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^[A-Za-z0-9 \-'.]+$", v):
            raise ValueError("Site name may only contain letters, numbers, spaces, hyphens, apostrophes, and periods.")
        return v


class QueryMetadata(BaseModel):
    category: str = ""
    classification_confidence: float = 0.0
    template_used: str = ""
    response_time_ms: int = 0


class QueryResponse(BaseModel):
    answer: str
    confidence: float = 0.0
    evidence: list[EvidenceItem] = []
    axioms_used: list[str] = []
    graph_path: list[dict] = []
    caveats: list[str] = []
    verified_claims: list[str] = []
    unverified_claims: list[str] = []
    confidence_breakdown: dict | None = None
    evidence_count: int = 0
    doi_citation_count: int = 0
    evidence_completeness_score: float = 0.0
    provenance_warnings: list[str] = []
    provenance_risk: str = "high"
    query_metadata: QueryMetadata = QueryMetadata()
    scenario_request: dict | None = None  # populated for scenario_analysis responses
    annual_revenue_usd: float | None = None  # populated for market (blue carbon) scenarios
    revenue_range: dict | None = None        # {"low": float, "high": float}


# ---------------------------------------------------------------------------
# Graph / Site / Axiom
# ---------------------------------------------------------------------------

class SiteResponse(BaseModel):
    site: str
    total_esv_usd: float | None = None
    biomass_ratio: float | None = None
    neoli_score: int | None = None
    asset_rating: str | None = None
    services: list[dict] = []
    evidence: list[EvidenceItem] = []


class AxiomResponse(BaseModel):
    axiom_id: str
    name: str = ""
    category: str = ""
    description: str = ""
    coefficients: dict = {}
    evidence: list[EvidenceItem] = []
    applicable_sites: list[str] = []
    translated_services: list[str] = []


class TraverseRequest(BaseModel):
    start_name: str = Field(..., min_length=1, max_length=100)
    max_hops: int = Field(default=3, ge=1, le=6)
    result_limit: int = Field(default=25, ge=1, le=1000)

    @field_validator("start_name")
    @classmethod
    def validate_start_name(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9 \-'.]+$", v):
            raise ValueError("start_name may only contain letters, numbers, spaces, hyphens, apostrophes, and periods.")
        return v


class CompareRequest(BaseModel):
    site_names: list[str] = Field(..., min_length=2)

    @field_validator("site_names")
    @classmethod
    def validate_site_names(cls, v: list[str]) -> list[str]:
        for name in v:
            if not re.match(r"^[A-Za-z0-9 \-'.]+$", name):
                raise ValueError(f"Invalid site name: '{name}'. Only letters, numbers, spaces, hyphens, apostrophes, and periods are allowed.")
        return v


class CompareResponse(BaseModel):
    sites: list[dict] = []


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "healthy"
    neo4j_connected: bool = False
    llm_available: bool = False
    graph_stats: dict = {}
