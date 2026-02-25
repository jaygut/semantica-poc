# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**Nereus** is a "Hybrid" Intelligence platform, powered by MARIS + Semantica. It creates auditable, **physically linked** pathways from peer-reviewed ecological science to investment-grade financial metrics. Unlike standard RAG, Nereus executes logic (axioms) extracted directly from literature.

**Current Status:** v6 Prospective Scenario Intelligence - **Forward-Looking ESV Analytics** (40 Bridge Axioms). Built on the v5 Audit-Grade Integrity platform. Neo4j knowledge graph (953+ nodes), 9 MPA sites, $1.62B ESV. Adds counterfactual analysis, SSP climate scenarios, McClanahan tipping point engine, blue carbon revenue modeling, portfolio Nature VaR, and real options valuation - all with deterministic provenance chains and P5/P50/P95 uncertainty envelopes.

## Core Philosophy: "The Logic is Physically Linked"
1.  **No Hallucinations:** Financial claims must be the result of a deterministic graph traversal.
2.  **Payload-Driven:** The intelligence comes from the *extracted axioms* (the payload), not the LLM's training data.
3.  **Semantica First:** All new intelligence starts with Extraction -> Axiom Formation -> Graph Ingestion. We do not hardcode logic; we extract it.

---

## Quick Start

```bash
./launch.sh v4      # v4 Global Scaling Platform (9 sites, 6 tabs, :8504)
./launch.sh v3      # Intelligence Platform (2 sites, 5 tabs, :8503)
./launch.sh v2      # Single-scroll dashboard (2 sites, :8501)
./launch.sh v1      # Static mode (1 site, no external services)
./launch.sh api     # API server only (:8000)
./launch.sh stop    # Stop all services
```

Manual: `cp .env.example .env` then `python scripts/populate_neo4j_v4.py && uvicorn maris.api.main:app --port 8000`. Use `MARIS_DEMO_MODE=true` for dev without API key.

---

## Module Structure

```
maris/
  api/              # FastAPI: main.py, models.py, auth.py, routes/
  graph/            # Neo4j: connection, schema, population, validation
  query/            # NL-to-Cypher: classifier, cypher_templates, executor, generator, formatter
  llm/              # LLM adapter (DeepSeek/Claude/GPT-4), prompts
  axioms/           # engine, confidence (+ apply_scenario_penalties), monte_carlo, sensitivity
  ingestion/        # pdf_extractor, llm_extractor, embedding_generator, graph_merger
  provenance/       # W3C PROV-O: manager, bridge_axiom_registry, certificate, storage, doi_verifier, models
  sites/            # Multi-site: characterizer, esv_estimator (dynamic carbon pricing), api_clients
  reasoning/        # Inference: context_builder, hybrid_retriever, rule_compiler
  disclosure/       # TNFD LEAP: leap_generator, leap_generator_v4, alignment_scorer
  discovery/        # Pattern detection, LLM detector, axiom candidates
  scenario/         # v6 NEW: constants, models, counterfactual_engine, climate_scenarios,
                    #          tipping_point_analyzer, blue_carbon_revenue, stress_test_engine,
                    #          real_options_valuator, scenario_parser
  semantica_bridge/ # SDK adapter: storage, axiom, provenance, integrity adapters
  services/ingestion/ # Modular ingestion: case_study_loader, concepts_loader, discovery
  settings.py       # Pydantic-based configuration (New)
  config.py         # Legacy wrapper around settings.py
  config_v4.py      # v4 dynamic site discovery wrapper

investor_demo/
  streamlit_app_v4.py               # v4: 9 sites, 6 tabs, $1.62B (:8504)
  streamlit_app_v3.py               # v3: 2 sites, 5 tabs (:8503)
  streamlit_app_v2.py               # v2: single-scroll (:8501)
  streamlit_app.py                  # v1: static mode
  api_client.py                     # HTTP client with TF-IDF fallback to precomputed
  precomputed_responses_v4.json     # 149 demo responses (9 sites, 7 query categories incl. scenario_analysis)
  precomputed_responses.json        # v3 fallback (63 queries)
  components/v4/                    # shared, portfolio_overview, intelligence_brief,
                                    # graphrag_chat, scenario_engine, site_intelligence,
                                    # tnfd_compliance
  components/v3/                    # shared, intelligence_brief, graphrag_chat,
                                    # scenario_engine, tnfd_compliance

scripts/
  populate_neo4j_v4.py    # 11-stage populator, auto-discovers examples/*_case_study.json
  enrich_obis.py          # OBIS enrichment: fetches biodiversity/quality/SST data for all 9 sites
  populate_neo4j.py       # Legacy 2-site populator (v2/v3)

tests/                    # 1265 tests (1057 unit + 208 integration, incl. 127 scenario + 6 OBIS enrichment)
tests/scenario/           # v6 NEW: phase A/B/C/D tests + test_scenario_invariants.py
scripts/
  generate_scenario_audit_bundle.py  # v6 NEW: generates 5 canonical scenario transcripts
docs/scenario_audit_bundle/           # v6 NEW: 5 canonical audit transcripts + README
launch.sh                 # Unified launcher
```

