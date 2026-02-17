# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**Nereus** is a provenance-first blue finance platform, powered by MARIS + Semantica. It creates auditable, DOI-backed pathways from peer-reviewed ecological science to investment-grade financial metrics for blue natural capital.

**Current Status:** Production-ready v4 Global Scaling Platform - a Neo4j knowledge graph (938 nodes, 244 edges) spanning 9 MPA sites across 4 ocean basins, $1.62B aggregate ESV portfolio. FastAPI query engine (9 endpoints), four Streamlit dashboards (v1-v4), 195 verified papers, 16 bridge axioms, Semantica SDK integration (P0-P4) complete across 27 modules. Validated by a 910-test suite (706 unit + 204 integration) with GitHub Actions CI.

---

## Quick Start

```bash
# v4 Global Scaling Platform (recommended) - 9 sites, 6 tabs
./launch.sh v4

# Other versions
./launch.sh v3    # Intelligence Platform (2 sites, 5 tabs, port 8503)
./launch.sh v2    # Single-scroll dashboard (2 sites, port 8501)
./launch.sh v1    # Static mode (1 site, no external services)
./launch.sh api   # API server only (port 8000)
./launch.sh stop  # Stop all services
```

Manual setup:

```bash
cp .env.example .env            # Configure: MARIS_NEO4J_PASSWORD, MARIS_LLM_API_KEY, MARIS_API_KEY
uv pip install -r requirements-v2.txt
python scripts/populate_neo4j_v4.py   # Populate v4 graph (9 sites, auto-discovers examples/*_case_study.json)
uvicorn maris.api.main:app --host 0.0.0.0 --port 8000   # Terminal 1
cd investor_demo && streamlit run streamlit_app_v4.py --server.port 8504  # Terminal 2
```

Docker: `docker compose up --build`

---

## System Architecture

```
User Question (NL) -> QueryClassifier (keyword + LLM fallback, 5 categories)
  -> CypherTemplates (8 parameterized, never string interpolation)
  -> QueryExecutor (Neo4j bolt, parameterized queries only)
  -> ResponseGenerator (LLM grounds graph results with DOI citations)
  -> ResponseFormatter (confidence score, evidence, caveats)
  -> FastAPI JSON Response -> Streamlit Dashboard (dark-mode investor UI)

Three-Layer Translation Model:
  ECOLOGICAL DATA -> BRIDGE AXIOMS (16 rules, DOI-backed) -> FINANCIAL METRICS
```

### Technology Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| Knowledge Graph | Neo4j Enterprise 5.x | 938 nodes, 244 edges; bolt://localhost:7687 |
| API Server | FastAPI + Uvicorn | 9 endpoints; http://localhost:8000 |
| Dashboard | Streamlit 1.54 | v4 at :8504, v3 at :8503, v2 at :8501 |
| LLM | DeepSeek V3 (default) | Classification + response synthesis |
| Computation | NumPy, NetworkX | Monte Carlo (10k runs), graph analysis |

---

## Module Structure

