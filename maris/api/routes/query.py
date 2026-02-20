"""Query endpoint - full NL-to-answer pipeline."""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from maris.api.auth import rate_limit_query
from maris.api.models import QueryRequest, QueryResponse, QueryMetadata, EvidenceItem
from maris.axioms.confidence import calculate_response_confidence
from maris.config import get_config
from maris.llm.adapter import LLMAdapter
from maris.provenance.bridge_axiom_registry import BridgeAxiomRegistry
from maris.query.classifier import QueryClassifier, register_dynamic_sites
from maris.query.executor import QueryExecutor
from maris.query.generator import ResponseGenerator
from maris.query.formatter import format_response
from maris.query.validators import build_provenance_summary, extract_numerical_claims
from maris.reasoning.inference_engine import InferenceEngine
from maris.services.ingestion.discovery import discover_case_study_paths, discover_site_names

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])

# Lazy singletons initialised on first request
_llm: LLMAdapter | None = None
_classifier: QueryClassifier | None = None
_executor: QueryExecutor | None = None
_generator: ResponseGenerator | None = None
_axiom_registry: BridgeAxiomRegistry | None = None
_inference_engine: InferenceEngine | None = None
_dynamic_sites_registered = False

_AXIOM_ID_RE = re.compile(r"\bBA-\d{3}\b", re.IGNORECASE)
_SITE_REQUIRED_CATEGORIES = {"site_valuation", "provenance_drilldown", "risk_assessment"}
_STRICT_DETERMINISTIC_CATEGORIES = {
    "site_valuation",
    "provenance_drilldown",
    "risk_assessment",
    "comparison",
    "axiom_explanation",
    "axiom_by_concept",
}
_CATEGORY_HOPS = {
    "site_valuation": 1,
    "provenance_drilldown": 2,
    "axiom_explanation": 2,
    "axiom_by_concept": 2,
    "concept_overview": 2,
    "mechanism_chain": 2,
    "comparison": 1,
    "risk_assessment": 3,
    "open_domain": 3,
}
_CLIENT_ERROR_TYPES = {"validation", "no_results", "unknown_template"}
_PORTFOLIO_SCOPE_TERMS = (
    "all characterized sites",
    "all characterised sites",
    "all sites",
    "across sites",
    "portfolio",
    "combined",
)


# Comprehensive keyword-to-axiom mapping for concept-based queries
_CONCEPT_AXIOM_MAP: list[tuple[str, list[str]]] = [
    (r"tourism|dive|diver|wtp|willingness", ["BA-001"]),
    (r"biomass.*(?:recover|increas|accumul)", ["BA-001", "BA-002"]),
    (r"no.?take|fully.?protect", ["BA-002"]),
    (r"kelp.*(?:carbon|otter|cascade)", ["BA-003"]),
    (r"otter|trophic.?cascade", ["BA-003"]),
    (r"coral.*(?:flood|protect|wave|attenuati)", ["BA-004"]),
    (r"(?:flood|wave|storm).*(?:protect|attenuati|reduct)", ["BA-004", "BA-005"]),
    (r"mangrove.*(?:flood|protect|storm|surge|coast)", ["BA-005"]),
    (r"mangrove.*(?:fish|nursery|spawn)", ["BA-006"]),
    (r"mangrove.*(?:carbon|stock|store|sequest)", ["BA-007"]),
    (r"seagrass.*(?:credit|market)", ["BA-008"]),
    (r"restor.*(?:cost|benefit|roi|return|bcr)", ["BA-009"]),
    (r"kelp.*(?:value|global|esv)", ["BA-010"]),
    (r"(?:climate|mpa).*resilien", ["BA-011"]),
    (r"(?:reef|coral).*(?:degrad|bleach|loss).*(?:fish|revenue)", ["BA-012"]),
    (r"seagrass.*sequest", ["BA-013"]),
    (r"blue.?carbon", ["BA-013", "BA-014", "BA-015", "BA-016"]),
    (r"carbon.*sequest", ["BA-013", "BA-007"]),
    (r"carbon.*(?:credit|market|price|value|trad)", ["BA-014"]),
    (r"habitat.*(?:loss|destruct|deforest).*(?:carbon|emission)", ["BA-015"]),
    (r"(?:carbon|sequest).*(?:perman|revers|buffer)", ["BA-016"]),
]


