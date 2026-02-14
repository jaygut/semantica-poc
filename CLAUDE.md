# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. It is designed to bring any new session to full operational context within seconds.

## Project Overview

**MARIS** (Marine Asset Risk Intelligence System) is a provenance-first knowledge graph that creates auditable, DOI-backed pathways from peer-reviewed ecological science to investment-grade financial metrics for blue natural capital. Built on the Semantica framework, it is designed for institutional investors, blue bond underwriters, TNFD working groups, and conservation finance professionals who require full scientific traceability behind every number.

**Current Status:** Production-ready POC deployed on `main` with Blue Carbon Extension complete. Semantica SDK integration (P0-P4) is complete on `feature/semantica-integration` branch with all gaps closed - including LLM-enhanced axiom discovery, rule compilation, enhanced multi-signal habitat characterization, and hardened API clients. The system comprises a Neo4j knowledge graph (893 nodes, 132 edges) spanning two fully characterized MPA sites (Cabo Pulmo and Shark Bay), a FastAPI query engine with 9 endpoints (7 core + provenance + disclosure), Bearer token authentication and rate limiting, natural-language-to-Cypher classification with LLM response validation, and an investor-facing Streamlit dashboard with interactive graph visualization. The document library contains 195 verified papers, 16 fully-evidenced bridge axioms (v1.3 with blue carbon axioms BA-013 through BA-016 and uncertainty quantification), and a Semantica-ready export bundle. The Semantica integration adds W3C PROV-O provenance tracking, multi-site scaling pipeline, cross-domain reasoning engine, TNFD LEAP disclosure automation, LLM-enhanced dynamic axiom discovery with regex fallback, rule compilation extracted from InferenceEngine, and a 6-file SDK bridge layer. Backed by a **910-test suite** (706 unit + 204 integration) with GitHub Actions CI, multi-stage Docker builds, and a composite confidence model. The system also runs in static mode from a pre-computed JSON bundle (63 precomputed responses) for zero-downtime investor demos.

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          MARIS v2 - LIVE SYSTEM ARCHITECTURE                      │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  User Question (natural language)                                                │
│       |                                                                          │
│       v                                                                          │
│  QueryClassifier  -- keyword-first with LLM fallback                             │
│       |              (5 categories: valuation, provenance, axiom, comparison,     │
│       v               risk)                                                      │
│  CypherTemplates  -- 8 parameterized templates, never raw string interpolation   │
│       |                                                                          │
│       v                                                                          │
│  QueryExecutor    -- Neo4j bolt driver, parameterized queries only               │
│       |                                                                          │
│       v                                                                          │
│  ResponseGenerator -- LLM grounds graph results into narrative with DOI          │
│       |               citations                                                  │
│       v                                                                          │
│  ResponseFormatter -- extracts confidence score, evidence items, caveats         │
│       |                                                                          │
│       v                                                                          │
│  FastAPI JSON Response -- answer + evidence + provenance chain + graph path      │
│       |                                                                          │
│       v                                                                          │
│  Streamlit Dashboard -- dark-mode, single-scroll investor UI with Ask MARIS      │
│                         chat and interactive graph explorer                       │
│                                                                                  │
│  Three-Layer Translation Model:                                                  │
│  ECOLOGICAL DATA  -->  BRIDGE AXIOMS (16 rules)  -->  FINANCIAL METRICS          │
│  Species, Habitats     BA-001 through BA-016         Blue bonds, TNFD,           │
│  MPAs, Observations    DOI-backed coefficients       Credits, Insurance          │
│                                                                                  │
│  Every claim traceable to DOI + evidence tier + bridge axiom                     │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Knowledge Graph | Neo4j Community 5.x | 893 nodes, 132 edges; bolt://localhost:7687 |
| API Server | FastAPI + Uvicorn | 7 REST endpoints; http://localhost:8000 |
| Dashboard | Streamlit 1.54 | Dark-mode investor UI; http://localhost:8501 |
| LLM | DeepSeek V3 (default) | Query classification and response synthesis |
| Computation | NumPy, NetworkX | Monte Carlo simulation (10,000 runs), graph analysis |

---

## Quick Start

### v2 - Live System (Recommended)

