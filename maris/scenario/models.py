"""Pydantic v2 models for scenario intelligence request/response types.

Importable without Neo4j, LLM, or any running service.
"""

from pydantic import BaseModel
from typing import Any, Literal


class ScenarioRequest(BaseModel):
    scenario_type: Literal["counterfactual", "climate", "intervention", "shock", "tipping_point", "market", "portfolio"]
    site_scope: list[str]
    time_horizon_years: int = 10
    assumptions: dict[str, Any] = {}
    compare_against: str = "baseline"
    ssp_scenario: str | None = None  # "SSP1-2.6" | "SSP2-4.5" | "SSP5-8.5"
    target_year: int | None = None    # 2030, 2040, 2050, 2075, 2100


class ScenarioDelta(BaseModel):
    metric: str
    baseline_value: float
    scenario_value: float
    absolute_change: float
    percent_change: float
    unit: str = "USD"


class PropagationStep(BaseModel):
    axiom_id: str
    description: str
    input_value: float
    input_parameter: str
    output_value: float
    output_parameter: str
    coefficient: float | None = None
    source_doi: str | None = None


class ScenarioUncertainty(BaseModel):
    p5: float
    p50: float
    p95: float
    dominant_driver: str
    n_simulations: int = 10_000


class ScenarioResponse(BaseModel):
    scenario_request: ScenarioRequest
    baseline_case: dict[str, Any]
    scenario_case: dict[str, Any]
    deltas: list[ScenarioDelta]
    propagation_trace: list[PropagationStep]
    uncertainty: ScenarioUncertainty
    confidence: float
    confidence_penalties: list[dict[str, Any]]
    scenario_validity: Literal["in_domain", "partially_out_of_domain", "out_of_domain"]
    tipping_point_proximity: str | None = None
    answer: str  # LLM-synthesized narrative from computed outputs
    caveats: list[str]
    axioms_used: list[str]
