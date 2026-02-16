# Nereus Developer Guide

## System Purpose

Nereus is a provenance-first blue finance platform, powered by MARIS (Marine Asset Risk Intelligence System) + Semantica. It creates auditable, DOI-backed pathways from peer-reviewed ecological science to investment-grade financial metrics for blue natural capital. The system is designed for institutional investors, blue bond underwriters, TNFD working groups, and conservation finance professionals who require full scientific traceability behind every number.

The v2 live system exposes the curated knowledge foundation through a Neo4j graph database, a FastAPI query engine with natural-language classification, and an investor-facing Streamlit dashboard with interactive provenance visualization.

## Architecture Overview

```
User Question (natural language)
     |
     v
 QueryClassifier  -- keyword-first with LLM fallback
     |              (5 categories: valuation, provenance, axiom, comparison, risk)
     v
 CypherTemplates  -- 8 templates (5 core + 3 utility), never raw string interpolation
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
    population.py             # 8-stage population pipeline from curated JSON assets
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
    confidence.py             # Multiplicative confidence interval propagation
    monte_carlo.py            # Monte Carlo ESV simulation (10,000 runs)
    sensitivity.py            # OAT sensitivity analysis for ESV simulations, tornado plot data generation
  ingestion/                  # Document ingestion pipeline
    pdf_extractor.py          # PDF text extraction
    llm_extractor.py          # LLM-based entity/relationship extraction
    embedding_generator.py    # Vector embeddings for semantic search
    graph_merger.py           # Merge extracted triples into Neo4j
  provenance/                 # P0: W3C PROV-O provenance tracking
    manager.py                # MARISProvenanceManager (entity/activity/agent tracking)
    bridge_axiom_registry.py  # 16 axioms as typed BridgeAxiom objects with TranslationChain
    bridge_axiom.py           # BridgeAxiom dataclass
    certificate.py            # Provenance certificate generation (JSON/Markdown)
    core.py                   # PROV-O core dataclasses (ProvenanceEntity, ProvenanceActivity, ProvenanceAgent)
    integrity.py              # SHA-256 checksum verification
    storage.py                # InMemoryStorage and SQLiteStorage backends
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

investor_demo/
  streamlit_app_v3.py          # v3 Intelligence Platform (multi-tab, recommended)
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
| `scripts/populate_neo4j.py` | Orchestrates the 8-stage graph population pipeline |
| `scripts/validate_graph.py` | Verifies node counts, relationship integrity, axiom evidence chains |
| `scripts/demo_healthcheck.py` | Pre-demo verification: Neo4j + API + dashboard connectivity |
| `scripts/run_ingestion.py` | Full PDF-to-graph ingestion pipeline |

---

## Knowledge Graph Data Lineage

The graph is populated from **seven curated data sources**, each serving a distinct role in the provenance chain. All population operations use `MERGE` (idempotent) so the pipeline is safe to re-run.

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
│  3. Cabo Pulmo Case Study       examples/cabo_pulmo_case_study.json         │
│     Reference calibration site  -> MPA enrichment (NEOLI, biomass, ESV),     │
│     (coral reef, tourism)         EcosystemService values, Species nodes,   │
│                                    TrophicLevel food web, GENERATES edges    │
│                                                                              │
│  3b. Shark Bay Case Study       examples/shark_bay_case_study.json          │
│      Second calibration site    -> MPA enrichment (NEOLI, seagrass, ESV),    │
│      (seagrass, carbon)           EcosystemService values, GENERATES edges  │
│                                                                              │
│  4. Bridge Axiom Templates      schemas/bridge_axiom_templates.json         │
│     + Evidence Mapping          data/semantica_export/bridge_axioms.json     │
│     16 axioms with coefficients -> BridgeAxiom nodes, EVIDENCED_BY edges,    │
│     and DOI-backed evidence       APPLIES_TO edges, TRANSLATES edges         │
│                                                                              │
│  5. Curated Relationships       data/semantica_export/relationships.json    │
│     15 cross-domain edges       -> Typed relationship edges with             │
│     with quantification           quantification, mechanism, confidence      │
│                                                                              │
│  6. Comparison Sites            Hardcoded in population.py                   │
│     Great Barrier Reef,         -> MPA nodes with basic metadata only        │
│     Papahanaumokuakea             (NEOLI, area, rating - no service values)  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Population Pipeline (8 stages)

The `scripts/populate_neo4j.py` script calls `maris.graph.population.populate_graph()`, which executes eight stages in order:

| Stage | Function | Source File | Creates |
|-------|----------|-------------|---------|
| 1 | `_populate_documents()` | `document_index.json` | 195 Document nodes with DOI, tier, domain |
| 2 | `_populate_entities()` | `entities.jsonld` | Species, MPA, Habitat, EcosystemService, etc. |
| 3 | `_populate_cabo_pulmo()` | `cabo_pulmo_case_study.json` | Enriches MPA with NEOLI/biomass/ESV; creates services, species, trophic nodes |
| 3b | `_populate_shark_bay()` | `shark_bay_case_study.json` | Enriches MPA with NEOLI/seagrass/ESV; creates carbon, fisheries, tourism, coastal services |
| 4 | `_populate_bridge_axioms()` | `bridge_axiom_templates.json` + `bridge_axioms.json` | 16 BridgeAxiom nodes (12 core + 4 blue carbon); EVIDENCED_BY, APPLIES_TO, TRANSLATES edges |
| 5 | `_populate_comparison_sites()` | Hardcoded | Great Barrier Reef, Papahanaumokuakea MPA nodes |
| 6 | `_populate_relationships()` | `relationships.json` | 15 cross-domain relationship edges |
| 7 | `_populate_cross_domain_links()` | Hardcoded | Structural edges (HAS_HABITAT, PROVIDES, INHABITS, GOVERNS, etc.) |
| 8 | `_populate_provenance()` | `cabo_pulmo_case_study.json` | DERIVED_FROM edges linking MPA to source Documents |

### Calibration Site Model

The system has two fully characterized reference sites with contrasting ESV profiles:

**Cabo Pulmo National Park** (Mexico) - coral reef-dominated, tourism-driven ESV:

| Property | Value | Source |
|----------|-------|--------|
| Total ESV | $29.27M/year (market-price) | `cabo_pulmo_case_study.json` |
| Tourism | $25.0M (market-price expenditure) | Marcos-Castillo et al. 2024 |
| Biomass ratio | 4.63x recovery, CI [3.8, 5.5] | Aburto-Oropeza et al. 2011 |
| NEOLI score | 4/5 criteria met | Edgar et al. 2014 framework |
| Asset rating | AAA (composite 0.90) | Derived from NEOLI + ESV + CI |

**Shark Bay World Heritage Area** (Australia) - seagrass-dominated, carbon-driven ESV:

| Property | Value | Source |
|----------|-------|--------|
| Total ESV | $21.5M/year (market-price) | `shark_bay_case_study.json` |
| Carbon sequestration | $12.1M (0.84 tCO2/ha/yr, $30/tonne) | Arias-Ortiz et al. 2018 |
| Fisheries | $5.2M (MSC-certified prawn fishery) | Market-price method |
| Tourism | $3.4M (108K visitors/year) | Tourism WA data |
| Coastal protection | $0.8M (40% wave reduction) | Avoided cost method |
| Seagrass extent | 4,800 km2 (world's largest) | Direct survey |
| NEOLI score | 4/5 criteria met | Edgar et al. 2014 framework |

**Comparison sites** (Great Barrier Reef Marine Park, Papahanaumokuakea Marine National Monument) are populated with governance metadata only (area, designation year, NEOLI score, asset rating). They do not have ecosystem service valuations or bridge axiom links. The dual-site architecture demonstrates the framework's habitat-agnostic design: tourism-dominant (Cabo Pulmo) vs. carbon-dominant (Shark Bay).

To add full coverage for another site, create a case study JSON following the structure of `examples/cabo_pulmo_case_study.json` or `examples/shark_bay_case_study.json` and add a population function in `maris/graph/population.py`.

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
uv pip install -r requirements-v2.txt

# Or using pip
pip install -r requirements-v2.txt
```