```bash
# 1. Configure environment (copy template, add your credentials)
cp .env.example .env
# Edit .env: set MARIS_NEO4J_PASSWORD, MARIS_LLM_API_KEY, and MARIS_API_KEY

# 2. Install dependencies
uv pip install -r requirements-v2.txt

# 3. Ensure Neo4j is running, then populate the knowledge graph
python scripts/populate_neo4j.py

# 4. Start the API server (terminal 1)
uvicorn maris.api.main:app --host 0.0.0.0 --port 8000

# 5. Start the dashboard (terminal 2)
cd investor_demo
streamlit run streamlit_app_v2.py
```

The dashboard opens at `http://localhost:8501`. Verify the stack with:

```bash
# API health check (returns Neo4j status, LLM availability, graph stats)
curl http://localhost:8000/api/health

# Full pre-demo stack verification
python scripts/demo_healthcheck.py

# Test a live query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MARIS_API_KEY" \
  -d '{"question": "What is Cabo Pulmo worth?", "include_graph_path": true}'
```

### Docker Compose (All-in-One)

```bash
docker compose up --build
```

### v1 - Static Mode (No External Services)

```bash
cd investor_demo
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Uses the pre-computed bundle at `demos/context_graph_demo/cabo_pulmo_investment_grade_bundle.json`. No Neo4j or API required.

---

## Knowledge Graph Data Lineage

The graph is populated from **seven curated data sources** through an idempotent pipeline (`scripts/populate_neo4j.py`). All operations use MERGE (safe to re-run).

### Source Datasets

| # | Source | File | What It Creates |
|---|--------|------|-----------------|
| 1 | Document Registry | `.claude/registry/document_index.json` | 195 Document nodes (DOI, title, year, evidence tier) |
| 2 | Entity Definitions | `data/semantica_export/entities.jsonld` | 14 JSON-LD entities: Species, MPA, Habitat, EcosystemService, FinancialInstrument, Framework, Concept |
| 3 | Cabo Pulmo Case Study | `examples/cabo_pulmo_case_study.json` | MPA enrichment (NEOLI, biomass, ESV), EcosystemService values, Species nodes, TrophicLevel food web, GENERATES edges |
| 4 | Shark Bay Case Study | `examples/shark_bay_case_study.json` | Second fully characterized MPA: seagrass carbon, fisheries, tourism, coastal protection; EcosystemService values, GENERATES edges |
| 5 | Bridge Axiom Templates + Evidence | `schemas/bridge_axiom_templates.json` + `data/semantica_export/bridge_axioms.json` | 16 BridgeAxiom nodes (BA-001 through BA-016); EVIDENCED_BY, APPLIES_TO, TRANSLATES edges |
| 6 | Curated Relationships | `data/semantica_export/relationships.json` | 15 cross-domain edges with quantification, mechanism, confidence |
| 7 | Comparison Sites | Hardcoded in `maris/graph/population.py` | Great Barrier Reef, Papahanaumokuakea MPA nodes (governance metadata only) |

### Fully Characterized Sites

**Cabo Pulmo National Park** (Mexico) - coral reef-dominated, tourism-driven ESV:

| Property | Value | Source |
|----------|-------|--------|
| Total ESV | $29.27M/year (market-price) | cabo_pulmo_case_study.json |
| Tourism | $25.0M (market-price expenditure) | Marcos-Castillo et al. 2024 |
| Biomass ratio | 4.63x recovery, CI [3.8, 5.5] | Aburto-Oropeza et al. 2011 |
| NEOLI score | 4/5 criteria met | Edgar et al. 2014 framework |
| Asset rating | AAA (composite 0.90) | Derived from NEOLI + ESV + CI |
| Monte Carlo | Median ~$28.7M, P5 ~$19.6M, P95 ~$36.1M | 10,000 simulations |

**Shark Bay World Heritage Area** (Australia) - seagrass-dominated, carbon-driven ESV:

| Property | Value | Source |
|----------|-------|--------|
| Total ESV | $21.5M/year (market-price) | shark_bay_case_study.json |
| Carbon sequestration | $12.1M (0.84 tCO2/ha/yr, $30/tonne) | Arias-Ortiz et al. 2018 |
| Fisheries | $5.2M (MSC-certified prawn fishery) | Market-price method |
| Tourism | $3.4M (108K visitors/year) | Tourism WA data |
| Coastal protection | $0.8M (40% wave reduction) | Avoided cost method |
| Seagrass extent | 4,800 km2 (world's largest) | Direct survey |
| NEOLI score | 4/5 criteria met | Edgar et al. 2014 framework |
| Area | 23,000 km2 | UNESCO designation |

**Comparison sites** (Great Barrier Reef, Papahanaumokuakea) have governance metadata only (area, designation year, NEOLI score, asset rating) - no ecosystem service valuations. The POC demonstrates the full provenance chain for two deeply characterized sites with contrasting ESV profiles: tourism-dominant (Cabo Pulmo) vs. carbon-dominant (Shark Bay).

---

## API Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/health` | No | System status: Neo4j connectivity, LLM availability, graph statistics |
| POST | `/api/query` | Yes | Primary endpoint: NL question -> classified Cypher -> grounded answer with provenance |
| GET | `/api/site/{site_name}` | Yes | Structured site data (full for Cabo Pulmo, governance-only for comparison sites) |
| GET | `/api/axiom/{axiom_id}` | Yes | Bridge axiom details: coefficients, evidence, applicable sites |
| POST | `/api/compare` | Yes | Side-by-side MPA comparison |
| POST | `/api/graph/traverse` | Yes | Graph traversal from a starting node (1-6 hops) |
| GET | `/api/graph/node/{element_id}` | Yes | Node properties and relationships by Neo4j element ID |
| GET | `/api/provenance/{entity_id}` | Yes | Provenance lineage and certificate for a tracked entity |
| GET | `/api/provenance/{entity_id}/markdown` | Yes | Markdown-formatted provenance certificate |
| GET | `/api/provenance` | Yes | Provenance store summary |
| POST | `/api/disclosure/tnfd-leap` | Yes | Generate TNFD LEAP disclosure for a site |

