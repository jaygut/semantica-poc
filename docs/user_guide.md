# Nereus User Guide

## What is Nereus?

Nereus is a provenance-first blue finance platform, powered by MARIS (Marine Asset Risk Intelligence System) + Semantica. It translates peer-reviewed ecological science into investment-grade financial metrics for marine natural capital. Unlike conventional ESG data platforms, Nereus provides full scientific provenance: every number traces back to a DOI-cited source through explicit, auditable bridge axioms.

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
   # Edit .env: set MARIS_NEO4J_PASSWORD, MARIS_LLM_API_KEY, and MARIS_API_KEY
   ```

   > **Security:** The `.env` file contains database passwords and API keys. It is excluded from version control via `.gitignore` and must never be shared or committed.

2. **Populate the knowledge graph** - Load all 9 sites into Neo4j:

   ```bash
   python scripts/populate_neo4j_v4.py
   ```

   This loads 195 peer-reviewed papers, 35 bridge axioms with DOI-backed evidence, ecosystem service valuations for 9 Gold-tier MPA sites, species data, and trophic network structure. The v4 populator dynamically discovers all case study files. See the [Developer Guide](developer_guide.md#knowledge-graph-data-lineage) for full data lineage.

3. **Launch the platform (recommended - one command):**

   ```bash
   ./launch.sh v4
   ```

   This starts Neo4j connectivity checks, the API server, and the v4 dashboard. The v4 dashboard opens at `http://localhost:8504`.

   **Or start services manually:**

   ```bash
   # Terminal 1: Start the API server
   uvicorn maris.api.main:app --host 0.0.0.0 --port 8000

   # Terminal 2: Start the dashboard
   cd investor_demo
   streamlit run streamlit_app_v4.py --server.port 8504
   ```

   **Alternative dashboard versions:**

   ```bash
   ./launch.sh v3   # v3 Intelligence Platform (2 sites, port 8503)
   ./launch.sh v2   # v2 single-scroll dashboard (port 8501)
   ./launch.sh v1   # v1 static dashboard (no API, port 8500)
   ```

---

## Using the Dashboard

Nereus provides four dashboard versions: the **v4 Global Portfolio** (recommended), the **v3 Intelligence Platform**, the **v2 single-scroll dashboard**, and the **v1 static dashboard** (offline/standalone).

### v4 Global Portfolio (Recommended)

The v4 dashboard is the global scaling milestone at `http://localhost:8504`, covering all 9 Gold-tier MPA sites across 4 habitat types and 9 countries. It features 6 tabs with dual-mode operation: **Live** (Neo4j + LLM) and **Demo** (precomputed + static bundle), toggled from the sidebar.

#### Tab 1: Portfolio Overview

The default landing tab presents a grid view of the entire 9-site portfolio:

| Section | What You See |
|---------|-------------|
| **Portfolio Summary** | Total portfolio ESV, site count, habitat coverage, average rating |
| **Site Grid** | Cards for all 9 sites showing ESV, habitat type, asset rating, and NEOLI score |
| **Portfolio Composition** | Breakdown by habitat type, geography, and ESV contribution |
| **Risk Heatmap** | Cross-site risk factors and data freshness indicators |

#### Tab 2: Intelligence Brief

Per-site deep dive with full provenance:

| Section | What You See |
|---------|-------------|
| **KPI Strip** | 4 expandable cards: Annual ESV, NEOLI Score, Asset Rating, Confidence Interval (with detailed breakdowns on expand) |
| **Investment Thesis** | Site-specific narrative with market context |
| **Provenance Chain** | Interactive Plotly network graph with semantic layers (MPA, Services, Axioms, Documents) |
| **Axiom Evidence Table** | Bridge axioms mapped to plain-English explanations, coefficients, and DOI citations |
| **Valuation Composition** | Bar chart showing ecosystem service breakdown with confidence intervals |
| **Risk Profile** | Monte Carlo distribution (10,000 simulations) with P5/P50/P95 percentiles |

