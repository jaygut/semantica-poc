"""Pydantic request/response models for the MARIS API."""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

class EvidenceItem(BaseModel):
    doi: str | None = None
    doi_url: str | None = None
    title: str = ""
    year: int | None = None
    tier: str = ""
    page_ref: str | None = None
    quote: str = ""


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str
    site: str | None = None
    include_graph_path: bool = True
    max_evidence_sources: int = Field(default=5, ge=1, le=20)


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
    query_metadata: QueryMetadata = QueryMetadata()


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
    start_name: str
    max_hops: int = Field(default=3, ge=1, le=6)
    result_limit: int = Field(default=25, ge=1, le=100)


class CompareRequest(BaseModel):
    site_names: list[str] = Field(..., min_length=2)


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
