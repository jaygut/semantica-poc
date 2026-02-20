# Nereus API Reference

## Overview

The Nereus API (powered by MARIS) is a FastAPI server that exposes the Neo4j knowledge graph through a natural-language query pipeline. It translates user questions into parameterized Cypher queries, executes them against the graph, and synthesizes grounded answers with DOI-backed evidence chains.

All endpoints are prefixed with `/api`. The server reads configuration from environment variables (see `.env.example`).

**Base URL:** `http://localhost:8000`

---

## Authentication

All endpoints except `GET /api/health` require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <MARIS_API_KEY>
```

Set the `MARIS_API_KEY` environment variable to configure the expected token. When `MARIS_DEMO_MODE=true`, authentication is bypassed so investor demos can run without token configuration.

**Error responses:**

| HTTP Code | Condition |
|-----------|-----------|
| 401 Unauthorized | Missing or invalid Bearer token |
| 429 Too Many Requests | Rate limit exceeded (see [Rate Limiting](#rate-limiting)) |

---

## Endpoints

### Health

#### `GET /api/health`

Returns system status including Neo4j connectivity, LLM availability, and graph statistics. Use this for pre-demo verification and monitoring. This endpoint does not require authentication.

**Response (`HealthResponse`):**
```json
{
  "status": "healthy",
  "neo4j_connected": true,
  "llm_available": true,
  "graph_stats": {
    "total_nodes": 938,
    "total_edges": 244,
    "node_breakdown": {
      "Document": 835,
      "EcosystemService": 39,
      "Species": 17,
      "BridgeAxiom": 40,
      "MPA": 11,
      "TrophicLevel": 10,
      "Concept": 15,
      "Habitat": 4,
      "FinancialInstrument": 3,
      "Framework": 3
    }
  }
}
```

---

### Query

#### `POST /api/query`

The primary endpoint. Classifies a natural-language question, selects a Cypher template, executes it against Neo4j, and returns a grounded answer with provenance. Requires authentication (returns 401/429 on failure).

**Input validation:**
- `question` must not exceed 500 characters (returns 400 Bad Request if exceeded)
- `site` name validation: alphanumeric characters, spaces, hyphens, apostrophes, and periods only

**Request body (`QueryRequest`):**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `question` | string | required | Natural-language question |
| `site` | string | null | Optional site name override. If omitted, the classifier extracts the site from the question text (e.g. "Cabo Pulmo" resolves to "Cabo Pulmo National Park") |
| `include_graph_path` | bool | false | Return structured provenance edges for graph visualization |
| `max_evidence_sources` | int | 5 | Maximum number of evidence items to return |

**Example request:**
```json
{
  "question": "What is Cabo Pulmo worth?",
  "include_graph_path": true,
  "max_evidence_sources": 3
}
```

**Response (`QueryResponse`):**
```json
{
  "answer": "Cabo Pulmo National Park generates an estimated $29.27M in annual ecosystem service value...",
  "confidence": 0.83,
  "evidence": [
    {
      "doi": "10.1038/s41598-024-83664-1",
      "title": "Dive tourism willingness-to-pay and fish biomass...",
      "year": 2024,
      "tier": "T1",
      "page_ref": null,
      "quote": null
    }
  ],
  "axioms_used": ["BA-001", "BA-002"],
  "graph_path": [
    {
      "from_node": "Cabo Pulmo National Park",
      "from_type": "MPA",
      "relationship": "GENERATES",
      "to_node": "Tourism",
      "to_type": "EcosystemService"
    }
  ],
  "caveats": ["Single-site calibration study; results should not be extrapolated without site-specific data"],
  "query_metadata": {
    "category": "site_valuation",
    "classification_confidence": 0.75,
    "template_used": "site_valuation",
    "response_time_ms": 2340
  }
}
```

**Response fields:**

| Field | Description |
|-------|-------------|
| `answer` | LLM-synthesized narrative grounded in graph data, with DOI citations |
| `confidence` | 0.0-1.0 composite score from tier_base * path_discount * staleness_discount * sample_factor (see Developer Guide for formula details) |
| `evidence` | Array of DOI-backed sources used in the answer (tier T1-T4) |
| `axioms_used` | Bridge axiom IDs invoked in the provenance chain |
| `graph_path` | Structured edges for visualization (only when `include_graph_path=true`) |
| `caveats` | Methodological limitations that apply to this answer |
| `query_metadata` | Classification category, confidence, template used, response time |
| `provenance_risk` | `"high"` when no site anchor was resolved and the query fell back to open_domain. Absent on normal site-anchored responses. |

---

### Site

#### `GET /api/site/{site_name}`

Retrieve structured data for a specific MPA. Returns full metadata for all 9 Gold-tier characterized sites (Sundarbans, Galapagos, Belize Barrier Reef, Ningaloo, Raja Ampat, Cabo Pulmo, Shark Bay, Cispata Bay, Aldabra); returns governance metadata only for comparison sites (Great Barrier Reef, Papahanaumokuakea). Requires authentication (returns 401/429 on failure).

**Response (`SiteResponse`):**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Canonical site name (as stored in Neo4j) |
| `area_km2` | float | Protected area size in square kilometers |
| `designation_year` | int | Year of MPA designation |
| `esv_usd` | float | Annual ecosystem service value in USD (null for comparison sites) |
| `biomass_ratio` | float | Biomass recovery ratio vs baseline (null for comparison sites) |
| `neoli_score` | int | NEOLI alignment score (0-5) |
| `asset_rating` | string | Investment-grade rating (e.g. "AAA", "AA") |
| `services` | list | Ecosystem service breakdown with per-service values |

> **Data coverage note:** All 9 Gold-tier sites return full ESV, biomass, and service breakdowns. Comparison sites (Great Barrier Reef Marine Park, Papahanaumokuakea Marine National Monument) return governance metadata but null for financial fields. See the [Developer Guide](developer_guide.md#site-portfolio-9-gold-tier-sites) for the full portfolio.

---

### Axiom

#### `GET /api/axiom/{axiom_id}`

Retrieve details for a specific bridge axiom, including its translation coefficients, DOI-backed evidence sources, and the sites and ecosystem services it applies to. Requires authentication (returns 401/429 on failure).

**Response (`AxiomResponse`):**

| Field | Type | Description |
|-------|------|-------------|
| `axiom_id` | string | Identifier (e.g. "BA-001") |
| `name` | string | Human-readable name (e.g. "mpa_biomass_dive_tourism_value") |
| `category` | string | Domain category (e.g. "ecological-financial") |
| `description` | string | Plain-English explanation of the translation |
| `coefficients` | dict | Numerical translation coefficients with units |
| `evidence` | list | DOI citations with title, year, and evidence tier |
| `applicable_sites` | list | MPA names where this axiom has been applied |

---

### Compare

#### `POST /api/compare`

Compare multiple MPA sites side by side. Returns whatever data is available for each site. All 9 Gold-tier sites have full ESV data; comparison sites return governance metadata only. Requires authentication (returns 401/429 on failure).

**Request body (`CompareRequest`):**
```json
{
  "site_names": ["Cabo Pulmo National Park", "Sundarbans Reserve Forest", "Galapagos Marine Reserve"]
}
```

**Response (`CompareResponse`):**
```json
{
  "sites": [
    {"name": "Cabo Pulmo National Park", "esv_usd": 29270000, "biomass_ratio": 4.63, "neoli_score": 4, "asset_rating": "AAA"},
    {"name": "Sundarbans Reserve Forest", "esv_usd": 778900000, "biomass_ratio": null, "neoli_score": 3, "asset_rating": "A"},
    {"name": "Galapagos Marine Reserve", "esv_usd": 320900000, "biomass_ratio": null, "neoli_score": 5, "asset_rating": "AAA"}
  ]
}
```

> The 2 comparison sites (Great Barrier Reef, Papahanaumokuakea) have governance metadata (NEOLI, area, rating) but not full ESV data. Financial fields return null when service-level valuations are not present in the graph.

---

### Graph Traversal

#### `POST /api/graph/traverse`

Traverse the knowledge graph from a starting node. Useful for exploring provenance chains beyond the pre-defined query templates. Requires authentication (returns 401/429 on failure).

**Request body (`TraverseRequest`):**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `start_name` | string | required | Name of the starting node |
| `max_hops` | int | 3 | Maximum traversal depth (1-6). Values outside this range return 400 Bad Request. |
| `result_limit` | int | 50 | Maximum paths to return |

#### `GET /api/graph/node/{element_id}`

Retrieve all properties and relationships for a specific node by its Neo4j element ID. Returns the node's labels, properties, and a list of connected neighbors with relationship types and directions. Requires authentication (returns 401/429 on failure).

---

### Provenance

#### `GET /api/provenance/{entity_id}`

Retrieve the W3C PROV-O provenance lineage for a tracked entity, including the full chain of activities and agents involved in its derivation. Requires authentication (returns 401/429 on failure).

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `entity_id` | string | The tracked entity identifier |
| `lineage` | list | Chain of provenance activities (extraction, axiom application, etc.) |
| `certificate` | object | Provenance certificate with integrity checksums |

#### `GET /api/provenance/{entity_id}/markdown`

Returns a Markdown-formatted provenance certificate for the specified entity. Suitable for embedding in reports or TNFD disclosures.

#### `GET /api/provenance`

Returns a summary of the provenance store, including entity count and storage backend status.

---

### Disclosure

#### `POST /api/disclosure/tnfd-leap`

Generate a TNFD LEAP (Locate, Evaluate, Assess, Prepare) disclosure for a specified site. The v4 generator auto-discovers all case study sites. Requires authentication (returns 401/429 on failure).

**Request body:**

| Field | Type | Description |
|-------|------|-------------|
| `site_name` | string | Canonical site name (e.g. "Cabo Pulmo National Park") |

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `site_name` | string | Site the disclosure was generated for |
| `alignment_score` | object | X/14 alignment score with per-pillar breakdown |
| `leap_phases` | object | Content for each LEAP phase (Locate, Evaluate, Assess, Prepare) |
| `gaps` | list | Identified disclosure gaps |

---

## Query Categories

The `QueryClassifier` maps natural-language questions into one of seven categories. Each category is backed by a parameterized Cypher template in `maris/query/cypher_templates.py`.

| Category | Keyword Triggers | What the Template Returns |
|----------|-----------------|--------------------------|
| `site_valuation` | value, worth, ESV, asset rating | MPA metadata, ecosystem service values, bridge axioms with evidence |
| `provenance_drilldown` | evidence, provenance, DOI, source, research | Multi-hop path from MPA through axioms to source Documents (1-4 hops) |
| `axiom_explanation` | bridge axiom, BA-001, coefficient, sequester | Axiom details, translation coefficients, evidence sources, applicable sites |
| `comparison` | compare, versus, rank, benchmark | Side-by-side MPA metrics (ESV, biomass ratio, NEOLI score, asset rating) |
| `risk_assessment` | risk, degradation, climate, threat, decline | Ecological-to-service axioms, risk factors, confidence intervals |
| `concept_explanation` | blue carbon, trophic cascade, mechanism, how does | Concept node details, involved axioms, linked documents - answers mechanism questions without a site anchor |
| `scenario_analysis` | what if, SSP, without protection, counterfactual, tipping point, carbon price at $X, nature VaR, restoration ROI | Forward-looking ScenarioResponse with baseline/scenario ESV, P5/P50/P95 uncertainty, propagation trace, confidence penalties |

If no keyword rules match and an LLM is configured, the classifier falls back to LLM-based classification. If neither matches, the default category is `site_valuation` with confidence 0.3.

**Siteless query handling:** When a site-required category (site_valuation, provenance_drilldown, risk_assessment) is classified but no site can be resolved from the question, the query is coerced to `open_domain` rather than returning a 422 error. The response includes `"provenance_risk": "high"` to flag that no site-specific graph data was retrieved.

---

## Graph Schema

The Neo4j graph uses the following node labels and relationship types. All nodes are created via MERGE operations (idempotent, keyed by the merge property shown below).

### Node Labels

| Label | Merge Key | Count | Key Properties | Description |
|-------|-----------|-------|----------------|-------------|
| `Document` | `doi` | 835 | title, year, source_tier, domain, abstract | Peer-reviewed evidence source from the 195-paper registry |
| `EcosystemService` | `service_name` or `service_id` | 39 | annual_value_usd, valuation_method, ci_low, ci_high | Valued ecosystem service (e.g. Tourism, Fisheries, Carbon Sequestration) |
| `Species` | `worms_id` or `name` | 17 | common_name, trophic_level, role_in_ecosystem, commercial_importance | Marine species with WoRMS taxonomic identifiers |
| `BridgeAxiom` | `axiom_id` | 40 | name, category, description, pattern, coefficients_json, confidence, evidence_tier, ci_low, ci_high, distribution, study_sample_size, effect_size_type | Ecological-to-financial translation rule with peer-reviewed coefficients and uncertainty quantification. 40 axioms (BA-001 through BA-040) covering carbon, coastal protection, tourism, fisheries, tipping point thresholds (BA-036-040), and cross-cutting mechanisms |
| `MPA` | `name` | 11 | area_km2, designation_year, neoli_score, total_esv_usd, biomass_ratio, asset_rating, biomass_measurement_year, last_validated_date, data_freshness_status | Marine Protected Area (9 Gold-tier + 2 comparison) |
| `TrophicLevel` | `name` | 10 | trophic_level | Trophic network node (apex predator, mesopredator, herbivore, etc.) |
| `Concept` | `concept_id` | 15 | name, description, domain, applicable_habitats, involved_axiom_ids | Blue finance domain concept (BC-001 through BC-015): Blue Carbon Sequestration, Coastal Protection, Marine Tourism Economics, Carbon Credits, Reef Insurance, TNFD Disclosure, etc. Enables mechanism questions without site anchor |
| `Habitat` | `habitat_id` or `name` | 4 | condition | Marine habitat type (coral reef, kelp forest, seagrass meadow, mangrove forest) |
| `FinancialInstrument` | `instrument_id` | 3 | name, description | Blue finance instrument (blue bond, parametric reef insurance) |
| `Framework` | `framework_id` | 3 | name, description | Disclosure or accounting framework (TNFD LEAP, SEEA) |

**Total:** 953+ nodes (includes 15 new Concept nodes pending population), 244+ edges

### Relationship Types

| Relationship | From | To | Count | Description |
|-------------|------|----|-------|-------------|
| `APPLIES_TO` | BridgeAxiom | MPA | 77 | Axiom applies to this site |
| `GENERATES` | MPA | EcosystemService | 36 | MPA produces this ecosystem service |
| `EVIDENCED_BY` | BridgeAxiom | Document | 28 | Axiom is backed by this peer-reviewed source |
| `DERIVED_FROM` | MPA | Document | 20 | Site data is sourced from this paper |
| `LOCATED_IN` | Species | MPA | 18 | Species is found in this MPA |
| `TRANSLATES` | BridgeAxiom | EcosystemService | 16 | Axiom converts ecological state to this service value |
| `HAS_HABITAT` | MPA | Habitat | 14 | MPA contains this habitat type |
| `INHABITS` | Species | Habitat | 10 | Species lives in this habitat |
| `PREYS_ON` | TrophicLevel | TrophicLevel | 7 | Trophic interaction in the food web |
| `PART_OF_FOODWEB` | TrophicLevel | MPA | 5 | Trophic level exists within this site |
| `PROVIDES` | Habitat | EcosystemService | 4 | Habitat type generates this service |
| `APPLICABLE_TO` | Framework | MPA | 3 | Disclosure framework is applicable to this site |
| `GOVERNS` | Framework | FinancialInstrument | 3 | Framework governs this instrument type |
| `APPLIES_TO_HABITAT` | BridgeAxiom | Habitat | 3 | Axiom is applicable to this habitat type |
| `INVOLVES_AXIOM` | Concept | BridgeAxiom | ~50 NEW | Concept involves this axiom (enables mechanism question routing) |
| `RELEVANT_TO` | Concept | Concept | ~15 NEW | Concept relationship (future cross-concept traversal) |
| `DOCUMENTED_BY` | Concept | Document | ~30 NEW | Concept is documented in this peer-reviewed source |

**Total:** 244+ edges (expanded with Concept relationships)

---

## Error Handling

| HTTP Code | Meaning |
|-----------|---------|
| 200 | Success |
| 400 | Bad request - invalid input (question too long, invalid site name, max_hops out of range) |
| 401 | Unauthorized - missing or invalid Bearer token |
| 429 | Too Many Requests - rate limit exceeded |
| 500 | Internal error - Neo4j unreachable, Cypher execution failed, or LLM error |

Error responses include a `detail` field with a human-readable message.

---

## Rate Limiting

API requests are rate-limited per API key using an in-memory sliding window:

| Endpoint | Limit |
|----------|-------|
| `POST /api/query` | 30 requests/minute |
| All other endpoints | 60 requests/minute |

When the rate limit is exceeded, the API returns `429 Too Many Requests`. Every response includes an `X-Request-ID` header for end-to-end request tracing and correlation with server logs.

---

## Configuration

The API reads all settings from environment variables with `MARIS_` prefix. Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `MARIS_API_HOST` | 0.0.0.0 | API bind address |
| `MARIS_API_PORT` | 8000 | API port |
| `MARIS_NEO4J_URI` | bolt://localhost:7687 | Neo4j bolt connection URI |
| `MARIS_NEO4J_USER` | neo4j | Neo4j username |
| `MARIS_NEO4J_PASSWORD` | - | Neo4j password (required) |
| `MARIS_LLM_PROVIDER` | deepseek | LLM provider: deepseek, anthropic, or openai |
| `MARIS_LLM_API_KEY` | - | LLM API key (required for live queries) |
| `MARIS_LLM_MODEL` | deepseek-chat | Model identifier |
| `MARIS_DEMO_MODE` | false | When true, uses precomputed responses instead of live LLM calls and bypasses authentication |
| `MARIS_API_KEY` | - | Bearer token for API authentication (required unless demo mode is enabled) |
| `MARIS_CORS_ORIGINS` | http://localhost:8501 | Allowed CORS origins (comma-separated for multiple) |
| `MARIS_PROVENANCE_DB` | provenance.db | SQLite database path for W3C PROV-O provenance persistence |

> **Security:** The `.env` file contains secrets and must never be committed. It is excluded via `.gitignore`.