#### Tab 3: Ask Nereus (GraphRAG)

A split-panel interface showing both the chat and the reasoning pipeline:

- **Left panel (60%)** - Natural-language chat with confidence badges, axiom tags, and evidence tables. An expandable **Confidence Transparency** section shows the full breakdown of the composite confidence score (tier_base, path_discount, staleness_discount, sample_factor) for each response.
- **Right panel (40%)** - Pipeline transparency showing 4 steps: CLASSIFY (query category detection), QUERY GRAPH (Cypher generation and execution), SYNTHESIZE (LLM grounding with graph context), VALIDATE (confidence scoring and DOI verification)
- Includes an integrated knowledge graph subgraph explorer with semantic layering
- Supports queries across all 9 sites

#### Tab 4: Scenario Lab

Interactive Monte Carlo simulation with site-aware axiom chains:

- **Site selector**: Run scenarios against any of the 9 Gold-tier sites
- **4 parameter sliders**: Carbon price ($10-100/tonne), Habitat loss (0-50%), Tourism growth (-20% to +30%), Fisheries change (-30% to +20%)
- **Overlay histogram**: Shows how parameter changes shift the ESV distribution relative to the baseline
- **Tornado sensitivity chart**: Ranks parameters by their impact on total ESV
- **Bridge axiom chain impact**: Shows how parameter changes flow through applicable axioms to affect the bottom line
- Uses `maris.axioms.monte_carlo` and `maris.axioms.sensitivity` engines for real computation

#### Tab 5: Site Intelligence

Four-panel intelligence view for the selected site:

- **NEOLI Heatmap** - Portfolio-wide NEOLI alignment scores across all 9 sites, with the selected site highlighted
- **Habitat-Axiom Map** - Which bridge axioms are applicable to each habitat type in the portfolio
- **Data Quality Dashboard** - Per-site evidence tier breakdown (T1-T4), DOI coverage, and provenance_summary badges
- **Characterization Pipeline Diagram** - Annotated flow showing the 5-step auto-characterization process (OBIS species pull, WoRMS taxonomy, Marine Regions geometry, ecological scoring, Gold/Silver/Bronze tiering)

#### Tab 6: TNFD Compliance

TNFD LEAP disclosure generation and alignment scoring for all 9 sites:

- **Site selector**: Generate LEAP disclosures for any site in the portfolio
- **Alignment gauge**: X/14 disclosure alignment score
- **Per-pillar progress bars**: Governance (X/3), Strategy (X/4), Risk & Impact (X/4), Metrics & Targets (X/3)
- **LEAP phase expanders**: Locate, Evaluate, Assess, Prepare - each with generated content
- **Gap analysis**: Identifies missing or partial disclosures
- **Download buttons**: Export as Markdown, JSON, or Executive Summary

#### v4 Sidebar Controls

- **Mode toggle** - Switch between Live Intelligence Mode (Neo4j + LLM) and Demo Mode (precomputed)
- **Service health panel** - Shows API, Neo4j, and LLM connectivity status (Live mode only)
- **Site selector** - All 9 Gold-tier sites available
- **Scenario slider** - Conservative (P5) / Base Case (Median) / Optimistic (P95)
- **System metadata** - Schema version, site count (9), bridge axiom count (40)

### v3 Intelligence Platform

The v3 dashboard at `http://localhost:8503` is a multi-tab intelligence platform covering 2 sites (Cabo Pulmo and Shark Bay). It shares the same tab architecture as v4 (5 tabs: Intelligence Brief, Ask Nereus, Scenario Lab, Site Scout, TNFD Compliance) but without the Portfolio Overview tab and limited to 2 sites.

### v2 Single-Scroll Dashboard

The v2 dashboard at `http://localhost:8501` is a single-scroll, dark-mode page designed for investor-facing presentations. The narrative flows from ecological evidence through bridge axioms to financial output.