# Concept ID mapping for mechanism_chain template
_CONCEPT_ID_MAP: list[tuple[str, str]] = [
    (r"blue.?carbon|carbon.?sequest", "BC-001"),
    (r"coastal.?protect|wave.?attenuati|storm.?surge", "BC-002"),
    (r"(?:marine|dive|reef).?tourism|ecotourism", "BC-003"),
    (r"fisher.*(?:product|spillover|biomass)", "BC-004"),
    (r"carbon.?(?:credit|market|trad|price)", "BC-005"),
    (r"biodiversity.*(?:value|insur)", "BC-006"),
    (r"mpa.*(?:effective|outcome|recovery)", "BC-007"),
    (r"(?:ecosystem|habitat).*restor", "BC-008"),
    (r"climate.*resilien", "BC-009"),
    (r"(?:nature|green|blue).?(?:bond|finance|invest)", "BC-010"),
    (r"trophic.?cascade", "BC-011"),
    (r"(?:habitat|reef|coral).*(?:degrad|risk|loss|bleach)", "BC-012"),
    (r"blue.?bond", "BC-013"),
    (r"(?:reef|parametric).?insur", "BC-014"),
    (r"tnfd|disclosure.?framework", "BC-015"),
]


def _extract_concept_id(question: str) -> str:
    """Map a question to a concept_id for mechanism_chain queries."""
    for pattern, concept_id in _CONCEPT_ID_MAP:
        if re.search(pattern, question):
            return concept_id
    return ""


def _extract_concept_term(question: str) -> str:
    """Extract the primary concept term from a question for axiom matching."""
    _TERM_MAP = [
        (r"blue.?carbon|carbon.?sequest", "carbon"),
        (r"mangrove", "mangrove"),
        (r"seagrass", "seagrass"),
        (r"kelp", "kelp"),
        (r"coral", "coral"),
        (r"tourism|dive", "tourism"),
        (r"fisher", "fisheries"),
        (r"(?:flood|coastal|storm).?protect", "protection"),
        (r"restor", "restoration"),
        (r"resilien", "resilience"),
        (r"degrad|bleach", "degradation"),
    ]
    for pattern, term in _TERM_MAP:
        if re.search(pattern, question):
            return term
    words = question.split()
    return max(words, key=len) if words else ""


# Site habitat lookup for response contextualization
_SITE_HABITAT_MAP: dict[str, str] = {
    "Cabo Pulmo National Park": "coral_reef",
    "Shark Bay World Heritage Area": "seagrass_meadow",
    "Ningaloo Coast World Heritage Area": "coral_reef",
    "Belize Barrier Reef Reserve System": "coral_reef",
    "Galapagos Marine Reserve": "mixed",
    "Raja Ampat Marine Park": "coral_reef",
    "Sundarbans Reserve Forest": "mangrove_forest",
    "Aldabra Atoll": "coral_reef",
    "Cispata Bay Mangrove Conservation Area": "mangrove_forest",
}


def _register_runtime_sites() -> None:
    """Load discovered site names into classifier dynamic patterns."""
    global _dynamic_sites_registered
    if _dynamic_sites_registered:
        return

    cfg = get_config()
    try:
        case_paths = discover_case_study_paths(cfg.project_root)
        discovered = discover_site_names(case_paths)
        site_names = sorted({name for name, _ in discovered if name})
        if not site_names:
            logger.warning("No case-study sites discovered for dynamic registration")
            _dynamic_sites_registered = True
            return
        registered = register_dynamic_sites(site_names)
        _dynamic_sites_registered = True
        logger.info(
            "Registered %s dynamic site patterns from %s case studies",
            registered,
            len(case_paths),
        )
    except Exception:
        logger.exception("Failed to register dynamic sites at API startup")


def _extract_axiom_ids(payload: Any) -> set[str]:
    """Recursively extract axiom IDs from nested dict/list payloads."""
    found: set[str] = set()
    if isinstance(payload, dict):
        for value in payload.values():
            found |= _extract_axiom_ids(value)
        return found
    if isinstance(payload, list):
        for item in payload:
            found |= _extract_axiom_ids(item)
        return found
    if isinstance(payload, str):
        return {m.upper() for m in _AXIOM_ID_RE.findall(payload)}
    return found