### Populate the Knowledge Graph

```bash
python scripts/populate_neo4j.py
```

This executes the 8-stage pipeline described above, loading all curated data sources into Neo4j. The script is idempotent (uses MERGE operations) and safe to re-run.

### Verify the Graph

```bash
python scripts/validate_graph.py
```

Checks node counts by label, relationship integrity, and that all 16 bridge axioms have at least one EVIDENCED_BY edge to a Document node.

---

## Running the Stack

### Manual (3 terminals)

```bash
# Terminal 1: Start Neo4j (if using Docker)
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/maris-dev neo4j:5-community

# Terminal 2: Start the API server
uvicorn maris.api.main:app --host 0.0.0.0 --port 8000

# Terminal 3: Start the investor dashboard
cd investor_demo

# v3 Intelligence Platform (recommended) - multi-tab with pipeline transparency
streamlit run streamlit_app_v3.py --server.port 8503

# v2 dashboard (alternative) - single-scroll with Ask MARIS chat
streamlit run streamlit_app_v2.py
```

The v3 dashboard opens at `http://localhost:8503` with 5 tabs: Intelligence Brief, Ask MARIS (GraphRAG), Scenario Lab, Site Scout, and TNFD Compliance. Each tab has dual-mode operation (Live/Demo) toggled from the sidebar. The v2 dashboard opens at `http://localhost:8501`.

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

