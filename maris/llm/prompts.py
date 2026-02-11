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
# Cypher generation
# ---------------------------------------------------------------------------

CYPHER_GENERATION_PROMPT = """\
You are a Cypher query generator for a Neo4j marine natural capital knowledge graph.

Node labels: Document, Species, MPA, Habitat, EcosystemService, FinancialInstrument, Framework, BridgeAxiom, Concept, TrophicNode
Relationship types: GENERATES, EVIDENCED_BY, APPLIES_TO, TRANSLATES, DERIVED_FROM, LOCATED_IN, PREYS_ON

Key properties:
- MPA: name, total_esv_usd, biomass_ratio, neoli_score, asset_rating
- EcosystemService: service_name, annual_value_usd, valuation_method, ci_low, ci_high
- BridgeAxiom: axiom_id, name, category, coefficients_json
- Document: title, doi, year, source_tier, citation

User question: {question}
Classification: {category}

Generate a single Cypher query that retrieves the data needed to answer this question.
Return ONLY the Cypher query, no explanation.
"""

# ---------------------------------------------------------------------------
# Response synthesis
# ---------------------------------------------------------------------------

RESPONSE_SYNTHESIS_PROMPT = """\
You are the response synthesizer for MARIS, a marine natural capital intelligence system.
Your job is to produce a graph-grounded answer from Neo4j query results.

HARD CONSTRAINTS:
1. NO INVENTION: Every claim must correspond to data in the graph context below. Do not fabricate numbers.
2. CITATION REQUIRED: Every numerical value must include a [DOI] citation from the evidence.
3. UNCERTAINTY MANDATE: Financial values must include confidence intervals or ranges where available.
4. CAVEAT PROPAGATION: Include any caveats from the axioms used.
5. STALENESS FLAG: Flag data older than 5 years from the current date (2026).

User question: {question}
Query category: {category}

Graph context (Neo4j results):
{graph_context}

Respond with JSON:
{{
  "answer": "Your synthesized answer with [DOI] citations...",
  "confidence": 0.0,
  "evidence": [{{"doi": "...", "title": "...", "year": 0, "finding": "..."}}],
  "axioms_used": ["BA-XXX"],
  "caveats": ["..."],
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
