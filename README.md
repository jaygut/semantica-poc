# Nereus - Blue Natural Capital Intelligence

**Translating ecological complexity into investment-grade natural capital assets.**
**The "Hybrid" Intelligence Model** - where Semantica's extracted axioms form the physical logic of ocean finance.
**Where ocean science meets investment intelligence.**

[![Status](https://img.shields.io/badge/Status-v6%20Scenario%20Intelligence-brightgreen)]()
[![Sites](https://img.shields.io/badge/MPA%20Sites-9-blue)]()
[![Portfolio](https://img.shields.io/badge/Portfolio-$1.62B-green)]()
[![Papers](https://img.shields.io/badge/Literature-195%20Papers-green)]()
[![Evidence](https://img.shields.io/badge/T1%20Sources-92%25-brightgreen)]()
[![Axioms](https://img.shields.io/badge/Bridge%20Axioms-40%2F40-brightgreen)]()

---

## Executive Summary

This repository contains the **complete knowledge foundation** for Nereus v4, a "Hybrid" Intelligence system where **Semantica plays a foundational role**. Unlike traditional RAG systems that merely cite text, Nereus "thinks" using **35 Bridge Axioms**—scientific rules physically extracted from literature and loaded into a Neo4j knowledge graph.

**Current Status:** The **Nereus v6 Prospective Scenario Intelligence** release transforms Nereus from retrospective ESV valuation into forward-looking scenario intelligence. Built on the v5 Audit-Grade Integrity platform (40 bridge axioms, DOI-backed provenance), v6 adds SSP climate pathways, counterfactual protection analysis, McClanahan tipping point engine, blue carbon revenue modeling, portfolio Nature VaR, and real options valuation - all with deterministic provenance chains and P5/P50/P95 uncertainty envelopes.

**The "Hybrid" Intelligence Model:**
1.  **Semantica Extraction:** Raw PDFs are processed into structured entities and **Bridge Axioms** (e.g., "Otters -> Kelp -> Carbon").
2.  **Physical Linking:** These axioms are not just text; they are **nodes in the graph** that physically connect ecological observations (L1) to financial values (L3).
3.  **Deterministic Reasoning:** The application "thinks" by traversing these verified paths. It doesn't hallucinate relationships; it executes the axioms that Semantica extracted.

**The Problem:** A $175B annual funding gap exists for ocean conservation. Investors can't trust opaque ecological claims. Scientists can't translate their findings into financial terms. The result: capital doesn't flow to where it's needed.

**The Solution:** Nereus - a platform where **The Logic is Physically Linked**. MARIS provides the intelligence engine; Semantica serves as the ontological core, ensuring that the "brain" of the system is composed entirely of validated scientific induction.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          THE "HYBRID" INTELLIGENCE                          │
│                    (Logic Physically Linked to Science)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   RAW SCIENCE              SEMANTICA AXIOMS             FINANCIAL TRUTH     │
│   ───────────              ────────────────            ─────────────────    │
│   [PDF: Beck 2018]   →     [Node: BA-004]         →    [Value: Risk Red.]   │
│   "Reefs reduce..."        (The Physical Link)         "Premiums -15%"      │
│                                     │                                       │
│                                     ▼                                       │
│                           The Application "Thinks"                          │
│                           via this Graph Edge                               │
│                                                                             │
│   Every query executes a traversal through a specific Semantica axiom.      │
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
| 3 | [`data/semantica_export/bridge_axioms.json`](./data/semantica_export/bridge_axioms.json) | 35 bridge axioms (BA-001 to BA-035) with 3+ evidence sources each |
| 4 | [`data/semantica_export/document_corpus.json`](./data/semantica_export/document_corpus.json) | 195-paper corpus summary |
| 5 | [`data/sample_extractions/`](./data/sample_extractions/) | 5 critical paper extractions |

### Python SDK Integration

```python
from maris.semantica_bridge import SemanticaBackedManager, SEMANTICA_AVAILABLE

# Drop-in replacement for MARISProvenanceManager with SQLite persistence
manager = SemanticaBackedManager(
    templates_path="schemas/bridge_axiom_templates.json",
    db_path="provenance.db",
)

# Track entity extraction with dual-write (MARIS + Semantica)
manager.track_extraction("cabo_pulmo_esv", "EcosystemService", "10.1371/...")

# Execute translation chains through bridge axioms
result = manager.execute_chain(
    axiom_ids=["BA-002", "BA-001"],
    input_data={"biomass_ratio": 4.63, "base_tourism": 25_000_000},
)

# Get provenance certificate (JSON or Markdown)
cert = manager.get_certificate("cabo_pulmo_esv")
```

See [SEMANTICA_HANDOFF_README.md](SEMANTICA_HANDOFF_README.md) for full integration architecture and P0-P4 module details.

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

The Nereus pipeline generates a **Semantica-ready export bundle** designed for direct ingestion into [Semantica](https://github.com/Hawksight-AI/semantica) - an open-source framework that transforms unstructured data into validated, explainable, and auditable knowledge.

### How Nereus Fits Into Semantica

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   NEREUS → SEMANTICA INTEGRATION FLOW                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   NEREUS PIPELINE                       SEMANTICA                           │
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
│   │ (16 axioms)      │  bridge_axioms   │ (Translate + Query)  │           │
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
| `bridge_axioms.json` | JSON | 16 axioms with 3+ evidence sources each | Inference rules |
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

All 16 bridge axioms now have **3+ supporting sources** (12 core + 4 blue carbon):

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
| BA-013 | Seagrass Carbon Sequestration Rate | 3 | Arias-Ortiz 2018 |
| BA-014 | Carbon Stock to Credit Value | 3 | Verra VCS VM0033 |
| BA-015 | Habitat Loss Carbon Emission | 3 | Arias-Ortiz 2018 |
| BA-016 | MPA Protection Carbon Permanence | 3 | IPCC 2019 |

### Using the Semantica Bridge

The Nereus codebase includes a 6-file Semantica SDK bridge layer (`maris/semantica_bridge/`) that provides drop-in integration. See [SEMANTICA_HANDOFF_README.md](SEMANTICA_HANDOFF_README.md) for full architecture details, API usage examples, and P0-P4 module documentation.

---

## How the Application "Thinks" with Semantica

When a user asks a question like *"What is the financial value of the coral reef in Cabo Pulmo?"*, the system does not merely search for text. It executes a **logical proof** using Semantica's extracted axioms.

### 1. The Physical Link
The logic is stored as a graph path:
`[MPA: Cabo Pulmo] -> [HABITAT: Coral Reef] -> [AXIOM: BA-004] -> [SERVICE: Flood Protection]`

*   **BA-004** is not a black box. It is a node with properties extracted by Semantica:
    *   `coefficient`: "Reefs reduce wave energy by 97%"
    *   `source`: "Beck et al. 2018, Nature Communications"
    *   `confidence`: "HIGH"

### 2. The Execution Flow
1.  **Classifier:** Detects intent (`site_valuation`).
2.  **Template Selection:** Loads the `site_valuation` Cypher template.
3.  **Graph Traversal:** The query traverses the `APPLIES_TO` and `TRANSLATES` edges created from the Semantica export.
4.  **Axiom Application:** The system retrieves the coefficients from the `BridgeAxiom` node.
5.  **Synthesis:** The LLM receives the structured graph result (not raw text) and synthesized the answer: *"Cabo Pulmo provides $14M in flood protection, calculated using the Beck et al. (2018) coefficient of wave attenuation..."*

**Result:** The "Hybrid" model ensures that **every financial number is a direct function of a scientific citation.**

---

## Nereus Live Query System

The live layer adds a **knowledge graph and query engine** on top of the curated knowledge foundation. Users can ask natural-language questions and receive grounded answers with interactive provenance visualization.

### Architecture

```
User Question (NL)
        |
   [Classifier]  -- keyword-first, LLM fallback
        |
   [Cypher Template]  -- 8 parameterized templates (5 core + 3 utility)
        |
   [Neo4j Graph]  -- 938 nodes, 244 relationships, 9 MPA sites
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

### Quick Start (Unified Launcher - Recommended)

```bash
# v4 Global Scaling Platform (9 sites, 6 tabs)
./launch.sh v4

# Other versions
./launch.sh v3    # Intelligence Platform (2 sites, 5 tabs, port 8503)
./launch.sh v2    # Single-scroll dashboard (2 sites, port 8501)
./launch.sh v1    # Static mode (1 site, no external services, port 8500)
./launch.sh api   # API server only (port 8000)
./launch.sh stop  # Stop all services
```

### Quick Start (Manual)

```bash
# 1. Start Neo4j (via Desktop or Docker)
# Default: bolt://localhost:7687, user: neo4j, password: maris-dev

# 2. Populate the knowledge graph (v4: 9 sites, dynamic discovery)
python scripts/populate_neo4j_v4.py

# 3. Start the API server
uvicorn maris.api.main:app --host 0.0.0.0 --port 8000

# 4. Start the v4 dashboard (in a separate terminal)
cd investor_demo
streamlit run streamlit_app_v4.py --server.port 8504
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

The project includes **910 tests** (706 unit + 204 integration) covering all core modules and the Semantica integration:

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all unit tests
pytest tests/ -v --ignore=tests/integration

# Run integration tests (requires Semantica SDK)
pytest tests/integration/ -v

# Run full suite with coverage
pytest tests/ --cov=maris --cov-report=term-missing
```

Tests are organized by module in `tests/` with shared fixtures in `conftest.py`. Integration tests live in `tests/integration/` with 7 phase files covering bridge validation, graph integrity, external APIs, query pipeline, disclosure/discovery, stress tests, and LLM-enhanced discovery (phase 6 tests against live DeepSeek). CI runs automatically on push and PR to `main` via GitHub Actions (`.github/workflows/ci.yml`): linting with ruff, then pytest.

---

## Architecture Overview

**Core Framework:** Nereus is built on **MARIS + Semantica** as the foundational engine for all operations:
- **Entity Extraction** → Semantica API
- **Relationship Extraction** → Semantica API  
- **Graph Construction** → Semantica graph database
- **Query Execution** → Semantica GraphRAG
- **Bridge Axioms** → Semantica inference rules

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NEREUS SYSTEM ARCHITECTURE                           │
│                  (Powered by MARIS + Semantica)                            │
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
| **Bridge Axioms** | `data/semantica_export/bridge_axioms.json` | JSON | 16 axioms with 3+ evidence sources each | Registered as Semantica inference rules |
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
│   │   └── routes/                        # /health, /query, /graph, /provenance, /disclosure
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
│   ├── provenance/                        # P0: W3C PROV-O provenance tracking
│   │   ├── manager.py                     # MARISProvenanceManager (entity/activity/agent)
│   │   ├── bridge_axiom_registry.py       # 16 axioms as typed BridgeAxiom objects
│   │   ├── certificate.py                 # Provenance certificate generation (JSON/Markdown)
│   │   ├── core.py                        # PROV-O core dataclasses
│   │   ├── integrity.py                   # SHA-256 checksum verification
│   │   └── storage.py                     # In-memory + SQLite storage backends
│   ├── sites/                             # P1: Multi-site scaling pipeline
│   │   ├── api_clients.py                 # OBIS (area resolution), WoRMS (204 fix), Marine Regions (404+JSON handling) API clients
│   │   ├── characterizer.py              # 5-step auto-characterization (Bronze/Silver/Gold) with multi-signal habitat scoring (keywords, taxonomy, functional groups)
│   │   ├── esv_estimator.py              # Bridge axiom-based ESV estimation
│   │   ├── models.py                      # Pydantic site models
│   │   └── registry.py                    # JSON-backed site registry
│   ├── reasoning/                         # P2: Cross-domain reasoning engine
│   │   ├── context_builder.py            # Graph -> Semantica ContextGraph conversion
│   │   ├── hybrid_retriever.py           # Graph + keyword + RRF hybrid retrieval
│   │   ├── inference_engine.py           # Forward/backward chaining with axiom rules
│   │   ├── rule_compiler.py             # Rule compilation extracted from InferenceEngine
│   │   └── explanation.py                # Investor-friendly explanation generation
│   ├── disclosure/                        # P3: TNFD LEAP disclosure automation
│   │   ├── leap_generator.py             # 4-phase TNFD LEAP document generation
│   │   ├── renderers.py                  # Markdown, JSON, summary output formats
│   │   ├── alignment_scorer.py           # 14-disclosure gap analysis
│   │   └── models.py                     # TNFD Pydantic models
│   ├── discovery/                         # P4: Dynamic axiom discovery
│   │   ├── pattern_detector.py           # Cross-paper quantitative pattern detection (regex)
│   │   ├── llm_detector.py              # LLM-enhanced pattern detection with regex fallback, retry logic, numeric confidence, robust JSON parsing
│   │   ├── aggregator.py                 # Multi-study aggregation + conflict detection
│   │   ├── candidate_axiom.py            # Candidate axiom formation
│   │   ├── reviewer.py                   # Human-in-the-loop validation workflow
│   │   └── pipeline.py                   # End-to-end discovery orchestration
│   ├── semantica_bridge/                  # Semantica SDK adapter layer
│   │   ├── storage_adapter.py            # SemanticaStorage wrapping SDK storage
│   │   ├── axiom_adapter.py              # MARIS <-> Semantica axiom conversion
│   │   ├── provenance_adapter.py         # Dual-write provenance manager
│   │   ├── integrity_adapter.py          # SDK-backed integrity verification
│   │   └── manager.py                    # SemanticaBackedManager (drop-in replacement)
│   ├── services/                          # ═══ MODULAR SERVICES ═══
│   │   └── ingestion/                     # Ingestion Logic (Case Studies + Concepts)
│   │       ├── case_study_loader.py       # Core case study loading
│   │       ├── concepts_loader.py         # Concept node loading
│   │       └── discovery.py               # Site discovery logic
│   ├── settings.py                        # Pydantic-based configuration (New)
│   ├── config.py                          # Legacy wrapper around settings.py
│   └── config_v4.py                      # v4 wrapper around settings.py
│
├── investor_demo/                         # ═══ STREAMLIT DASHBOARDS ═══
│   ├── streamlit_app_v4.py                # v4 Global Scaling Platform (9 sites, 6 tabs, latest)
│   ├── streamlit_app_v3.py                # v3 Intelligence Platform (multi-tab)
│   ├── streamlit_app_v2.py                # v2 dashboard (live API + static bundle)
│   ├── streamlit_app.py                   # v1 dashboard (static bundle only)
│   ├── components/
│   │   ├── v4/                            # v4 Global Scaling Platform components
│   │   │   ├── __init__.py                # Package init with shared exports
│   │   │   ├── shared.py                  # Dynamic site discovery, tier-aware feature gating
│   │   │   ├── portfolio_overview.py      # Tab: Portfolio grid ($1.62B aggregate)
│   │   │   ├── intelligence_brief.py      # Tab: Per-site KPIs, provenance, axiom evidence
│   │   │   ├── graphrag_chat.py           # Tab: Split-panel GraphRAG with pipeline transparency
│   │   │   ├── scenario_engine.py         # Tab: Monte Carlo with site-aware axiom chains
│   │   │   └── tnfd_compliance.py         # Tab: TNFD LEAP for all 9 sites
│   │   ├── v3/                            # v3 Intelligence Platform components
│   │   │   ├── __init__.py                # Package init with shared exports
│   │   │   ├── shared.py                  # Colors, CSS, formatters, service health
│   │   │   ├── intelligence_brief.py      # Tab: KPIs, provenance graph, axiom evidence
│   │   │   ├── graphrag_chat.py           # Tab: Split-panel GraphRAG with pipeline transparency
│   │   │   ├── scenario_engine.py         # Tab: Interactive Monte Carlo with parameter sliders
│   │   │   └── tnfd_compliance.py         # Tab: TNFD LEAP generation + alignment scoring
│   │   ├── chat_panel.py                  # Ask Nereus query interface (v2)
│   │   ├── graph_explorer.py              # Interactive provenance visualization (v2)
│   │   └── roadmap_section.py             # Scaling Intelligence section (shared v1/v2)
│   ├── api_client.py                      # HTTP client for MARIS API
│   ├── precomputed_responses_v4.json      # v4 demo fallback for all 9 sites
│   ├── precomputed_responses.json         # v3 fallback responses (63 queries)
│   └── README.md                          # Dashboard architecture and usage
│
├── schemas/                               # ═══ INGEST THESE FIRST ═══
│   ├── entity_schema.json                 # 8 entity types (JSON-LD)
│   ├── relationship_schema.json           # 14 relationship types
│   └── bridge_axiom_templates.json        # 16 translation rules
│
├── data/
│   ├── semantica_export/                  # ═══ SEMANTICA-READY BUNDLE ═══
│   │   ├── entities.jsonld                # 14 entities (JSON-LD)
│   │   ├── relationships.json             # 15 relationships
│   │   ├── bridge_axioms.json             # 16 axioms with evidence
│   │   └── document_corpus.json           # Corpus summary
│   └── sample_extractions/                # 5 critical paper extractions
│
├── scripts/
│   ├── populate_neo4j_v4.py               # v4 population (11-stage, dynamic site discovery)
│   ├── populate_neo4j.py                  # Legacy population (2-site, v2/v3)
│   ├── demo_healthcheck.py                # Pre-demo system verification
│   ├── validate_graph.py                  # Post-population integrity checks
│   └── run_ingestion.py                   # PDF ingestion pipeline
│
├── tests/                                # ═══ TEST SUITE (910 tests) ═══
│   ├── conftest.py                        # Shared fixtures
│   ├── test_api_endpoints.py              # API route tests with auth validation
│   ├── test_auth.py                       # Auth enforcement, rate limiting, input validation
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
│   ├── test_validators.py                 # LLM response validation tests
│   ├── test_provenance.py                 # P0: Provenance engine tests (40 tests)
│   ├── test_site_scaling.py               # P1: Site scaling pipeline tests (45 tests)
│   ├── test_reasoning.py                  # P2: Reasoning engine tests (35 tests)
│   ├── test_disclosure.py                 # P3: TNFD disclosure tests (30 tests)
│   ├── test_axiom_discovery.py            # P4: Axiom discovery pipeline tests (70+ tests)
│   ├── test_semantica_bridge.py           # Semantica SDK bridge adapter tests (51 tests)
│   └── integration/                       # ═══ INTEGRATION TESTS (204 tests) ═══
│       ├── test_phase0_bridge.py          # SDK availability, SQLite persistence, dual-write
│       ├── test_phase1_graph.py           # Graph integrity, idempotent re-population
│       ├── test_phase2_apis.py            # OBIS, WoRMS, Marine Regions real API calls
│       ├── test_phase3_query.py           # 5-category regression, classifier accuracy
│       ├── test_phase4_disclosure.py      # TNFD disclosure, axiom discovery
│       ├── test_phase5_stress.py          # SQLite persistence, concurrent queries
│       └── test_phase6_llm_discovery.py   # LLM-enhanced discovery integration (7 tests against live DeepSeek)
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
├── launch.sh                              # Unified launcher (v1|v2|v3|v4|api|stop)
│
└── examples/                              # ═══ 9 MPA CASE STUDIES ═══
    ├── cabo_pulmo_case_study.json         # AAA reference (Mexico, coral reef, $29.3M)
    ├── shark_bay_case_study.json          # AA reference (Australia, seagrass, $21.5M)
    ├── galapagos_case_study.json          # AAA (Ecuador, coral+kelp+mangrove, $320.9M)
    ├── belize_barrier_reef_case_study.json # AA (Belize, coral+mangrove+seagrass, $292.5M)
    ├── sundarbans_case_study.json         # A (Bangladesh/India, mangrove, $778.9M)
    ├── ningaloo_case_study.json           # AA (Australia, coral reef, $83.0M)
    ├── raja_ampat_case_study.json         # AA (Indonesia, coral+mangrove, $78.0M)
    ├── cispata_bay_case_study.json        # A (Colombia, mangrove, $8.0M)
    ├── aldabra_case_study.json            # AAA (Seychelles, coral+mangrove+seagrass, $6.0M)
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

Bridge axioms are the **core innovation** - explicit, quantified rules that translate ecological states into financial values. Each axiom has:

- **Antecedent**: Ecological condition (measurable)
- **Consequent**: Financial implication (calculable)
- **Confidence**: Evidence strength (HIGH/MEDIUM/LOW)
- **Provenance**: Source papers with DOI + page references

### The 16 Bridge Axioms

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
| **BA-013** | Seagrass-Carbon-Rate | Seagrass area → Carbon sequestration (0.84 tCO2/ha/yr) | HIGH |
| **BA-014** | Carbon-Credit-Value | Carbon stock → Credit value ($30/tonne, Verra VCS) | HIGH |
| **BA-015** | Habitat-Loss-Emission | Habitat loss → Carbon emission (294 tCO2/ha released) | HIGH |
| **BA-016** | MPA-Carbon-Permanence | MPA protection → Carbon permanence guarantee | MEDIUM |

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
| `DisclosureFramework` | framework_name, required_metrics, update_frequency | - |
| `Observation` | value, unit, methodology, timestamp | - |
| `BridgeAxiom` | antecedent, consequent, confidence, provenance | - |

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

A correctly functioning Nereus system should:

1. Return Cabo Pulmo's biomass trajectory with full provenance
2. Calculate ecosystem service values within ±20% of published estimates
3. Generate TNFD-compliant disclosures for a hypothetical blue bond
4. Explain the trophic cascade mechanism (apex predators → mesopredators → herbivores → algae → coral)

---

## Investor Demo Dashboards

The repository includes four dashboard versions, each building on the previous:

### v4 Global Scaling Platform (Latest)

The v4 dashboard is a **registry-driven global scaling platform** spanning 9 MPA sites across 4 ocean basins with a combined portfolio value of $1.62B. All sites are discovered dynamically from `examples/*_case_study.json` files.

```bash
./launch.sh v4
# Or manually:
cd investor_demo
streamlit run streamlit_app_v4.py --server.port 8504
```

Opens at `http://localhost:8504` with 6 tabs:

| Tab | Content |
|-----|---------|
| **Portfolio Overview** | Grid of all 9 MPA sites with ESV, asset rating, habitat type, country, and tier indicators |
| **Intelligence Brief** | Per-site KPIs, provenance chain graph, axiom evidence table, valuation composition, Monte Carlo risk profile |
| **Ask Nereus (GraphRAG)** | Split-panel: chat on left (60%), reasoning pipeline on right (40%) showing CLASSIFY -> QUERY -> SYNTHESIZE -> VALIDATE steps with Cypher display, confidence breakdown, and knowledge graph subgraph visualization |
| **Scenario Lab** | Interactive Monte Carlo with site-aware axiom chains, 4 parameter sliders, overlay histogram, tornado sensitivity chart |
| **Site Scout** | Deferred (placeholder with pipeline-ready description) |
| **TNFD Compliance** | TNFD LEAP disclosure with alignment scoring for all 9 sites, per-pillar breakdown, gap analysis, download buttons |

**Sidebar:** Mode toggle (Live/Demo), service health panel, site selector (all 9 sites), scenario slider, system metadata.

### Portfolio ($1.62B across 9 MPA sites)

| Site | Country | Habitat | ESV | Rating |
|------|---------|---------|-----|--------|
| Sundarbans Reserve Forest | Bangladesh/India | Mangrove | $778.9M | A |
| Galapagos Marine Reserve | Ecuador | Coral+Kelp+Mangrove | $320.9M | AAA |
| Belize Barrier Reef | Belize | Coral+Mangrove+Seagrass | $292.5M | AA |
| Ningaloo Coast WHA | Australia | Coral Reef | $83.0M | AA |
| Raja Ampat Marine Park | Indonesia | Coral+Mangrove | $78.0M | AA |
| Cabo Pulmo National Park | Mexico | Coral Reef | $29.3M | AAA |
| Shark Bay WHA | Australia | Seagrass | $21.5M | AA |
| Cispata Bay Mangrove CA | Colombia | Mangrove | $8.0M | A |
| Aldabra Atoll | Seychelles | Coral+Mangrove+Seagrass | $6.0M | AAA |

### v3 Intelligence Platform

The v3 dashboard is a **multi-tab intelligence platform** that makes the P0-P4 backend infrastructure visible and interactive. Every feature has dual-mode operation: LIVE (Neo4j + LLM) and DEMO (precomputed + static bundle).

```bash
./launch.sh v3
# Or manually:
cd investor_demo
streamlit run streamlit_app_v3.py --server.port 8503
```

Opens at `http://localhost:8503` with 5 tabs:

| Tab | Content |
|-----|---------|
| **Intelligence Brief** | KPI strip (ESV, NEOLI, asset rating, CI), provenance chain graph, axiom evidence table, valuation composition bar chart, Monte Carlo risk profile |
| **Ask Nereus (GraphRAG)** | Split-panel: chat on left (60%), reasoning pipeline on right (40%) showing CLASSIFY -> QUERY -> SYNTHESIZE -> VALIDATE steps with Cypher display and confidence breakdown |
| **Scenario Lab** | 4 parameter sliders (carbon price, habitat loss, tourism growth, fisheries change), real-time Monte Carlo recalculation (10k simulations), overlay histogram, tornado sensitivity chart, bridge axiom chain impact |
| **Site Scout** | Deferred (placeholder with pipeline-ready description) |
| **TNFD Compliance** | TNFD LEAP disclosure generation with X/14 alignment scoring, per-pillar breakdown (Governance, Strategy, Risk/Impact, Metrics/Targets), gap analysis, download buttons |

**Sidebar:** Mode toggle (Live/Demo), service health panel, site selector (Cabo Pulmo / Shark Bay), scenario slider, system metadata.

### v2 Dashboard (Single-Scroll)

The v2 dashboard is the original single-scroll investor UI with Ask Nereus chat and interactive graph explorer. Requires Neo4j + API server running (see [Nereus Live Query System](#nereus-live-query-system)):

```bash
./launch.sh v2
# Or manually:
cd investor_demo
streamlit run streamlit_app_v2.py
```

Opens at `http://localhost:8501`. Sections include: Masthead, Investment Thesis, KPI Strip, Provenance Chain, Bridge Axiom Evidence, Valuation Composition, Risk Profile, Comparison Sites, Framework Alignment, Scaling Intelligence, Ask Nereus chat, and Graph Explorer.

### v1 Dashboard (Static Fallback)

No external services needed:

```bash
./launch.sh v1
# Or manually:
cd investor_demo
pip install -r requirements.txt
streamlit run streamlit_app.py
```

All versions include a **confidence slider** (Conservative P5 / Base Case Median / Optimistic P95) that updates KPI values and highlights the Monte Carlo distribution.

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

## Implementation Milestones

All development milestones are complete. The platform is production-ready with the v4 Global Scaling Platform as the latest milestone.

---

## Semantica SDK Integration (P0-P4) - Complete

The Semantica framework (v0.2.7+) has been integrated across five priority tiers, adding 27 modules and 690+ new tests. All P0-P4 gaps have been closed.

### P0: Automated Provenance Chains - Complete

- [x] `maris/provenance/` module (7 files) - W3C PROV-O entity/activity/agent tracking
- [x] `BridgeAxiomRegistry` - all 16 axioms as typed BridgeAxiom objects
- [x] `ProvenanceCertificate` - JSON and Markdown certificate generation
- [x] `MARISProvenanceManager` - track_extraction, track_axiom_application, get_lineage
- [x] SHA-256 integrity verification with InMemoryStorage and SQLiteStorage
- [x] `GET /api/provenance/{entity_id}` endpoint registered and functional
- [x] SemanticaBackedManager wired into provenance route with ImportError fallback
- [x] `MARIS_PROVENANCE_DB` config option for SQLite persistence path

### P1: Multi-Site Scaling Pipeline - Complete

- [x] `maris/sites/` module (5 files) - OBIS, WoRMS, Marine Regions API clients
- [x] `SiteCharacterizer` - 5-step pipeline (Locate, Species, Habitat, ESV, Score) with multi-signal habitat scoring (keywords, taxonomy, functional groups)
- [x] Bronze/Silver/Gold tier model with Pydantic v2 models
- [x] ESV estimator with bridge axiom selection by habitat type
- [x] JSON-backed site registry with CRUD operations
- [x] WoRMS 204 No Content fix in `api_clients.py`
- [x] OBIS numeric area ID resolution for geometry lookups
- [x] Marine Regions 404 and JSON error handling

### P2: Cross-Domain Reasoning Engine - Complete

- [x] `maris/reasoning/` module (5 files) - context builder, hybrid retriever, inference engine, rule compiler
- [x] Forward chaining: ecological facts -> financial conclusions
- [x] Backward chaining: financial query -> needed ecological evidence
- [x] Investor-friendly explanation generation with DOI citations
- [x] `open_domain` 6th query category in classifier
- [x] `rule_compiler.py` extracted as separate module from InferenceEngine

### P3: TNFD Disclosure Automation - Complete

- [x] `maris/disclosure/` module (4 files) - full TNFD LEAP generation
- [x] 4-phase LEAP: Locate, Evaluate, Assess, Prepare
- [x] Markdown, JSON, and summary renderers
- [x] 14-disclosure alignment scorer with gap analysis
- [x] `POST /api/disclosure/tnfd-leap` endpoint
- [x] All integration tests passing

### P4: Dynamic Axiom Discovery - Complete

- [x] `maris/discovery/` module (6 files) - pattern detection, LLM-enhanced detection, aggregation, review
- [x] Cross-paper quantitative pattern detector (regex + domain classification)
- [x] `llm_detector.py` - LLM-enhanced pattern detection with regex fallback, retry logic, numeric confidence, robust JSON parsing
- [x] Multi-study aggregation with conflict detection (3+ sources required)
- [x] Candidate axiom formation compatible with bridge_axiom_templates.json
- [x] Human-in-the-loop reviewer with accept/reject workflow
- [x] Phase 6 integration tests (7 tests against live DeepSeek)

### Semantica SDK Bridge Layer

- [x] `maris/semantica_bridge/` package (6 files) - adapter layer wrapping real Semantica SDK
- [x] `SemanticaBackedManager` - drop-in replacement for MARISProvenanceManager with SQLite persistence
- [x] Dual-write provenance: writes to both MARIS and Semantica backends simultaneously
- [x] Graceful degradation when `semantica` package is not installed
- [x] 51 unit tests + 204 integration tests validating all bridge adapters

---

## Implementation Phases (All Complete)

### Document Library + Core System ✅ COMPLETE

- [x] Neo4j knowledge graph (938 nodes, 244 edges, 9 MPA sites)
- [x] FastAPI query engine with 9 endpoints (7 core + provenance + disclosure)
- [x] Streamlit investor dashboards (v1 static, v2 live, v3 intelligence, v4 global scaling)
- [x] NL-to-Cypher classification (5 categories + open_domain)
- [x] 16 bridge axioms with Monte Carlo simulation
- [x] Composite confidence model (GRADE/IPCC-inspired)
- [x] Bearer token auth + rate limiting + CORS
- [x] Multi-stage Docker builds
- [x] GitHub Actions CI pipeline

### Phase 5: Global Scaling (v4) ✅ COMPLETE

- [x] Registry-driven site discovery from `examples/*_case_study.json`
- [x] 9 MPA sites across 4 ocean basins ($1.62B combined portfolio)
- [x] v4 Global Scaling Platform dashboard (6 tabs, port 8504)
- [x] Tier-aware feature gating (Gold/Silver/Bronze)
- [x] LEAPGeneratorV4 with auto-discovery of all case study files
- [x] Unified launcher (`./launch.sh v1|v2|v3|v4|api|stop`)

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
| Bridge axiom coverage | All 16 axioms functional |
| Multi-habitat support | Coral, kelp, mangrove, seagrass |
| Test suite | 910 tests passing (706 unit + 204 integration) |
| API authentication | Bearer token + rate limiting |
| Docker builds | Multi-stage API + Dashboard |
| CI pipeline | GitHub Actions (lint + test) |
| Semantica SDK integration | P0-P4 complete (27 modules, 6-file bridge layer) |
| Provenance tracking | W3C PROV-O with SQLite persistence |
| TNFD disclosure | LEAP automation with 14-disclosure alignment scoring |
| Multi-site scaling | 9 MPA sites, $1.62B portfolio, 4 ocean basins |
| v4 Global Scaling Platform | Registry-driven, 6 tabs, tier-aware feature gating |

---

## Key Files Reference

### Must-Read Files (Priority Order)

| File | Purpose | Read When |
|------|---------|-----------|
| `data/semantica_export/entities.jsonld` | JSON-LD entities for ingestion | **Day 1 - Ingest first** |
| `data/semantica_export/relationships.json` | Typed relationships with provenance | **Day 1 - Ingest second** |
| `data/semantica_export/bridge_axioms.json` | 16 axioms with evidence | **Day 1 - Configure inference** |
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
| `SEMANTICA_HANDOFF_README.md` | Semantica SDK integration guide (P0-P4 modules, bridge layer) |
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
| `investor_demo/streamlit_app_v4.py` | v4 Global Scaling Platform (9 sites, 6 tabs, latest) |
| `investor_demo/streamlit_app_v3.py` | v3 Intelligence Platform (multi-tab) |
| `investor_demo/streamlit_app_v2.py` | v2 dashboard with live API integration |
| `investor_demo/components/v3/` | v3/v4 tab components (intelligence brief, GraphRAG, scenario, TNFD) |
| `launch.sh` | Unified service launcher (v1/v2/v3/v4/api/stop) |
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

**Project Lead:** Jay Gutierrez (Cross-System Architect) - [biome-translator.emergent.host](https://biome-translator.emergent.host/)  
**Semantica Integration:** Mohd Kaif (Lead Developer)  
**Repository:** [github.com/jaygut/semantica-poc](https://github.com/jaygut/semantica-poc)

---

## License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.

---

*Blue Natural Capital Knowledge Engineering - Where ocean science meets investment intelligence.*
