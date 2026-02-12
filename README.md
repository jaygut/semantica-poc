# Semantica × MARIS POC

**Marine Asset Risk Intelligence System** — Translating ecological complexity into investment-grade natural capital assets.  
**Built on Semantica Framework** — All operations (extraction, graph construction, queries) powered by Semantica.  
**Blue Natural Capital Knowledge Engineering** — Where ocean science meets investment intelligence.

[![Status](https://img.shields.io/badge/Status-Library%20Complete-brightgreen)]()
[![Papers](https://img.shields.io/badge/Literature-195%20Papers-green)]()
[![Evidence](https://img.shields.io/badge/T1%20Sources-92%25-brightgreen)]()
[![Abstracts](https://img.shields.io/badge/Abstracts-67%25-yellow)]()
[![Axioms](https://img.shields.io/badge/Bridge%20Axioms-12%2F12-brightgreen)]()

---

## Executive Summary

This repository contains the **complete knowledge foundation** for a proof-of-concept knowledge graph system that bridges marine ecological science with blue finance frameworks. The goal: enable investors, asset managers, and conservation organizations to make data-driven decisions about marine natural capital with full scientific provenance.

**Current Status:** The document library reconstruction is complete with **195 verified papers**, **5 critical paper extractions**, and a **Semantica-ready export bundle** containing 14 entities, 15 relationships, and 12 fully-evidenced bridge axioms. A **live MARIS v2 system** (Neo4j knowledge graph + FastAPI query engine + Streamlit dashboard) demonstrates the full end-to-end pipeline: natural language questions are classified, translated to Cypher, executed against the graph, and answered with full provenance and interactive graph visualization. The system also runs in static mode from a pre-computed JSON bundle for zero-downtime investor demos. The API is secured with Bearer token authentication and rate limiting, and the codebase is validated by a 177-test suite with CI via GitHub Actions.

**Implementation Timeline:** **8 weeks** - This POC follows a compressed 8-week implementation schedule focused on **Semantica integration** for entity extraction, relationship extraction, graph construction, and GraphRAG query execution. See [Implementation Roadmap](#implementation-roadmap) for detailed week-by-week breakdown.

**The Problem:** A $175B annual funding gap exists for ocean conservation. Investors can't trust opaque ecological claims. Scientists can't translate their findings into financial terms. The result: capital doesn't flow to where it's needed.

**The Solution:** MARIS — a knowledge graph **built entirely on Semantica framework** that creates auditable, traceable pathways from peer-reviewed ecological data to investment-grade financial metrics. Semantica serves as the core platform for entity extraction, relationship extraction, graph construction, and GraphRAG query execution.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              THE TRUST BRIDGE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ECOLOGICAL DATA          BRIDGE AXIOMS           FINANCIAL METRICS        │
│   ───────────────          ────────────           ─────────────────        │
│   • Fish biomass     →     BA-001: Tourism        → Blue bond KPIs          │
│   • Trophic networks →     BA-003: Carbon         → Credit pricing          │
│   • MPA effectiveness →    BA-002: Recovery       → Asset ratings           │
│   • Habitat condition →    BA-004: Protection     → Insurance premiums      │
│                                                                             │
│   Every claim traceable to DOI + page number + direct quote                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Table of Contents

- [Quick Start for Semantica Integration](#quick-start-for-semantica-integration)
- [Semantica Export Bundle](#semantica-export-bundle)
- [Architecture Overview](#architecture-overview)
- [Repository Structure](#repository-structure)
- [The Three-Layer Model](#the-three-layer-model)
- [Bridge Axioms](#bridge-axioms)
- [Entity & Relationship Schemas](#entity--relationship-schemas)
- [Document Library](#document-library)
- [Reference Case: Cabo Pulmo](#reference-case-cabo-pulmo)
- [Sample Queries](#sample-queries)
- [Implementation Roadmap](#implementation-roadmap)
- [Success Criteria](#success-criteria)
- [Key Files Reference](#key-files-reference)

---

## Quick Start for Semantica Integration

### Priority Files (Read First)

| Priority | File | Purpose |
|----------|------|---------|
| 1 | [`data/semantica_export/entities.jsonld`](./data/semantica_export/entities.jsonld) | 14 entities with JSON-LD context (WoRMS, FishBase, TNFD) |
| 2 | [`data/semantica_export/relationships.json`](./data/semantica_export/relationships.json) | 15 typed relationships with provenance |
| 3 | [`data/semantica_export/bridge_axioms.json`](./data/semantica_export/bridge_axioms.json) | 12 bridge axioms with 3+ evidence sources each |
| 4 | [`data/semantica_export/document_corpus.json`](./data/semantica_export/document_corpus.json) | 195-paper corpus summary |
| 5 | [`data/sample_extractions/`](./data/sample_extractions/) | 5 critical paper extractions |

### Day 1 Tasks

```bash
# 1. Ingest the MARIS export bundle
semantica ingest data/semantica_export/entities.jsonld
semantica ingest data/semantica_export/relationships.json
semantica ingest data/semantica_export/bridge_axioms.json

# 2. Index the document corpus
semantica index data/semantica_export/document_corpus.json

# 3. Test a validation query
semantica query "What ecological factors explain Cabo Pulmo's 463% recovery?"

# 4. Validate bridge axiom BA-002 (no-take → biomass)
semantica validate --axiom BA-002 --site cabo_pulmo
```

### Environment Setup (Recommended: uv)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a virtual env and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -e .

# Optional dev tooling
uv pip install -e ".[dev]"
```

Pip fallback:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### End-to-End Pipeline (Search → Registry → PDFs)

```bash
# 0. Review/update the tracked keyword matrix
#    data/keywords/search_keywords.md

# 1. Search literature by domain and update registry
python scripts/search_literature.py trophic --depth deep --tiers T1,T2 --update-registry --min-year 2018

# 2. Validate registry integrity
python scripts/validate_registry.py

# 2b. Purge asset-like entries (figures/tables/supplements) from registry
python scripts/purge_registry_assets.py --apply

# 3. Fetch validated PDFs (strict content checks, capped to 250 for now)
python scripts/fetch_pdfs_batch.py \
  --max-docs 250 --tiers T1,T2,T3,T4 --workers 6 --delay-s 0.4 \
  --min-text-chars 2000 --check-pages 5 --min-year 2018

# 3b. Normalize cached PDF filenames based on PDF signals (optional)
python scripts/normalize_pdf_filenames.py \
  --min-text-chars 2000 --check-pages 5 --apply

# 4. Validate and clean the PDF cache
python scripts/validate_pdf_cache.py \
  --delete-invalid --delete-html --min-text-chars 2000 --check-pages 5 --update-registry
```

### PDF Cache (Validated)

Build a local PDF cache for downstream ingestion with strict validation:
- PDF header check
- Text extractable (non-scanned) content with a high minimum text threshold
- Content match to registry (title match preferred; DOI fallback)
- Access notice detection (login/download notices rejected)

```bash
# Optional: clear existing cache
rm -f data/papers/*.pdf data/papers/*.html

# Fetch PDFs for the registry (strict validation enabled by default; cap 250)
python scripts/fetch_pdfs_batch.py \
  --max-docs 250 --tiers T1,T2,T3,T4 --workers 6 --delay-s 0.4 \
  --min-text-chars 2000 --check-pages 5 --min-year 2018

# Validate cache and remove invalid/mismatched files (optionally sync registry)
python scripts/validate_pdf_cache.py \
  --delete-invalid --delete-html --min-text-chars 2000 --check-pages 5 --update-registry
```

Search results are written to `data/search_results/<domain>_<timestamp>.json` with metadata
(keywords path, tiers, sources, and queries).
The search runner skips obvious non-article assets (figure/table/supplement titles or
DOI patterns), plus entries missing both authors and year, to avoid junk doc IDs.
If source tier helpers are unavailable, `search_literature.py` defaults `source_tier` to `T1`
so results are not dropped; use `--verify` with the helper to compute real tiers.
Both search and fetch default to `--min-year 2018`; use `--allow-missing-year` to include
entries with unknown years.
Fetch also skips asset-like entries in the registry to avoid downloading figures/tables.

PDF reports are written to `data/pdf_registry.json` and `data/pdf_cache_report.json`.
Filename normalization report is written to `data/pdf_filename_report.json`.
Run manifests are written to `data/run_manifests/`.
Registry purge report is written to `data/registry_purge_report.json`.

Tuning knobs:
- `--title-match-ratio` (default 0.6): raise for stricter title alignment
- `--min-text-chars`: raise to filter short notices or cover pages
- `--allow-mismatch` / `--allow-non-text`: debugging only (not recommended)
- `--no-update-registry`: skip writing `pdf_cache` back to the registry

### Data Outputs & Cleanup

Safe to delete (derived artifacts, regenerated by the pipeline):
- `data/papers/` (PDF cache)
- `data/search_results/` (search outputs)
- `data/pdf_registry.json`
- `data/pdf_cache_report.json`
- `data/fetch_report.json`
- `data/fetch_quality_report.tsv`
- `data/pdf_filename_report.json`
- `data/run_manifests/`
- `data/registry_purge_report.json`

Keep (inputs and ground truth for reproducibility):
- `data/keywords/search_keywords.md` (search matrix)
- `data/semantica_export/` (Semantica-ready bundle)
- `data/sample_extractions/` (gold extracts)
- `data/document_manifest.json`

### Critical Papers ✅ EXTRACTED

| Paper | Why Critical | Target Axioms | Status |
|-------|--------------|---------------|--------|
| Edgar et al. 2014 | NEOLI framework (MPA effectiveness) | BA-002 | ✅ Extracted |
| Aburto-Oropeza et al. 2011 | Cabo Pulmo recovery data | BA-001, BA-002, BA-011 | ✅ Extracted |
| Costanza et al. 2014 | Global ES valuation methods | BA-005, BA-006 | ✅ Extracted |
| Hopf et al. 2024 | No-take MPA biomass multipliers | BA-002 | ✅ Extracted |
| Beck et al. 2018 | Coral reef flood protection | BA-004 | ✅ Extracted |

---

## Semantica Export Bundle

The MARIS pipeline generates a **Semantica-ready export bundle** designed for direct ingestion into [Semantica](https://github.com/Hawksight-AI/semantica) — an open-source framework that transforms unstructured data into validated, explainable, and auditable knowledge.

### How MARIS Fits Into Semantica

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MARIS → SEMANTICA INTEGRATION FLOW                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   MARIS PIPELINE                        SEMANTICA                           │
│   ══════════════                        ═════════                           │
│                                                                             │
│   ┌──────────────────┐                  ┌──────────────────────┐           │
│   │ Document Library │ ──────────────→  │ Document Ingestion   │           │
│   │ (195 papers)     │  corpus.json     │ (Parse + Index)      │           │
│   └──────────────────┘                  └──────────────────────┘           │
│                                                    ↓                        │
│   ┌──────────────────┐                  ┌──────────────────────┐           │
│   │ Entity Schema    │ ──────────────→  │ Ontology Builder     │           │
│   │ (14 entities)    │  entities.jsonld │ (Type + Validate)    │           │
│   └──────────────────┘                  └──────────────────────┘           │
│                                                    ↓                        │
│   ┌──────────────────┐                  ┌──────────────────────┐           │
│   │ Relationships    │ ──────────────→  │ Graph Construction   │           │
│   │ (15 edges)       │  relationships   │ (Link + Infer)       │           │
│   └──────────────────┘                  └──────────────────────┘           │
│                                                    ↓                        │
│   ┌──────────────────┐                  ┌──────────────────────┐           │
│   │ Bridge Axioms    │ ──────────────→  │ Inference Engine     │           │
│   │ (12 axioms)      │  bridge_axioms   │ (Translate + Query)  │           │
│   └──────────────────┘                  └──────────────────────┘           │
│                                                    ↓                        │
│                                         ┌──────────────────────┐           │
│                                         │ GraphRAG Interface   │           │
│                                         │ (Answer + Cite)      │           │
│                                         └──────────────────────┘           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Export Files

Located in `data/semantica_export/`:

| File | Format | Contents | Semantica Use |
|------|--------|----------|---------------|
| `entities.jsonld` | JSON-LD | 14 entities with WoRMS/FishBase/TNFD URIs | Ontology ingestion |
| `relationships.json` | JSON | 15 typed relationships with provenance | Graph construction |
| `bridge_axioms.json` | JSON | 12 axioms with 3+ evidence sources each | Inference rules |
| `document_corpus.json` | JSON | 195-paper corpus summary | Retrieval index |

### Entity Types in Export

```json
{
  "@context": {
    "worms": "http://www.marinespecies.org/aphia.php?p=taxdetails&id=",
    "fishbase": "https://www.fishbase.org/summary/",
    "tnfd": "https://tnfd.global/",
    "seea": "https://seea.un.org/"
  }
}
```

| Type | Count | Examples |
|------|-------|----------|
| Concept | 1 | NEOLI Criteria |
| MarineProtectedArea | 1 | Cabo Pulmo National Park |
| Species | 2 | *Lutjanus argentiventris*, *Mycteroperca rosacea* |
| EcosystemService | 2 | Flood protection, Coastal wetland services |
| Habitat | 4 | Coral reef, Kelp forest, Seagrass, Mangrove |
| FinancialInstrument | 2 | Blue bond, Parametric reef insurance |
| Framework | 2 | TNFD LEAP, SEEA Ecosystem Accounting |

### Bridge Axiom Evidence

All 12 bridge axioms now have **3+ supporting sources**:

| Axiom | Name | Sources | Key Paper |
|-------|------|---------|-----------|
| BA-001 | Biomass-Tourism Value | 3 | Sala 2021 |
| BA-002 | No-take MPA Biomass Multiplier | 4 | Edgar 2014 |
| BA-003 | Otter-Kelp-Carbon Cascade | 3 | Wilmers 2012 |
| BA-004 | Reef Coastal Protection | 3 | Beck 2018 |
| BA-005 | Mangrove Flood Protection | 3 | Menendez 2020 |
| BA-006 | Ecosystem Service Unit Values | 3 | Costanza 2014 |
| BA-007 | Mangrove Carbon Stock | 3 | Donato 2011 |
| BA-008 | Seagrass Carbon Sequestration | 3 | Fourqurean 2012 |
| BA-009 | Connectivity MPA Effectiveness | 3 | Green 2015 |
| BA-010 | Thermal Tolerance Resilience | 3 | Lachs 2023 |
| BA-011 | Fisheries Spillover | 3 | Aburto 2011 |
| BA-012 | Disclosure Biodiversity Dependency | 3 | TNFD 2023 |

### Ingesting Into Semantica

```bash
# 1. Clone Semantica
git clone https://github.com/Hawksight-AI/semantica.git
cd semantica

# 2. Load the MARIS export bundle
semantica ingest ../semantica-poc/data/semantica_export/entities.jsonld
semantica ingest ../semantica-poc/data/semantica_export/relationships.json
semantica ingest ../semantica-poc/data/semantica_export/bridge_axioms.json

# 3. Index the document corpus
semantica index ../semantica-poc/data/semantica_export/document_corpus.json

# 4. Validate with a test query
semantica query "What explains Cabo Pulmo's biomass recovery?" --cite
```

---

## MARIS v2 - Live Query System

The v2 layer adds a **live knowledge graph and query engine** on top of the curated knowledge foundation. Users can ask natural-language questions and receive grounded answers with interactive provenance visualization.

### Architecture

```
User Question (NL)
        |
   [Classifier]  -- keyword-first, LLM fallback
        |
   [Cypher Template]  -- 8 parameterized templates (5 core + 3 utility)
        |
   [Neo4j Graph]  -- 878 nodes, 101 relationships
        |
   [LLM Synthesis]  -- DeepSeek/Claude/GPT-4 (configurable)
        |
   Answer + Evidence + Provenance Graph
```

**Stack:** Neo4j Community 5.x + FastAPI + Streamlit + OpenAI-compatible LLM

### Prerequisites

- **Python 3.11+** with `uv` (recommended) or `pip`
- **Neo4j** - either [Neo4j Desktop](https://neo4j.com/download/) or Docker
- **LLM API key** - DeepSeek (default), Claude, or OpenAI

### Environment Setup

```bash
# 1. Copy the environment template and fill in your credentials
cp .env.example .env
# Edit .env: set MARIS_LLM_API_KEY and MARIS_API_KEY

# 2. Install dependencies
uv venv .venv && source .venv/bin/activate
uv pip install -r requirements-v2.txt
```

> **Security:** The `.env` file contains your API keys and is excluded from git via `.gitignore`. Never commit `.env` - use `.env.example` as the template. Key variables: `MARIS_LLM_API_KEY` (LLM provider), `MARIS_API_KEY` (API Bearer token), `MARIS_CORS_ORIGINS` (allowed origins, default `http://localhost:8501`).

### Quick Start (Manual)

```bash
# 1. Start Neo4j (via Desktop or Docker)
# Default: bolt://localhost:7687, user: neo4j, password: maris-dev

# 2. Populate the knowledge graph
python scripts/populate_neo4j.py

# 3. Start the API server
uvicorn maris.api.main:app --host 0.0.0.0 --port 8000

# 4. Start the dashboard (in a separate terminal)
cd investor_demo
streamlit run streamlit_app_v2.py
```

### Quick Start (Docker Compose)

```bash
cp .env.example .env
# Edit .env: set MARIS_LLM_API_KEY and MARIS_API_KEY

docker-compose up
# Neo4j: http://localhost:7474
# API:   http://localhost:8000
# Dashboard: http://localhost:8501
```

### API Endpoints

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/health` | No | System health, Neo4j connectivity, graph stats |
| POST | `/api/query` | Yes | Natural-language query with provenance |
| GET | `/api/site/{name}` | Yes | Full site valuation with evidence |
| GET | `/api/axiom/{id}` | Yes | Bridge axiom details and sources |
| POST | `/api/compare` | Yes | Compare multiple sites |
| POST | `/api/graph/traverse` | Yes | Multi-hop graph traversal |
| GET | `/api/graph/node/{id}` | Yes | Single node with relationships |

### Query Categories

The classifier routes questions to parameterized Cypher templates:

| Category | Triggers | Example |
|----------|----------|---------|
| `site_valuation` | value, worth, ESV, asset rating | "What is Cabo Pulmo worth?" |
| `provenance_drilldown` | evidence, source, DOI, research | "What evidence backs the ESV?" |
| `axiom_explanation` | bridge axiom, BA-001, coefficient | "Explain BA-002" |
| `comparison` | compare, versus, rank | "Compare to other sites" |
| `risk_assessment` | risk, climate, threat, decline | "What if protection fails?" |

### Authentication and Security

All endpoints except `/api/health` require a Bearer token via the `Authorization` header:

```
Authorization: Bearer <MARIS_API_KEY>
```

Authentication is implemented in `maris/api/auth.py`. When `MARIS_DEMO_MODE=true`, authentication is bypassed for development and demos.

**Rate Limiting:** In-memory sliding-window rate limiting is applied per API key:
- `/api/query`: 30 requests per minute
- All other endpoints: 60 requests per minute

Exceeding the limit returns HTTP 429. Rate limit headers are included in responses. CORS origins are configured via `MARIS_CORS_ORIGINS`. Request tracing logs hashed IP addresses for auditability.

### Testing

The project includes 177 tests covering all core modules:

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=maris --cov-report=term-missing
```

Tests are organized by module in `tests/` with shared fixtures in `conftest.py`. CI runs automatically on push and PR to `main` via GitHub Actions (`.github/workflows/ci.yml`): linting with ruff, then pytest.

---

## Architecture Overview

**Core Framework:** MARIS is built entirely on **Semantica** as the foundational platform for all operations:
- **Entity Extraction** → Semantica API
- **Relationship Extraction** → Semantica API  
- **Graph Construction** → Semantica graph database
- **Query Execution** → Semantica GraphRAG
- **Bridge Axioms** → Semantica inference rules

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MARIS SYSTEM ARCHITECTURE                           │
│                    (Built on Semantica Framework)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  LITERATURE │    │   ENTITY    │    │  KNOWLEDGE  │    │   GRAPHRAG  │  │
│  │   LIBRARY   │ →  │ EXTRACTION  │ →  │    GRAPH    │ →  │   QUERIES   │  │
│  │  (195 T1/T2)│    │ (Semantica) │    │ (Semantica) │    │ (Semantica) │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│        ↓                  ↓                  ↓                  ↓          │
│   document_index    sample_extractions   entity_schema    sample_queries   │
│   (Semantica        (Semantica API)      (Semantica       (Semantica       │
│    document index)                       schema)          GraphRAG)        │
│                                          relationship     cabo_pulmo       │
│                                          bridge_axioms    demo_narrative   │
│                                          (Semantica       (Semantica       │
│                                           inference)      queries)        │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                              DATA FLOW                                      │
│                    (All operations via Semantica)                          │
│                                                                             │
│   Papers → Entities → Relationships → Bridge Axioms → Financial Outputs    │
│     ↓          ↓           ↓              ↓                ↓               │
│   DOIs     Species     PREYS_ON      Biomass→$        Bond KPIs            │
│   URLs     Habitats    PROVIDES      Carbon→$         TNFD Fields          │
│   Quotes   MPAs        FUNDS         Tourism→$        Credit Prices        │
│                                                                             │
│   All extraction, graph construction, and queries executed via Semantica    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Components (All Integrated with Semantica)

| Component | Location | Format | Purpose | Semantica Integration |
|-----------|----------|--------|---------|----------------------|
| **Entities** | `data/semantica_export/entities.jsonld` | JSON-LD | 14 entities with WoRMS/FishBase/TNFD URIs | Ingested via Semantica API |
| **Relationships** | `data/semantica_export/relationships.json` | JSON | 15 relationship types with provenance | Ingested via Semantica API |
| **Bridge Axioms** | `data/semantica_export/bridge_axioms.json` | JSON | 12 axioms with 3+ evidence sources each | Registered as Semantica inference rules |
| **Corpus Summary** | `data/semantica_export/document_corpus.json` | JSON | 195-paper library statistics | Indexed in Semantica document index |
| Document Library | `.claude/registry/document_index.json` | JSON | 195 indexed papers with full metadata | Indexed via Semantica API |
| Critical Extractions | `data/sample_extractions/` | JSON | 5 papers with entities/relationships | Extracted via Semantica API |
| Reference Case | `examples/cabo_pulmo_case_study.json` | JSON | AAA-rated validation site | Validated via Semantica queries |
| Query Templates | `examples/sample_queries.md` | Markdown | 11 GraphRAG query examples | Executed via Semantica GraphRAG |

---

## Repository Structure

```
semantica-poc/
│
├── README.md                              # This file
├── CLAUDE.md                              # Claude Code instructions
├── SEMANTICA_HANDOFF_README.md            # Integration guide
├── .env.example                           # Environment template (copy to .env)
├── docker-compose.yml                     # One-command deployment (Neo4j + API + Dashboard)
├── requirements-v2.txt                    # Python dependencies for v2 stack
│
├── maris/                                 # ═══ MARIS v2 BACKEND ═══
│   ├── api/                               # FastAPI application
│   │   ├── main.py                        # App factory, CORS, router registration
│   │   ├── models.py                      # Pydantic request/response schemas
│   │   ├── auth.py                        # Bearer token auth, rate limiting, request tracing
│   │   └── routes/                        # /health, /query, /graph endpoints
│   ├── graph/                             # Neo4j integration
│   │   ├── connection.py                  # Driver + session pooling
│   │   ├── schema.py                      # Constraints and indexes
│   │   ├── population.py                  # Populate from curated JSON assets
│   │   └── validation.py                  # Post-population checks
│   ├── query/                             # NL-to-Cypher pipeline
│   │   ├── classifier.py                  # Intent detection (keyword + LLM)
│   │   ├── cypher_templates.py            # 8 parameterized Cypher templates
│   │   ├── executor.py                    # Template execution + provenance edges
│   │   ├── generator.py                   # LLM response synthesis
│   │   ├── formatter.py                   # Evidence normalization
│   │   └── validators.py                  # LLM response validation, claim verification, DOI checks
│   ├── axioms/                            # Bridge axiom engine + sensitivity analysis
│   ├── llm/                               # OpenAI-compatible LLM adapter
│   ├── ingestion/                         # PDF extraction + graph merging
│   └── config.py                          # Centralized env-based configuration
│
├── investor_demo/                         # ═══ STREAMLIT DASHBOARD ═══
│   ├── streamlit_app_v2.py                # v2 dashboard (live API + static bundle)
│   ├── streamlit_app.py                   # v1 dashboard (static bundle only)
│   ├── components/
│   │   ├── chat_panel.py                  # Ask MARIS query interface
│   │   └── graph_explorer.py              # Interactive provenance visualization
│   ├── api_client.py                      # HTTP client for MARIS API
│   ├── precomputed_responses.json         # Fallback responses for demo mode
│   └── README.md                          # Dashboard architecture and usage
│
├── schemas/                               # ═══ INGEST THESE FIRST ═══
│   ├── entity_schema.json                 # 8 entity types (JSON-LD)
│   ├── relationship_schema.json           # 14 relationship types
│   └── bridge_axiom_templates.json        # 12 translation rules
│
├── data/
│   ├── semantica_export/                  # ═══ SEMANTICA-READY BUNDLE ═══
│   │   ├── entities.jsonld                # 14 entities (JSON-LD)
│   │   ├── relationships.json             # 15 relationships
│   │   ├── bridge_axioms.json             # 12 axioms with evidence
│   │   └── document_corpus.json           # Corpus summary
│   └── sample_extractions/                # 5 critical paper extractions
│
├── scripts/
│   ├── populate_neo4j.py                  # Graph population (schema + data)
│   ├── demo_healthcheck.py                # Pre-demo system verification
│   ├── validate_graph.py                  # Post-population integrity checks
│   └── run_ingestion.py                   # PDF ingestion pipeline
│
├── tests/                                # ═══ TEST SUITE (177 tests) ═══
│   ├── conftest.py                        # Shared fixtures
│   ├── test_api_endpoints.py              # API route tests with auth validation
│   ├── test_bridge_axioms.py              # Bridge axiom computation tests
│   ├── test_cabo_pulmo_validation.py      # Cabo Pulmo reference data integrity
│   ├── test_classifier.py                 # Query classification accuracy
│   ├── test_confidence.py                 # Composite confidence model tests
│   ├── test_cypher_templates.py           # Template parameterization and LIMIT tests
│   ├── test_entity_extraction.py          # Entity extraction pipeline tests
│   ├── test_integration.py                # End-to-end pipeline integration tests
│   ├── test_monte_carlo.py                # Monte Carlo simulation tests
│   ├── test_population.py                 # Graph population pipeline tests
│   ├── test_query_engine.py               # Query execution and response formatting
│   ├── test_relationship_extraction.py    # Relationship extraction tests
│   └── test_validators.py                 # LLM response validation tests
│
├── demos/context_graph_demo/
│   ├── cabo_pulmo_investment_grade.ipynb   # Investment-grade analysis notebook
│   └── cabo_pulmo_investment_grade_bundle.json  # Exported data bundle
│
├── docs/
│   ├── api_reference.md                   # FastAPI endpoint reference
│   ├── developer_guide.md                 # Development setup and patterns
│   └── user_guide.md                      # End-user query guide
│
└── examples/
    ├── cabo_pulmo_case_study.json         # AAA reference (validation target)
    └── sample_queries.md                  # 11 GraphRAG query templates
```

---

## The Three-Layer Model

MARIS operates on a **three-layer translation model** that converts ecological measurements into financial metrics through explicit, auditable bridge axioms.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   LAYER 1: ECOLOGICAL FOUNDATIONS                                          │
│   ════════════════════════════════                                          │
│   Entities: Species, Habitat, MarineProtectedArea, Observation              │
│   Metrics:  Biomass (kg/ha), Species richness, Trophic level               │
│   Sources:  FishBase, WoRMS, OBIS, GloBI, field surveys                    │
│                                                                             │
│                              ↓ BRIDGE AXIOMS ↓                              │
│                                                                             │
│   LAYER 2: ECOSYSTEM SERVICES                                              │
│   ═══════════════════════════                                              │
│   Entities: EcosystemService (provisioning, regulating, cultural)          │
│   Metrics:  Fish yield (tonnes/yr), Carbon stock (Mg C/ha), Visitor-days   │
│   Sources:  TEEB, SEEA-EA, regional valuations                             │
│                                                                             │
│                          ↓ TRANSLATION PIPELINES ↓                          │
│                                                                             │
│   LAYER 3: FINANCIAL INSTRUMENTS                                           │
│   ══════════════════════════════                                           │
│   Entities: FinancialInstrument, DisclosureFramework                       │
│   Outputs:  Blue bond KPIs, TNFD disclosures, Credit prices, AQR ratings   │
│   Standards: TNFD, ESRS E4, SEEA-EA, SBTN                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Layer Details

| Layer | Entity Types | Key Metrics | External Standards |
|-------|--------------|-------------|-------------------|
| **L1: Ecological** | Species, Habitat, MPA, Observation | Biomass, richness, trophic level, NEOLI score | WoRMS, FishBase, WDPA |
| **L2: Services** | EcosystemService | $/ha/yr valuation, carbon stock, visitor-days | TEEB, SEEA-EA |
| **L3: Financial** | FinancialInstrument, DisclosureFramework | Bond yields, credit prices, risk ratings | TNFD, ESRS E4, SBTN |

---

## Bridge Axioms

Bridge axioms are the **core innovation** — explicit, quantified rules that translate ecological states into financial values. Each axiom has:

- **Antecedent**: Ecological condition (measurable)
- **Consequent**: Financial implication (calculable)
- **Confidence**: Evidence strength (HIGH/MEDIUM/LOW)
- **Provenance**: Source papers with DOI + page references

### The 12 Core Axioms

| ID | Name | Translation | Confidence |
|----|------|-------------|------------|
| **BA-001** | Biomass-Tourism | Fish biomass → Tourism revenue (elasticity: 0.346) | HIGH |
| **BA-002** | Protection-Recovery | No-take MPA → 6-7× biomass multiplier | HIGH |
| **BA-003** | Otter-Kelp-Carbon | Sea otter presence → Kelp carbon sequestration | HIGH |
| **BA-004** | Reef-Protection | Coral condition → Coastal flood protection value | HIGH |
| **BA-005** | Mangrove-Flood | Mangrove extent → $65B/yr global protection | HIGH |
| **BA-006** | Mangrove-Fisheries | Mangrove → Fisheries yield enhancement | MEDIUM |
| **BA-007** | Mangrove-Carbon | Mangrove → 1,061 Mg C/ha stock | HIGH |
| **BA-008** | Seagrass-Credits | Seagrass → $198-$15,337/ha credit value | MEDIUM |
| **BA-009** | Restoration-ROI | Restoration investment → 6-15× benefit-cost ratio | HIGH |
| **BA-010** | Kelp-Services | Kelp forest → $500B/yr global services | MEDIUM |
| **BA-011** | MPA-Resilience | MPA network → Climate resilience buffer | MEDIUM |
| **BA-012** | Structure-Fisheries | Reef structural complexity → +35% fisheries productivity | HIGH |

### Example: BA-001 in Action

```json
{
  "axiom_id": "BA-001",
  "name": "biomass_tourism_elasticity",
  "antecedent": {
    "metric": "fish_biomass_kg_ha",
    "condition": "INCREASE",
    "magnitude": "1%"
  },
  "consequent": {
    "metric": "tourism_revenue_usd",
    "effect": "INCREASE",
    "magnitude": "0.346%"
  },
  "evidence": {
    "primary_source": "Sala et al. 2021",
    "doi": "10.1038/s41586-021-03371-z",
    "page": "Table S4",
    "quote": "A 1% increase in fish biomass is associated with a 0.346% increase in tourism revenue"
  },
  "confidence": "HIGH",
  "applicability": ["coral_reef", "tropical_mpa"]
}
```

---

## Entity & Relationship Schemas

### Entity Types (8)

All entities use **JSON-LD** format with external identifier linking.

| Entity | Key Properties | External IDs |
|--------|---------------|--------------|
| `Species` | scientific_name, trophic_level, functional_group | WoRMS AphiaID, FishBase speccode |
| `Habitat` | habitat_type, condition_score, carbon_potential | EUNIS code |
| `MarineProtectedArea` | neoli_criteria, effectiveness_rating, area_km2 | WDPA ID |
| `EcosystemService` | service_type, valuation_usd_ha_yr, evidence_tier | CICES code |
| `FinancialInstrument` | instrument_type, kpis, verification_standard | ISIN (if applicable) |
| `DisclosureFramework` | framework_name, required_metrics, update_frequency | — |
| `Observation` | value, unit, methodology, timestamp | — |
| `BridgeAxiom` | antecedent, consequent, confidence, provenance | — |

### Relationship Types (14)

| Category | Relationships |
|----------|--------------|
| **Ecological** | `PREYS_ON`, `CONTROLS_VIA_CASCADE`, `HABITAT_OF`, `CONNECTED_TO`, `INDICATOR_OF` |
| **Service** | `PROVIDES_SERVICE`, `DEPENDS_ON`, `QUANTIFIED_BY` |
| **Financial** | `INFORMS_INSTRUMENT`, `FUNDED_BY`, `REPORTS_TO`, `TRANSLATES_TO` |
| **Provenance** | `DERIVED_FROM`, `SUPPORTS_CLAIM`, `AGGREGATED_FROM` |

### Inference Rules

The schema includes inference rules for multi-hop reasoning:

```json
{
  "rule_id": "transitive_cascade",
  "description": "If A controls B via cascade and B provides service C, then A enables C",
  "pattern": "(a)-[:CONTROLS_VIA_CASCADE]->(b)-[:PROVIDES_SERVICE]->(c)",
  "inference": "(a)-[:ENABLES_SERVICE {indirect: true}]->(c)"
}
```

---

## Document Library

### Composition (Verified 2026-01-24)

```
Total Papers:        195
Evidence Quality:    92% T1 (peer-reviewed), 5% T2 (institutional), 3% T3 (data)
DOI Coverage:        90.3% (176/195)
Abstract Coverage:   67.2% (131/195)

By Domain:
├── MPA Effectiveness    42 papers   (NEOLI, reserve outcomes, biomass)
├── Trophic Ecology      35 papers   (food webs, cascades, keystone species)
├── Ecosystem Services   32 papers   (valuation methods)
├── Blue Carbon          28 papers   (sequestration, stocks)
├── Climate Resilience   25 papers   (thermal tolerance, refugia)
├── Restoration          24 papers   (coral, kelp, seagrass, mangrove)
├── Connectivity         22 papers   (larval dispersal, MPA networks)
├── Methods & Data       20 papers   (eDNA, acoustic, satellite)
├── Blue Finance         18 papers   (bonds, credits, mechanisms)
└── Disclosure           12 papers   (TNFD, ESRS, SEEA)

By Habitat:
├── Coral Reef           45 papers
├── Kelp Forest          28 papers
├── Mangrove             25 papers
├── Seagrass             22 papers
└── General/Multiple     75 papers
```

### Evidence Tier System

| Tier | Classification | Count | Usage |
|------|----------------|-------|-------|
| **T1** | Peer-reviewed journals | 179 | Cite without qualification |
| **T2** | Institutional reports (World Bank, UN, IPBES, TNFD) | 10 | Cite with context |
| **T3** | Data repositories (GBIF, OBIS, FishBase) | 6 | Cite with methodology |
| **T4** | Preprints/grey literature | 0 | Cite with caveats |

---

## Registry Spec & Ingestion Agreement

This registry is the ingestion contract for Semantica. It is the single source of truth for document metadata and retrieval.

**Registry file:** `.claude/registry/document_index.json`

**Fetched artifacts:** `data/papers/` (intentionally gitignored; local-only cache)

### Minimal JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Semantica MARIS Document Registry",
  "type": "object",
  "required": ["version", "created_at", "updated_at", "document_count", "documents"],
  "properties": {
    "version": {"type": "string"},
    "created_at": {"type": "string"},
    "updated_at": {"type": "string"},
    "document_count": {"type": "integer"},
    "documents": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": [
          "title",
          "url",
          "year",
          "source_tier",
          "document_type",
          "domain_tags",
          "added_at"
        ],
        "properties": {
          "title": {"type": "string"},
          "url": {"type": "string"},
          "doi": {"type": "string"},
          "authors": {"type": ["string", "array"]},
          "year": {"type": "integer"},
          "journal": {"type": "string"},
          "source_tier": {"type": "string", "enum": ["T1", "T2", "T3", "T4"]},
          "document_type": {"type": "string"},
          "domain_tags": {"type": "array", "items": {"type": "string"}},
          "added_at": {"type": "string"},
          "notes": {"type": "string"},
          "access_status": {
            "type": "string",
            "enum": ["open_access", "paywalled", "institutional", "unknown"]
          },
          "retrieval": {
            "type": "object",
            "properties": {
              "retrieved_at": {"type": "string"},
              "sha256": {"type": "string"},
              "content_type": {"type": "string"},
              "source_url": {"type": "string"}
            }
          }
        }
      }
    }
  }
}
```

### Required Fields (per document entry)

- `title`, `url`, `year`, `source_tier`, `document_type`, `domain_tags`, `added_at`
- Optional but recommended: `doi`, `authors`, `journal`, `access_status`, `retrieval.sha256`

### Ingestion Agreement (Handoff Contract)

- The registry is the authoritative list of documents to ingest; new sources must be added here first.
- The Semantica team will attempt fetch and parse from `url`; any access issues are reported with HTTP status and reason.
- For paywalled or blocked documents, MARIS will provide local PDFs or alternate access URLs.
- Provenance must include DOI + page reference + quote for all numeric claims used in bridge axioms.
- Parsing should use Docling for PDFs with tables/figures; OCR enabled when scans are detected.
- Extraction outputs must map to Semantica canonical entity/relation schemas with provenance metadata.

---

## Reference Case: Cabo Pulmo

**Cabo Pulmo National Park** (Gulf of California, Mexico) serves as the **AAA-rated reference site** for model validation. It represents the best-documented marine ecosystem recovery globally.

### Key Metrics

| Metric | Value | Source |
|--------|-------|--------|
| Biomass recovery | **463%** increase (1999-2009) | Aburto-Oropeza 2011 |
| Apex predator increase | **5.9×** | Aburto-Oropeza 2011 |
| Annual ecosystem services | **$29.27M** | Calculated |
| NEOLI score | **4/5** criteria met | Edgar 2014 framework |
| Protection duration | **29 years** (est. 1995) | WDPA |

### NEOLI Assessment

| Criterion | Status | Notes |
|-----------|--------|-------|
| **N**o-take | ✅ Yes | Full no-take since 1995 |
| **E**nforced | ✅ Yes | Community-led enforcement |
| **O**ld | ✅ Yes | >10 years (29 years) |
| **L**arge | ❌ No | 71 km² (threshold: 100 km²) |
| **I**solated | ✅ Yes | Deep water boundaries |

### Validation Target

A correctly functioning MARIS system should:

1. Return Cabo Pulmo's biomass trajectory with full provenance
2. Calculate ecosystem service values within ±20% of published estimates
3. Generate TNFD-compliant disclosures for a hypothetical blue bond
4. Explain the trophic cascade mechanism (apex predators → mesopredators → herbivores → algae → coral)

---

## Investor Demo Dashboard

The repository includes an **interactive Streamlit dashboard** designed for investor-facing demonstrations of the Cabo Pulmo investment case. This is the presentation layer for the MARIS/Semantica system.

### Architecture: "The Artifact is the Asset"

The dashboard is powered by a **static JSON bundle** (`cabo_pulmo_investment_grade_bundle.json`) generated by the investment-grade Jupyter notebook. This is a deliberate architectural choice - in investor pitch contexts, zero latency and 100% uptime are non-negotiable. The bundle itself demonstrates that MARIS outputs are portable, immutable, and auditable.

### Dashboard Sections (single-scroll, dark-mode)

| Section | Purpose |
|---------|---------|
| **Masthead** | Site branding, IFC/TNFD alignment badges |
| **Investment Thesis** | MARIS + Semantica + context graphs explanation |
| **KPI Strip** | ESV, biomass recovery, NEOLI score, climate buffer |
| **Provenance Chain** | Fixed-position graph: Site -> Ecology -> Services -> Finance |
| **Bridge Axiom Evidence** | 4 axioms with plain-English meanings and DOI links |
| **Valuation Composition** | Horizontal bar chart with CI context |
| **Risk Profile** | Monte Carlo distribution + climate/degradation risk cards |
| **Comparison Sites** | Papahanaumokuakea, Cabo Pulmo, Mesoamerican Reef |
| **Framework Alignment** | IFC Blue Finance + TNFD LEAP details |

### Running the Dashboard

**v2 (Live mode - recommended):** Requires Neo4j + API server running (see [MARIS v2 - Live Query System](#maris-v2---live-query-system)):

```bash
cd investor_demo
streamlit run streamlit_app_v2.py
```

This adds **Ask MARIS** (natural-language query chat) and an **interactive Graph Explorer** showing provenance chains pulled live from Neo4j.

**v1 (Static mode - fallback):** No external services needed:

```bash
cd investor_demo
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Both versions include a **confidence slider** (Conservative P5 / Base Case Median / Optimistic P95) that updates KPI values and highlights the Monte Carlo distribution.

### Investment-Grade Notebook

The analysis notebook (`demos/context_graph_demo/cabo_pulmo_investment_grade.ipynb`) generates the data bundle and includes:

- Market-price ecosystem service valuation with propagated 95% confidence intervals
- Monte Carlo simulation (10,000 iterations) for risk-adjusted ESV
- NEOLI governance assessment with bridge axiom mapping
- Climate resilience and degradation risk quantification
- IFC Blue Finance and TNFD LEAP framework alignment
- Evidence provenance maps linking every value to its peer-reviewed source

---

## Sample Queries

The system is designed to answer complex, multi-hop questions with full provenance.

### Query Categories

| Category | Example Query |
|----------|--------------|
| **Impact Assessment** | "If we establish a no-take MPA at Site X, what biomass recovery can we expect in 10 years?" |
| **Financial Structuring** | "What KPIs should a blue bond for coral restoration include, and what peer-reviewed targets exist?" |
| **Site Comparison** | "Compare the ecological and financial profiles of Cabo Pulmo vs. Great Barrier Reef MPAs" |
| **Mechanistic** | "Explain the trophic cascade linking sea otter recovery to kelp carbon sequestration" |
| **Validation** | "What is the confidence interval on BA-001 (biomass-tourism elasticity)?" |

### Example Query Response

**Query:** "What ecological factors explain Cabo Pulmo's 463% biomass recovery?"

**Expected Response Structure:**
```json
{
  "answer": {
    "primary_factors": [
      "Full no-take protection since 1995",
      "Community-led enforcement (high compliance)",
      "Isolation by deep water (limited poaching)"
    ],
    "trophic_mechanism": "Apex predator recovery → mesopredator control → herbivore release → algae control → coral health",
    "key_species": ["Lutjanus argentiventris", "Mycteroperca rosacea"]
  },
  "provenance": [
    {
      "claim": "463% biomass increase",
      "source": "Aburto-Oropeza et al. 2011",
      "doi": "10.1371/journal.pone.0023601",
      "page": "Figure 2",
      "quote": "Total fish biomass increased by 463% from 1999 to 2009"
    }
  ],
  "confidence": "HIGH",
  "reasoning_path": ["NEOLI criteria", "BA-002", "trophic_cascade_inference"]
}
```

---

## Implementation Roadmap

**Total Duration:** 8 weeks  
**Timeline:** Compressed schedule focused on Semantica integration and core functionality

### Phase 0: Document Library Reconstruction ✅ COMPLETE

- [x] Validate initial registry (70 papers)
- [x] Enrich abstracts via CrossRef/OpenAlex/Semantic Scholar APIs
- [x] Expand library to 195 papers across 10 domains
- [x] Extract knowledge from 5 critical papers
- [x] Generate Semantica export bundle (4 files)
- [x] Evidence 12 bridge axioms with 3+ sources each

---

## Four Main Implementation Phases (All Aligned with Semantica)

### Phase 1: Foundation & Semantica Integration (Weeks 1-2)

**Focus:** Establish Semantica connection, ingest export bundle, and set up data pipelines

**Week 1: Core Foundation & Semantica API Setup**
- [x] `maris/__init__.py` ✅ - Package initialization
- [x] `maris/config.py` ✅ - Configuration management
- [ ] `maris/utils.py` - Utility functions
- [ ] `maris/schemas.py` - Schema loading utilities
- [ ] `maris/semantica_integration.py` - **Main Semantica integration** (CRITICAL)
- [ ] `config/config.yaml` - Configuration file
- [ ] `config/.env.example` - Environment variables template
- [ ] **Establish Semantica API connection**
- [ ] **Ingest `entities.jsonld` into Semantica** (via Semantica API)
- [ ] **Ingest `relationships.json` with inference rules** (via Semantica API)
- [ ] **Index `document_corpus.json` in Semantica** (via Semantica API)
- [ ] Validate Semantica connection and basic operations

**Week 2: Data Loading & Entity Extraction via Semantica**
- [ ] `maris/data_loader.py` - Load existing Semantica export bundle
- [ ] `maris/document_processor.py` - Document ingestion via Semantica
- [ ] `maris/provenance.py` - Provenance tracking
- [ ] `maris/entity_extractor.py` - **Entity extraction using Semantica API**
- [ ] `tests/test_entity_extraction.py` - Entity extraction tests
- [x] Extract entities from 5 CRITICAL papers ✅ (manual extractions complete)
- [ ] **Extract entities from 30+ high-priority papers using Semantica**
- [ ] Load Cabo Pulmo case study into Semantica
- [ ] Validate data integrity in Semantica

**Phase 1 Milestones:**
- ✅ Semantica API connection established
- ✅ Export bundle ingested into Semantica
- ✅ Document corpus indexed in Semantica
- ✅ Entity extraction pipeline operational using Semantica
- ✅ 30+ papers processed with >85% extraction accuracy

---

### Phase 2: Knowledge Extraction & Bridge Axioms via Semantica (Weeks 3-4)

**Focus:** Extract relationships and implement bridge axioms as Semantica inference rules

**Week 3: Relationship Extraction via Semantica**
- [ ] `maris/relationship_extractor.py` - **Relationship extraction using Semantica API**
- [ ] `tests/test_relationship_extraction.py` - Relationship extraction tests
- [ ] **Build trophic network subgraph in Semantica**
- [ ] Extract habitat-service links using Semantica
- [ ] Extract MPA-effectiveness relationships using Semantica
- [ ] `maris/bridge_axiom_engine.py` - Bridge axiom application engine (start)
- [x] Define BA-001 through BA-012 with coefficients ✅
- [ ] **Register bridge axioms as Semantica inference rules**

**Week 4: Bridge Axioms Implementation & Validation via Semantica**
- [ ] `maris/bridge_axiom_engine.py` - Bridge axiom application engine (complete)
- [ ] `maris/validators.py` - Validation utilities
- [ ] `tests/test_bridge_axioms.py` - Bridge axiom tests
- [ ] `tests/test_cabo_pulmo_validation.py` - Cabo Pulmo validation tests
- [ ] **Implement bridge axioms as Semantica inference rules**
- [ ] **Test axiom pattern matching in Semantica**
- [x] Validate Cabo Pulmo metrics (463% ±20% tolerance) ✅
- [ ] **Test cascade reasoning (otter → kelp → carbon) via Semantica**
- [ ] Validate all 12 bridge axioms

**Phase 2 Milestones:**
- ✅ Relationship extraction operational using Semantica
- ✅ Trophic networks built in Semantica graph
- ✅ All 12 bridge axioms implemented as Semantica inference rules
- ✅ Bridge axioms registered and functional in Semantica
- ✅ Cabo Pulmo validation passing (±20% tolerance)
- ✅ Cascade reasoning functional via Semantica

---

### Phase 3: Graph Construction & Query Interface via Semantica (Weeks 5-6)

**Focus:** Build knowledge graph and GraphRAG query interface using Semantica

**Week 5: GraphRAG Query Interface via Semantica**
- [ ] `maris/query_engine.py` - **GraphRAG query interface using Semantica**
- [ ] `tests/test_query_engine.py` - Query engine tests
- [ ] **Configure Semantica GraphRAG interface**
- [ ] **Implement multi-hop reasoning (up to 4 hops) via Semantica**
- [ ] **Implement all 11 sample queries using Semantica GraphRAG**
- [ ] Add confidence scoring to responses
- [ ] Build provenance visualization
- [ ] Test TNFD disclosure field population

**Week 6: Knowledge Graph Construction via Semantica**
- [ ] `maris/graph_builder.py` - **Knowledge graph construction via Semantica**
- [ ] **Use Semantica's native graph database** (or configure Neo4j integration)
- [ ] **Create entity nodes from extracted entities in Semantica**
- [ ] **Create relationship edges in Semantica**
- [ ] **Apply bridge axioms as graph inference rules in Semantica**
- [ ] Build trophic network subgraphs in Semantica
- [ ] Create MPA network connectivity graphs in Semantica
- [ ] Validate graph integrity

**Phase 3 Milestones:**
- ✅ GraphRAG interface configured in Semantica
- ✅ All 11 sample queries working via Semantica
- ✅ Query latency <5 seconds
- ✅ Full knowledge graph built in Semantica
- ✅ Bridge axioms applied as inference rules in Semantica
- ✅ Graph integrity validated
- ✅ Subgraphs operational in Semantica

---

### Phase 4: Integration, Testing & Demo via Semantica (Weeks 7-8)

**Focus:** End-to-end testing, CLI, and demo using Semantica queries

**Week 7: Integration Testing & CLI**
- [ ] `maris/cli.py` - Command-line interface
- [ ] `tests/test_integration.py` - Integration tests
- [ ] Implement all CLI commands
- [ ] **Test end-to-end pipeline with Semantica**
- [ ] **Process remaining papers for entity extraction (batch via Semantica)**
- [ ] Performance testing and optimization
- [ ] Validate all success criteria

**Week 8: Demo & Documentation**
- [ ] **Run investor demo narrative using Semantica queries**
- [ ] Validate all success criteria
- [ ] `docs/api_reference.md` - API documentation
- [ ] `docs/user_guide.md` - User guide
- [ ] `docs/developer_guide.md` - Developer guide
- [ ] **Document Semantica integration patterns**
- [ ] Finalize all documentation

**Phase 4 Milestones:**
- ✅ CLI commands functional
- ✅ End-to-end pipeline tested with Semantica
- ✅ All integration tests passing
- ✅ Investor demo complete using Semantica queries (10-min narrative without gaps)
- ✅ All documentation finalized with Semantica integration patterns
- ✅ All success criteria validated
- ✅ POC ready for handoff

---

## Success Criteria

### Technical Validation

| Criterion | Target | Validation Method |
|-----------|--------|-------------------|
| Cabo Pulmo query | Full provenance returned | Manual review |
| Ecosystem service values | ±20% of published | Compare to Aburto 2011 |
| TNFD field coverage | 100% required fields | Schema validation |
| Query latency | <5 seconds (3-4 hops) | Performance test |
| Provenance completeness | DOI + page for all claims | Automated audit |

### Business Validation

| Criterion | Target |
|-----------|--------|
| Investor demo | Complete 10-min narrative without gaps |
| Bridge axiom coverage | All 12 axioms functional |
| Multi-habitat support | Coral, kelp, mangrove, seagrass |
| Test suite | 177 tests passing |
| API authentication | Bearer token + rate limiting |
| Docker builds | Multi-stage API + Dashboard |
| CI pipeline | GitHub Actions (lint + test) |

---

## Key Files Reference

### Must-Read Files (Priority Order)

| File | Purpose | Read When |
|------|---------|-----------|
| `data/semantica_export/entities.jsonld` | JSON-LD entities for ingestion | **Day 1 - Ingest first** |
| `data/semantica_export/relationships.json` | Typed relationships with provenance | **Day 1 - Ingest second** |
| `data/semantica_export/bridge_axioms.json` | 12 axioms with evidence | **Day 1 - Configure inference** |
| `data/semantica_export/document_corpus.json` | Corpus summary for indexing | **Day 1 - Build retrieval** |
| `examples/cabo_pulmo_case_study.json` | Validation target | During testing |
| `examples/sample_queries.md` | Query templates | During GraphRAG dev |

### Critical Paper Extractions

| File | Paper | Key Data |
|------|-------|----------|
| `data/sample_extractions/edgar_2014_extraction.json` | Edgar et al. 2014 | NEOLI criteria, 670% biomass differential |
| `data/sample_extractions/aburto_2011_extraction.json` | Aburto-Oropeza et al. 2011 | Cabo Pulmo 463% recovery |
| `data/sample_extractions/costanza_2014_extraction.json` | Costanza et al. 2014 | Global ES $125T, per-hectare values |
| `data/sample_extractions/hopf_2024_extraction.json` | Hopf et al. 2024 | No-take meta-analysis, 2.7× multiplier |
| `data/sample_extractions/beck_2018_extraction.json` | Beck et al. 2018 | Coral flood protection, $4B/yr global |

### Reference Files

| File | Purpose |
|------|---------|
| `Semantica_POC_Conceptual_Framework.md` | Full conceptual architecture (35KB) |
| `SYSTEM_OVERVIEW.md` | Detailed system design |
| `SEMANTICA_HANDOFF_README.md` | Integration instructions |
| `ai_docs/RECONSTRUCTION_COMPLETE.md` | Pipeline reconstruction report |
| `.claude/registry/document_index.json` | Full bibliography with metadata (195 papers) |

### MARIS v2 System Files

| File | Purpose |
|------|---------|
| `.env.example` | Environment configuration template (copy to `.env`) |
| `docker-compose.yml` | One-command deployment (Neo4j + API + Dashboard) |
| `requirements-v2.txt` | Python dependencies for v2 stack |
| `maris/api/main.py` | FastAPI application factory |
| `maris/api/models.py` | Pydantic request/response schemas |
| `maris/query/cypher_templates.py` | 8 parameterized Cypher query templates |
| `maris/graph/population.py` | Graph population from curated JSON assets |
| `investor_demo/streamlit_app_v2.py` | v2 dashboard with live API integration |
| `scripts/populate_neo4j.py` | Idempotent graph population script |
| `scripts/demo_healthcheck.py` | Pre-demo system verification |
| `Dockerfile.api` | Multi-stage API container (python:3.11-slim, non-root) |
| `Dockerfile.dashboard` | Multi-stage dashboard container |
| `requirements-dev.txt` | Test and lint dependencies (pytest, ruff, httpx) |
| `.github/workflows/ci.yml` | GitHub Actions CI: lint + test pipeline |
| `maris/api/auth.py` | Bearer token auth, rate limiting, request tracing |
| `maris/query/validators.py` | LLM response validation, claim verification |
| `maris/axioms/sensitivity.py` | OAT sensitivity analysis, tornado plot data |

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/validate_registry.py` | Validate registry structure and statistics |
| `scripts/enrich_abstracts.py` | Fetch abstracts via CrossRef/OpenAlex/Semantic Scholar |
| `scripts/add_papers_batch.py` | Batch paper addition to registry |

---

## External Resources

### Data Sources (for future integration)

| Source | URL | Data Type |
|--------|-----|-----------|
| WoRMS | marinespecies.org | Marine taxonomy |
| FishBase | fishbase.org | Fish species data |
| OBIS | obis.org | Occurrence records |
| GloBI | globalbioticinteractions.org | Species interactions |
| WDPA | protectedplanet.net | MPA boundaries |

### Standards & Frameworks

| Standard | Purpose |
|----------|---------|
| TNFD | Nature-related financial disclosures |
| SEEA-EA | Ecosystem accounting |
| ESRS E4 | EU biodiversity reporting |
| SBTN | Science-based targets for nature |

---

## Contact

**Project Lead:** Jay Gutierrez (Cross-System Architect) — [biome-translator.emergent.host](https://biome-translator.emergent.host/)  
**Semantica Integration:** Mohd Kaif (Lead Developer)  
**Repository:** [github.com/jaygut/semantica-poc](https://github.com/jaygut/semantica-poc)

---

## License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.

---

*Blue Natural Capital Knowledge Engineering — Where ocean science meets investment intelligence.*
