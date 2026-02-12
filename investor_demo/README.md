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
# Edit ../.env: set MARIS_LLM_API_KEY and MARIS_API_KEY
```

| Variable | Purpose |
|----------|---------|
| `MARIS_LLM_API_KEY` | API key for your LLM provider (DeepSeek, Claude, or OpenAI) |
| `MARIS_API_KEY` | Bearer token for authenticating with the MARIS API |

> The `.env` file contains secrets (API keys, database passwords) and is excluded from git via `.gitignore`. Never commit it. See `.env.example` for all available settings.

---

## Data Provenance

Every number displayed in the dashboard traces back to curated, DOI-backed source data. The dashboard does not generate or infer financial figures - it renders pre-computed and graph-queried values that originate from six curated datasets:

| Data Source | File | What It Provides to the Dashboard |
|-------------|------|-----------------------------------|
| **Document Registry** | `.claude/registry/document_index.json` | 195 peer-reviewed papers (DOI, title, year, evidence tier) |
| **Cabo Pulmo Case Study** | `examples/cabo_pulmo_case_study.json` | Site metadata, NEOLI assessment, ecosystem service values ($29.27M ESV), biomass recovery (4.63x), species data, trophic network |
| **Bridge Axiom Templates** | `schemas/bridge_axiom_templates.json` | 12 axioms with translation coefficients and DOI-backed evidence |
| **Entity Definitions** | `data/semantica_export/entities.jsonld` | 14 JSON-LD entities (Species, Habitats, Financial Instruments, Frameworks) |
| **Curated Relationships** | `data/semantica_export/relationships.json` | 15 cross-domain edges with quantification and mechanism |
| **Investment-Grade Bundle** | `demos/context_graph_demo/cabo_pulmo_investment_grade_bundle.json` | Pre-computed Monte Carlo results, risk scenarios, framework alignment (used by v1 static mode) |

The v2 live mode queries these through the Neo4j graph (populated by `scripts/populate_neo4j.py`). The v1 static mode reads directly from the investment-grade bundle JSON.

**Calibration site model:** Cabo Pulmo National Park is the fully characterized reference site with complete ecosystem service valuations. Comparison sites (Great Barrier Reef, Papahanaumokuakea) have governance metadata only (NEOLI score, area, asset rating) and do not have financial data in the current graph. See the [Developer Guide](../docs/developer_guide.md#calibration-site-model) for details on adding new sites.

---

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
| `api_client.py` | HTTP client wrapping MARIS API endpoints; passes Bearer token if `MARIS_API_KEY` is configured; auto-falls back to precomputed responses via TF-IDF keyword matching |
| `precomputed_responses.json` | Cached responses for 27 queries across all 5 categories (fallback when API is offline) |

---

## Strategic Architecture: "The Artifact is the Asset"

The v1 dashboard uses a **static JSON bundle** rather than a live database connection - this is a deliberate architectural choice. In high-stakes investor contexts, zero latency and 100% uptime are non-negotiable. The bundle itself demonstrates that MARIS outputs are portable, immutable, and auditable.

The v2 dashboard extends this with **live querying** - any question the investor asks is answered in real time with full provenance traced through the Neo4j knowledge graph. If the API is unreachable, the dashboard gracefully degrades to 27 precomputed responses (covering all 5 query categories), maintaining the zero-downtime guarantee. The `StaticBundleClient` uses TF-IDF-style keyword overlap scoring (with IDF weighting, geometric mean normalization, and a 0.3 similarity threshold) to match user questions to the best precomputed response. This replaced the earlier SequenceMatcher approach for more robust matching.

---

## Sensitivity Analysis

The dashboard includes a tornado plot component showing parameter sensitivity for total ESV. Each ecosystem service parameter is perturbed using One-at-a-Time (OAT) methodology at +/-10% and +/-20% to identify which services drive the most variance in the headline valuation. Tourism ($25.0M) is typically the dominant parameter.

---

## Data Freshness

The dashboard displays freshness badges next to data-dependent metrics:

- **Current** (green) - measurement data is 5 years old or less
- **Aging** (yellow) - measurement data is between 5 and 10 years old
- **Stale** (red) - measurement data is more than 10 years old

Freshness is derived from the `measurement_year` property on MPA nodes and feeds into the staleness_discount factor in the confidence scoring model.

---

## Design Principles

- **Dark mode**: Navy/slate palette (`#0B1120` background, `#162039` card gradient)
- **No tabs**: Single-scroll page keeps the narrative flowing from ecology to finance
- **No emojis**: Professional, sober financial tone appropriate for institutional audiences
- **Provenance-first**: Every number traces to a DOI-backed source through explicit bridge axioms
- **Market-price methodology**: Actual expenditure data (not contingent valuation or willingness-to-pay)
- **Custom HTML/CSS**: All cards, KPIs, and tables use injected HTML for precise visual control

---

## Dependencies

See `requirements.txt` for v1 (static) or `../requirements-v2.txt` for v2 (live).

Core: streamlit, plotly, numpy, pandas, networkx, requests

## Terminology

- "NEOLI alignment" not "compliance" (the system does not claim NEOLI certification)
- "market-price" not "NOAA-adjusted" for Cabo Pulmo tourism
- ESV = $29.27M, Tourism = $25.0M, Biomass = 4.63x
