# MARIS Developer Guide

## System Purpose

MARIS (Marine Asset Risk Intelligence System) is a provenance-first knowledge graph that creates auditable, DOI-backed pathways from peer-reviewed ecological science to investment-grade financial metrics for blue natural capital. The system is designed for institutional investors, blue bond underwriters, TNFD working groups, and conservation finance professionals who require full scientific traceability behind every number.

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
  graph/                      # Neo4j integration layer
    connection.py             # Bolt driver singleton, run_query() helper
    schema.py                 # Uniqueness constraints and indexes
    population.py             # 8-stage population pipeline from curated JSON assets
    validation.py             # Post-population integrity checks
  query/                      # NL-to-Cypher pipeline
    classifier.py             # Two-tier classification: keyword regex + LLM fallback
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
  config.py                   # Centralized configuration from .env
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

The graph is populated from **six curated data sources**, each serving a distinct role in the provenance chain. All population operations use `MERGE` (idempotent) so the pipeline is safe to re-run.

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
│                                    EcosystemService values, Species nodes,   │
│                                    TrophicLevel food web, GENERATES edges    │
│                                                                              │
│  4. Bridge Axiom Templates      schemas/bridge_axiom_templates.json         │
│     + Evidence Mapping          data/semantica_export/bridge_axioms.json     │
│     12 axioms with coefficients -> BridgeAxiom nodes, EVIDENCED_BY edges,    │
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
| 4 | `_populate_bridge_axioms()` | `bridge_axiom_templates.json` + `bridge_axioms.json` | 12 BridgeAxiom nodes; EVIDENCED_BY, APPLIES_TO, TRANSLATES edges |
| 5 | `_populate_comparison_sites()` | Hardcoded | Great Barrier Reef, Papahanaumokuakea MPA nodes |
| 6 | `_populate_relationships()` | `relationships.json` | 15 cross-domain relationship edges |
| 7 | `_populate_cross_domain_links()` | Hardcoded | Structural edges (HAS_HABITAT, PROVIDES, INHABITS, GOVERNS, etc.) |
| 8 | `_populate_provenance()` | `cabo_pulmo_case_study.json` | DERIVED_FROM edges linking MPA to source Documents |

### Calibration Site Model

**Cabo Pulmo National Park** is the fully characterized reference site (AAA-rated) with complete financial data:

| Property | Value | Source |
|----------|-------|--------|
| Total ESV | $29.27M/year (market-price) | `cabo_pulmo_case_study.json` |
| Tourism | $25.0M (market-price expenditure) | Marcos-Castillo et al. 2024 |
| Biomass ratio | 4.63x recovery, CI [3.8, 5.5] | Aburto-Oropeza et al. 2011 |
| NEOLI score | 4/5 criteria met | Edgar et al. 2014 framework |
| Asset rating | AAA (composite 0.90) | Derived from NEOLI + ESV + CI |

**Comparison sites** (Great Barrier Reef Marine Park, Papahanaumokuakea Marine National Monument) are populated with governance metadata only (area, designation year, NEOLI score, asset rating). They do not have ecosystem service valuations, species data, or bridge axiom links in the current graph. This is by design: the POC demonstrates the full provenance chain for one deeply characterized site, with comparison sites providing NEOLI benchmarking context.

To add full coverage for another site, create a case study JSON following the structure of `examples/cabo_pulmo_case_study.json` and add a population function in `maris/graph/population.py`.

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

Checks node counts by label, relationship integrity, and that all 12 bridge axioms have at least one EVIDENCED_BY edge to a Document node.

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
streamlit run streamlit_app_v2.py
```

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

**Empty result protection:** Before calling the LLM, `is_graph_context_empty()` checks whether the Cypher query returned meaningful data. If the graph context is empty, the system returns a structured "no data available" response without incurring an LLM call.

### Confidence Model

The confidence model in `maris/axioms/confidence.py` computes a composite score from four independently auditable factors:

```
composite = tier_base * path_discount * staleness_discount * sample_factor
```

| Factor | Description | Range |
|--------|-------------|-------|
| `tier_base` | Evidence quality: T1=0.95, T2=0.80, T3=0.65, T4=0.50. Multiple independent DOIs are combined multiplicatively; corroborating sources use max. | 0.50 - 0.95 |
| `path_discount` | Graph distance penalty: -5% per hop from source to claim, with a floor of 0.1. | 0.10 - 1.00 |
| `staleness_discount` | Data age penalty: no penalty for data <=5 years old, -2% per year beyond that, floor of 0.3. If no year information is available, defaults to 0.85. | 0.30 - 1.00 |
| `sample_factor` | Source diversity: `1 - 1/sqrt(n)` where n is the number of independent sources. A single source yields 0.5. | 0.50 - 1.00 |

This replaces the earlier simple `min()` aggregation with a transparent, decomposable formula. The model is inspired by the GRADE framework (evidence certainty grading), the IPCC likelihood scale, and knowledge-graph confidence propagation techniques.

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

Bridge axiom templates (v1.2) now include uncertainty quantification fields alongside the existing coefficient data:

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

1. Create a case study JSON following the structure of `examples/cabo_pulmo_case_study.json` with site metadata, NEOLI assessment, ecological recovery metrics, ecosystem service valuations (with DOI sources and valuation methods), and key species
2. Add a population function in `maris/graph/population.py` (pattern: `_populate_cabo_pulmo()`)
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

The project includes 220 tests across 14 test files in the `tests/` directory. Tests cover the full stack: query classification, Cypher template generation, LLM response validation, confidence model, sensitivity analysis, API endpoints, and graph population.

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
  conftest.py           # Shared fixtures: sample_graph_result, sample_llm_response,
                        #   sample_services, mock_neo4j, mock_config
  test_classifier.py    # Query classification (keyword + LLM fallback)
  test_cypher.py        # Cypher template generation and parameterization
  test_executor.py      # Query execution against mock Neo4j
  test_generator.py     # LLM response synthesis
  test_formatter.py     # Response formatting and structure
  test_validators.py    # LLM response validation pipeline
  test_confidence.py    # Composite confidence model
  test_sensitivity.py   # OAT sensitivity analysis
  test_monte_carlo.py   # Monte Carlo ESV simulation
  test_auth.py          # Authentication, rate limiting, input validation
  test_api.py           # FastAPI endpoint integration tests
  test_population.py    # Graph population pipeline
  test_config.py        # Configuration loading
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
2. **Test** - Runs the full pytest suite (220 tests)

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
  -d '{"question": "What is Cabo Pulmo worth?", "include_graph_path": true}'
```

Expected: JSON response with `answer`, `confidence` >= 0.5, `evidence` array with DOIs, `axioms_used`, and `graph_path` edges.

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