def _is_portfolio_scope_question(question: str) -> bool:
    """Return True when a prompt asks for multi-site/portfolio aggregation."""
    q = question.lower()
    return any(term in q for term in _PORTFOLIO_SCOPE_TERMS)


def _build_inference_trace(
    axiom_ids: set[str],
    site: str | None,
) -> tuple[list[dict[str, Any]], str, list[str]]:
    """Build a deterministic inference trace from resolved axiom IDs."""
    assert _axiom_registry is not None

    axioms = [
        axiom
        for aid in sorted(axiom_ids)
        if (axiom := _axiom_registry.get(aid)) is not None
    ]
    if not axioms:
        return [], "", []

    temp_engine = InferenceEngine()
    temp_engine.register_axioms(axioms)

    start_domain = next((a.input_domain for a in axioms if a.input_domain), "ecological")
    facts = {start_domain: {"site": site or "unspecified"}}
    steps = temp_engine.forward_chain(facts, max_steps=max(len(axioms), 1))

    if not steps:
        return [], "", []

    trace: list[dict[str, Any]] = []
    lines: list[str] = []
    provisional_axioms: set[str] = set()
    for idx, step in enumerate(steps, start=1):
        axiom = _axiom_registry.get(step.axiom_id)
        source_count = len(axiom.evidence_sources) if axiom else 0
        provisional = source_count < 2
        if provisional:
            provisional_axioms.add(step.axiom_id)

        trace.append({
            "step": idx,
            "axiom_id": step.axiom_id,
            "rule_id": step.rule_id,
            "input_fact": step.input_fact,
            "output_fact": step.output_fact,
            "coefficient": step.coefficient,
            "confidence": step.confidence,
            "source_doi": step.source_doi,
            "provisional": provisional,
        })
        lines.append(
            f"{idx}. {step.axiom_id}: {step.input_fact} -> {step.output_fact} "
            f"(doi={step.source_doi or 'unavailable'})"
        )

    return trace, "\n".join(lines), sorted(provisional_axioms)