| Section | What You See |
|---------|-------------|
| **Investment Thesis** | Three-paragraph overview: what Nereus is, how MARIS + Semantica provide provenance, and what context graphs mean for blue finance |
| **Key Metrics** | 4 KPI cards: Annual ESV ($29.27M), Biomass Recovery (4.63x), NEOLI Score (4/5), Climate Buffer |
| **Provenance Chain** | Fixed causal graph tracing ecological data through bridge axioms to financial value - the core "trust bridge" |
| **Bridge Axiom Evidence** | Table mapping key axioms (BA-001, BA-002, BA-011 through BA-016) to plain-English explanations and DOI citations |
| **Valuation Composition** | Horizontal bar chart showing ecosystem service breakdown (tourism, fisheries, carbon, coastal protection) with confidence intervals |
| **Risk Profile** | Monte Carlo distribution (10,000 simulations) with P5/P50/P95 percentiles, plus resilience and degradation risk scenario cards |
| **Comparison Sites** | 2x2 grid: Papahanaumokuakea (5/5), Cabo Pulmo (4/5), Shark Bay (4/5), Mesoamerican Reef (1-2/5) |
| **Framework Alignment** | IFC Blue Finance eligible uses and TNFD LEAP four-phase summary |
| **Scaling Intelligence** | Intelligence stack (public data, ecological, financial layers), 4-phase execution roadmap from 1 to 100+ MPAs |
| **Ask Nereus** | Natural-language query chat with live provenance-backed answers |
| **Graph Explorer** | Interactive Plotly network visualization of the knowledge graph from Neo4j |
| **Caveats** | All 7 methodology caveats, displayed for transparency |

#### v2 Sidebar Controls

- **Characterized sites** - Cabo Pulmo ($29.3M ESV, tourism-dominant) and Shark Bay ($21.5M ESV, carbon-dominant)
- **NEOLI alignment** - Visual breakdown of each NEOLI criterion (No-take, Enforced, Old, Large, Isolated) with green/amber indicators
- **Confidence slider** - Switch between Conservative (P5), Base Case (Median), and Optimistic (P95) Monte Carlo scenarios
- **Methodology note** - Valuation methodology and data vintage

### Confidence Levels

Nereus uses two distinct confidence models:

**Monte Carlo ESV Confidence** - Statistical uncertainty in ecosystem service values. The confidence slider adjusts which percentile drives the headline ESV figure, based on confidence interval propagation across 10,000 simulations:

| Level | Percentile | ESV Estimate | Use Case |
|-------|-----------|-------------|----------|
| Conservative | P5 | ~$19.6M | Worst-case for risk assessment and stress testing |
| Base Case | Median (P50) | ~$28.7M | Central estimate for standard reporting and bond sizing |
| Optimistic | P95 | ~$36.1M | Best-case for opportunity analysis and upside framing |

**Answer-Level Confidence** - A composite score shown on Ask Nereus responses, computed as:

```
composite = tier_base * path_discount * staleness_discount * sample_factor
```

| Factor | What It Measures | Values |
|--------|-----------------|--------|
| tier_base | Evidence quality of source documents (mean of tier confidences) | T1=0.95, T2=0.80, T3=0.65, T4=0.50 |
| path_discount | Inference chain length (graph hops) | -5% per hop, floor 0.1 |
| staleness_discount | Age of underlying data (based on median year) | No penalty <=5 years, -2%/year beyond, floor 0.3 |
| sample_factor | Number of independent sources | Linear ramp: 0.6 (1 source) to 1.0 (4+ sources) |

Typical score ranges: direct site valuations score 80-88%, mechanism explanations ~74%, and multi-hop risk assessments ~57%. Each factor is independently auditable, so investors can see exactly why a particular answer received its confidence score.

---

## Ask Nereus - Natural-Language Queries