Bridge axiom templates (v1.3) now include uncertainty quantification fields alongside the existing coefficient data:

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

1. Create a case study JSON following the structure of `examples/cabo_pulmo_case_study.json` or `examples/shark_bay_case_study.json` with site metadata, NEOLI assessment, ecological recovery metrics, ecosystem service valuations (with DOI sources and valuation methods), and key species
2. Add a population function in `maris/graph/population.py` (pattern: `_populate_cabo_pulmo()` or `_populate_shark_bay()`)
3. Add the site's canonical name to the classifier's `_SITE_PATTERNS` in `maris/query/classifier.py`
4. Run `python scripts/populate_neo4j.py` to load the new site

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
3. Run `python scripts/populate_neo4j.py` to create the BridgeAxiom node and evidence edges

---

## Testing

### Test Suite

The project includes **910 tests** (706 unit + 204 integration) across 23 test files. Tests cover the full stack: query classification (with hardened regex patterns), Cypher template generation, LLM response validation, confidence model, sensitivity analysis, API endpoints, graph population, W3C PROV-O provenance, multi-site scaling (with OBIS area resolution and WoRMS 204 handling), cross-domain reasoning (with rule compilation), TNFD disclosure, axiom discovery (with LLM-enhanced pattern detection), Semantica SDK bridge adapters, and LLM discovery integration against live DeepSeek.

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
  integration/                      # Integration test suite (204 tests)
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
2. **Test** - Runs the full pytest suite (910 tests: 706 unit + 204 integration)

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

Checks: node counts per label, all BridgeAxiom nodes have EVIDENCED_BY edges, all MPA nodes have GENERATES edges to EcosystemService nodes.

---

## Code Style and Terminology

- Python 3.11+ with type hints throughout
- Pydantic v2 for all API models
- PEP 8 conventions
- "NEOLI alignment" not "NEOLI compliance" (the system does not claim NEOLI certification)
- "market-price" not "NOAA-adjusted" for Cabo Pulmo tourism valuation
- "anticipates alignment with" not "anticipates compliance with" for framework references
- No em dashes in prose (use hyphens or " - " instead)
