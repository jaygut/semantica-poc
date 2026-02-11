# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. It is designed to bring any new session to full operational context within seconds.

## Project Overview

**MARIS** (Marine Asset Risk Intelligence System) is a provenance-first knowledge graph that creates auditable, DOI-backed pathways from peer-reviewed ecological science to investment-grade financial metrics for blue natural capital. Built on the Semantica framework, it is designed for institutional investors, blue bond underwriters, TNFD working groups, and conservation finance professionals who require full scientific traceability behind every number.

**Current Status:** Production-ready POC deployed on `main`. The system comprises a Neo4j knowledge graph (878 nodes, 101 edges), a FastAPI query engine with natural-language-to-Cypher classification, and an investor-facing Streamlit dashboard with interactive graph visualization. The document library contains 195 verified papers, 12 fully-evidenced bridge axioms, and a Semantica-ready export bundle. The system also runs in static mode from a pre-computed JSON bundle for zero-downtime investor demos.

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
│  CypherTemplates  -- 6 parameterized templates, never raw string interpolation   │
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
│  ECOLOGICAL DATA  -->  BRIDGE AXIOMS (12 rules)  -->  FINANCIAL METRICS          │
│  Species, Habitats     BA-001 through BA-012         Blue bonds, TNFD,           │
│  MPAs, Observations    DOI-backed coefficients       Credits, Insurance          │
│                                                                                  │
│  Every claim traceable to DOI + evidence tier + bridge axiom                     │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Knowledge Graph | Neo4j Community 5.x | 878 nodes, 101 edges; bolt://localhost:7687 |
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
# Edit .env: set MARIS_NEO4J_PASSWORD and MARIS_LLM_API_KEY

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

The graph is populated from **six curated data sources** through an 8-stage idempotent pipeline (`scripts/populate_neo4j.py`). All operations use MERGE (safe to re-run).

### Source Datasets

| # | Source | File | What It Creates |
|---|--------|------|-----------------|
| 1 | Document Registry | `.claude/registry/document_index.json` | 195 Document nodes (DOI, title, year, evidence tier) |
| 2 | Entity Definitions | `data/semantica_export/entities.jsonld` | 14 JSON-LD entities: Species, MPA, Habitat, EcosystemService, FinancialInstrument, Framework, Concept |
| 3 | Cabo Pulmo Case Study | `examples/cabo_pulmo_case_study.json` | MPA enrichment (NEOLI, biomass, ESV), EcosystemService values, Species nodes, TrophicLevel food web, GENERATES edges |
| 4 | Bridge Axiom Templates + Evidence | `schemas/bridge_axiom_templates.json` + `data/semantica_export/bridge_axioms.json` | 12 BridgeAxiom nodes; EVIDENCED_BY, APPLIES_TO, TRANSLATES edges |
| 5 | Curated Relationships | `data/semantica_export/relationships.json` | 15 cross-domain edges with quantification, mechanism, confidence |
| 6 | Comparison Sites | Hardcoded in `maris/graph/population.py` | Great Barrier Reef, Papahanaumokuakea MPA nodes (governance metadata only) |

### Calibration Site Model

**Cabo Pulmo National Park** is the fully characterized reference site (AAA-rated) with complete financial data:

| Property | Value | Source |
|----------|-------|--------|
| Total ESV | $29.27M/year (market-price) | cabo_pulmo_case_study.json |
| Tourism | $25.0M (market-price expenditure) | Marcos-Castillo et al. 2024 |
| Biomass ratio | 4.63x recovery, CI [3.8, 5.5] | Aburto-Oropeza et al. 2011 |
| NEOLI score | 4/5 criteria met | Edgar et al. 2014 framework |
| Asset rating | AAA (composite 0.90) | Derived from NEOLI + ESV + CI |
| Monte Carlo | Median ~$28.7M, P5 ~$19.6M, P95 ~$36.1M | 10,000 simulations |

**Comparison sites** (Great Barrier Reef, Papahanaumokuakea) have governance metadata only (area, designation year, NEOLI score, asset rating) - no ecosystem service valuations. This is by design: the POC demonstrates the full provenance chain for one deeply characterized site.