def _init_components():
    global _llm, _classifier, _executor, _generator, _axiom_registry, _inference_engine
    if _llm is None:
        _llm = LLMAdapter(get_config())
        _classifier = QueryClassifier(llm=_llm)
        _executor = QueryExecutor()
        _generator = ResponseGenerator(llm=_llm)

    _register_runtime_sites()

    if _axiom_registry is None or _inference_engine is None:
        cfg = get_config()
        _axiom_registry = BridgeAxiomRegistry(
            templates_path=cfg.schemas_dir / "bridge_axiom_templates.json",
            evidence_path=cfg.export_dir / "bridge_axioms.json",
        )
        _inference_engine = InferenceEngine()
        _inference_engine.register_axioms(_axiom_registry.get_all())


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(rate_limit_query)])
def query(request: QueryRequest):
    """Classify a natural-language question, run Cypher, and return a grounded answer."""
    _init_components()
    assert _classifier and _executor and _generator and _axiom_registry and _inference_engine  # narrowing for type checker

    start = time.monotonic()

    # 1. Classify
    classification = _classifier.classify(request.question)
    category = classification["category"]
    site = request.site or classification.get("site")

    # 2. Build parameters for the Cypher template
    params: dict = {}
    if category in _SITE_REQUIRED_CATEGORIES:
        if not site:
            logger.info("Siteless %s query coerced to open_domain", category)
            category = "open_domain"
        if category in _SITE_REQUIRED_CATEGORIES and site:
            params["site_name"] = site
    elif category == "axiom_explanation":
        # Try to extract explicit axiom ID from question
        m = re.search(r"BA-\d{3}", request.question, re.IGNORECASE)
        if m:
            params["axiom_id"] = m.group(0).upper()
        else:
            # Infer axiom(s) from question keywords using concept map
            q_lower = request.question.lower()
            matched_axioms: list[str] = []
            for pattern, axiom_ids in _CONCEPT_AXIOM_MAP:
                if re.search(pattern, q_lower):
                    for aid in axiom_ids:
                        if aid not in matched_axioms:
                            matched_axioms.append(aid)

            if len(matched_axioms) == 1:
                # Single axiom match - use standard template
                params["axiom_id"] = matched_axioms[0]
            elif matched_axioms:
                # Multiple axioms match - use axiom_by_concept template
                concept_term = _extract_concept_term(q_lower)
                category = "axiom_by_concept"
                params["concept_term"] = concept_term
                params["axiom_ids"] = matched_axioms
            else:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Ambiguous axiom query. Please specify a BA-XXX ID or a clearer concept "
                        "(e.g., 'Explain BA-013')."
                    ),
                )
    elif category == "concept_explanation":
        # Map question to concept for mechanism_chain or concept_overview template
        q_lower = request.question.lower()
        concept_id = _extract_concept_id(q_lower)
        if concept_id:
            category = "mechanism_chain"
            params["concept_id"] = concept_id
        else:
            # Use concept_overview with search term
            search_term = _extract_concept_term(q_lower)
            if len(search_term.strip()) < 3:
                raise HTTPException(
                    status_code=422,
                    detail="Concept query is ambiguous. Please specify a clearer mechanism or concept.",
                )
            category = "concept_overview"
            params["search_term"] = search_term
            params["concept_id"] = ""  # empty, won't match by ID
    elif category == "comparison":
        # Use multi-site list from classifier when available
        sites = classification.get("sites", [])
        if len(sites) >= 2:
            params["site_names"] = sites
        elif _is_portfolio_scope_question(request.question):
            logger.info("Portfolio-scope comparison query coerced to open_domain")
            category = "open_domain"
        else:
            raise HTTPException(
                status_code=422,
                detail="Comparison queries must specify at least two sites.",
            )
    elif category == "scenario_analysis":
        # Scenario analysis uses its own engine pipeline, bypassing graph execution.
        # Lazy imports to avoid circular dependencies and allow incremental build.
        try:
            from maris.scenario.scenario_parser import parse_scenario_request
            from maris.scenario.counterfactual_engine import run_counterfactual
            from maris.scenario.climate_scenarios import run_climate_scenario
            from maris.scenario.tipping_point_analyzer import get_tipping_point_site_report
            from maris.scenario.blue_carbon_revenue import compute_blue_carbon_revenue
            from maris.scenario.counterfactual_engine import _load_site_data as _load_cf_data
        except ImportError:
            logger.warning("Scenario modules not yet available")
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return QueryResponse(
                answer="Scenario analysis module is not yet initialized. Please try again later.",
                confidence=0.0,
                evidence=[],
                axioms_used=[],
                graph_path=[],
                caveats=["Scenario module not available"],
                verified_claims=[],
                unverified_claims=[],
                evidence_count=0,
                doi_citation_count=0,
                evidence_completeness_score=0.0,
                provenance_warnings=["Scenario module import failed"],
                provenance_risk="high",
                query_metadata=QueryMetadata(
                    category="scenario_analysis",
                    classification_confidence=classification.get("confidence", 0.0),
                    template_used="scenario_analysis:unavailable",
                    response_time_ms=elapsed_ms,
                ),
            )

        scenario_req = parse_scenario_request(request.question, site, classification)

        if scenario_req.scenario_type == "counterfactual":
            result = run_counterfactual(scenario_req)
        elif scenario_req.scenario_type == "climate":
            result = run_climate_scenario(scenario_req)
        elif scenario_req.scenario_type == "tipping_point":
            site_name = scenario_req.site_scope[0] if scenario_req.site_scope else ""
            site_data = _load_cf_data(site_name) if site_name else None
            if site_data is None:
                result = {
                    "answer": "No site data available for tipping point analysis. Please specify a site.",
                    "confidence": 0.0, "caveats": ["Site not found"],
                    "axioms_used": [], "provenance_risk": "high",
                }
            else:
                report = get_tipping_point_site_report(site_data)
                if report.get("applicable"):
                    answer = (
                        f"{report['site_name']} current fish biomass: {report['current_biomass_kg_ha']:.0f} kg/ha "
                        f"(reef function: {report['reef_function_current']:.1%}, {report['nearest_threshold']['name']} zone). "
                        f"{report['proximity_description']} "
                        f"ESV at collapse threshold (150 kg/ha): ${report['esv_at_collapse']:,.0f}/yr "
                        f"vs current ${report['esv_current']:,.0f}/yr. "
                        f"Source: McClanahan et al. 2011 (doi:{report['source_doi']})"
                    )
                    result = {
                        "answer": answer, "confidence": 0.80,
                        "caveats": ["McClanahan piecewise function calibrated on Indo-Pacific reefs",
                                    "Biomass derived from recovery_ratio * 200 kg/ha pre-protection baseline (Aburto-Oropeza et al. 2011)"],
                        "axioms_used": ["BA-036", "BA-037", "BA-038", "BA-039"],
                        "provenance_risk": "medium",
                        "scenario_request": scenario_req.model_dump(),
                    }
                else:
                    answer = (
                        f"Tipping point analysis for {report['site_name']}: {report.get('reason', 'Not applicable')}. "
                        f"Habitat type: {report.get('habitat_type', 'unknown')}. "
                        f"The McClanahan et al. 2011 piecewise function (doi:10.1073/pnas.1106861108) applies to coral reef "
                        f"fish biomass. For mangrove habitats, deforestation thresholds apply; for seagrass, heatwave-driven "
                        f"dieback thresholds per Arias-Ortiz et al. 2018 (doi:10.1038/s41558-018-0096-y)."
                    )
                    result = {
                        "answer": answer, "confidence": 0.60,
                        "caveats": ["Tipping point analysis requires site-specific biomass survey data"],
                        "axioms_used": ["BA-036", "BA-040"], "provenance_risk": "medium",
                        "scenario_request": scenario_req.model_dump(),
                    }
        elif scenario_req.scenario_type == "market":
            site_name = scenario_req.site_scope[0] if scenario_req.site_scope else ""
            site_data = _load_cf_data(site_name) if site_name else None
            if site_data is None:
                result = {
                    "answer": "No site data available for blue carbon revenue analysis.",
                    "confidence": 0.0, "caveats": ["Site not found"],
                    "axioms_used": [], "provenance_risk": "high",
                }
            else:
                # Map requested carbon price to nearest price scenario key
                carbon_price = scenario_req.assumptions.get("carbon_price_usd", 25.25)
                from maris.scenario.constants import CARBON_PRICE_SCENARIOS
                price_scenario = min(
                    CARBON_PRICE_SCENARIOS,
                    key=lambda k: abs(CARBON_PRICE_SCENARIOS[k]["price_usd"] - carbon_price),
                )
                rev = compute_blue_carbon_revenue(
                    site_name, site_data,
                    price_scenario=price_scenario,
                    target_year=scenario_req.target_year or 2030,
                )
                if "error" in rev:
                    answer = (
                        f"{site_name} does not have blue carbon habitat eligible for voluntary carbon market credits "
                        f"in the current knowledge base ({rev['error']}). "
                        f"Blue carbon credits require mangrove forest or seagrass meadow habitat with verified area data. "
                        f"Reference: Blue Carbon Initiative (bluecarboninitiative.org)."
                    )
                    result = {
                        "answer": answer, "confidence": 0.70,
                        "caveats": ["No eligible blue carbon habitat detected for this site"],
                        "axioms_used": [], "provenance_risk": "medium",
                    }
                else:
                    answer = (
                        f"{site_name} could generate approximately ${rev['annual_revenue_usd']:,.0f}/yr in blue carbon credits "
                        f"at ${rev['price_usd']}/tCO2e ({price_scenario} price scenario). "
                        f"Based on {rev['habitat_area_ha']:,.0f} ha of {rev['habitat_type'].replace('_', ' ')} "
                        f"at {rev['seq_rate_tco2_ha_yr']:.1f} tCO2/ha/yr (mid estimate, 60% Verra-verified). "
                        f"Range: ${rev['annual_revenue_range']['low']:,.0f} to ${rev['annual_revenue_range']['high']:,.0f}/yr. "
                        f"Source: {rev.get('source', 'Blue Carbon Initiative')}."
                    )
                    result = {
                        "answer": answer,
                        "confidence": 0.75,
                        "caveats": [
                            "Revenue based on global average sequestration rates - site-specific measurement recommended",
                            "Verra VCS verification adds 12-18 months and certification costs before credit issuance",
                            "Carbon price reflects voluntary market; CORSIA compliance market prices may differ",
                        ],
                        "axioms_used": ["BA-007", "BA-017"],
                        "provenance_risk": "medium",
                        "scenario_request": scenario_req.model_dump(),
                        "annual_revenue_usd": rev["annual_revenue_usd"],
                        "revenue_range": rev["annual_revenue_range"],
                    }
        else:
            result = {
                "answer": (
                    f"Scenario type '{scenario_req.scenario_type}' is not yet supported. "
                    f"Supported types: counterfactual, climate (SSP), tipping_point, market (blue carbon revenue). "
                    f"Please rephrase your question using one of these scenario types."
                ),
                "confidence": 0.0,
                "provenance_risk": "high",
                "category": "scenario_analysis",
                "caveats": [f"Scenario type '{scenario_req.scenario_type}' not implemented"],
                "axioms_used": [],
            }

        # Convert Pydantic ScenarioResponse to dict for uniform .get() access
        if hasattr(result, "model_dump"):
            result = result.model_dump()

        elapsed_ms = int((time.monotonic() - start) * 1000)
        # Return scenario result as QueryResponse
        return QueryResponse(
            answer=result.get("answer", "Scenario analysis complete."),
            confidence=result.get("confidence", 0.0),
            evidence=[],
            axioms_used=result.get("axioms_used", []),
            graph_path=[],
            caveats=result.get("caveats", []),
            verified_claims=[],
            unverified_claims=[],
            evidence_count=0,
            doi_citation_count=0,
            evidence_completeness_score=0.0,
            provenance_warnings=result.get("provenance_warnings", []),
            provenance_risk=result.get("provenance_risk", "high"),
            scenario_request=result.get("scenario_request"),
            annual_revenue_usd=result.get("annual_revenue_usd"),
            revenue_range=result.get("revenue_range"),
            query_metadata=QueryMetadata(
                category="scenario_analysis",
                classification_confidence=classification.get("confidence", 0.0),
                template_used=f"scenario_analysis:{scenario_req.scenario_type}",
                response_time_ms=elapsed_ms,
            ),
        )

    # 3. Execute with strict strategy enforcement
    graph_result = _executor.execute_with_strategy(
        category,
        params,
        question=request.question,
        site_name=site,
    )
    if graph_result.get("error"):
        error_type = graph_result.get("error_type", "execution_failed")
        if category == "open_domain" and error_type == "no_results":
            elapsed_ms = int((time.monotonic() - start) * 1000)
            formatted = format_response({
                "answer": (
                    "Insufficient citation-grade graph context for this open-domain query. "
                    "Please provide a specific site, axiom ID, or mechanism."
                ),
                "confidence": 0.0,
                "evidence": [],
                "axioms_used": [],
                "graph_path": [],
                "caveats": [graph_result["error"]],
                "verified_claims": [],
                "unverified_claims": [],
                "evidence_count": 0,
                "doi_citation_count": 0,
                "evidence_completeness_score": 0.0,
                "provenance_warnings": [graph_result["error"]],
                "provenance_risk": "high",
            })
            return QueryResponse(
                answer=formatted["answer"],
                confidence=formatted["confidence"],
                evidence=[],
                axioms_used=[],
                graph_path=[],
                caveats=formatted["caveats"],
                verified_claims=formatted.get("verified_claims", []),
                unverified_claims=formatted.get("unverified_claims", []),
                confidence_breakdown=formatted.get("confidence_breakdown"),
                evidence_count=formatted.get("evidence_count", 0),
                doi_citation_count=formatted.get("doi_citation_count", 0),
                evidence_completeness_score=formatted.get("evidence_completeness_score", 0.0),
                provenance_warnings=formatted.get("provenance_warnings", []),
                provenance_risk=formatted.get("provenance_risk", "high"),
                query_metadata=QueryMetadata(
                    category=category,
                    classification_confidence=classification.get("confidence", 0.0),
                    template_used=f"{category}:safe_open_domain_retrieval",
                    response_time_ms=elapsed_ms,
                ),
            )
        status_code = 422 if error_type in _CLIENT_ERROR_TYPES else 500
        raise HTTPException(status_code=status_code, detail=graph_result["error"])

    provenance_edges: list[dict[str, Any]] = []
    if category != "open_domain":
        provenance_edges = _executor.get_provenance_edges(category, params)

    if category in _STRICT_DETERMINISTIC_CATEGORIES and not provenance_edges:
        raise HTTPException(
            status_code=422,
            detail=(
                "No deterministic graph traversal path was found for this query. "
                "Please refine your request with explicit site/axiom context."
            ),
        )

    explanation_chain: str | None = None
    inference_trace: list[dict[str, Any]] = []
    provisional_axioms: list[str] = []
    if category in _STRICT_DETERMINISTIC_CATEGORIES:
        axiom_ids = _extract_axiom_ids(graph_result) | _extract_axiom_ids(provenance_edges)
        if not axiom_ids:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No bridge axioms were resolved from the graph path. "
                    "Please provide a query with explicit axiom or mechanism context."
                ),
            )

        inference_trace, explanation_chain, provisional_axioms = _build_inference_trace(
            axiom_ids,
            site,
        )
        if not inference_trace:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Deterministic inference chain could not be constructed from the resolved axioms. "
                    "Please refine your question."
                ),
            )

    # 4. Generate response via LLM
    # Inject site context for habitat-aware responses
    site_context = ""
    if site and site in _SITE_HABITAT_MAP:
        habitat = _SITE_HABITAT_MAP[site]
        site_context = f" [Site context: {site} ({habitat.replace('_', ' ')})]"

    try:
        raw = _generator.generate(
            question=request.question + site_context,
            graph_context=graph_result,
            category=category,
            explanation_chain=explanation_chain,
        )
    except Exception:
        logger.exception("Response generation failed for category=%s", category)
        raise HTTPException(status_code=500, detail="Response generation failed")

    # 5. Format
    try:
        formatted = format_response(raw)
    except Exception:
        logger.exception("Response formatting failed")
        raise HTTPException(status_code=500, detail="Response formatting failed")

    if not formatted.get("axioms_used") and inference_trace:
        formatted["axioms_used"] = [s["axiom_id"] for s in inference_trace]

    if provisional_axioms:
        formatted["caveats"] = list(formatted.get("caveats", []))
        formatted["caveats"].append(
            "Provisional axioms (Two-Key rule requires independent corroboration): "
            + ", ".join(provisional_axioms)
        )

    if classification.get("caveats"):
        formatted["caveats"] = list(formatted.get("caveats", [])) + classification["caveats"]

    # 6. Build structured graph_path from actual Neo4j traversal (not LLM text)
    graph_path = []
    if request.include_graph_path:
        graph_path = list(provenance_edges)
        if inference_trace:
            graph_path.extend({
                "from_node": step["axiom_id"],
                "from_type": "BridgeAxiom",
                "relationship": "INFERRED_AS",
                "to_node": step["output_fact"],
                "to_type": "DerivedFact",
            } for step in inference_trace)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    visible_evidence_payload = formatted["evidence"][:request.max_evidence_sources]
    evidence = [EvidenceItem(**e) for e in visible_evidence_payload]

    visible_evidence_dicts = [item.model_dump() for item in evidence]
    provenance_summary = build_provenance_summary(visible_evidence_dicts, formatted.get("answer", ""))
    provenance_summary["has_numeric_claims"] = bool(
        extract_numerical_claims(formatted.get("answer", ""))
    )
    confidence_breakdown = calculate_response_confidence(
        visible_evidence_dicts,
        n_hops=_CATEGORY_HOPS.get(category, 1),
        provenance_summary=provenance_summary,
    )
    formatted["confidence"] = confidence_breakdown["composite"]

    return QueryResponse(
        answer=formatted["answer"],
        confidence=formatted["confidence"],
        evidence=evidence,
        axioms_used=formatted["axioms_used"],
        graph_path=graph_path,
        caveats=formatted["caveats"],
        verified_claims=formatted.get("verified_claims", []),
        unverified_claims=formatted.get("unverified_claims", []),
        confidence_breakdown=confidence_breakdown,
        evidence_count=provenance_summary["evidence_count"],
        doi_citation_count=provenance_summary["doi_citation_count"],
        evidence_completeness_score=provenance_summary["evidence_completeness_score"],
        provenance_warnings=provenance_summary["provenance_warnings"],
        provenance_risk=provenance_summary["provenance_risk"],
        query_metadata=QueryMetadata(
            category=category,
            classification_confidence=classification.get("confidence", 0.0),
            template_used=f"{category}:{graph_result.get('strategy', 'unknown')}",
            response_time_ms=elapsed_ms,
        ),
    )
