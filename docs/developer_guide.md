# MARIS Developer Guide

## Architecture Overview

MARIS v2 is a live query system built on Neo4j, FastAPI, and Streamlit. The architecture follows a layered pipeline: natural-language questions are classified, mapped to Cypher templates, executed against the knowledge graph, and grounded via LLM into provenance-backed answers.

```
User Question
     |
     v
 QueryClassifier  (keyword rules + LLM fallback)
     |
     v
 CypherTemplates  (6 parameterized templates)
     |
     v
 QueryExecutor    (Neo4j bolt driver)
     |
     v
 ResponseGenerator (LLM grounds graph results into narrative)
     |
     v
 ResponseFormatter (extracts confidence, evidence, caveats)
     |
     v
 FastAPI Response  (JSON with provenance chain)
```

### Module Structure

```
maris/
  api/                  # FastAPI server
    main.py             # App factory, CORS, route registration
    models.py           # Pydantic request/response schemas
    routes/
      health.py         # GET /api/health (Neo4j + LLM status)
      query.py          # POST /api/query (NL-to-answer pipeline)
      graph.py          # Graph traversal and node detail endpoints
  graph/                # Neo4j integration
    connection.py       # Bolt driver, run_query() helper
    schema.py           # Node/relationship type definitions
    population.py       # Graph population from export bundle
    validation.py       # Post-population integrity checks
  query/                # NL-to-Cypher pipeline
    classifier.py       # Keyword + LLM query classification
    cypher_templates.py # 6 parameterized Cypher templates
    executor.py         # Template execution + provenance edges
    generator.py        # LLM response generation from graph context
    formatter.py        # Structured output (confidence, evidence, caveats)
  llm/                  # LLM abstraction
    adapter.py          # OpenAI-compatible client (DeepSeek, Claude, GPT)
    prompts.py          # System prompts for classification and generation
  axioms/               # Bridge axiom logic
    engine.py           # Axiom application and chaining
    confidence.py       # Confidence interval propagation
    monte_carlo.py      # Monte Carlo ESV simulation
  ingestion/            # Document ingestion pipeline
    pdf_extractor.py    # PDF text extraction
    llm_extractor.py    # LLM-based entity/relationship extraction
    embedding_generator.py  # Vector embeddings
    graph_merger.py     # Merge extracted data into Neo4j
  config.py             # Centralized configuration from .env
```

### Key Scripts

| Script | Purpose |
|--------|---------|
| `scripts/populate_neo4j.py` | Load export bundle into Neo4j |
| `scripts/validate_graph.py` | Verify graph integrity post-population |
| `scripts/demo_healthcheck.py` | End-to-end health check (Neo4j + API + dashboard) |
| `scripts/run_ingestion.py` | Full ingestion pipeline orchestration |

## Development Setup

### Prerequisites

- Python 3.11+
- Neo4j Community 5.x (Desktop or Docker)
- An LLM API key (DeepSeek, Claude, or OpenAI)

### Environment Configuration

```bash
# Copy the template - NEVER commit .env (it is excluded via .gitignore)
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

See `.env.example` for all available settings including alternative LLM providers (Claude, OpenAI).

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

This loads the export bundle (`data/semantica_export/`) into Neo4j, creating nodes for MPAs, ecosystem services, bridge axioms, documents, habitats, and species.

### Verify the Graph

```bash
python scripts/validate_graph.py
```

## Running the Stack

### Manual (3 terminals)

```bash
# Terminal 1: Start Neo4j (if using Docker)
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/maris-dev neo4j:5-community

# Terminal 2: Start the API server
uvicorn maris.api.main:app --host 0.0.0.0 --port 8000

# Terminal 3: Start the dashboard
cd investor_demo
streamlit run streamlit_app_v2.py
```

### Docker Compose (single command)

```bash
docker compose up --build
```

This starts Neo4j, the API server, and the Streamlit dashboard together.

### Health Check

```bash
# Quick API check
curl http://localhost:8000/api/health

# Full stack check
python scripts/demo_healthcheck.py
```

## Key Patterns

### Configuration (maris/config.py)

All settings are loaded from environment variables with `MARIS_` prefix. The `get_config()` function returns a singleton config object:

```python
from maris.config import get_config
config = get_config()
print(config.neo4j_uri)  # bolt://localhost:7687
```

### Lazy Singletons in Routes

API route modules use lazy initialization to avoid connecting to Neo4j/LLM at import time:

```python
_llm: LLMAdapter | None = None

def _init_components():
    global _llm
    if _llm is None:
        _llm = LLMAdapter(get_config())
```

### Query Classification

The `QueryClassifier` uses a two-tier strategy:

1. **Keyword rules** - Fast regex matching against 5 category patterns (site_valuation, provenance_drilldown, axiom_explanation, comparison, risk_assessment)
2. **LLM fallback** - For ambiguous queries, the LLM classifies into a category with confidence score

### Cypher Templates

All graph queries use parameterized Cypher templates (never raw string interpolation). Templates are defined in `maris/query/cypher_templates.py` and selected by query category.

### LLM Adapter

The `LLMAdapter` wraps an OpenAI-compatible client, supporting DeepSeek, Claude, and OpenAI with a single interface. Switch providers by changing `MARIS_LLM_PROVIDER` in `.env`.

## Adding New Features

### Adding a New Cypher Template

1. Add the template to `maris/query/cypher_templates.py`:
   ```python
   "my_template": {
       "cypher": "MATCH (n:MyNode {name: $name}) RETURN n",
       "description": "Look up a custom node",
   }
   ```
2. Add a keyword rule in `maris/query/classifier.py` if it maps to a new query category
3. Handle the new category in `maris/api/routes/query.py` (parameter extraction)

### Adding a New API Endpoint

1. Create a route function in the appropriate file under `maris/api/routes/`
2. Define Pydantic request/response models in `maris/api/models.py`
3. Register the router in `maris/api/main.py` if it's a new file

### Adding a New Graph Node Type

1. Update the graph schema in `maris/graph/schema.py`
2. Add population logic in `maris/graph/population.py`
3. Update Cypher templates that should include the new type
4. Add provenance edge queries in `maris/query/executor.py` if needed

## Testing

### API Health Check

```bash
curl http://localhost:8000/api/health
# Expected: {"status":"healthy","neo4j_connected":true,"llm_available":true,"graph_stats":{"node_count":878,"edge_count":101,...}}
```

### Manual Query Test

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Cabo Pulmo worth?", "include_graph_path": true}'
```

### Graph Validation

```bash
python scripts/validate_graph.py
```

Checks node counts, relationship integrity, and that all bridge axioms have evidence chains.

## Code Style

- Python 3.11+ with type hints throughout
- Pydantic v2 for all API models
- Follow PEP 8 conventions
- Terminology: "NEOLI alignment" (not "compliance"), "market-price" (not "NOAA-adjusted")