---

## Authentication

All endpoints except `/api/health` require a Bearer token via the `Authorization` header:

```
Authorization: Bearer <MARIS_API_KEY>
```

Authentication is implemented in `maris/api/auth.py`. When `MARIS_DEMO_MODE=true`, authentication is bypassed for development and demos.

**Rate Limiting:** In-memory sliding-window rate limiting is applied per API key:
- `/api/query`: 30 requests per minute
- All other endpoints: 60 requests per minute

Exceeding the limit returns HTTP 429. Rate limit headers are included in responses.

---

## Testing

The project includes a comprehensive test suite with 910 tests (706 unit + 204 integration) covering all core modules.

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=maris --cov-report=term-missing
```

Tests are organized by module in `tests/` with shared fixtures in `conftest.py`. CI runs automatically on push and PR to `main` via GitHub Actions (`.github/workflows/ci.yml`): linting with ruff, then pytest.

---

## Module Structure

```
maris/
  api/                          # FastAPI server
    main.py                     # App factory, CORS, router registration
    models.py                   # Pydantic v2 request/response schemas
    auth.py                     # Bearer token auth, rate limiting, request tracing
    routes/
      health.py                 # GET /api/health
      query.py                  # POST /api/query - full NL-to-answer pipeline
      graph.py                  # Graph traversal and node detail endpoints
      provenance.py             # GET /api/provenance/{entity_id} - lineage and certificates
      disclosure.py             # POST /api/disclosure/tnfd-leap - TNFD LEAP generation
  graph/                        # Neo4j integration layer
    connection.py               # Bolt driver singleton, run_query() helper
    schema.py                   # Uniqueness constraints and indexes
    population.py               # 8-stage population pipeline from curated JSON
    validation.py               # Post-population integrity checks
  query/                        # NL-to-Cypher pipeline
    classifier.py               # Two-tier: keyword regex (case-insensitive BA, DOI, risk patterns, comparison tie-break) + LLM fallback
    cypher_templates.py         # 8 parameterized Cypher templates by category
    executor.py                 # Template execution + provenance edge extraction
    generator.py                # LLM response synthesis from graph context
    formatter.py                # Structured output: confidence, evidence, caveats
    validators.py              # LLM response validation, claim verification, DOI checks
  llm/                          # LLM abstraction
    adapter.py                  # OpenAI-compatible client (DeepSeek, Claude, GPT-4)
    prompts.py                  # System prompts for classification and generation
  axioms/                       # Bridge axiom computation
    engine.py                   # Axiom application and chaining
    confidence.py               # Multiplicative confidence interval propagation
    monte_carlo.py              # Monte Carlo ESV simulation (10,000 runs)
    sensitivity.py            # OAT sensitivity analysis, tornado plot data
  ingestion/                    # Document ingestion pipeline
    pdf_extractor.py            # PDF text extraction
    llm_extractor.py            # LLM-based entity/relationship extraction
    embedding_generator.py      # Vector embeddings for semantic search
    graph_merger.py             # Merge extracted triples into Neo4j
  provenance/                   # P0: W3C PROV-O provenance tracking
    manager.py                  # MARISProvenanceManager
    bridge_axiom_registry.py    # 16 axioms as typed BridgeAxiom objects
    certificate.py              # Provenance certificate generation
    core.py                     # PROV-O dataclasses
    integrity.py                # SHA-256 checksum verification
    storage.py                  # InMemoryStorage + SQLiteStorage
  sites/                        # P1: Multi-site scaling pipeline
    api_clients.py              # OBIS (area resolution), WoRMS (204 fix), Marine Regions (404 handling) clients
    characterizer.py            # 5-step auto-characterization (Bronze/Silver/Gold) with multi-signal habitat scoring (keywords, taxonomy, functional groups)
    esv_estimator.py            # Bridge axiom-based ESV estimation
    models.py                   # Pydantic site models
    registry.py                 # JSON-backed site registry
  reasoning/                    # P2: Cross-domain reasoning engine
    context_builder.py          # Graph -> Semantica ContextGraph
    hybrid_retriever.py         # Graph + keyword + RRF retrieval
    inference_engine.py         # Forward/backward chaining
    rule_compiler.py            # Rule compilation extracted from InferenceEngine
    explanation.py              # Investor-friendly explanations
  disclosure/                   # P3: TNFD LEAP disclosure automation
    leap_generator.py           # 4-phase TNFD LEAP generation
    renderers.py                # Markdown, JSON, summary output
    alignment_scorer.py         # 14-disclosure gap analysis
    models.py                   # TNFD Pydantic models
  discovery/                    # P4: Dynamic axiom discovery
    pattern_detector.py         # Cross-paper pattern detection (regex)
    llm_detector.py             # LLM-enhanced pattern detection with regex fallback, retry logic, numeric confidence, robust JSON parsing
    aggregator.py               # Multi-study aggregation + conflict detection
    candidate_axiom.py          # Candidate axiom formation
    reviewer.py                 # Human-in-the-loop validation
    pipeline.py                 # Discovery orchestration
  semantica_bridge/             # Semantica SDK adapter layer
    storage_adapter.py          # SemanticaStorage wrapping SDK
    axiom_adapter.py            # MARIS <-> Semantica axiom conversion
    provenance_adapter.py       # Dual-write provenance manager
    integrity_adapter.py        # SDK-backed integrity verification
    manager.py                  # SemanticaBackedManager (drop-in replacement)
  config.py                     # Centralized config from .env (MARIS_ prefix)

