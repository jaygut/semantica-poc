"""Query endpoint - full NL-to-answer pipeline."""

import logging
import re
import time

from fastapi import APIRouter, Depends, HTTPException

from maris.api.auth import rate_limit_query
from maris.api.models import QueryRequest, QueryResponse, QueryMetadata, EvidenceItem
from maris.config import get_config
from maris.llm.adapter import LLMAdapter
from maris.query.classifier import QueryClassifier
from maris.query.executor import QueryExecutor
from maris.query.generator import ResponseGenerator
from maris.query.formatter import format_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["query"])

# Lazy singletons initialised on first request
_llm: LLMAdapter | None = None
_classifier: QueryClassifier | None = None
_executor: QueryExecutor | None = None
_generator: ResponseGenerator | None = None


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
    "Ningaloo Coast": "coral_reef",
    "Belize Barrier Reef Reserve System": "coral_reef",
    "Galapagos Marine Reserve": "mixed",
    "Raja Ampat MPA Network": "coral_reef",
    "Sundarbans Reserve Forest": "mangrove_forest",
    "Aldabra Atoll": "coral_reef",
    "Cispata Bay MPA": "mangrove_forest",
}


def _init_components():
    global _llm, _classifier, _executor, _generator
    if _llm is None:
        _llm = LLMAdapter(get_config())
        _classifier = QueryClassifier(llm=_llm)
        _executor = QueryExecutor()
        _generator = ResponseGenerator(llm=_llm)


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(rate_limit_query)])
def query(request: QueryRequest):
    """Classify a natural-language question, run Cypher, and return a grounded answer."""
    _init_components()
    assert _classifier and _executor and _generator  # narrowing for type checker

    start = time.monotonic()

    # 1. Classify
    classification = _classifier.classify(request.question)
    category = classification["category"]
    site = request.site or classification.get("site")

    # 2. Build parameters for the Cypher template
    params: dict = {}
    if category in ("site_valuation", "provenance_drilldown", "risk_assessment"):
        if not site:
            # Default to primary reference site for general questions
            site = "Cabo Pulmo National Park"
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
                # No axiom match - fall back to provenance with site context
                category = "provenance_drilldown"
                if not site:
                    site = "Cabo Pulmo National Park"
                params["site_name"] = site
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
            category = "concept_overview"
            params["search_term"] = search_term
            params["concept_id"] = ""  # empty, won't match by ID
    elif category == "comparison":
        # Use multi-site list from classifier when available
        sites = classification.get("sites", [])
        if len(sites) >= 2:
            params["site_names"] = sites
        elif site:
            params["site_names"] = [site]
        else:
            # Default to all fully characterized sites
            params["site_names"] = [
                "Cabo Pulmo National Park",
                "Shark Bay World Heritage Area",
            ]

    # 3. Execute Cypher
    graph_result = _executor.execute(category, params)
    if graph_result.get("error"):
        raise HTTPException(status_code=500, detail=graph_result["error"])

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

    # 6. Build structured graph_path from actual Neo4j traversal (not LLM text)
    graph_path = []
    if request.include_graph_path:
        graph_path = _executor.get_provenance_edges(category, params)

    elapsed_ms = int((time.monotonic() - start) * 1000)

    evidence = [EvidenceItem(**e) for e in formatted["evidence"][:request.max_evidence_sources]]

    return QueryResponse(
        answer=formatted["answer"],
        confidence=formatted["confidence"],
        evidence=evidence,
        axioms_used=formatted["axioms_used"],
        graph_path=graph_path,
        caveats=formatted["caveats"],
        verified_claims=formatted.get("verified_claims", []),
        unverified_claims=formatted.get("unverified_claims", []),
        confidence_breakdown=formatted.get("confidence_breakdown"),
        query_metadata=QueryMetadata(
            category=category,
            classification_confidence=classification.get("confidence", 0.0),
            template_used=category,
            response_time_ms=elapsed_ms,
        ),
    )