The Ask Nereus panel accepts natural-language questions about any site in the knowledge graph. Behind the scenes, questions are classified into categories, mapped to Cypher templates, executed against Neo4j, and synthesized into grounded answers with full provenance.

In the **v4 Global Portfolio** (Tab 3) and **v3 Intelligence Platform** (Tab 2), the GraphRAG interface uses a split-panel layout: chat on the left with a reasoning pipeline panel on the right that shows each step of the query pipeline (CLASSIFY, QUERY GRAPH, SYNTHESIZE, VALIDATE) in real time with Cypher display and confidence breakdown. In the **v2 dashboard**, Ask Nereus appears as a chat panel near the bottom of the page.

### Example Questions

| Question | What You Get |
|----------|-------------|
| "What is Cabo Pulmo worth?" | $29.3M ESV breakdown by service type, with DOI citations for each valuation |
| "What is the Sundarbans ESV?" | $778.9M ESV driven by mangrove ecosystem services with full provenance chain |
| "What evidence supports the biomass recovery?" | Provenance chain from Aburto-Oropeza et al. 2011 through bridge axioms to financial output |
| "Explain bridge axiom BA-001" | Translation: fish biomass increase -> up to 84% higher tourism WTP, with coefficients and 3 supporting DOIs |
| "Compare Galapagos with Belize Barrier Reef" | Side-by-side metrics: ESV, NEOLI score, asset rating, habitat coverage |
| "Compare Cabo Pulmo with Great Barrier Reef" | Side-by-side metrics: ESV, biomass ratio, NEOLI score, asset rating |
| "What is Aldabra Atoll's carbon value?" | Carbon sequestration ESV from seagrass and mangrove habitats with axiom chain |
| "What are the risks if coral degrades at Ningaloo?" | Ecosystem service impact estimates under degradation scenarios, with axiom-level risk factors |
| "How does Raja Ampat's mangrove provide flood protection?" | Axiom-backed coastal protection valuation with DOI evidence |

### Understanding the Response

Each answer includes:

- **Confidence badge** - Green (>= 0.7), amber (0.4-0.7), or red (< 0.4). Reflects the strength of graph evidence behind the answer, not just LLM certainty.
- **Axiom tags** - The bridge axioms invoked (e.g. BA-001, BA-002). Each axiom is a peer-reviewed translation rule with explicit coefficients.
- **Evidence table** - DOI citations with paper title, publication year, and evidence tier (T1 = peer-reviewed journal, the strongest level).
- **Caveats** - Methodological limitations. Nereus surfaces these proactively rather than burying them.

### Site Coverage

All 9 Gold-tier sites are fully characterized with complete ESV data, species records, and bridge axiom links:

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

Valuation and provenance queries for any of these sites return rich, multi-layered responses with full DOI-backed evidence chains.

**Comparison sites** (Great Barrier Reef, Papahanaumokuakea) have governance metadata (NEOLI score, area, asset rating) but not full ecosystem service valuations. Queries about their financial value will note the absence of site-specific valuation data.

When the API is unavailable, Ask Nereus falls back to 139 precomputed responses covering all 7 query categories (valuation, provenance, axiom, comparison, risk, concept_explanation, scenario_analysis). The fallback uses TF-IDF-style keyword matching to find the best precomputed answer for your question.

### Graph Explorer

The interactive network visualization shows the provenance chain as a layered graph:

- **Blue nodes** (top layer) - Marine Protected Areas
- **Green nodes** - Ecosystem Services (tourism, fisheries, carbon, coastal protection)
- **Orange nodes** - Bridge Axioms (the translation rules linking ecology to finance)
- **Teal nodes** - Habitats (coral reef, kelp forest, seagrass, mangrove)
- **Gray nodes** (bottom layer) - Source Documents (peer-reviewed papers by DOI)

Edges show provenance relationships: GENERATES (MPA -> service), TRANSLATES (axiom -> service), EVIDENCED_BY (axiom -> paper), APPLIES_TO (axiom -> MPA).