investor_demo/
  streamlit_app_v2.py           # Live dashboard - CSS, layout, data, Ask MARIS, Graph Explorer
  streamlit_app.py              # Static dashboard - bundle-only, zero dependencies
  api_client.py                 # HTTP client wrapping MARIS API; auto-fallback to precomputed
  components/
    chat_panel.py               # Ask MARIS query UI with markdown, confidence badges, evidence
    graph_explorer.py           # Plotly network graph with semantic layering
    roadmap_section.py          # Scaling Intelligence section (shared between v1 and v2)
  precomputed_responses.json    # Cached responses for 63 common queries (API fallback)
  demo_narrative.md             # 10-minute pitch script (v1)
  demo_narrative_v2.md          # Updated pitch script (v2)

scripts/
  populate_neo4j.py             # Orchestrates 8-stage graph population pipeline
  validate_graph.py             # Verifies node counts, relationship integrity, axiom evidence
  demo_healthcheck.py           # Pre-demo: Neo4j + API + dashboard connectivity check
  run_ingestion.py              # Full PDF-to-graph ingestion pipeline
  validate_registry.py          # Registry validation with auto-fix
  enrich_abstracts.py           # 5-tier abstract enrichment cascade
  fetch_documents.py            # Document fetcher with retry logic

tests/
  conftest.py                       # Shared fixtures (graph results, LLM responses, mock config)
  test_api_endpoints.py             # API route tests with auth validation
  test_auth.py                      # Auth enforcement, rate limiting, input validation
  test_bridge_axioms.py             # Bridge axiom computation tests
  test_cabo_pulmo_validation.py     # Cabo Pulmo reference data integrity
  test_classifier.py                # Query classification accuracy
  test_confidence.py                # Composite confidence model tests
  test_cypher_templates.py          # Template parameterization and LIMIT tests
  test_entity_extraction.py         # Entity extraction pipeline tests
  test_integration.py               # End-to-end pipeline integration tests
  test_monte_carlo.py               # Monte Carlo simulation tests
  test_population.py                # Graph population pipeline tests
  test_query_engine.py              # Query execution and response formatting
  test_relationship_extraction.py   # Relationship extraction tests
  test_validators.py                # LLM response validation tests
  test_provenance.py                # P0: Provenance engine tests
  test_site_scaling.py              # P1: Site scaling tests
  test_reasoning.py                 # P2: Reasoning engine tests
  test_disclosure.py                # P3: TNFD disclosure tests
  test_axiom_discovery.py           # P4: Axiom discovery tests
  test_semantica_bridge.py          # Semantica SDK bridge tests (51 tests)
  integration/                      # Integration test suite (204 tests)
    test_phase0_bridge.py           # SDK availability, SQLite persistence, dual-write
    test_phase1_graph.py            # Graph integrity, idempotent re-population
    test_phase2_apis.py             # External API validation (OBIS, WoRMS, Marine Regions)
    test_phase3_query.py            # Query pipeline regression
    test_phase4_disclosure.py       # TNFD disclosure, axiom discovery
    test_phase5_stress.py           # Stress tests, concurrent queries
    test_phase6_llm_discovery.py    # LLM-enhanced discovery integration tests (7 tests against live DeepSeek)