```
maris/
  api/                            # FastAPI server
    main.py, models.py, auth.py   # App factory, Pydantic schemas, Bearer auth + rate limiting
    routes/                       # health, query, graph, provenance, disclosure
  graph/                          # Neo4j: connection.py, schema.py, population.py, validation.py
  query/                          # NL-to-Cypher: classifier.py, cypher_templates.py, executor.py,
                                  #   generator.py, formatter.py, validators.py
  llm/                            # adapter.py (DeepSeek/Claude/GPT-4), prompts.py
  axioms/                         # engine.py, confidence.py, monte_carlo.py, sensitivity.py
  ingestion/                      # pdf_extractor.py, llm_extractor.py, embedding_generator.py, graph_merger.py
  provenance/                     # P0: W3C PROV-O - manager.py, bridge_axiom_registry.py, certificate.py,
                                  #   core.py, integrity.py, storage.py (InMemory + SQLite)
  sites/                          # P1: Multi-site - api_clients.py (OBIS/WoRMS/Marine Regions),
                                  #   characterizer.py, esv_estimator.py, models.py, registry.py
  reasoning/                      # P2: context_builder.py, hybrid_retriever.py, inference_engine.py,
                                  #   rule_compiler.py, explanation.py
  disclosure/                     # P3: TNFD LEAP - leap_generator.py, leap_generator_v4.py,
                                  #   renderers.py, alignment_scorer.py, models.py
  discovery/                      # P4: pattern_detector.py, llm_detector.py, aggregator.py,
                                  #   candidate_axiom.py, reviewer.py, pipeline.py
  semantica_bridge/               # SDK adapter: storage_adapter.py, axiom_adapter.py,
                                  #   provenance_adapter.py, integrity_adapter.py, manager.py
  config.py                       # Centralized config from .env (MARIS_ prefix)
  config_v4.py                    # v4 dynamic site discovery, Neo4j config overlay

investor_demo/
  streamlit_app_v4.py             # v4 Global Scaling Platform (9 sites, 6 tabs, $1.62B)
  streamlit_app_v3.py             # v3 Intelligence Platform (2 sites, 5 tabs)
  streamlit_app_v2.py             # v2 Live dashboard
  streamlit_app.py                # v1 Static dashboard
  api_client.py                   # HTTP client with auto-fallback to precomputed
  precomputed_responses_v4.json   # v4 demo fallback (9 sites)
  precomputed_responses.json      # v3 fallback (63 queries)
  components/
    v4/                           # v4 components: shared.py, portfolio_overview.py,
                                  #   intelligence_brief.py, graphrag_chat.py,
                                  #   scenario_engine.py, tnfd_compliance.py
    v3/                           # v3 components: shared.py, intelligence_brief.py,
                                  #   graphrag_chat.py, scenario_engine.py, tnfd_compliance.py
    chat_panel.py, graph_explorer.py, roadmap_section.py  # v2 components

scripts/
  populate_neo4j_v4.py            # v4 populator (11-stage, dynamic site discovery)
  populate_neo4j.py               # Legacy populator (2-site, v2/v3)
  validate_graph.py, demo_healthcheck.py, run_ingestion.py

tests/                            # 910 tests (706 unit + 204 integration)
  conftest.py                     # Shared fixtures
  test_*.py                       # Unit tests for all modules
  integration/                    # 7-phase integration suite (204 tests)

launch.sh                         # Unified launcher (v1|v2|v3|v4|api|stop)
```

---

## Knowledge Graph Data Lineage

The v4 populator (`scripts/populate_neo4j_v4.py`) auto-discovers sites from `examples/*_case_study.json` through an 11-stage idempotent pipeline (all MERGE operations):

| Source | File(s) | Creates |
|--------|---------|---------|
| Document Registry | `.claude/registry/document_index.json` | 835 Document nodes |
| Entity Definitions | `data/semantica_export/entities.jsonld` | 14 JSON-LD entities |
| 9 Case Study JSONs | `examples/*_case_study.json` | MPA nodes, EcosystemService values, Species, TrophicLevel, GENERATES edges |
| Bridge Axioms | `schemas/bridge_axiom_templates.json` + `data/semantica_export/bridge_axioms.json` | 16 BridgeAxiom nodes; EVIDENCED_BY, APPLIES_TO, TRANSLATES edges |
| Relationships | `data/semantica_export/relationships.json` | 15 cross-domain edges |
| Comparison Sites | Hardcoded | GBR + Papahanaumokuakea (governance metadata only) |

---

## API Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/health` | No | System status, graph stats |
| POST | `/api/query` | Yes | NL question -> classified Cypher -> grounded answer with provenance |
| GET | `/api/site/{site_name}` | Yes | Structured site data (full for 9 Gold-tier, governance-only for comparison) |
| GET | `/api/axiom/{axiom_id}` | Yes | Bridge axiom details, coefficients, evidence |
| POST | `/api/compare` | Yes | Side-by-side MPA comparison |
| POST | `/api/graph/traverse` | Yes | Graph traversal (1-6 hops) |
| GET | `/api/graph/node/{element_id}` | Yes | Node properties and relationships |
| GET | `/api/provenance/{entity_id}` | Yes | W3C PROV-O lineage and certificate |
| POST | `/api/disclosure/tnfd-leap` | Yes | TNFD LEAP disclosure generation |

**Auth:** Bearer token via `Authorization: Bearer <MARIS_API_KEY>`. Bypassed when `MARIS_DEMO_MODE=true`.
**Rate limits:** `/api/query` 30/min, others 60/min. HTTP 429 when exceeded.

---

## Query Classification

