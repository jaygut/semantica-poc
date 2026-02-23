# Nereus Developer Guide

## System Purpose

Nereus is a provenance-first blue finance platform, powered by MARIS (Marine Asset Risk Intelligence System) + Semantica. It creates auditable, DOI-backed pathways from peer-reviewed ecological science to investment-grade financial metrics for blue natural capital. The system is designed for institutional investors, blue bond underwriters, TNFD working groups, and conservation finance professionals who require full scientific traceability behind every number.

The v6 Prospective Scenario Intelligence release (built on v5 Audit-Grade Integrity) transforms Nereus from retrospective ESV valuation into forward-looking scenario intelligence. It adds a `maris/scenario/` module with counterfactual analysis, SSP climate degradation curves, McClanahan tipping point engine, blue carbon revenue modeling, portfolio Nature VaR (Cholesky-correlated Monte Carlo), and real options valuation - all provenance-traced with P5/P50/P95 uncertainty envelopes. A 7th query category (`scenario_analysis`) routes "what if" and SSP questions through the new engine. Bridge axioms expanded from 35 to 40 (BA-036-040: McClanahan threshold axioms). The Neo4j graph contains 953+ nodes and 244+ edges across 9 Gold-tier MPA sites, with a FastAPI query engine covering 7 natural-language classification categories.

## Architecture Overview

```
User Question (natural language)
     |
     v
 QueryClassifier  -- keyword-first with LLM fallback
     |              (7 categories: valuation, provenance, axiom, comparison, risk, concept_explanation, scenario_analysis)
     v
 CypherTemplates  -- 11 templates (5 core + 3 utility + 3 concept), never raw string interpolation
     |
     v
 QueryExecutor    -- Neo4j bolt driver, parameterized queries only
     |
     v
 ResponseGenerator -- LLM grounds graph results into narrative with DOI citations
     |
     v
 ResponseFormatter -- extracts confidence score, evidence items, caveats
     |
     v
 FastAPI JSON Response -- answer + evidence + provenance chain + graph path
```

### Module Structure