---

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/health` | System status: Neo4j connectivity, LLM availability, graph statistics |
| POST | `/api/query` | Primary endpoint: NL question -> classified Cypher -> grounded answer with provenance |
| GET | `/api/site/{site_name}` | Structured site data (full for Cabo Pulmo, governance-only for comparison sites) |
| GET | `/api/axiom/{axiom_id}` | Bridge axiom details: coefficients, evidence, applicable sites |
| POST | `/api/compare` | Side-by-side MPA comparison |
| POST | `/api/graph/traverse` | Graph traversal from a starting node (1-6 hops) |
| GET | `/api/graph/node/{element_id}` | Node properties and relationships by Neo4j element ID |

---

## Module Structure

```
maris/
  api/                          # FastAPI server
    main.py                     # App factory, CORS, router registration
    models.py                   # Pydantic v2 request/response schemas
    routes/
      health.py                 # GET /api/health
      query.py                  # POST /api/query - full NL-to-answer pipeline
      graph.py                  # Graph traversal and node detail endpoints
  graph/                        # Neo4j integration layer
    connection.py               # Bolt driver singleton, run_query() helper
    schema.py                   # Uniqueness constraints and indexes
    population.py               # 8-stage population pipeline from curated JSON
    validation.py               # Post-population integrity checks
  query/                        # NL-to-Cypher pipeline
    classifier.py               # Two-tier: keyword regex + LLM fallback
    cypher_templates.py         # 6 parameterized Cypher templates by category
    executor.py                 # Template execution + provenance edge extraction
    generator.py                # LLM response synthesis from graph context
    formatter.py                # Structured output: confidence, evidence, caveats
  llm/                          # LLM abstraction
    adapter.py                  # OpenAI-compatible client (DeepSeek, Claude, GPT-4)
    prompts.py                  # System prompts for classification and generation
  axioms/                       # Bridge axiom computation
    engine.py                   # Axiom application and chaining
    confidence.py               # Multiplicative confidence interval propagation
    monte_carlo.py              # Monte Carlo ESV simulation (10,000 runs)
  ingestion/                    # Document ingestion pipeline
    pdf_extractor.py            # PDF text extraction
    llm_extractor.py            # LLM-based entity/relationship extraction
    embedding_generator.py      # Vector embeddings for semantic search
    graph_merger.py             # Merge extracted triples into Neo4j
  config.py                     # Centralized config from .env (MARIS_ prefix)