| Category | Triggers | Returns |
|----------|----------|---------|
| `site_valuation` | value, worth, ESV, asset rating | MPA metadata, service values, axioms with evidence |
| `provenance_drilldown` | evidence, provenance, DOI, source | Multi-hop path: MPA -> axioms -> Documents |
| `axiom_explanation` | bridge axiom, BA-001, coefficient, seagrass | Axiom details, coefficients, evidence |
| `comparison` | compare, versus, rank, benchmark | Side-by-side MPA metrics |
| `risk_assessment` | risk, degradation, climate, threat | Risk factors, confidence intervals |

**Site resolution:** "Cabo Pulmo" -> "Cabo Pulmo National Park", "Shark Bay"/"SB" -> "Shark Bay World Heritage Area", etc. Patterns in `_SITE_PATTERNS` in `classifier.py`.

---

## Graph Schema

### Node Labels (938 total)

| Label | Key | Count | Description |
|-------|-----|-------|-------------|
| Document | doi | 835 | Peer-reviewed evidence from 195-paper registry |
| EcosystemService | service_name | 39 | Valued services across 9 sites |
| Species | worms_id | 17 | Marine species with WoRMS IDs |
| BridgeAxiom | axiom_id | 16 | Ecological-to-financial translation rules |
| MPA | name | 11 | 9 Gold-tier + GBR + Papahanaumokuakea |
| Concept | name | 10 | Domain concepts (NEOLI, Blue Carbon, etc.) |
| TrophicLevel | name | 10 | Food web nodes |
| Habitat | habitat_id | 4 | Coral reef, kelp, seagrass, mangrove |
| FinancialInstrument | instrument_id | 3 | Blue bond, reef insurance, carbon credit |
| Framework | framework_id | 3 | TNFD LEAP, SEEA, Verra VCS |

### Relationships (244 total)

GENERATES (MPA->Service), APPLIES_TO (Axiom->MPA), TRANSLATES (Axiom->Service), EVIDENCED_BY (Axiom->Document), HAS_HABITAT (MPA->Habitat), INHABITS (Species->Habitat), LOCATED_IN (Species->MPA), PREYS_ON (Trophic->Trophic), PART_OF_FOODWEB (Trophic->MPA), PROVIDES (Habitat->Service), DERIVED_FROM (MPA->Document), APPLICABLE_TO (Framework->MPA), GOVERNS (Framework->Instrument), APPLIES_TO_HABITAT (Axiom->Habitat)

---

## Bridge Axioms (16)

| ID | Name | Translation | Coefficient |
|----|------|-------------|-------------|
| BA-001 | mpa_biomass_dive_tourism_value | Fish biomass -> Tourism WTP | Up to 84% higher WTP |
| BA-002 | notake_mpa_biomass_multiplier | No-take MPA -> Biomass recovery | 4.63x over 10 years |
| BA-003 | sea_otter_kelp_carbon_cascade | Kelp forest -> Carbon value | Trophic cascade |
| BA-004 | coral_reef_flood_protection | Coral reef -> Flood protection | Wave energy reduction |
| BA-005 | mangrove_flood_protection | Mangrove -> Flood protection | $/ha coastal defense |
| BA-006 | mangrove_fisheries_production | Mangrove -> Fisheries yield | Nursery production |
| BA-007 | mangrove_carbon_stock | Mangrove -> Carbon stock | tCO2/ha stored |
| BA-008 | seagrass_carbon_credit_value | Seagrass -> Carbon credits | $/ha credit value |
| BA-009 | mangrove_restoration_bcr | Restoration -> BCR | 6-15x multiplier |
| BA-010 | kelp_forest_global_value | Kelp forest -> Global value | $/ha ESV |
| BA-011 | mpa_climate_resilience | MPA -> Climate resilience | Resilience index |
| BA-012 | reef_degradation_fisheries_loss | Reef degradation -> Fisheries loss | Revenue decline |
| BA-013 | seagrass_carbon_sequestration_rate | Seagrass -> Carbon sequestration | 0.84 tCO2/ha/yr |
| BA-014 | carbon_stock_to_credit_value | Carbon stock -> Credit value | $30/tonne Verra VCS |
| BA-015 | habitat_loss_carbon_emission | Habitat loss -> Carbon emission | 294 tCO2/ha released |
| BA-016 | mpa_protection_carbon_permanence | MPA -> Carbon permanence | Buffer pool discount |

---

## Site Portfolio ($1.62B across 9 Gold-tier MPAs)