---

## Site Portfolio ($1.62B across 9 Gold-tier MPAs)

| Site | Country | Habitat | ESV | Rating |
|------|---------|---------|-----|--------|
| Cabo Pulmo National Park | Mexico | Coral reef | $29.27M | AAA |
| Shark Bay World Heritage Area | Australia | Seagrass | $21.5M | AA |
| Ningaloo Coast | Australia | Coral reef | $83.0M | AA |
| Belize Barrier Reef | Belize | Coral reef + mangrove | $292.5M | AA |
| Galapagos Marine Reserve | Ecuador | Mixed/volcanic | $320.9M | AAA |
| Raja Ampat MPA Network | Indonesia | Coral reef | $78.0M | AA |
| Sundarbans Reserve Forest | Bangladesh/India | Mangrove | $778.9M | A |
| Aldabra Atoll | Seychelles | Coral reef/atoll | $6.0M | AAA |
| Cispata Bay MPA | Colombia | Mangrove | $8.0M | A |

Comparison sites (GBR, Papahanaumokuakea): governance metadata only, no ESV.

**ESV data quality:** Each service has confidence intervals (+/-20% market-price, +/-30% avoided-cost, +/-50% regional analogue). Each source has a provenance tier (T1-T4) and provenance_summary per site.

**Cabo Pulmo reference:** ESV $29.27M (market-price), Tourism $25.0M, Biomass 4.63x CI [3.8, 5.5], NEOLI 4/5, Rating AAA.

---

## v4 Dashboard Tabs

| Tab | Content |
|-----|---------|
| Portfolio Overview | 9-site grid with ESV, rating, habitat, data quality badges, OBIS biodiversity column (species richness, IUCN threatened) |
| Intelligence Brief | Per-site KPIs, provenance chain, axiom evidence, CI ranges, Monte Carlo, OBIS data confidence banner |
| Ask Nereus (GraphRAG) | Split-panel chat + reasoning pipeline, 149 precomputed demo responses (incl. 15 scenario), scenario response block |
| Scenario Lab | 4 tabs: Climate Pathway (SSP selector + year slider), Counterfactual, Restoration ROI, Custom. McClanahan tipping point badges. Scenario Workbench (save/compare). OBIS observed baseline context block. |
| Site Intelligence | NEOLI heatmap, habitat-axiom map, data quality dashboard (incl. observation quality column), pipeline diagram, tipping point proximity panel, OBIS environmental profile |
| TNFD Compliance | LEAP disclosure for all 9 sites (incl. MT-A/MT-B biodiversity metrics from OBIS), alignment scoring, downloads |

---

## Key Technical Details

**Three-Layer Translation:** ECOLOGICAL DATA -> BRIDGE AXIOMS (40 rules: BA-001 to BA-040) -> FINANCIAL METRICS + FORWARD SCENARIOS

**Query classification (7 categories):** site_valuation, provenance_drilldown, axiom_explanation, comparison, risk_assessment, concept_explanation, scenario_analysis (v6 NEW). Site resolution via `_SITE_PATTERNS` in `classifier.py`. Scenario parsing via `maris/scenario/scenario_parser.py`.