investor_demo/
  streamlit_app_v2.py           # Live dashboard - CSS, layout, data, Ask MARIS, Graph Explorer
  streamlit_app.py              # Static dashboard - bundle-only, zero dependencies
  api_client.py                 # HTTP client wrapping MARIS API; auto-fallback to precomputed
  components/
    chat_panel.py               # Ask MARIS query UI with markdown, confidence badges, evidence
    graph_explorer.py           # Plotly network graph with semantic layering
  precomputed_responses.json    # Cached responses for 5 common queries (API fallback)
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
```

---

## Key Files Reference

### Core Data Assets

| File | Purpose |
|------|---------|
| `.claude/registry/document_index.json` | Master bibliography (195 papers with DOI, tier, domain) |
| `examples/cabo_pulmo_case_study.json` | AAA reference site: NEOLI, biomass, ESV, species, trophic network |
| `schemas/bridge_axiom_templates.json` | 12 bridge axioms with translation coefficients and DOI evidence |
| `data/semantica_export/entities.jsonld` | 14 JSON-LD entities (WoRMS, FishBase, TNFD URIs) |
| `data/semantica_export/relationships.json` | 15 cross-domain edges with quantification and mechanism |
| `data/semantica_export/bridge_axioms.json` | Axiom evidence mapping for graph population |
| `demos/context_graph_demo/cabo_pulmo_investment_grade_bundle.json` | Pre-computed bundle for static dashboard |

### Schemas

| File | Purpose |
|------|---------|
| `schemas/entity_schema.json` | 8 entity types (JSON-LD format) |
| `schemas/relationship_schema.json` | 14 relationship types + inference rules |
| `schemas/bridge_axiom_templates.json` | 12 translation rules with coefficients |
| `schemas/registry_schema.json` | Document validation schema |

### Infrastructure

| File | Purpose |
|------|---------|
| `.env.example` | Environment template (Neo4j, LLM, feature flags) |
| `docker-compose.yml` | Neo4j + API + Dashboard one-command startup |
| `requirements-v2.txt` | Full v2 dependencies (FastAPI, neo4j, streamlit, etc.) |
| `investor_demo/requirements.txt` | Minimal v1 dependencies |

### Documentation

| File | Purpose |
|------|---------|
| `README.md` | Project overview, architecture, implementation roadmap |
| `docs/developer_guide.md` | Architecture, data lineage, population pipeline, extension guide |
| `docs/api_reference.md` | Endpoint specs, graph schema, query categories, configuration |
| `docs/user_guide.md` | Dashboard usage, Ask MARIS examples, confidence levels, troubleshooting |
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

**Security:** `.env` contains secrets and is excluded from git via `.gitignore`. Never commit it.

---

## Query Classification System

The `QueryClassifier` (`maris/query/classifier.py`) maps natural-language questions into five categories. Each category is backed by a parameterized Cypher template.

| Category | Keyword Triggers | What the Template Returns |
|----------|-----------------|--------------------------|
| `site_valuation` | value, worth, ESV, asset rating | MPA metadata, ecosystem service values, bridge axioms with evidence |
| `provenance_drilldown` | evidence, provenance, DOI, source | Multi-hop path from MPA through axioms to source Documents |
| `axiom_explanation` | bridge axiom, BA-001, coefficient | Axiom details, translation coefficients, evidence sources |
| `comparison` | compare, versus, rank, benchmark | Side-by-side MPA metrics |
| `risk_assessment` | risk, degradation, climate, threat | Ecological-to-service axioms, risk factors, confidence intervals |

**Site name resolution:** The classifier maps common names to canonical Neo4j node names (e.g., "Cabo Pulmo" -> "Cabo Pulmo National Park"). Patterns are defined in `_SITE_PATTERNS` in `classifier.py`.

---

## Graph Schema (Neo4j)

### Node Labels

| Label | Merge Key | Count | Description |
|-------|-----------|-------|-------------|
| Document | doi | 828 | Peer-reviewed evidence sources from 195-paper registry |
| BridgeAxiom | axiom_id | 12 | Ecological-to-financial translation rules |
| TrophicLevel | name | 10 | Food web nodes (apex predator, mesopredator, etc.) |
| Concept | name | 8 | Domain concepts (NEOLI Criteria, etc.) |
| EcosystemService | service_name | 6 | Valued services (Tourism, Fisheries, Carbon, etc.) |
| Habitat | habitat_id | 4 | Marine habitats (coral reef, kelp, seagrass, mangrove) |
| MPA | name | 3 | Marine Protected Areas |
| Species | worms_id | 3 | Marine species with WoRMS identifiers |
| FinancialInstrument | instrument_id | 2 | Blue bond, parametric reef insurance |
| Framework | framework_id | 2 | TNFD LEAP, SEEA |

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

Bridge axioms are the core translation mechanism - each converts an ecological state measurement into a financial value through peer-reviewed coefficients.

| Axiom | Name | Translation | Key Coefficient |
|-------|------|-------------|-----------------|
| BA-001 | mpa_biomass_dive_tourism_value | Fish biomass -> Tourism WTP | Up to 84% higher WTP per unit biomass |
| BA-002 | notake_mpa_biomass_recovery | No-take MPA -> Biomass recovery | 4.63x over 10-year recovery arc |
| BA-003 | reef_carbon_sequestration | Coral reef area -> Carbon value | Calcification rate per hectare |
| BA-004 | habitat_coastal_flood_protection | Coastal habitat -> Flood protection | Wave energy reduction per meter reef |
| BA-005 | biodiversity_reef_insurance | Species diversity -> Insurance value | Reef complexity index |
| BA-006 | water_quality_regulation_value | Reef filtering -> Water quality | Nutrient cycling per hectare |
| BA-007 | genetic_bioprospecting_value | Marine biodiversity -> Biotech potential | Patent-to-species ratio |
| BA-008 | sustainable_fisheries_value | Fish biomass -> Fisheries yield | Maximum sustainable yield model |
| BA-009 | trophic_cascade_multiplier | Apex predator -> Ecosystem health | Top-down trophic control |
| BA-010 | mpa_network_connectivity | MPA spacing -> Larval connectivity | Dispersal distance model |
| BA-011 | neoli_asset_rating_mapping | NEOLI criteria -> Asset rating | Composite 0-1 score |
| BA-012 | tnfd_leap_disclosure | Ecosystem data -> TNFD reporting | 4-phase LEAP framework |

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

1. Create a case study JSON following the structure of `examples/cabo_pulmo_case_study.json`
2. Add a population function in `maris/graph/population.py` (pattern: `_populate_cabo_pulmo()`)
3. Add the site's canonical name to `_SITE_PATTERNS` in `maris/query/classifier.py`
4. Run `python scripts/populate_neo4j.py` to load the new site

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
| Bridge axiom evidence | 12 axioms x 3+ sources | Complete |
| Live query pipeline | End-to-end NL-to-answer | Working |
| Graph population | 878 nodes, 101 edges | Complete |
| Dashboard (live + static) | Both modes operational | Working |