| Site | Country | Habitat | ESV | Rating |
|------|---------|---------|-----|--------|
| Cabo Pulmo National Park | Mexico | Coral reef | $29.27M | AAA |
| Shark Bay World Heritage Area | Australia | Seagrass | $21.5M | AA |
| Ningaloo Coast | Australia | Coral reef | $145.0M | AA |
| Belize Barrier Reef | Belize | Coral reef + mangrove | $395.0M | AA |
| Galapagos Marine Reserve | Ecuador | Mixed/volcanic | $285.0M | AAA |
| Raja Ampat MPA Network | Indonesia | Coral reef | $362.0M | AA |
| Sundarbans Reserve Forest | Bangladesh/India | Mangrove | $187.0M | A |
| Aldabra Atoll | Seychelles | Coral reef/atoll | $78.0M | AAA |
| Cispata Bay MPA | Colombia | Mangrove | $139.0M | A |

Comparison sites (GBR, Papahanaumokuakea): governance metadata only, no ESV.
4 ocean basins: Pacific, Indian, Atlantic, Caribbean. 4 habitats: coral, seagrass, mangrove, mixed.

**Cabo Pulmo reference values:** ESV $29.27M (market-price), Tourism $25.0M, Biomass 4.63x CI [3.8, 5.5], NEOLI 4/5, Rating AAA (composite 0.90).

---

## Testing

```bash
pip install -r requirements-dev.txt
pytest tests/ -v                              # All 910 tests
pytest tests/ --cov=maris --cov-report=term-missing  # With coverage
```

910 tests (706 unit + 204 integration) covering all modules. CI via GitHub Actions (`.github/workflows/ci.yml`): ruff lint + pytest.

---

## Environment Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MARIS_NEO4J_URI` | bolt://localhost:7687 | Neo4j bolt connection |
| `MARIS_NEO4J_USER` | neo4j | Neo4j username |
| `MARIS_NEO4J_PASSWORD` | - | Neo4j password (required) |
| `MARIS_LLM_PROVIDER` | deepseek | deepseek, anthropic, openai |
| `MARIS_LLM_API_KEY` | - | LLM API key (required for live queries) |
| `MARIS_LLM_MODEL` | deepseek-chat | Model identifier |
| `MARIS_DEMO_MODE` | false | true = precomputed responses, bypass auth |
| `MARIS_API_KEY` | - | Bearer token (required unless DEMO_MODE) |
| `MARIS_CORS_ORIGINS` | http://localhost:8501 | Allowed CORS origins |
| `MARIS_PROVENANCE_DB` | provenance.db | SQLite path for PROV-O persistence |
| `MARIS_NEO4J_URI_V4` | bolt://localhost:7687 | v4 populator Neo4j URI |
| `MARIS_NEO4J_DATABASE_V4` | neo4j | v4 populator database name |

`.env` is gitignored. Never commit secrets. Use `MARIS_DEMO_MODE=true` for dev startup without API key.

---

## Extending the System

**New MPA site:** Create `examples/<name>_case_study.json` (follow any existing case study structure), then run `python scripts/populate_neo4j_v4.py`. The v4 populator auto-discovers new files.

**New bridge axiom:** Add to `schemas/bridge_axiom_templates.json` + `data/semantica_export/bridge_axioms.json`, then re-run the populator.

**New Cypher template:** Add to `maris/query/cypher_templates.py`, add keyword rules in `classifier.py`, handle parameters in `routes/query.py`.

**New API endpoint:** Define Pydantic models in `models.py`, create route in `routes/`, register in `main.py`.

---

## Terminology Rules

- **"NEOLI alignment"** not "NEOLI compliance"
- **"market-price"** not "NOAA-adjusted" for tourism valuation
- **"anticipates alignment with"** not "anticipates compliance with"
- **No em dashes** (use hyphens or " - ")
- ESV = $29.27M, Tourism = $25.0M, Biomass = 4.63x with CI [3.8, 5.5]

---

## Success Criteria

| Criterion | Status |
|-----------|--------|
| 195 papers, 92% T1 | Complete |
| 16 axioms x 3+ sources | Complete |
| 9-site portfolio, $1.62B, 4 ocean basins | Complete |
| Neo4j: 938 nodes, 244 edges | Complete |
| 910 tests (706 unit + 204 integration) | Complete |
| v1-v4 dashboards operational | Complete |
| Semantica SDK P0-P4 (27 modules) | Complete |
| W3C PROV-O + TNFD LEAP + Auth + CI | Complete |