```
maris/
  api/                        # FastAPI server
    main.py                   # App factory, CORS, router registration
    models.py                 # Pydantic v2 request/response schemas
    auth.py                   # Bearer token auth, rate limiting (30/min query, 60/min other), input validation, request tracing (X-Request-ID), hashed IP logging
    routes/
      health.py               # GET /api/health - Neo4j + LLM status + graph stats
      query.py                # POST /api/query - full NL-to-answer pipeline
      graph.py                # Graph traversal and node detail endpoints
      provenance.py           # GET /api/provenance/{entity_id} - lineage and certificates
      disclosure.py           # POST /api/disclosure/tnfd-leap - TNFD LEAP generation
  graph/                      # Neo4j integration layer
    connection.py             # Bolt driver singleton, run_query() helper
    schema.py                 # Uniqueness constraints and indexes
    population.py             # Legacy 8-stage population pipeline (Cabo Pulmo + Shark Bay)
    population_v4.py          # v4 11-stage generic populator with dynamic site discovery
    validation.py             # Post-population integrity checks
  query/                      # NL-to-Cypher pipeline
    classifier.py             # Two-tier classification: keyword regex (case-insensitive BA, DOI, risk patterns, comparison tie-break) + LLM fallback
    cypher_templates.py       # 8 Cypher templates (5 core + 3 utility) by category
    validators.py             # LLM response validation: schema checks, confidence bounds, DOI format, numerical claim verification, robust JSON extraction
    executor.py               # Template execution + provenance edge extraction
    generator.py              # LLM response synthesis from graph context
    formatter.py              # Structured output: confidence, evidence, caveats
  llm/                        # LLM abstraction
    adapter.py                # OpenAI-compatible client (DeepSeek, Claude, GPT-4)
    prompts.py                # System prompts for classification and generation
  axioms/                     # Bridge axiom computation
    engine.py                 # Axiom application and chaining
    confidence.py             # Multiplicative confidence interval propagation + apply_scenario_penalties() (v6)
    monte_carlo.py            # Monte Carlo ESV simulation (10,000 runs)
    sensitivity.py            # OAT sensitivity analysis for ESV simulations, tornado plot data generation
  scenario/                   # v6 NEW: Prospective scenario intelligence
    constants.py              # SSP_SCENARIOS, BIOMASS_THRESHOLDS, CARBON_PRICE_SCENARIOS, BLUE_CARBON_SEQUESTRATION (DOI-sourced)
    models.py                 # Pydantic v2: ScenarioRequest, ScenarioResponse, ScenarioDelta, PropagationStep, ScenarioUncertainty
    scenario_parser.py        # NL -> ScenarioRequest (pattern-based, no LLM required in demo mode)
    counterfactual_engine.py  # run_counterfactual(): protection removal delta (Cabo Pulmo -$20.16M validated)
    climate_scenarios.py      # run_climate_scenario(): SSP1-2.6/SSP2-4.5/SSP5-8.5 degradation curves per habitat/year
    tipping_point_analyzer.py # compute_reef_function(): McClanahan 4-threshold piecewise; get_tipping_point_site_report()
    blue_carbon_revenue.py    # compute_blue_carbon_revenue(): dynamic carbon pricing, mangrove/seagrass sequestration
    stress_test_engine.py     # run_portfolio_stress_test(): Nature VaR with Cholesky-correlated Monte Carlo
    real_options_valuator.py  # compute_conservation_option_value(): GBM-based option premium above static NPV
  ingestion/                  # Document ingestion pipeline
    pdf_extractor.py          # PDF text extraction
    llm_extractor.py          # LLM-based entity/relationship extraction
    embedding_generator.py    # Vector embeddings for semantic search
    graph_merger.py           # Merge extracted triples into Neo4j
  provenance/                 # P0: W3C PROV-O provenance tracking
    manager.py                # MARISProvenanceManager (entity/activity/agent tracking)
    bridge_axiom_registry.py  # 40 axioms as typed BridgeAxiom objects with TranslationChain
    bridge_axiom.py           # BridgeAxiom dataclass
    certificate.py            # Provenance certificate generation (JSON/Markdown)
    core.py                   # PROV-O core dataclasses (ProvenanceEntity, ProvenanceActivity, ProvenanceAgent)
    integrity.py              # SHA-256 checksum verification
    storage.py                # InMemoryStorage and SQLiteStorage backends
    doi_verifier.py           # DOI format and reachability verification (v5 NEW)
    models.py                 # Provenance Pydantic models for strict deterministic guards (v5 NEW)
  sites/                      # P1: Multi-site scaling pipeline
    api_clients.py            # OBIS (numeric area resolution), WoRMS (204 fix), Marine Regions (404+JSON handling) API clients
    characterizer.py          # 5-step auto-characterization pipeline (Bronze/Silver/Gold) with multi-signal habitat scoring (keywords, taxonomy, functional groups)
    esv_estimator.py          # Bridge axiom-based ESV estimation with CI propagation
    models.py                 # Pydantic v2 models (SiteCharacterization, SpeciesRecord, etc.)
    registry.py               # JSON-backed site registry with CRUD operations
  reasoning/                  # P2: Cross-domain reasoning engine
    context_builder.py        # Convert Neo4j results to Semantica ContextGraph
    hybrid_retriever.py       # Graph + keyword + Reciprocal Rank Fusion retrieval
    inference_engine.py       # Forward/backward chaining with bridge axiom rules
    rule_compiler.py          # Rule compilation extracted from InferenceEngine
    explanation.py            # Investor-friendly explanation generation
  disclosure/                 # P3: TNFD LEAP disclosure automation
    models.py                 # Pydantic models for TNFD LEAP 4-phase sections
    leap_generator.py         # TNFD LEAP document generation from graph data
    renderers.py              # Markdown, JSON, and executive summary output
    alignment_scorer.py       # 14-disclosure gap analysis and scoring
  discovery/                  # P4: Dynamic axiom discovery pipeline
    pattern_detector.py       # Cross-paper quantitative pattern detection (regex)
    llm_detector.py           # LLM-enhanced pattern detection with regex fallback, retry logic, numeric confidence, robust JSON parsing
    aggregator.py             # Multi-study aggregation with conflict detection
    candidate_axiom.py        # Candidate axiom formation (compatible with bridge_axiom_templates.json)
    reviewer.py               # Human-in-the-loop accept/reject workflow
    pipeline.py               # End-to-end discovery pipeline orchestration
  semantica_bridge/           # Semantica SDK adapter layer
    storage_adapter.py        # SemanticaStorage wrapping semantica.provenance.storage
    axiom_adapter.py          # MARIS <-> Semantica BridgeAxiom conversion + chaining
    provenance_adapter.py     # Dual-write ProvenanceManager (MARIS + Semantica)
    integrity_adapter.py      # Integrity verification backed by Semantica checksums
    manager.py                # SemanticaBackedManager - drop-in replacement with SQLite persistence
  config.py                   # Centralized configuration from .env
  config_v4.py                # v4 dynamic site discovery, separate Neo4j config overlay

investor_demo/
  streamlit_app_v4.py          # v4 Global Portfolio dashboard (9 sites, 6 tabs, recommended)
  streamlit_app_v3.py          # v3 Intelligence Platform (multi-tab, 2 sites)
  streamlit_app_v2.py          # v2 dashboard (live API + static bundle)
  streamlit_app.py             # v1 dashboard (static bundle only)
  api_client.py                # HTTP client for MARIS API with auto-fallback
  precomputed_responses.json   # Cached responses for 63 common queries
  components/
    v3/                        # v3 Intelligence Platform components
      __init__.py              # Package init with shared exports
      shared.py                # COLORS dict, V3_CSS, formatters, service health checks
      intelligence_brief.py    # Tab 1: KPIs, provenance graph, axiom evidence, risk profile
      graphrag_chat.py         # Tab 2: Split-panel GraphRAG with pipeline transparency
      scenario_engine.py       # Tab 3: Interactive Monte Carlo with 4 parameter sliders
      tnfd_compliance.py       # Tab 5: TNFD LEAP generation + alignment scoring
    chat_panel.py              # v2 Ask MARIS query interface
    graph_explorer.py          # v2 interactive Plotly provenance visualization
    roadmap_section.py         # Scaling Intelligence section (shared v1/v2)
```

### Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/populate_neo4j_v4.py` | v4 11-stage generic populator with dynamic site discovery (recommended) |
| `scripts/populate_neo4j.py` | Legacy 8-stage population pipeline (Cabo Pulmo + Shark Bay only) |
| `scripts/validate_graph.py` | Verifies node counts, relationship integrity, axiom evidence chains |
| `scripts/generate_scenario_audit_bundle.py` | v6 NEW: generates 5 canonical scenario transcripts in docs/scenario_audit_bundle/ |
| `scripts/demo_healthcheck.py` | Pre-demo verification: Neo4j + API + dashboard connectivity |
| `scripts/run_ingestion.py` | Full PDF-to-graph ingestion pipeline |
| `launch.sh` | One-command launcher for any dashboard version + API (see Running the Stack) |

---

## Knowledge Graph Data Lineage

The graph is populated from curated data sources through the v4 generic populator (`scripts/populate_neo4j_v4.py`), which uses dynamic site discovery to automatically find and load all case study JSON files in `examples/*_case_study.json`. All population operations use `MERGE` (idempotent) so the pipeline is safe to re-run.

### Source Datasets

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        DATA LINEAGE: SOURCE -> GRAPH                         │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Document Registry           .claude/registry/document_index.json         │
│     195 peer-reviewed papers    -> Document nodes (DOI, title, year, tier)   │
│                                                                              │
│  2. Entity Definitions          data/semantica_export/entities.jsonld        │
│     14 JSON-LD instances        -> Species, MPA, Habitat, EcosystemService,  │
│     (WoRMS, FishBase, TNFD)       FinancialInstrument, Framework, Concept    │
│                                                                              │
│  3. Case Study JSONs            examples/*_case_study.json                   │
│     9 Gold-tier MPA sites       -> MPA enrichment (NEOLI, ESV, habitats),    │
│     (dynamic discovery)           EcosystemService values, Species nodes,    │
│                                   TrophicLevel food web, GENERATES edges     │
│                                                                              │
│  4. Bridge Axiom Templates      schemas/bridge_axiom_templates.json         │
│     + Evidence Mapping          data/semantica_export/bridge_axioms.json     │
│     40 axioms with coefficients -> BridgeAxiom nodes, EVIDENCED_BY edges,    │
│     and DOI-backed evidence       APPLIES_TO edges, TRANSLATES edges         │
│     (BA-036-040: McClanahan tipping point thresholds, v6 NEW)                │
│                                                                              │
│  5. Curated Relationships       data/semantica_export/relationships.json    │
│     15 cross-domain edges       -> Typed relationship edges with             │
│     with quantification           quantification, mechanism, confidence      │
│                                                                              │
│  6. Comparison Sites            Hardcoded in population_v4.py                │
│     Great Barrier Reef,         -> MPA nodes with basic metadata only        │
│     Papahanaumokuakea             (NEOLI, area, rating - no service values)  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Population Pipeline (v4 - 11 stages)

The `scripts/populate_neo4j_v4.py` script uses `maris.config_v4` for dynamic site discovery, automatically finding all `examples/*_case_study.json` files and populating them through a generic pipeline. No per-site population functions or classifier patterns are needed - just create a case study JSON and run the populator.

| Stage | Function | Source | Creates |
|-------|----------|--------|---------|
| 1 | `_populate_documents()` | `document_index.json` | 835 Document nodes with DOI, tier, domain |
| 2 | `_populate_entities()` | `entities.jsonld` | Species, MPA, Habitat, EcosystemService, etc. |
| 3 | `_discover_sites()` | `examples/*_case_study.json` | Discovers all case study files dynamically |
| 4 | `_populate_site(site)` | Each case study JSON | MPA enrichment (NEOLI, ESV, habitats), EcosystemService values, Species nodes, TrophicLevel food web |
| 5 | `_populate_site_services(site)` | Each case study JSON | GENERATES edges linking MPA to EcosystemService |
| 6 | `_populate_site_species(site)` | Each case study JSON | Species nodes with LOCATED_IN and INHABITS edges |
| 7 | `_populate_bridge_axioms()` | `bridge_axiom_templates.json` + `bridge_axioms.json` | 40 BridgeAxiom nodes; EVIDENCED_BY, APPLIES_TO, TRANSLATES edges |
| 8 | `_populate_comparison_sites()` | Hardcoded | Great Barrier Reef, Papahanaumokuakea MPA nodes |
| 9 | `_populate_relationships()` | `relationships.json` | Cross-domain relationship edges |
| 10 | `_populate_cross_domain_links()` | Dynamic | Structural edges (HAS_HABITAT, PROVIDES, INHABITS, GOVERNS, etc.) |
| 11 | `_populate_provenance()` | All case study JSONs | DERIVED_FROM edges linking each MPA to source Documents |

The legacy `scripts/populate_neo4j.py` (8-stage) is still available but only loads Cabo Pulmo and Shark Bay.

### Site Portfolio (9 Gold-Tier Sites)

The system has 9 fully characterized Gold-tier sites spanning 4 habitat types and 9 countries. The portfolio demonstrates the framework's habitat-agnostic design across coral reef, seagrass, mangrove, and multi-habitat ecosystems.

| Site | Country | Habitat(s) | ESV | Rating |
|------|---------|-----------|-----|--------|
| Sundarbans Reserve Forest | Bangladesh/India | Mangrove | $778.9M | A |
| Galapagos Marine Reserve | Ecuador | Coral+Kelp+Mangrove | $320.9M | AAA |
| Belize Barrier Reef Reserve System | Belize | Coral+Mangrove+Seagrass | $292.5M | AA |
| Ningaloo Coast WHA | Australia | Coral Reef | $83.0M | AA |
| Raja Ampat Marine Park | Indonesia | Coral+Mangrove | $78.0M | AA |
| Cabo Pulmo National Park | Mexico | Coral Reef | $29.3M | AAA |
| Shark Bay WHA | Australia | Seagrass | $21.5M | AA |
| Cispata Bay Mangrove CA | Colombia | Mangrove | $8.0M | A |
| Aldabra Atoll | Seychelles | Coral+Mangrove+Seagrass | $6.0M | AAA |

**Comparison sites** (Great Barrier Reef Marine Park, Papahanaumokuakea Marine National Monument) are populated with governance metadata only (area, designation year, NEOLI score, asset rating). They do not have ecosystem service valuations or bridge axiom links.

To add a new site, create a case study JSON in `examples/<site_name>_case_study.json` following the structure of any existing case study and run `python scripts/populate_neo4j_v4.py`. The v4 populator discovers new case study files automatically - no manual population functions or classifier patterns are needed.

### Evidence Tier System

All 195 documents in the registry are classified by evidence quality, which propagates into the graph as the `source_tier` property on Document nodes:

| Tier | Classification | Usage in Financial Context |
|------|----------------|---------------------------|
| T1 | Peer-reviewed journal articles | Cite without qualification in investor materials |
| T2 | Institutional reports (World Bank, UNEP, TNFD) | Cite with institutional context |
| T3 | Data repositories (FishBase, WoRMS, OBIS) | Cite with methodology notes |
| T4 | Preprints and grey literature | Cite with explicit caveats |

---

## Development Setup

### Prerequisites

- Python 3.11+
- Neo4j Community 5.x ([Desktop](https://neo4j.com/download/) or Docker)
- An LLM API key (DeepSeek, Claude, or OpenAI)

### Environment Configuration

```bash
# Copy the template - .env is excluded from git via .gitignore
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Required: Neo4j connection
MARIS_NEO4J_URI=bolt://localhost:7687
MARIS_NEO4J_USER=neo4j
MARIS_NEO4J_PASSWORD=<your-neo4j-password>

# Required: LLM API key (DeepSeek is the default provider)
MARIS_LLM_API_KEY=<your-api-key>
```

> **Security:** The `.env` file contains secrets (database passwords, API keys) and must never be committed to version control. It is excluded via `.gitignore`. Use `.env.example` as the template for new environments. See `.env.example` for all available settings including alternative LLM providers.

### Install Dependencies

```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

### Populate the Knowledge Graph

```bash
# v4 populator (recommended) - dynamic site discovery, 9 sites
python scripts/populate_neo4j_v4.py

# Legacy populator - Cabo Pulmo + Shark Bay only
python scripts/populate_neo4j.py
```

The v4 populator executes the 11-stage pipeline described above, dynamically discovering and loading all case study JSON files from `examples/`. The script is idempotent (uses MERGE operations) and safe to re-run.

### Verify the Graph

```bash
python scripts/validate_graph.py
```

Checks node counts by label (953+ nodes expected), relationship integrity (244+ edges expected), and that all 40 bridge axioms have at least one EVIDENCED_BY edge to a Document node.

---

## Running the Stack

### One-Command Launcher (Recommended)

```bash
# v4 Global Portfolio (9 sites, 6 tabs) - recommended
./launch.sh v4

# v3 Intelligence Platform (2 sites, 5 tabs)
./launch.sh v3

# v2 Single-scroll dashboard
./launch.sh v2

# v1 Static dashboard (no API needed)
./launch.sh v1

# API server only
./launch.sh api

# Stop all running services
./launch.sh stop
```

The launcher handles environment loading, Neo4j connectivity checks, API startup, and dashboard process management. PID files are stored in `.pids/` for clean shutdown.

### Manual (3 terminals)

```bash
# Terminal 1: Start Neo4j (if using Docker)
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/maris-dev neo4j:5-community

# Terminal 2: Start the API server
uvicorn maris.api.main:app --host 0.0.0.0 --port 8000

# Terminal 3: Start the investor dashboard
cd investor_demo

# v4 Global Portfolio (recommended) - 9 sites, 6 tabs
streamlit run streamlit_app_v4.py --server.port 8504

# v3 Intelligence Platform (alternative) - 2 sites, 5 tabs
streamlit run streamlit_app_v3.py --server.port 8503

# v2 dashboard (alternative) - single-scroll with Ask Nereus chat
streamlit run streamlit_app_v2.py
```

The v4 dashboard opens at `http://localhost:8504` with 6 tabs: Portfolio Overview, Intelligence Brief, Ask Nereus (GraphRAG), Scenario Lab, Site Intelligence, and TNFD Compliance. Each tab has dual-mode operation (Live/Demo) toggled from the sidebar. The v3 dashboard opens at `http://localhost:8503`. The v2 dashboard opens at `http://localhost:8501`.

### Docker Compose

```bash
docker compose up --build
```

Starts Neo4j, the API server, and the Streamlit dashboard together.

### Health Check

```bash
# API health (returns Neo4j status, LLM availability, graph stats)
curl http://localhost:8000/api/health

# Full pre-demo stack check
python scripts/demo_healthcheck.py
```

---

## Key Patterns

### Configuration

All settings are loaded from environment variables with `MARIS_` prefix. `get_config()` returns a singleton:

```python
from maris.config import get_config
config = get_config()
print(config.neo4j_uri)  # bolt://localhost:7687
```

### Lazy Singletons in API Routes

Route modules use lazy initialization so that importing the module does not open database connections or LLM clients:

```python
_llm: LLMAdapter | None = None

def _init_components():
    global _llm
    if _llm is None:
        _llm = LLMAdapter(get_config())
```

### Query Classification (Two-Tier)

1. **Keyword rules** - Fast regex matching against 5 category patterns. Extracts site name via canonical mapping (e.g. "Cabo Pulmo" -> "Cabo Pulmo National Park") and metric keywords.
2. **LLM fallback** - For ambiguous queries, the LLM classifies into a category with a confidence score. Falls back to `site_valuation` at confidence 0.3 if LLM is unavailable.

### Parameterized Cypher Templates

All graph queries use parameterized Cypher templates (never string interpolation). Eight templates are defined in `maris/query/cypher_templates.py` - five core templates mapped to classifier categories plus three utility templates (node_detail, graph_traverse, graph_stats). All templates include `LIMIT $result_limit` (configurable, max 1000). The executor substitutes validated parameters via the Neo4j driver's parameter binding.

### LLM Adapter

The `LLMAdapter` wraps an OpenAI-compatible HTTP client. DeepSeek, Claude, and OpenAI are supported by changing `MARIS_LLM_PROVIDER` in `.env`. The adapter exposes `complete()` for text responses and `complete_json()` for structured JSON output.

### Authentication and Authorization

API security is implemented in `maris/api/auth.py`:

- **Bearer token flow:** The `require_api_key` FastAPI dependency validates requests against `MARIS_API_KEY`. When `MARIS_DEMO_MODE=true`, authentication is bypassed so investor demos can run without token configuration.
- **Input validation:** Three validators are exposed as reusable functions:
  - `validate_question()` - enforces a 500-character maximum for query text
  - `validate_site_name()` - allows alphanumeric characters, spaces, hyphens, apostrophes, and periods only
  - `validate_axiom_id()` - requires the `BA-NNN` format (e.g. BA-001)
- **Rate limiting:** In-memory sliding window per API key. `/api/query` is limited to 30 requests/minute; all other endpoints allow 60 requests/minute. Returns 429 when exceeded.
- **Request tracing:** Every response includes an `X-Request-ID` header for end-to-end tracing. Client IP addresses are hashed (SHA-256) before logging to preserve privacy while enabling abuse detection.

### LLM Response Validation

The `maris/query/validators.py` module implements a 5-step validation pipeline that runs on every LLM-generated response before it reaches the user:

1. **Schema validation** - Verifies required fields (answer, confidence, evidence, caveats) are present and correctly typed
2. **Confidence bounds enforcement** - Clamps the confidence score to the [0, 1] range
3. **Evidence DOI format checks** - Validates that DOI strings match the expected `10.NNNN/...` pattern
4. **Numerical claim verification** - Extracts numerical claims from the answer text and cross-checks them against the graph context that was provided to the LLM. Unverified claims trigger caveat injection.
5. **Caveat injection** - Appends caveats for any claims that could not be verified against graph data

**Robust JSON extraction:** LLM responses sometimes arrive malformed. The validator uses a 5-tier fallback strategy: (1) code-fence extraction, (2) direct JSON parse, (3) brace extraction, (4) truncated-JSON repair, (5) structured error response.

**EvidenceItem null coercion:** The `EvidenceItem` Pydantic model (`maris/api/models.py`) includes a `field_validator` that coerces `None` values to empty strings for `title`, `tier`, and `quote` fields. This prevents validation errors when the LLM returns null for optional evidence metadata.

**Empty result protection:** Before calling the LLM, `is_graph_context_empty()` checks whether the Cypher query returned meaningful data. If the graph context is empty, the system returns a structured "no data available" response without incurring an LLM call.

### Confidence Model

The confidence model in `maris/axioms/confidence.py` computes a composite score from four independently auditable factors:

```
composite = tier_base * path_discount * staleness_discount * sample_factor
```

| Factor | Description | Range |
|--------|-------------|-------|
| `tier_base` | Evidence quality: T1=0.95, T2=0.80, T3=0.65, T4=0.50. Multiple sources are combined as the **mean** of their tier confidences, so more high-quality evidence increases the score. Nodes without an explicit tier default to T2 (0.80) since their presence in the curated graph implies institutional-level vetting. | 0.50 - 0.95 |
| `path_discount` | Graph distance penalty: -5% per hop from source to claim, with a floor of 0.1. | 0.10 - 1.00 |
| `staleness_discount` | Data age penalty based on the **median** data year (not the oldest), so a single old foundational paper does not tank the score when most evidence is recent. No penalty for data <=5 years old, -2% per year beyond that, floor of 0.3. If no year information is available, defaults to 0.85. | 0.30 - 1.00 |
| `sample_factor` | Source diversity: **linear ramp** from 0.6 (single source) to 1.0 (4+ sources). A single peer-reviewed source still carries meaningful weight (0.6); additional sources provide incremental corroboration up to saturation at 4 independent sources. | 0.60 - 1.00 |

The model is inspired by the GRADE framework (evidence certainty grading), the IPCC likelihood scale, and knowledge-graph confidence propagation techniques. It produces sensible gradients: well-characterized sites with mostly T1 evidence score 80-88%, mechanism explanations ~74%, and multi-hop risk assessments ~57%.

The function returns a breakdown dict containing the composite score, each individual factor, and a human-readable explanation string suitable for display in the dashboard.

### Data Freshness Tracking

MPA nodes in the knowledge graph carry freshness metadata to flag aging data:

| Property | Type | Description |
|----------|------|-------------|
| `biomass_measurement_year` | int | Year of the most recent biomass measurement |
| `data_freshness_status` | string | Computed status: "current" (<=5 years old), "aging" (<=10 years), or "stale" (>10 years) |
| `last_validated_date` | string | ISO date when the data was last verified against source publications |

Freshness status is computed during the population pipeline in `maris/graph/population.py`. Graph validation (`scripts/validate_graph.py`) warns on missing `biomass_measurement_year` and flags stale data. The staleness status feeds directly into the confidence model via the `staleness_discount` factor described above.

### Sensitivity Analysis

The `maris/axioms/sensitivity.py` module implements one-at-a-time (OAT) sensitivity analysis for ESV Monte Carlo simulations. OAT is justified here because the ESV model is additive (total ESV = sum of independent service values), so interaction effects between parameters are negligible.

**Methodology:**

- Each ecosystem service value is perturbed by configurable percentages (default: 10% and 20%) in both positive and negative directions
- For 12 parameters with 2 perturbation levels and 2 directions, this produces 49 model runs (48 perturbations + 1 baseline)
- Impact on total ESV is recorded for each perturbation

**Output:**

| Field | Description |
|-------|-------------|
| `tornado_plot_data` | Service parameters sorted by impact magnitude, suitable for direct visualization |
| `dominant_parameter` | The single parameter with the largest influence on total ESV |
| `methodology_justification` | Text explaining why OAT is appropriate for this model structure |

The output is designed to be directly interpretable by investors and underwriters without requiring statistical expertise.

### Bridge Axiom Uncertainty Quantification

Bridge axiom templates (v2.1) now include uncertainty quantification fields alongside the existing coefficient data:

| Field | Type | Description |
|-------|------|-------------|
| `ci_low` | float | Lower bound of the confidence interval for the primary coefficient |
| `ci_high` | float | Upper bound of the confidence interval |
| `distribution` | string | Statistical distribution assumption: "triangular" or "lognormal" |
| `study_sample_size` | int | Number of observations in the source study |
| `effect_size_type` | string | Type of effect size reported (e.g. "cohens_d", "ratio", "percentage") |

These fields feed into the Monte Carlo simulation and sensitivity analysis to produce defensible uncertainty bounds for investor-facing outputs.

---

## Adding New Features

### Adding a New Site

In v4, adding a new MPA site requires only two steps:

1. Create a case study JSON at `examples/<site_name>_case_study.json` following the structure of any existing case study (e.g. `examples/cabo_pulmo_case_study.json`) with site metadata, NEOLI assessment, ecological recovery metrics, ecosystem service valuations (with DOI sources and valuation methods), and key species
2. Run `python scripts/populate_neo4j_v4.py` to load the new site

The v4 populator discovers case study files automatically via `maris/config_v4.py` dynamic site discovery. No manual population functions, classifier patterns, or config changes are needed - the generic pipeline handles all site types.

### Adding a New Cypher Template

1. Add the template to `maris/query/cypher_templates.py`:
   ```python
   "my_template": {
       "cypher": "MATCH (n:MyNode {name: $name}) RETURN n",
       "description": "Look up a custom node",
   }
   ```
2. Add keyword rules in `maris/query/classifier.py` if it maps to a new category
3. Handle parameter extraction for the new category in `maris/api/routes/query.py`

### Adding a New API Endpoint

1. Define Pydantic request/response models in `maris/api/models.py`
2. Create a route function under `maris/api/routes/`
3. Register the router in `maris/api/main.py` if it is a new file

### Adding a New Bridge Axiom

1. Add the axiom definition to `schemas/bridge_axiom_templates.json` with coefficients, applicable habitats, DOI-backed sources, and uncertainty fields (see below)
2. Add the evidence mapping to `data/semantica_export/bridge_axioms.json`
3. Run `python scripts/populate_neo4j_v4.py` to create the BridgeAxiom node and evidence edges

---

## Testing

### Test Suite

The project includes **1141 tests** (790+ unit + 230+ integration + 13 scenario invariants) across 27 test files. Tests cover the full stack: query classification (with hardened regex patterns), Cypher template generation, LLM response validation, confidence model (aligned with visible evidence payload), sensitivity analysis, API endpoints, graph population, W3C PROV-O provenance, DOI verification, deterministic provenance guards, multi-site scaling (with OBIS area resolution and WoRMS 204 handling), cross-domain reasoning (with rule compilation), TNFD disclosure, axiom discovery (with LLM-enhanced pattern detection), Semantica SDK bridge adapters, and LLM discovery integration against live DeepSeek.

**Setup and execution:**

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=maris
```

**Test directory layout:**

```
tests/
  conftest.py                       # Shared fixtures: sample_graph_result, sample_llm_response,
                                    #   sample_services, mock_neo4j, mock_config
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
  test_provenance.py                # P0: Provenance engine tests (40 tests)
  test_site_scaling.py              # P1: Multi-site scaling pipeline tests (45 tests)
  test_reasoning.py                 # P2: Cross-domain reasoning engine tests (35 tests)
  test_disclosure.py                # P3: TNFD LEAP disclosure tests (30 tests)
  test_axiom_discovery.py           # P4: Axiom discovery pipeline tests (70+ tests)
  test_semantica_bridge.py          # Semantica SDK bridge adapter tests (51 tests)
  test_confidence.py                # Confidence model invariant tests (v5)
  test_doi_verifier.py              # DOI verifier unit tests (v5)
  test_bridge_axiom_provenance.py   # Axiom provenance integrity tests (v5)
  test_graphrag_chat_v4.py          # GraphRAG chat regression tests (v5)
  test_site_intelligence_provenance.py  # Site intelligence provenance tests (v5)
  integration/                      # Integration test suite (230+ tests)
    test_phase0_bridge.py           # SDK availability, SQLite persistence, dual-write
    test_phase1_graph.py            # Graph integrity, idempotent re-population
    test_phase2_apis.py             # OBIS, WoRMS, Marine Regions real API calls
    test_phase3_query.py            # 5-category regression, classifier accuracy
    test_phase4_disclosure.py       # TNFD disclosure, axiom discovery
    test_phase5_stress.py           # SQLite persistence, concurrent queries
    test_phase6_llm_discovery.py    # LLM-enhanced discovery integration (7 tests against live DeepSeek)
```

**Key fixtures** (defined in `conftest.py`):

| Fixture | Purpose |
|---------|---------|
| `sample_graph_result` | Mock Neo4j query result for testing downstream pipeline |
| `sample_llm_response` | Well-formed LLM JSON response for validation tests |
| `sample_services` | Ecosystem service list for Monte Carlo and sensitivity tests |
| `mock_neo4j` | Patched Neo4j driver that returns predictable results |
| `mock_config` | Config object with test-safe defaults (no real connections) |

### CI Pipeline

The project uses GitHub Actions (`.github/workflows/ci.yml`) for continuous integration on every push and pull request to `main`:

1. **Lint** - Runs `ruff` for code style and import order checks
2. **Test** - Runs the full pytest suite (1141 tests: 790+ unit + 230+ integration + 13 scenario invariants)

Dev dependencies are specified in `requirements-dev.txt`: pytest>=8.0, pytest-asyncio>=0.23, httpx>=0.26, ruff>=0.8, pytest-cov>=4.0.

### Manual Verification

**API health check:**

```bash
curl http://localhost:8000/api/health
```

**Query end-to-end:**

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MARIS_API_KEY" \
  -d '{"question": "What is Cabo Pulmo worth?", "include_graph_path": true}'
```

Expected: JSON response with `answer`, `confidence` >= 0.5, `evidence` array with DOIs, `axioms_used`, and `graph_path` edges. Requires a valid Bearer token (or `MARIS_DEMO_MODE=true`).

**Graph validation:**

```bash
python scripts/validate_graph.py
```

Checks: node counts per label (953+ nodes, 244+ edges across 11 MPA nodes), all 40 BridgeAxiom nodes have EVIDENCED_BY edges, all MPA nodes have GENERATES edges to EcosystemService nodes.

---

## Code Style and Terminology

- Python 3.11+ with type hints throughout
- Pydantic v2 for all API models
- PEP 8 conventions
- "NEOLI alignment" not "NEOLI compliance" (the system does not claim NEOLI certification)
- "market-price" not "NOAA-adjusted" for Cabo Pulmo tourism valuation
- "anticipates alignment with" not "anticipates compliance with" for framework references
- No em dashes in prose (use hyphens or " - " instead)