---

## v6 Scenario Intelligence - Ask Nereus Forward-Looking Queries

v6 adds a seventh query category - `scenario_analysis` - to the Ask Nereus engine. Scenario queries are automatically detected, parsed into structured `ScenarioRequest` objects, routed to the appropriate computation engine, and returned with P5/P50/P95 uncertainty envelopes and full provenance.

### Scenario Query Types

| Type | Description | Example Question |
|------|-------------|-----------------|
| **Counterfactual** | ESV delta if protection were removed | "What would Cabo Pulmo be worth without protection?" |
| **Climate / SSP** | Habitat degradation under SSP1-2.6, SSP2-4.5, or SSP5-8.5 | "What happens to Belize under SSP2-4.5 by 2050?" |
| **Blue Carbon Market** | Revenue at a given carbon price ($/tCO2e) | "What blue carbon revenue could Sundarbans generate at $45/tCO2?" |
| **Tipping Point** | McClanahan piecewise proximity to regime shift | "How close is Cabo Pulmo to a tipping point?" |
| **Portfolio Nature VaR** | Correlated portfolio loss at P95 | "What is the portfolio nature VaR at 95th percentile?" |
| **Intervention / ROI** | Benefit-cost ratio for a restoration investment | "What if we invest $5M to restore mangroves at Cispata?" |

### Quick-Query Buttons

Each site in the Scenario Lab (Tab 4) has four pre-wired quick-query buttons that fire the most common scenario question for that site. In demo mode all 36 combinations (9 sites x 4 types) are answered from precomputed responses grounded in actual Python engine output.

### Example Scenario Responses

**Counterfactual (Cabo Pulmo):**
```
Without protection, Cabo Pulmo National Park ESV would decline from $29.27M
to an estimated $9.11M/yr - a loss of $20.16M (68.9%). The 4.63x biomass
multiplier (Edgar et al. 2014, doi:10.1038/nature13022) collapses without
the no-take zone, eliminating the tourism premium that accounts for $25M of
the total. P5/P50/P95: $7.3M / $9.1M / $11.0M.
```

**Blue Carbon Market (Sundarbans at $45/tCO2e):**
```
Sundarbans Reserve Forest could generate ~$19.4M/yr in blue carbon revenue
at $45/tCO2e. Calculation: 460,000 ha mangrove x 7.0 tCO2/ha/yr (Blue
Carbon Initiative) x 0.60 Verra-verified fraction x $45 = $19,404,000/yr.
Source: Friess et al. 2020 (doi:10.1146/annurev-environ-012220-012511).
```

**Climate / SSP (Belize under SSP2-4.5 by 2050):**
```
Under SSP2-4.5 by 2050, Belize Barrier Reef Reserve System ESV is projected
to decline from $292.5M to ~$224.2M (-23.4%). Coral reef bleaching
frequency rises from 1-in-5 years to annual under +2.0C (IPCC AR6 WG1).
P5/P50/P95: -32% / -23% / -14%.
```

**Tipping Point (Cabo Pulmo - data available):**
```
Cabo Pulmo fish biomass is approximately 1,039 kg/ha - within the upper
"Near-pristine" band of the McClanahan et al. 2011 piecewise reef function
(threshold: 1,130 kg/ha). Tipping point proximity: 8.1% below the Near-
pristine ceiling. Source: McClanahan et al. 2011
(doi:10.1073/pnas.1106861108).
```

### Scientific Grounding

All scenario computations are deterministically derived from the knowledge graph and case study data. The engines that power live mode are:

| Engine | File | Sources |
|--------|------|---------|
| Counterfactual | `maris/scenario/counterfactual_engine.py` | Edgar et al. 2014 (biomass multiplier) |
| Climate/SSP | `maris/scenario/climate_scenarios.py` | IPCC AR6, coral bleaching literature |
| Blue Carbon | `maris/scenario/blue_carbon_revenue.py` | Blue Carbon Initiative, Friess et al. 2020 |
| Tipping Point | `maris/scenario/tipping_point_analyzer.py` | McClanahan et al. 2011 (piecewise reef function) |
| Stress Test | `maris/scenario/stress_test_engine.py` | Cholesky-correlated Monte Carlo (N=10,000) |
| Real Options | `maris/scenario/real_options_valuator.py` | Black-Scholes conservation option value |

Scenario responses include `axioms_used`, `propagation_trace` (step-by-step axiom chain with coefficients), `uncertainty` (P5/P50/P95), `confidence` score, and `caveats` - all surfaced in the UI. Parser validation anchors: Cabo Pulmo counterfactual delta -$20.16M, Cispata Bay BCR 13.34, Portfolio VaR_95 $646.6M (all verified against 13 invariant tests in `tests/scenario/test_scenario_invariants.py`).

---

## Data Freshness Indicators

The dashboard displays freshness badges next to data-dependent metrics, indicating the age of the underlying measurements:

| Badge | Color | Meaning |
|-------|-------|---------|
| **Current** | Green | Data is 5 years old or less |
| **Aging** | Yellow | Data is between 5 and 10 years old |
| **Stale** | Red | Data is more than 10 years old |

Freshness is derived from the `measurement_year` property on MPA nodes in the knowledge graph. Stale data carries a higher staleness_discount penalty in the answer-level confidence model (see Confidence Levels above), signaling to investors that the underlying measurements may warrant updated field surveys.

---

## Sensitivity Analysis

The dashboard includes a tornado plot showing which ecosystem service parameters have the greatest impact on total ESV. This uses One-at-a-Time (OAT) methodology:

- Each service parameter is perturbed by +/-10% and +/-20% from its base value
- The resulting change in total ESV is measured for each perturbation
- Parameters are ranked by their impact magnitude in the tornado plot

The dominant parameter is typically Tourism ($25.0M), which accounts for the largest share of total ESV. This analysis helps investors understand which service values are most critical to monitor and where updated field data would most reduce valuation uncertainty.

---

## Offline / Demo Mode

The v4, v3, and v2 dashboards all support **Demo Mode** (toggle in sidebar) which uses precomputed responses and static data bundles - no Neo4j or LLM required.

For a fully standalone experience with no external services, run the static v1 dashboard:

```bash
cd investor_demo
streamlit run streamlit_app.py
```

This uses a pre-computed JSON bundle (`demos/context_graph_demo/cabo_pulmo_investment_grade_bundle.json`). The Ask MARIS and Graph Explorer features are not available in v1 static mode, but all pre-computed sections (KPIs, provenance chain, risk profile, framework alignment) render fully.

---

## Troubleshooting

| Symptom | Solution |
|---------|----------|
| Dashboard shows "API unreachable" | Verify the API server is running: `curl http://localhost:8000/api/health` |
| Neo4j connection refused | Confirm Neo4j is running and the credentials in `.env` match your instance |
| LLM errors in Ask MARIS | Verify `MARIS_LLM_API_KEY` in `.env` is valid for your chosen provider |
| Empty graph explorer | Run `python scripts/populate_neo4j_v4.py` to load data into Neo4j |
| Import errors on dashboard start | Ensure you are running from inside the `investor_demo/` directory |
| Queries return empty for comparison sites | Expected behavior - only the 9 Gold-tier sites have full ESV data. Comparison sites (GBR, Papahanaumokuakea) have governance metadata only (see Site Coverage above) |
| **401 Unauthorized** from API | API key is missing or invalid. Set `MARIS_API_KEY` in `.env` and include `Authorization: Bearer <key>` header in requests |
| **429 Rate Limited** | Too many requests. The API allows 30 queries/minute and 60 other requests/minute per API key. Wait and retry |