```

---

## Key Files Reference

### Core Data Assets

| File | Purpose |
|------|---------|
| `.claude/registry/document_index.json` | Master bibliography (195 papers with DOI, tier, domain) |
| `examples/cabo_pulmo_case_study.json` | AAA reference site: NEOLI, biomass, ESV, species, trophic network |
| `examples/shark_bay_case_study.json` | Second reference site: seagrass carbon, fisheries, tourism, coastal protection |
| `schemas/bridge_axiom_templates.json` | 16 bridge axioms with translation coefficients and DOI evidence |
| `data/semantica_export/entities.jsonld` | 14 JSON-LD entities (WoRMS, FishBase, TNFD URIs) |
| `data/semantica_export/relationships.json` | 15 cross-domain edges with quantification and mechanism |
| `data/semantica_export/bridge_axioms.json` | Axiom evidence mapping for graph population |
| `demos/context_graph_demo/cabo_pulmo_investment_grade_bundle.json` | Pre-computed bundle for static dashboard |

### Schemas

| File | Purpose |
|------|---------|
| `schemas/entity_schema.json` | 8 entity types (JSON-LD format) |
| `schemas/relationship_schema.json` | 14 relationship types + inference rules |
| `schemas/bridge_axiom_templates.json` | 16 translation rules with coefficients |
| `schemas/registry_schema.json` | Document validation schema |

### Infrastructure

| File | Purpose |
|------|---------|
| `.env.example` | Environment template (Neo4j, LLM, feature flags) |
| `docker-compose.yml` | Neo4j + API + Dashboard one-command startup |
| `requirements-v2.txt` | Full v2 dependencies (FastAPI, neo4j, streamlit, etc.) |
| `investor_demo/requirements.txt` | Minimal v1 dependencies |
| `Dockerfile.api` | Multi-stage API container (python:3.11-slim, non-root) |
| `Dockerfile.dashboard` | Multi-stage dashboard container |
| `.dockerignore` | Docker build exclusions |
| `requirements-dev.txt` | Test and lint dependencies (pytest, ruff, httpx) |
| `.github/workflows/ci.yml` | GitHub Actions CI: lint + test pipeline |

### Documentation

| File | Purpose |
|------|---------|
| `README.md` | Project overview, architecture, implementation roadmap |
| `docs/developer_guide.md` | Architecture, data lineage, population pipeline, extension guide |
| `docs/api_reference.md` | Endpoint specs, graph schema, query categories, configuration |
| `docs/user_guide.md` | Dashboard usage, Ask MARIS examples, confidence levels, troubleshooting |
| `docs/investment_grade_definition.md` | Investment-grade definition and criteria |
| `docs/second_site_characterization_plan.md` | Plan for characterizing a second MPA site |
| `investor_demo/README.md` | Dashboard architecture, data provenance, design principles |
| `SEMANTICA_HANDOFF_README.md` | Integration guide for Semantica team |

---

## Environment Configuration

All settings use `MARIS_` prefix. Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `MARIS_NEO4J_URI` | bolt://localhost:7687 | Neo4j bolt connection |
| `MARIS_NEO4J_USER` | neo4j | Neo4j username |
| `MARIS_NEO4J_PASSWORD` | - | Neo4j password (required) |
| `MARIS_LLM_PROVIDER` | deepseek | LLM provider: deepseek, anthropic, openai |
| `MARIS_LLM_API_KEY` | - | LLM API key (required for live queries) |
| `MARIS_LLM_MODEL` | deepseek-chat | Model identifier |
| `MARIS_DEMO_MODE` | false | true = use precomputed responses (no LLM calls) |
| `MARIS_ENABLE_LIVE_GRAPH` | true | Enable Neo4j graph explorer in dashboard |
| `MARIS_ENABLE_CHAT` | true | Enable Ask MARIS chat panel |
| `MARIS_API_KEY` | - | Bearer token for API authentication (required unless MARIS_DEMO_MODE=true) |
| `MARIS_CORS_ORIGINS` | http://localhost:8501 | Comma-separated list of allowed CORS origins |
| `MARIS_PROVENANCE_DB` | provenance.db | SQLite database path for W3C PROV-O provenance persistence |

**Security:** `.env` contains secrets and is excluded from git via `.gitignore`. Never commit it.

---

## Query Classification System

The `QueryClassifier` (`maris/query/classifier.py`) maps natural-language questions into five categories. Each category is backed by a parameterized Cypher template. There are 8 templates total (5 core + 3 utility). The classifier has been hardened with four regex gap fixes: case-insensitive bridge axiom ID matching (e.g., "ba-001"), DOI keyword routing to provenance, expanded risk patterns (including "lost"), and comparison tie-break logic.

| Category | Keyword Triggers | What the Template Returns |
|----------|-----------------|--------------------------|
| `site_valuation` | value, worth, ESV, asset rating | MPA metadata, ecosystem service values, bridge axioms with evidence |
| `provenance_drilldown` | evidence, provenance, DOI, source | Multi-hop path from MPA through axioms to source Documents |
| `axiom_explanation` | bridge axiom, BA-001, coefficient, seagrass, blue carbon | Axiom details, translation coefficients, evidence sources |
| `comparison` | compare, versus, rank, benchmark | Side-by-side MPA metrics |
| `risk_assessment` | risk, degradation, climate, threat | Ecological-to-service axioms, risk factors, confidence intervals |

**Site name resolution:** The classifier maps common names to canonical Neo4j node names (e.g., "Cabo Pulmo" -> "Cabo Pulmo National Park", "Shark Bay" -> "Shark Bay World Heritage Area"). Patterns are defined in `_SITE_PATTERNS` in `classifier.py`. The query endpoint infers axiom IDs for mechanism questions (e.g., "How does seagrass sequester carbon?" -> BA-013).

---

## Graph Schema (Neo4j)

### Node Labels

| Label | Merge Key | Count | Description |
|-------|-----------|-------|-------------|
| Document | doi | 829 | Peer-reviewed evidence sources from 195-paper registry |
| BridgeAxiom | axiom_id | 16 | Ecological-to-financial translation rules (12 core + 4 blue carbon) |
| EcosystemService | service_name | 11 | Valued services (Tourism, Fisheries, Carbon, Coastal Protection, etc.) |
| TrophicLevel | name | 10 | Food web nodes (apex predator, mesopredator, etc.) |
| Concept | name | 10 | Domain concepts (NEOLI Criteria, Blue Carbon, etc.) |
| Habitat | habitat_id | 4 | Marine habitats (coral reef, kelp, seagrass, mangrove) |
| MPA | name | 4 | Marine Protected Areas (Cabo Pulmo, Shark Bay, GBR, Papahanaumokuakea) |
| Species | worms_id | 3 | Marine species with WoRMS identifiers |
| FinancialInstrument | instrument_id | 3 | Blue bond, parametric reef insurance, carbon credit |
| Framework | framework_id | 3 | TNFD LEAP, SEEA, Verra VCS |

### Relationship Types

| Relationship | From -> To | Description |
|-------------|-----------|-------------|
| GENERATES | MPA -> EcosystemService | MPA produces this service |
| APPLIES_TO | BridgeAxiom -> MPA | Axiom applies to this site |
| TRANSLATES | BridgeAxiom -> EcosystemService | Axiom converts ecological state to service value |
| EVIDENCED_BY | BridgeAxiom -> Document | Axiom backed by peer-reviewed source |
| HAS_HABITAT | MPA -> Habitat | MPA contains this habitat type |
| INHABITS | Species -> Habitat | Species lives in this habitat |
| LOCATED_IN | Species -> MPA | Species found in this MPA |
| PREYS_ON | TrophicLevel -> TrophicLevel | Trophic interaction in food web |
| PART_OF_FOODWEB | TrophicLevel -> MPA | Trophic level exists within this site |
| PROVIDES | Habitat -> EcosystemService | Habitat generates this service |
| DERIVED_FROM | MPA -> Document | Site data sourced from this paper |
| APPLICABLE_TO | Framework -> MPA | Framework applicable to this site |
| GOVERNS | Framework -> FinancialInstrument | Framework governs this instrument |
| APPLIES_TO_HABITAT | BridgeAxiom -> Habitat | Axiom applicable to this habitat |

---

## Bridge Axioms

Bridge axioms are the core translation mechanism - each converts an ecological state measurement into a financial value through peer-reviewed coefficients. The original 12 axioms cover coral reef and general MPA translations; BA-013 through BA-016 extend coverage to blue carbon and seagrass ecosystems.

| Axiom | Name | Translation | Key Coefficient |
|-------|------|-------------|-----------------|
| BA-001 | mpa_biomass_dive_tourism_value | Fish biomass -> Tourism WTP | Up to 84% higher WTP per unit biomass |
| BA-002 | notake_mpa_biomass_multiplier | No-take MPA -> Biomass recovery | 4.63x over 10-year recovery arc |
| BA-003 | sea_otter_kelp_carbon_cascade | Kelp forest area -> Carbon value | Otter-mediated trophic cascade |
| BA-004 | coral_reef_flood_protection | Coral reef -> Flood protection | Wave energy reduction per meter reef |
| BA-005 | mangrove_flood_protection | Mangrove -> Flood protection | Coastal defense value per hectare |
| BA-006 | mangrove_fisheries_production | Mangrove -> Fisheries yield | Nursery habitat production function |
| BA-007 | mangrove_carbon_stock | Mangrove -> Carbon stock | Tonnes CO2/ha stored |
| BA-008 | seagrass_carbon_credit_value | Seagrass -> Carbon credits | Credit value per hectare |
| BA-009 | mangrove_restoration_bcr | Restoration -> Benefit-cost ratio | BCR multiplier |
| BA-010 | kelp_forest_global_value | Kelp forest -> Global value | Per-hectare ESV estimate |
| BA-011 | mpa_climate_resilience | MPA -> Climate resilience | Resilience index composite |
| BA-012 | reef_degradation_fisheries_loss | Reef degradation -> Fisheries loss | Revenue decline per degradation unit |
| BA-013 | seagrass_carbon_sequestration_rate | Seagrass area -> Carbon sequestration | 0.84 tCO2/ha/yr (Arias-Ortiz 2018) |
| BA-014 | carbon_stock_to_credit_value | Carbon stock -> Credit value | $30/tonne (Verra VCS VM0033) |
| BA-015 | habitat_loss_carbon_emission | Habitat loss -> Carbon emission | 294 tCO2/ha released (Arias-Ortiz 2018) |
| BA-016 | mpa_protection_carbon_permanence | MPA protection -> Carbon permanence | Buffer pool discount for reversal risk |

---

## Domain Context

### Document Library

195 papers across 9 domains, 92% peer-reviewed (T1):

| Domain | Count |
|--------|-------|
| Trophic Ecology | 42 |
| Connectivity | 35 |
| Blue Finance | 35 |
| Ecosystem Services | 28 |
| Restoration | 24 |
| Blue Carbon | 22 |
| MPA Effectiveness | 18 |
| Measurement Methods | 18 |
| Climate Resilience | 12 |

### Evidence Tier System

| Tier | Classification | Financial Usage |
|------|----------------|----------------|
| T1 | Peer-reviewed journal articles | Cite without qualification in investor materials |
| T2 | Institutional reports (World Bank, UNEP, TNFD) | Cite with institutional context |
| T3 | Data repositories (FishBase, WoRMS, OBIS) | Cite with methodology notes |
| T4 | Preprints and grey literature | Cite with explicit caveats |

---

## Terminology Rules

These MUST be followed in all code, documentation, and generated content:

- **"NEOLI alignment"** not "NEOLI compliance" (the system does not claim NEOLI certification)
- **"market-price"** not "NOAA-adjusted" for Cabo Pulmo tourism valuation
- **"anticipates alignment with"** not "anticipates compliance with" for framework references
- **No em dashes** in prose (use hyphens or " - " instead)
- **ESV = $29.27M** (market-price total, not WTP-adjusted)
- **Tourism = $25.0M** (market-price expenditure method)
- **Biomass = 4.63x** with CI [3.8, 5.5]

---

## Agentic Workflow Commands

### Registry Maintenance

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/validate-registry` | Check integrity, fix statistics | After any registry changes |
| `/enrich-abstracts` | Populate missing abstracts | Before entity extraction |
| `/fetch-documents` | Download paper content | Before extraction, after discovery |

