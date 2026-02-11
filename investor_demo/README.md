# MARIS | SEMANTICA - Investor Demo Dashboard

## Overview

Interactive Streamlit dashboard for the **Cabo Pulmo Investment Case**, designed for investor-facing demonstrations of the MARIS/Semantica provenance-first blue finance infrastructure. Dark-mode, single-scroll layout with professional financial styling.

**Two operating modes:**

- **v2 (Live)** - Full stack with Neo4j knowledge graph, FastAPI query engine, and interactive graph explorer. Users can ask natural-language questions and see provenance chains rendered in real time.
- **v1 (Static)** - Standalone mode powered by a pre-computed JSON bundle. No external services required - ideal for offline demos or when zero-downtime is critical.

## Quick Start

### v2 - Live Mode (Recommended)

Requires Neo4j and the MARIS API server. See the [root README](../README.md#maris-v2---live-query-system) for full setup.

```bash
# 1. Ensure Neo4j is running and the graph is populated
python scripts/populate_neo4j.py

# 2. Start the API server (in one terminal)
uvicorn maris.api.main:app --host 0.0.0.0 --port 8000

# 3. Start the dashboard (in another terminal)
cd investor_demo
streamlit run streamlit_app_v2.py
```

The dashboard opens at `http://localhost:8501`. If the API is unreachable, the Ask MARIS panel falls back to precomputed responses automatically.

### v1 - Static Mode

```bash
cd investor_demo
pip install -r requirements.txt
streamlit run streamlit_app.py
```

**Data source:** The bundle at `demos/context_graph_demo/cabo_pulmo_investment_grade_bundle.json`. If missing, run the notebook at `demos/context_graph_demo/cabo_pulmo_investment_grade.ipynb` to generate it.

### Environment Configuration

Copy the template and add your LLM API key:

```bash
cp ../.env.example ../.env
# Edit ../.env: set MARIS_LLM_API_KEY to your DeepSeek/Claude/OpenAI key
```

> The `.env` file is excluded from git via `.gitignore`. Never commit it. See `.env.example` for all available settings.

## Dashboard Architecture

### Page Structure (v2, single-scroll, dark-mode)

| Section | Content |
|---------|---------|
| **Masthead** | MARIS/SEMANTICA branding, site name, IFC Blue Finance and TNFD LEAP badges |
| **Investment Thesis** | Three-paragraph block: MARIS definition, Semantica provenance framework, context graphs concept |
| **Key Metrics** | 4 KPI cards: Annual ESV, Biomass Recovery, NEOLI Score, Climate Buffer |
| **Provenance Chain** | Fixed-position causal graph with 5 layers: Site, Ecological State, Ecosystem Services, Financial Value, Risk |
| **Bridge Axiom Evidence** | Table mapping 4 axioms (BA-001, BA-002, BA-011, BA-012) to plain-English meanings and DOI citations |
| **Valuation Composition** | Horizontal bar chart of service breakdown + CI context |
| **Risk Profile** | Monte Carlo distribution (10,000 simulations) + resilience/degradation risk cards |
| **Ask MARIS** | Natural-language query chat with confidence badges, axiom tags, and evidence tables (v2 only) |
| **Graph Explorer** | Interactive Plotly visualization of the provenance chain from Neo4j (v2 only) |
| **Comparison Sites** | Papahanaumokuakea (5/5), Cabo Pulmo (4/5), Mesoamerican Reef (1-2/5) |
| **Framework Alignment** | IFC Blue Finance eligible uses + TNFD LEAP four-phase summary |
| **Caveats** | All 7 caveats from the data bundle |

### Sidebar

- Asset information (site name, area, designation year)
- NEOLI alignment breakdown with visual indicators
- Confidence level slider: Conservative (P5) / Base Case (Median) / Optimistic (P95)
- Methodology note and metadata

### Component Files (v2)

| File | Purpose |
|------|---------|
| `streamlit_app_v2.py` | Main dashboard - CSS, layout, data sections |
| `components/chat_panel.py` | Ask MARIS query UI with markdown rendering, confidence badges, evidence tables |
| `components/graph_explorer.py` | Plotly network graph with semantic layering (MPA -> Habitat -> Services -> Axioms -> Sources) |
| `api_client.py` | HTTP client wrapping MARIS API endpoints; auto-falls back to precomputed responses |
| `precomputed_responses.json` | Cached responses for 5 common queries (fallback when API is offline) |

## Strategic Architecture: "The Artifact is the Asset"

The v1 dashboard uses a **static JSON bundle** rather than a live database connection - this is a deliberate architectural choice. In high-stakes investor contexts, zero latency and 100% uptime are non-negotiable. The bundle itself demonstrates that MARIS outputs are portable, immutable, and auditable.

The v2 dashboard extends this with **live querying** - any question the investor asks is answered in real time with full provenance traced through the Neo4j knowledge graph. If the API is unreachable, the dashboard gracefully degrades to precomputed responses.

## Design Principles

- **Dark mode**: Navy/slate palette (`#0B1120` background, `#162039` card gradient)
- **No tabs**: Single-scroll page keeps the narrative flowing
- **No emojis**: Professional, sober financial tone
- **Provenance-first**: Every number traces to a DOI-backed source
- **Market-price methodology**: Actual expenditure data, not willingness-to-pay
- **Custom HTML/CSS**: All cards, KPIs, and tables use injected HTML for full visual control

## Dependencies

See `requirements.txt` for v1 (static) or `../requirements-v2.txt` for v2 (live).

Core: streamlit, plotly, numpy, pandas, networkx, requests

## Terminology

- "NEOLI alignment" not "compliance" (we don't claim certification)
- "market-price" not "NOAA-adjusted" for Cabo Pulmo tourism
- ESV = $29.3M, Tourism = $25.0M, Biomass = 4.63x
