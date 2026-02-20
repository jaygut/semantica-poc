# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

**Nereus** is a "Hybrid" Intelligence platform, powered by MARIS + Semantica. It creates auditable, **physically linked** pathways from peer-reviewed ecological science to investment-grade financial metrics. Unlike standard RAG, Nereus executes logic (axioms) extracted directly from literature.

**Current Status:** v5 Audit-Grade Integrity - **Fully Synchronized Payload** (35 Bridge Axioms). Built on the v4 Global Scaling Platform with Intelligence Upgrade. Neo4j knowledge graph (953+ nodes), 9 MPA sites, $1.62B ESV. Every financial claim is verified through deterministic provenance chains with DOI-backed evidence and validated confidence scoring.

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
  axioms/           # engine, confidence, monte_carlo, sensitivity
  ingestion/        # pdf_extractor, llm_extractor, embedding_generator, graph_merger
  provenance/       # W3C PROV-O: manager, bridge_axiom_registry, certificate, storage, doi_verifier, models
  sites/            # Multi-site: characterizer, esv_estimator, api_clients (OBIS/WoRMS)
  reasoning/        # Inference: context_builder, hybrid_retriever, rule_compiler
  disclosure/       # TNFD LEAP: leap_generator, leap_generator_v4, alignment_scorer
  discovery/        # Pattern detection, LLM detector, axiom candidates
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
  precomputed_responses_v4.json     # 73 demo responses (9 sites, 6 query categories)
  precomputed_responses.json        # v3 fallback (63 queries)
  components/v4/                    # shared, portfolio_overview, intelligence_brief,
                                    # graphrag_chat, scenario_engine, site_intelligence,
                                    # tnfd_compliance
  components/v3/                    # shared, intelligence_brief, graphrag_chat,
                                    # scenario_engine, tnfd_compliance

scripts/
  populate_neo4j_v4.py    # 11-stage populator, auto-discovers examples/*_case_study.json
  populate_neo4j.py       # Legacy 2-site populator (v2/v3)

tests/                    # 1020 tests (790+ unit + 230+ integration)
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
| Portfolio Overview | 9-site grid with ESV, rating, habitat, data quality badges |
| Intelligence Brief | Per-site KPIs, provenance chain, axiom evidence, CI ranges, Monte Carlo |
| Ask Nereus (GraphRAG) | Split-panel chat + reasoning pipeline, 73 precomputed demo responses |
| Scenario Lab | Monte Carlo with site-aware axiom chains, CI-driven parameter bounds |
| Site Intelligence | NEOLI heatmap, habitat-axiom map, data quality dashboard, pipeline diagram |
| TNFD Compliance | LEAP disclosure for all 9 sites, alignment scoring, downloads |

---

## Key Technical Details

**Three-Layer Translation:** ECOLOGICAL DATA -> BRIDGE AXIOMS (35 rules, expanded from 16) -> FINANCIAL METRICS

**Query classification (6 categories):** site_valuation, provenance_drilldown, axiom_explanation, comparison, risk_assessment, concept_explanation (NEW). Site resolution via `_SITE_PATTERNS` in `classifier.py`. Concept-based traversal for mechanism questions without site anchor.

**API auth:** Bearer token via `MARIS_API_KEY`. Bypassed with `MARIS_DEMO_MODE=true`. Rate limits: 30/min (query), 60/min (others).

**Graph schema:** 953+ nodes (Document 835, EcosystemService 39, Species 17, BridgeAxiom 35, MPA 11, Concept 15 NEW, TrophicLevel 10, Habitat 4, FinancialInstrument 3, Framework 3). 244+ relationships (added INVOLVES_AXIOM, RELEVANT_TO, DOCUMENTED_BY for concepts).

**Data lineage:** `scripts/populate_neo4j_v4.py` auto-discovers `examples/*_case_study.json` through 11-stage idempotent MERGE pipeline.

---

## Extending the System

- **New MPA site:** Create `examples/<name>_case_study.json`, run `python scripts/populate_neo4j_v4.py`
- **New bridge axiom:** Add to `schemas/bridge_axiom_templates.json` + `data/semantica_export/bridge_axioms.json`, re-run populator. (35 axioms now: BA-001 through BA-035)
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
pytest tests/ -v                    # All 1020 tests
ruff check maris/ tests/            # Lint
```

CI: GitHub Actions (`.github/workflows/ci.yml`) - ruff + pytest on push/PR to main.