### Literature Discovery

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/search-literature` | Find papers by domain | Expanding library |
| `/build-library` | Automated library expansion | Initial setup or major expansion |

### Knowledge Extraction and Pipeline

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/extract-knowledge` | Extract entities from papers | After documents are fetched |
| `/semantica-pipeline` | Full end-to-end pipeline | Final export to Semantica |

---

## Extending the System

### Adding a New MPA Site

1. Create a case study JSON following the structure of `examples/cabo_pulmo_case_study.json` or `examples/shark_bay_case_study.json`
2. Add a population function in `maris/graph/population.py` (pattern: `_populate_cabo_pulmo()` or `_populate_shark_bay()`)
3. Add the site's canonical name to `_SITE_PATTERNS` in `maris/query/classifier.py`
4. Add the case study path to `MARISConfig.case_study_paths` in `maris/config.py`
5. Run `python scripts/populate_neo4j.py` to load the new site

### Adding a New Bridge Axiom

1. Add the axiom to `schemas/bridge_axiom_templates.json` with coefficients, habitats, and DOI sources
2. Add the evidence mapping to `data/semantica_export/bridge_axioms.json`
3. Run `python scripts/populate_neo4j.py` to create the BridgeAxiom node and evidence edges

### Adding a New Cypher Template

1. Add the template to `maris/query/cypher_templates.py`
2. Add keyword rules in `maris/query/classifier.py` if it maps to a new category
3. Handle parameter extraction in `maris/api/routes/query.py`

