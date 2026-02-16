# Nereus - Investor Demo Dashboard

## Overview

Interactive Streamlit dashboards for the **Nereus provenance-first blue finance platform** (powered by MARIS + Semantica), designed for investor-facing demonstrations. Dark-mode layout with professional financial styling.

**Three operating modes:**

- **v3 (Intelligence Platform - Recommended)** - Multi-tab dashboard that makes the P0-P4 backend infrastructure visible and interactive. 5 tabs: Intelligence Brief, GraphRAG Chat, Scenario Lab, Site Scout, TNFD Compliance. Dual-mode operation (Live/Demo) on every tab.
- **v2 (Live)** - Single-scroll dashboard with Neo4j knowledge graph, FastAPI query engine, and interactive graph explorer. Users can ask natural-language questions and see provenance chains rendered in real time.
- **v1 (Static)** - Standalone mode powered by a pre-computed JSON bundle. No external services required - ideal for offline demos or when zero-downtime is critical.

## Quick Start

### v3 - Intelligence Platform (Recommended)

Requires Neo4j and the MARIS API server for Live mode, or runs standalone in Demo mode. See the [root README](../README.md#nereus-v2---live-query-system) for full backend setup.

```bash
# 1. Ensure Neo4j is running and the graph is populated
python scripts/populate_neo4j.py

# 2. Start the API server (in one terminal)
uvicorn maris.api.main:app --host 0.0.0.0 --port 8000

# 3. Start the v3 dashboard (in another terminal)
cd investor_demo
streamlit run streamlit_app_v3.py --server.port 8503
```

The dashboard opens at `http://localhost:8503`. Toggle between Live and Demo modes in the sidebar. In Demo mode, no external services are required.

### v2 - Single-Scroll Dashboard

```bash
cd investor_demo
streamlit run streamlit_app_v2.py
```

The dashboard opens at `http://localhost:8501`. If the API is unreachable, the Ask Nereus panel falls back to precomputed responses automatically.

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
| **Bridge Axiom Templates** | `schemas/bridge_axiom_templates.json` | 16 axioms with translation coefficients and DOI-backed evidence |
| **Entity Definitions** | `data/semantica_export/entities.jsonld` | 14 JSON-LD entities (Species, Habitats, Financial Instruments, Frameworks) |
| **Curated Relationships** | `data/semantica_export/relationships.json` | 15 cross-domain edges with quantification and mechanism |
| **Investment-Grade Bundle** | `demos/context_graph_demo/cabo_pulmo_investment_grade_bundle.json` | Pre-computed Monte Carlo results, risk scenarios, framework alignment (used by v1 static mode) |

The v2 live mode queries these through the Neo4j graph (populated by `scripts/populate_neo4j.py`). The v1 static mode reads directly from the investment-grade bundle JSON.

**Calibration site model:** Cabo Pulmo National Park ($29.27M ESV, tourism-dominant) and Shark Bay World Heritage Area ($21.5M ESV, carbon-dominant) are fully characterized reference sites with complete ecosystem service valuations. Comparison sites (Great Barrier Reef, Papahanaumokuakea) have governance metadata only (NEOLI score, area, asset rating) and do not have financial data in the current graph. See the [Developer Guide](../docs/developer_guide.md#calibration-site-model) for details on adding new sites.

---

## Dashboard Architecture

### v3 Tab Structure (multi-tab, dark-mode)

| Tab | Content |
|-----|---------|
| **Intelligence Brief** | KPI strip (4 expandable cards), investment thesis, provenance chain graph, axiom evidence table, valuation composition, Monte Carlo risk profile |
| **Ask MARIS (GraphRAG)** | Split-panel: chat (60%) + reasoning pipeline (40%) showing CLASSIFY -> QUERY -> SYNTHESIZE -> VALIDATE steps with Cypher display, confidence breakdown, and integrated graph explorer |
| **Scenario Lab** | 4 parameter sliders (carbon price, habitat loss, tourism growth, fisheries change), real-time Monte Carlo recalculation (10k simulations), overlay histogram, tornado sensitivity chart, bridge axiom chain impact |
| **Site Scout** | Deferred placeholder (pipeline ready, dashboard pending) |
| **TNFD Compliance** | LEAP disclosure generation, X/14 alignment gauge, per-pillar progress bars, gap analysis, download buttons (Markdown, JSON, Executive Summary) |

**v3 Sidebar:** Mode toggle (Live/Demo), service health panel, site selector, scenario slider, system metadata.

### v2 Page Structure (single-scroll, dark-mode)

| Section | Content |
|---------|---------|
| **Masthead** | MARIS/SEMANTICA branding, site name, IFC Blue Finance and TNFD LEAP badges |
| **Investment Thesis** | Three-paragraph block: MARIS definition, Semantica provenance framework, context graphs concept |
| **Key Metrics** | 4 KPI cards: Annual ESV, Biomass Recovery, NEOLI Score, Climate Buffer |
| **Provenance Chain** | Fixed-position causal graph with 5 layers: Site, Ecological State, Ecosystem Services, Financial Value, Risk |
| **Bridge Axiom Evidence** | Table mapping key axioms (BA-001, BA-002, BA-011 through BA-016) to plain-English meanings and DOI citations |
| **Valuation Composition** | Horizontal bar chart of service breakdown + CI context |
| **Risk Profile** | Monte Carlo distribution (10,000 simulations) + resilience/degradation risk cards |
| **Comparison Sites** | 2x2 grid: Papahanaumokuakea (5/5), Cabo Pulmo (4/5), Shark Bay (4/5), Mesoamerican Reef (1-2/5) |
| **Framework Alignment** | IFC Blue Finance eligible uses + TNFD LEAP four-phase summary |
| **Scaling Intelligence** | Intelligence stack (public data, ecological, financial layers), 4-phase execution roadmap |
| **Ask MARIS** | Natural-language query chat with confidence badges, axiom tags, and evidence tables |
| **Graph Explorer** | Interactive Plotly visualization of the provenance chain from Neo4j |
| **Caveats** | All 7 caveats from the data bundle |

**v2 Sidebar:** Characterized sites, NEOLI alignment breakdown, confidence level slider (P5/Median/P95), methodology note.

### Component Files

**v3 Intelligence Platform:**

| File | Purpose |
|------|---------|
| `streamlit_app_v3.py` | Main v3 app - page config, CSS, sidebar, 5-tab structure |
| `components/v3/__init__.py` | Package init with shared exports (COLORS, formatters, health checks) |
| `components/v3/shared.py` | 26-color palette, V3_CSS (14k chars), formatters (fmt_usd, fmt_pct, confidence_badge, tier_badge), service health, site data loading |
| `components/v3/intelligence_brief.py` | Tab 1: KPIs, provenance graph, axiom evidence, valuation, risk profile |
| `components/v3/graphrag_chat.py` | Tab 2: Split-panel GraphRAG with pipeline transparency and graph explorer |
| `components/v3/scenario_engine.py` | Tab 3: Interactive Monte Carlo with 4 sliders, tornado chart, axiom impact |
| `components/v3/tnfd_compliance.py` | Tab 5: TNFD LEAP generation, alignment scoring, gap analysis, downloads |

**v2 Dashboard:**

| File | Purpose |
|------|---------|
| `streamlit_app_v2.py` | Main v2 dashboard - CSS, layout, data sections |
| `components/chat_panel.py` | Ask MARIS query UI with markdown rendering, confidence badges, evidence tables |
| `components/graph_explorer.py` | Plotly network graph with semantic layering (MPA -> Habitat -> Services -> Axioms -> Sources) |
| `components/roadmap_section.py` | Scaling Intelligence section (intelligence stack + execution roadmap), shared between v1 and v2 |

**Shared:**

| File | Purpose |
|------|---------|
| `api_client.py` | HTTP client wrapping MARIS API endpoints; passes Bearer token if `MARIS_API_KEY` is configured; auto-falls back to precomputed responses via TF-IDF keyword matching |
| `precomputed_responses.json` | Cached responses for 63 queries across all 5 categories (fallback when API is offline) |

---

## Strategic Architecture: "The Artifact is the Asset"

The v1 dashboard uses a **static JSON bundle** rather than a live database connection - this is a deliberate architectural choice. In high-stakes investor contexts, zero latency and 100% uptime are non-negotiable. The bundle itself demonstrates that MARIS outputs are portable, immutable, and auditable.

The v2 dashboard extends this with **live querying** - any question the investor asks is answered in real time with full provenance traced through the Neo4j knowledge graph. If the API is unreachable, the dashboard gracefully degrades to 35 precomputed responses (covering all 5 query categories), maintaining the zero-downtime guarantee. The `StaticBundleClient` uses TF-IDF-style keyword overlap scoring (with IDF weighting, geometric mean normalization, and a 0.3 similarity threshold) to match user questions to the best precomputed response. This replaced the earlier SequenceMatcher approach for more robust matching.

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

- **Dark mode**: Navy/slate palette (`#0B1120` background, `#162039` card gradient) - shared across v2 and v3
- **v3 multi-tab**: Organized into 5 focused tabs for deeper exploration of each domain
- **v2 single-scroll**: Narrative flows from ecology to finance in one continuous page
- **No emojis**: Professional, sober financial tone appropriate for institutional audiences
- **Provenance-first**: Every number traces to a DOI-backed source through explicit bridge axioms
- **Dual-mode operation**: Every v3 tab works in Live (Neo4j + LLM) and Demo (precomputed) modes
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
