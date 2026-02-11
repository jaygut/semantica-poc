# MARIS User Guide

## Overview

MARIS (Marine Asset Risk Intelligence System) translates ecological complexity into investment-grade natural capital assets. This guide covers day-to-day usage of the investor dashboard and the Ask MARIS query interface.

## Getting Started

### Prerequisites

- Python 3.11+
- Neo4j Community 5.x running locally (or via Docker)
- An LLM API key (DeepSeek, Claude, or OpenAI)

### First-Time Setup

1. **Configure your environment** - Copy the template and add your credentials:

   ```bash
   cp .env.example .env
   # Edit .env: set MARIS_NEO4J_PASSWORD and MARIS_LLM_API_KEY
   ```

   > The `.env` file contains secrets and is excluded from git via `.gitignore`. Never share or commit it.

2. **Populate the knowledge graph:**

   ```bash
   python scripts/populate_neo4j.py
   ```

3. **Start the API server:**

   ```bash
   uvicorn maris.api.main:app --host 0.0.0.0 --port 8000
   ```

4. **Start the dashboard:**

   ```bash
   cd investor_demo
   streamlit run streamlit_app_v2.py
   ```

   The dashboard opens at `http://localhost:8501`.

## Using the Dashboard

### Layout

The dashboard is a single-scroll page with these sections:

| Section | What You See |
|---------|-------------|
| **Investment Thesis** | Three-paragraph overview of MARIS, Semantica, and context graphs |
| **Key Metrics** | 4 KPI cards: Annual ESV, Biomass Recovery, NEOLI Score, Climate Buffer |
| **Provenance Chain** | Fixed causal graph tracing site data through axioms to financial value |
| **Bridge Axiom Evidence** | Table mapping 4 axioms to plain-English meanings and DOI citations |
| **Valuation Composition** | Bar chart of ecosystem service breakdown with confidence intervals |
| **Risk Profile** | Monte Carlo distribution (10,000 simulations) and risk scenario cards |
| **Ask MARIS** | Natural-language query chat with provenance-backed answers |
| **Graph Explorer** | Interactive network visualization of the knowledge graph |
| **Comparison Sites** | Side-by-side NEOLI ratings for three reference MPAs |
| **Framework Alignment** | IFC Blue Finance and TNFD LEAP alignment summary |
| **Caveats** | All methodology caveats for transparency |

### Sidebar

- **Asset information** - Site name, area, designation year
- **NEOLI alignment** - Breakdown of each NEOLI criterion with visual indicators
- **Confidence slider** - Switch between Conservative (P5), Base Case (Median), and Optimistic (P95) scenarios
- **Methodology note** - Data sources and methodology context

### Confidence Levels

The sidebar slider adjusts which Monte Carlo percentile is displayed:

| Level | Percentile | Use Case |
|-------|-----------|----------|
| Conservative | P5 | Worst-case for risk assessment |
| Base Case | Median | Central estimate for standard reporting |
| Optimistic | P95 | Best-case for opportunity analysis |

## Ask MARIS - Natural-Language Queries

The Ask MARIS panel lets you ask questions about any site in the knowledge graph. Answers include confidence scores, supporting evidence with DOI links, and the bridge axioms used.

### Example Questions

| Question | What You Get |
|----------|-------------|
| "What is Cabo Pulmo worth?" | ESV breakdown with service-level values and methodology |
| "What evidence supports the biomass recovery claim?" | DOI-backed provenance chain from ecological observation to financial output |
| "Explain bridge axiom BA-001" | Plain-English explanation with coefficients, evidence sources, and applicable sites |
| "Compare Cabo Pulmo with Papahanaumokuakea" | Side-by-side ESV, biomass, and NEOLI metrics |
| "What are the risks if coral degrades?" | Risk scenarios with ecosystem service impact estimates |

### Reading the Response

Each answer includes:

- **Confidence badge** - Green (high), amber (medium), or red (low) indicating answer reliability
- **Axiom tags** - Which bridge axioms were used to derive the answer (e.g. BA-001, BA-002)
- **Evidence table** - DOI citations with title, year, and evidence tier (T1 = peer-reviewed)
- **Caveats** - Any methodological limitations that apply

### Graph Explorer

Below each query response (and in the dedicated Graph Explorer section), you can see an interactive network visualization showing:

- **Blue nodes** (top) - Marine Protected Areas
- **Green nodes** - Ecosystem Services
- **Orange nodes** - Bridge Axioms
- **Teal nodes** - Habitats
- **Gray nodes** (bottom) - Source Documents (DOIs)

Edges show the provenance relationships: which axioms apply to which sites, what services they translate to, and which documents provide evidence.

## Offline / Static Mode

If Neo4j or the API is unavailable, you can run the static dashboard:

```bash
cd investor_demo
streamlit run streamlit_app.py
```

This uses a pre-computed JSON bundle and requires no external services. The Ask MARIS and Graph Explorer features are not available in static mode.

## Troubleshooting

| Symptom | Solution |
|---------|----------|
| Dashboard shows "API unreachable" | Ensure the API server is running: `curl http://localhost:8000/api/health` |
| Neo4j connection refused | Check Neo4j is running and credentials in `.env` match |
| LLM errors in Ask MARIS | Verify `MARIS_LLM_API_KEY` in `.env` is valid |
| Empty graph explorer | Run `python scripts/populate_neo4j.py` to populate the graph |
| Import errors on dashboard start | Run from inside `investor_demo/` directory: `cd investor_demo && streamlit run streamlit_app_v2.py` |
