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
 CypherTemplates  -- 6 parameterized templates, never raw string interpolation
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
    cypher_templates.py       # 6 parameterized Cypher templates by category
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

All graph queries use parameterized Cypher templates (never string interpolation). Six templates are defined in `maris/query/cypher_templates.py`, each mapped to a classifier category. The executor substitutes validated parameters via the Neo4j driver's parameter binding.

### LLM Adapter

The `LLMAdapter` wraps an OpenAI-compatible HTTP client. DeepSeek, Claude, and OpenAI are supported by changing `MARIS_LLM_PROVIDER` in `.env`. The adapter exposes `complete()` for text responses and `complete_json()` for structured JSON output.

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

1. Add the axiom definition to `schemas/bridge_axiom_templates.json` with coefficients, applicable habitats, and DOI-backed sources
2. Add the evidence mapping to `data/semantica_export/bridge_axioms.json`
3. Run `python scripts/populate_neo4j.py` to create the BridgeAxiom node and evidence edges

---

## Testing

### API Health Check

```bash
curl http://localhost:8000/api/health
```

### Query End-to-End

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Cabo Pulmo worth?", "include_graph_path": true}'
```

Expected: JSON response with `answer`, `confidence` >= 0.5, `evidence` array with DOIs, `axioms_used`, and `graph_path` edges.

### Graph Validation

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
