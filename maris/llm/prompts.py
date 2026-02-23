"""Prompt templates for MARIS LLM interactions."""

# ---------------------------------------------------------------------------
# Query classification
# ---------------------------------------------------------------------------

QUERY_CLASSIFICATION_PROMPT = """\
You are the query classifier for MARIS (Marine Asset Risk Intelligence System).
Given a user question about marine natural capital, classify it into exactly ONE category.

Categories:
- site_valuation: Questions about a specific site's ecosystem service values, ESV breakdown, or asset rating.
- provenance_drilldown: Questions asking for the evidence, DOIs, or scientific backing for a claim.
- axiom_explanation: Questions about HOW ecological states translate to financial values (bridge axiom mechanics).
- comparison: Questions comparing two or more sites on metrics like NEOLI score, biomass, or ESV.
- risk_assessment: Questions about degradation scenarios, climate risk, or what-if analyses.

Also extract:
- site: The site name mentioned (or null if none).
- metrics: List of metrics mentioned (e.g. biomass, ESV, NEOLI, tourism, carbon).
- confidence: Your confidence in the classification (0.0-1.0).

User question: {question}

Respond with JSON only:
{{"category": "...", "site": "...", "metrics": [...], "confidence": 0.0}}
"""



# ---------------------------------------------------------------------------
# Response synthesis
# ---------------------------------------------------------------------------

RESPONSE_SYNTHESIS_PROMPT = """\
You are the response synthesizer for MARIS, a marine natural capital intelligence system.
Your job is to produce a graph-grounded answer from Neo4j query results.

HARD CONSTRAINTS - VIOLATION OF ANY RULE INVALIDATES THE RESPONSE:
1. NO INVENTION: Every numerical claim (dollar amounts, percentages, ratios) MUST appear in the graph context below. Do not fabricate, estimate, or recall numbers from training data.
2. EVIDENCE SELECTION: Populate the "evidence" JSON array by SELECTING 3-5 items directly from the "evidence" array in the graph context below. Copy the doi, title, year, and tier values exactly as they appear. NEVER write "source DOI unavailable", "N/A", or any invented string as a doi value. If no evidence array is present, return an empty evidence list.
3. UNCERTAINTY MANDATE: Where confidence intervals appear in the graph context (ci_low/ci_high), include them in the answer. If absent, add caveat: "No confidence interval available for this estimate."
4. CAVEAT PROPAGATION: Include any caveats from the axioms or data freshness status.
5. STALENESS FLAG: If measurement_year or data_freshness_status appears in the context and data is older than 5 years from 2026, add caveat: "Data from [year] - [N] years old."
6. ZERO HALLUCINATION: If the graph context does not contain sufficient data to answer the question, say "Insufficient data" rather than guessing.
7. CONFIDENCE CALIBRATION: Use the evidence tier to set confidence. With multiple T1 peer-reviewed sources supporting the claim, set confidence to 0.75-0.90. With T2 sources only, 0.55-0.75. With no usable evidence, 0.0.
8. PROVENANCE COMPLETENESS: Copy tier and year values exactly from the selected evidence items. Do not substitute "N/A" unless that is the actual value in the graph context.
9. DETERMINISTIC SAFETY: If the evidence array in the graph context is empty, return an insufficiency answer and an empty evidence list.

RESPONSE FORMAT: Return ONLY valid JSON with no additional text.
User question: {question}
Query category: {category}

Graph context (Neo4j results):
{graph_context}

Respond with JSON:
{{
  "answer": "Your synthesized answer. Only use numbers from the graph context.",
  "confidence": 0.85,
  "evidence": [{{"doi": "10.xxxx/yyyy", "title": "Paper title", "year": 2024, "tier": "T1", "finding": "Specific finding that supports the answer"}}],
  "axioms_used": ["BA-XXX"],
  "caveats": ["Any limitations, data age warnings, or missing information"],
  "graph_path": ["Node1 -[REL]-> Node2"]
}}
"""

# ---------------------------------------------------------------------------
# Entity extraction (reference, shared with Phase 2)
# ---------------------------------------------------------------------------

ENTITY_EXTRACTION_PROMPT = """\
Extract marine ecology entities from the text below. For each entity return:
- type: one of Species, Habitat, MPA, EcosystemService, FinancialInstrument, Framework, Concept, TrophicNode
- name: canonical name
- properties: dict of key properties with values
- confidence: 0.0-1.0

Text:
{text}

Respond with JSON array of entities.
"""

# ---------------------------------------------------------------------------
# Relationship extraction (reference, shared with Phase 2)
# ---------------------------------------------------------------------------

RELATIONSHIP_EXTRACTION_PROMPT = """\
Given the entities and source text below, extract relationships between them.
Valid relationship types: GENERATES, EVIDENCED_BY, APPLIES_TO, TRANSLATES, DERIVED_FROM, LOCATED_IN, PREYS_ON

For each relationship return:
- source: entity name
- target: entity name
- type: relationship type
- properties: dict (e.g. weight, evidence_text)
- confidence: 0.0-1.0

Entities:
{entities}

Text:
{text}

Respond with JSON array of relationships.
"""

# ---------------------------------------------------------------------------
# Axiom discovery - cross-domain coefficient extraction
# ---------------------------------------------------------------------------

AXIOM_DISCOVERY_PROMPT = """\
You are a scientific data extraction system for marine natural capital research.
Extract all quantitative ecological-to-financial or ecological-to-service
relationships from the abstract below.

ABSTRACT (DOI: {doi}):
---
{abstract}
---

For each cross-domain quantitative relationship found, provide:
1. ecological_metric: The ecological input (e.g. "fish biomass", "seagrass area", "coral cover")
2. financial_metric: The financial or service output (e.g. "tourism revenue", "carbon credit value", "fisheries yield")
3. coefficient: The numeric coefficient, multiplier, rate, or percentage (as a float)
4. unit: The unit of the coefficient (e.g. "%", "x", "tCO2/ha/yr", "USD/ha", "million")
5. confidence: Your confidence in this extraction (high, medium, or low)
6. quote: The exact sentence or phrase from the abstract supporting this relationship (max 200 chars)

Rules:
- Only extract relationships that cross domains (ecological -> financial/service)
- The coefficient must be explicitly stated in the text, not inferred
- If no cross-domain quantitative relationships are found, return []

Return ONLY a JSON array. Example:
[
  {{
    "ecological_metric": "fish biomass recovery",
    "financial_metric": "dive tourism revenue",
    "coefficient": 84.0,
    "unit": "%",
    "confidence": "high",
    "quote": "divers willing to pay up to 84% more for higher biomass sites"
  }}
]
"""