### Adding a New API Endpoint

1. Define Pydantic models in `maris/api/models.py`
2. Create a route function under `maris/api/routes/`
3. Register the router in `maris/api/main.py`

---

## Success Criteria

| Criterion | Target | Status |
|-----------|--------|--------|
| Document library | 195 papers, 92% T1 | Complete |
| DOI coverage | 100% | 90.3% |
| Abstract coverage | >=80% | 67.2% |
| Cabo Pulmo ESV accuracy | +/-20% of published | $29.27M (within range) |
| Shark Bay ESV accuracy | +/-20% of published | $21.5M (within range) |
| Bridge axiom evidence | 16 axioms x 3+ sources | Complete |
| Dual-site characterization | 2 fully characterized MPAs | Complete (Cabo Pulmo + Shark Bay) |
| Blue carbon axioms | BA-013 through BA-016 | Complete |
| Live query pipeline | End-to-end NL-to-answer | Working |
| Graph population | 893 nodes, 132 edges | Complete |
| Dashboard (live + static) | Both modes operational | Working |
| Test suite | 910 tests passing (706 unit + 204 integration) | Complete |
| Semantica SDK integration | P0-P4 complete (27 modules) on feature/semantica-integration | Complete |
| Provenance tracking | W3C PROV-O with SQLite persistence | Complete |
| TNFD disclosure | LEAP automation with alignment scoring | Complete |
| API authentication | Bearer token + rate limiting | Complete |
| Docker builds | Multi-stage API + Dashboard | Complete |
| CI pipeline | GitHub Actions (lint + test) | Complete |