**v6 Scenario Engine (maris/scenario/):**
- `counterfactual_engine.py` - protection removal delta (Cabo Pulmo -$20.16M validated)
- `climate_scenarios.py` - SSP1-2.6/SSP2-4.5/SSP5-8.5 degradation curves per habitat; enriched with observed SST baseline when available
- `tipping_point_analyzer.py` - McClanahan 4-threshold piecewise reef function
- `blue_carbon_revenue.py` - dynamic carbon pricing ($15-$65/tCO2e)
- `stress_test_engine.py` - portfolio Nature VaR (Cholesky-correlated Monte Carlo, VaR_95 $646.6M)
- `real_options_valuator.py` - conservation option value above static NPV
- `environmental_baselines.py` - OBIS SST baseline extraction; bleaching threshold proximity for coral reef sites
- `constants.py` - SSP_SCENARIOS, BIOMASS_THRESHOLDS, CARBON_PRICE_SCENARIOS (source DOIs)

**OBIS Biodiversity Integration (maris/sites/):**
- `biodiversity_metrics.py` - species richness, IUCN Red List counts (CR/EN/VU), TNFD MT-A/MT-B summaries from OBIS checklist API
- `observation_quality.py` - composite quality score (0-1) from record density, dataset diversity, QC pass rate, temporal coverage; feeds multiplicative confidence factor
- `api_clients.py` - OBISClient extended with 5 methods: `get_statistics`, `get_checklist_redlist`, `get_statistics_composition`, `get_statistics_qc`, `get_statistics_env`

**OBIS Enrichment Pipeline:**
- `scripts/enrich_obis.py` - standalone script to fetch live OBIS data for all 9 sites (--dry-run, --site, --force flags); writes biodiversity_metrics, observation_quality, environmental_baselines dicts into each case study JSON and 9 OBIS properties onto Neo4j MPA nodes
- Live data (2026-02-24): Aldabra 2,055 spp / quality 0.800; Galapagos 2,786 spp / quality 0.796; Sundarbans 611 spp / quality 0.692

**API auth:** Bearer token via `MARIS_API_KEY`. Bypassed with `MARIS_DEMO_MODE=true`. Rate limits: 30/min (query), 60/min (others).

**Graph schema:** 953+ nodes (Document 835, EcosystemService 39, Species 17, BridgeAxiom 40, MPA 11, Concept 15, TrophicLevel 10, Habitat 4, FinancialInstrument 3, Framework 3). 244+ relationships. MPA nodes carry 9 OBIS properties: `obis_species_richness`, `obis_iucn_threatened_count`, `obis_total_records`, `obis_observation_quality_score`, `obis_median_sst_c`, `obis_bleaching_proximity_c`, `obis_data_year_min`, `obis_data_year_max`, `obis_fetched_at`.

**Data lineage:** `scripts/populate_neo4j_v4.py` auto-discovers `examples/*_case_study.json` through 11-stage idempotent MERGE pipeline.

---

## Extending the System

- **New MPA site:** Create `examples/<name>_case_study.json`, run `python scripts/populate_neo4j_v4.py`
- **New bridge axiom:** Add to `schemas/bridge_axiom_templates.json` + `data/semantica_export/bridge_axioms.json`, re-run populator. (40 axioms now: BA-001 through BA-040)
- **New Concept node:** Add to `data/semantica_export/concepts.json`, update `classifier.py` patterns, re-run populator. (15 Concepts: BC-001 through BC-015)
- **New API endpoint:** Pydantic models in `models.py`, route in `routes/`, register in `main.py`

---

## Terminology Rules

- "NEOLI alignment" not "compliance"
- "market-price" not "NOAA-adjusted" for tourism
- No em dashes (use hyphens or " - ")
- ESV figures must reconcile: sum(services) == total per site, sum(sites) == portfolio aggregate

---

## Testing

```bash
pytest tests/ -v                    # All 1265 tests (1057 unit + 208 integration)
pytest tests/scenario/ -v           # Scenario-only suite (127 tests)
pytest tests/ --ignore=tests/integration -q  # Fast unit-only run (1057 tests, ~5s)
python scripts/generate_scenario_audit_bundle.py  # Regenerate 5 canonical audit transcripts
ruff check maris/ tests/            # Lint
```

CI: GitHub Actions (`.github/workflows/ci.yml`) - ruff + pytest on push/PR to main.
