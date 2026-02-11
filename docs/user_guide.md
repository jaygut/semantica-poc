# MARIS User Guide

## What is MARIS?

MARIS (Marine Asset Risk Intelligence System) translates peer-reviewed ecological science into investment-grade financial metrics for marine natural capital. Unlike conventional ESG data platforms, MARIS provides full scientific provenance: every number traces back to a DOI-cited source through explicit, auditable bridge axioms.

The system is designed for blue bond underwriters, conservation finance analysts, TNFD working groups, and marine ecologists who need defensible valuations backed by transparent methodology.

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

   > **Security:** The `.env` file contains database passwords and API keys. It is excluded from version control via `.gitignore` and must never be shared or committed.

2. **Populate the knowledge graph** - Load the curated data sources into Neo4j:

   ```bash
   python scripts/populate_neo4j.py
   ```

   This loads 195 peer-reviewed papers, 12 bridge axioms with DOI-backed evidence, ecosystem service valuations, species data, and trophic network structure from six curated JSON assets. See the [Developer Guide](developer_guide.md#knowledge-graph-data-lineage) for full data lineage.

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

---

## Using the Dashboard

### Layout

The dashboard is a single-scroll, dark-mode page designed for investor-facing presentations. No tabs - the narrative flows from ecological evidence through bridge axioms to financial output.

| Section | What You See |
|---------|-------------|
| **Investment Thesis** | Three-paragraph overview: what MARIS is, how Semantica provides provenance, and what context graphs mean for blue finance |
| **Key Metrics** | 4 KPI cards: Annual ESV ($29.27M), Biomass Recovery (4.63x), NEOLI Score (4/5), Climate Buffer |
| **Provenance Chain** | Fixed causal graph tracing ecological data through bridge axioms to financial value - the core "trust bridge" |
| **Bridge Axiom Evidence** | Table mapping 4 key axioms (BA-001, BA-002, BA-011, BA-012) to plain-English explanations and DOI citations |
| **Valuation Composition** | Horizontal bar chart showing ecosystem service breakdown (tourism, fisheries, carbon, coastal protection) with confidence intervals |
| **Risk Profile** | Monte Carlo distribution (10,000 simulations) with P5/P50/P95 percentiles, plus resilience and degradation risk scenario cards |
| **Ask MARIS** | Natural-language query chat with live provenance-backed answers |
| **Graph Explorer** | Interactive Plotly network visualization of the knowledge graph from Neo4j |
| **Comparison Sites** | Side-by-side NEOLI ratings: Papahanaumokuakea (5/5), Cabo Pulmo (4/5), Mesoamerican Reef (1-2/5) |
| **Framework Alignment** | IFC Blue Finance eligible uses and TNFD LEAP four-phase summary |
| **Caveats** | All 7 methodology caveats, displayed for transparency |

### Sidebar Controls

- **Asset information** - Site name, area (71 km2), designation year (1995)
- **NEOLI alignment** - Visual breakdown of each NEOLI criterion (No-take, Enforced, Old, Large, Isolated) with green/amber indicators
- **Confidence slider** - Switch between Conservative (P5), Base Case (Median), and Optimistic (P95) Monte Carlo scenarios
- **Methodology note** - Valuation methodology and data vintage

### Confidence Levels

The confidence slider adjusts which Monte Carlo percentile drives the headline ESV figure:

| Level | Percentile | ESV Estimate | Use Case |
|-------|-----------|-------------|----------|
| Conservative | P5 | ~$19.6M | Worst-case for risk assessment and stress testing |
| Base Case | Median (P50) | ~$28.7M | Central estimate for standard reporting and bond sizing |
| Optimistic | P95 | ~$36.1M | Best-case for opportunity analysis and upside framing |

---

## Ask MARIS - Natural-Language Queries

The Ask MARIS panel accepts natural-language questions about any site in the knowledge graph. Behind the scenes, questions are classified into categories, mapped to Cypher templates, executed against Neo4j, and synthesized into grounded answers with full provenance.

### Example Questions

| Question | What You Get |
|----------|-------------|
| "What is Cabo Pulmo worth?" | $29.27M ESV breakdown by service type, with DOI citations for each valuation |
| "What evidence supports the biomass recovery?" | Provenance chain from Aburto-Oropeza et al. 2011 through bridge axioms to financial output |
| "Explain bridge axiom BA-001" | Translation: fish biomass increase -> up to 84% higher tourism WTP, with coefficients and 3 supporting DOIs |
| "Compare Cabo Pulmo with Great Barrier Reef" | Side-by-side metrics: ESV, biomass ratio, NEOLI score, asset rating |
| "What are the risks if coral degrades?" | Ecosystem service impact estimates under degradation scenarios, with axiom-level risk factors |

### Understanding the Response

Each answer includes:

- **Confidence badge** - Green (>= 0.7), amber (0.4-0.7), or red (< 0.4). Reflects the strength of graph evidence behind the answer, not just LLM certainty.
- **Axiom tags** - The bridge axioms invoked (e.g. BA-001, BA-002). Each axiom is a peer-reviewed translation rule with explicit coefficients.
- **Evidence table** - DOI citations with paper title, publication year, and evidence tier (T1 = peer-reviewed journal, the strongest level).
- **Caveats** - Methodological limitations. MARIS surfaces these proactively rather than burying them.

### Site Coverage

**Cabo Pulmo National Park** is the fully characterized calibration site with complete ESV data, species records, trophic network, and bridge axiom links. Valuation and provenance queries for Cabo Pulmo return rich, multi-layered responses.

**Comparison sites** (Great Barrier Reef, Papahanaumokuakea) have governance metadata (NEOLI score, area, asset rating) but not full ecosystem service valuations. Queries about their financial value will note the absence of site-specific valuation data.

### Graph Explorer

The interactive network visualization shows the provenance chain as a layered graph:

- **Blue nodes** (top layer) - Marine Protected Areas
- **Green nodes** - Ecosystem Services (tourism, fisheries, carbon, coastal protection)
- **Orange nodes** - Bridge Axioms (the translation rules linking ecology to finance)
- **Teal nodes** - Habitats (coral reef, kelp forest, seagrass, mangrove)
- **Gray nodes** (bottom layer) - Source Documents (peer-reviewed papers by DOI)

Edges show provenance relationships: GENERATES (MPA -> service), TRANSLATES (axiom -> service), EVIDENCED_BY (axiom -> paper), APPLIES_TO (axiom -> MPA).

---

## Offline / Static Mode

If Neo4j or the API is unavailable, run the static v1 dashboard:

```bash
cd investor_demo
streamlit run streamlit_app.py
```

This uses a pre-computed JSON bundle (`demos/context_graph_demo/cabo_pulmo_investment_grade_bundle.json`) and requires no external services. The Ask MARIS and Graph Explorer features are not available in static mode, but all pre-computed sections (KPIs, provenance chain, risk profile, framework alignment) render fully.

---

## Troubleshooting

| Symptom | Solution |
|---------|----------|
| Dashboard shows "API unreachable" | Verify the API server is running: `curl http://localhost:8000/api/health` |
| Neo4j connection refused | Confirm Neo4j is running and the credentials in `.env` match your instance |
| LLM errors in Ask MARIS | Verify `MARIS_LLM_API_KEY` in `.env` is valid for your chosen provider |
| Empty graph explorer | Run `python scripts/populate_neo4j.py` to load data into Neo4j |
| Import errors on dashboard start | Ensure you are running from inside the `investor_demo/` directory |
| Queries return empty for non-Cabo Pulmo sites | Expected behavior - only the calibration site has full ESV data (see Site Coverage above) |
