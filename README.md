# Semantica × MARIS POC

**Marine Asset Risk Intelligence System** — Translating ecological complexity into investment-grade natural capital assets.
**Blue Natural Capital Knowledge Engineering** — Where ocean science meets investment intelligence.

[![Status](https://img.shields.io/badge/Status-Library%20Complete-brightgreen)]()
[![Papers](https://img.shields.io/badge/Literature-195%20Papers-green)]()
[![Evidence](https://img.shields.io/badge/T1%20Sources-92%25-brightgreen)]()
[![Abstracts](https://img.shields.io/badge/Abstracts-67%25-yellow)]()
[![Axioms](https://img.shields.io/badge/Bridge%20Axioms-12%2F12-brightgreen)]()

---

## Executive Summary

This repository contains the **complete knowledge foundation** for a proof-of-concept knowledge graph system that bridges marine ecological science with blue finance frameworks. The goal: enable investors, asset managers, and conservation organizations to make data-driven decisions about marine natural capital with full scientific provenance.

**Current Status:** The document library reconstruction is complete with **195 verified papers**, **5 critical paper extractions**, and a **Semantica-ready export bundle** containing 14 entities, 15 relationships, and 12 fully-evidenced bridge axioms.

**The Problem:** A $175B annual funding gap exists for ocean conservation. Investors can't trust opaque ecological claims. Scientists can't translate their findings into financial terms. The result: capital doesn't flow to where it's needed.

**The Solution:** MARIS — a knowledge graph powered by Semantica that creates auditable, traceable pathways from peer-reviewed ecological data to investment-grade financial metrics.

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

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MARIS SYSTEM ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  LITERATURE │    │   ENTITY    │    │  KNOWLEDGE  │    │   GRAPHRAG  │  │
│  │   LIBRARY   │ →  │ EXTRACTION  │ →  │    GRAPH    │ →  │   QUERIES   │  │
│  │  (195 T1/T2)│    │  (LLM-based)│    │ (Semantica) │    │  (MARIS)    │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│        ↓                  ↓                  ↓                  ↓          │
│   document_index    sample_extractions   entity_schema    sample_queries   │
│                                          relationship     cabo_pulmo       │
│                                          bridge_axioms    demo_narrative   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                              DATA FLOW                                      │
│                                                                             │
│   Papers → Entities → Relationships → Bridge Axioms → Financial Outputs    │
│     ↓          ↓           ↓              ↓                ↓               │
│   DOIs     Species     PREYS_ON      Biomass→$        Bond KPIs            │
│   URLs     Habitats    PROVIDES      Carbon→$         TNFD Fields          │
│   Quotes   MPAs        FUNDS         Tourism→$        Credit Prices        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component | Location | Format | Purpose |
|-----------|----------|--------|---------|
| **Entities** | `data/semantica_export/entities.jsonld` | JSON-LD | 14 entities with WoRMS/FishBase/TNFD URIs |
| **Relationships** | `data/semantica_export/relationships.json` | JSON | 15 relationship types with provenance |
| **Bridge Axioms** | `data/semantica_export/bridge_axioms.json` | JSON | 12 axioms with 3+ evidence sources each |
| **Corpus Summary** | `data/semantica_export/document_corpus.json` | JSON | 195-paper library statistics |
| Document Library | `.claude/registry/document_index.json` | JSON | 195 indexed papers with full metadata |
| Critical Extractions | `data/sample_extractions/` | JSON | 5 papers with entities/relationships |
| Reference Case | `examples/cabo_pulmo_case_study.json` | JSON | AAA-rated validation site |
| Query Templates | `examples/sample_queries.md` | Markdown | 11 GraphRAQ query examples |

---

## Repository Structure

```
semantica-poc/
│
├── README.md                              # This file
├── CLAUDE.md                              # Claude Code instructions
├── SYSTEM_OVERVIEW.md                     # Detailed architecture docs
├── SEMANTICA_HANDOFF_README.md            # Integration guide
├── BUNDLE_CHECKLIST.md                    # Quick-start checklist
├── Semantica_POC_Conceptual_Framework.md  # Full conceptual framework (35KB)
│
├── schemas/                               # ═══ INGEST THESE FIRST ═══
│   ├── entity_schema.json                 # 8 entity types (JSON-LD)
│   ├── relationship_schema.json           # 14 relationship types
│   └── bridge_axiom_templates.json        # 12 translation rules
│
├── data/
│   ├── document_manifest.json             # 195 papers, prioritized
│   ├── papers/                            # Local fetch cache (gitignored)
│   ├── sample_extractions/                # ═══ 5 CRITICAL PAPER EXTRACTIONS ═══
│   │   ├── aburto_2011_extraction.json    # Cabo Pulmo 463% recovery
│   │   ├── edgar_2014_extraction.json     # NEOLI framework
│   │   ├── costanza_2014_extraction.json  # Global ES valuation ($125T)
│   │   ├── hopf_2024_extraction.json      # No-take meta-analysis (2.7×)
│   │   └── beck_2018_extraction.json      # Coral flood protection ($4B)
│   └── semantica_export/                  # ═══ SEMANTICA-READY BUNDLE ═══
│       ├── entities.jsonld                # 14 entities (JSON-LD)
│       ├── relationships.json             # 15 relationships
│       ├── bridge_axioms.json             # 12 axioms with evidence
│       └── document_corpus.json           # Corpus summary
│
├── examples/
│   ├── cabo_pulmo_case_study.json         # AAA reference (validation target)
│   └── sample_queries.md                  # 11 GraphRAG query templates
│
├── investor_demo/
│   └── demo_narrative.md                  # 10-minute pitch script
│
└── .claude/                               # Agentic workflow system
    ├── skills/                            # Domain knowledge
    │   ├── literature-scout/              # Search & verification
    │   └── kg-architect/                  # Schema design
    ├── commands/                          # Workflow entry points
    ├── agents/                            # Parallel execution specs
    └── registry/                          # Document database
        ├── document_index.json            # Master bibliography
        └── reports/                       # Pipeline reports
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

### Phase 0: Document Library Reconstruction ✅ COMPLETE

- [x] Validate initial registry (70 papers)
- [x] Enrich abstracts via CrossRef/OpenAlex/Semantic Scholar APIs
- [x] Expand library to 195 papers across 10 domains
- [x] Extract knowledge from 5 critical papers
- [x] Generate Semantica export bundle (4 files)
- [x] Evidence 12 bridge axioms with 3+ sources each

### Phase 1: Foundation (Weeks 1-2)

**Week 1:**
- [x] `maris/__init__.py` ✅ - Package initialization
- [x] `maris/config.py` ✅ - Configuration management
- [ ] `maris/utils.py` - Utility functions (Week 1)
- [ ] `maris/schemas.py` - Schema loading utilities (Week 1-2)
- [ ] `config/config.yaml` - Configuration file (Week 1)
- [ ] `config/.env.example` - Environment variables template (Week 1)

**Week 2:**
- [ ] `maris/semantica_integration.py` - Main Semantica integration (Week 1-2)
- [ ] Ingest `entities.jsonld` into Semantica
- [ ] Ingest `relationships.json` with inference rules
- [ ] Load Cabo Pulmo case study
- [ ] Validate basic queries return provenance

### Phase 2: Data Loading & Processing (Weeks 2-3)

**Week 2-3:**
- [ ] `maris/data_loader.py` - Load existing Semantica export bundle (Week 2-3)
- [ ] `maris/document_processor.py` - Document ingestion (Week 2-3)
- [ ] `maris/provenance.py` - Provenance tracking (Week 2-3)
- [ ] Index document corpus into Semantica
- [ ] Validate data integrity

### Phase 3: Extraction (Weeks 3-5)

**Week 3-4:**
- [ ] `maris/entity_extractor.py` - Entity extraction pipeline (Week 3-5)
- [ ] `tests/test_entity_extraction.py` - Entity extraction tests (Week 3-5)
- [x] Extract entities from 5 CRITICAL papers ✅
- [ ] Extract entities from remaining high-priority papers (50+ papers)
- [ ] Achieve >85% extraction accuracy

**Week 4-5:**
- [ ] `maris/relationship_extractor.py` - Relationship extraction (Week 3-5)
- [ ] `tests/test_relationship_extraction.py` - Relationship extraction tests (Week 3-5)
- [ ] Build trophic network subgraph
- [ ] Extract habitat-service links
- [ ] Extract MPA-effectiveness relationships

### Phase 4: Bridge Axioms (Weeks 6-7)

**Week 6:**
- [ ] `maris/bridge_axiom_engine.py` - Bridge axiom application engine (Week 6-7)
- [ ] `tests/test_bridge_axioms.py` - Bridge axiom tests (Week 6-7)
- [x] Define BA-001 through BA-012 with coefficients ✅
- [ ] Implement bridge axioms as inference rules in Semantica
- [ ] Test axiom pattern matching

**Week 7:**
- [ ] `maris/validators.py` - Validation utilities (Week 6-7, Week 13-14)
- [ ] `tests/test_cabo_pulmo_validation.py` - Cabo Pulmo validation tests (Week 6-7, Week 13-14)
- [x] Validate Cabo Pulmo metrics (463% ±20% tolerance) ✅
- [ ] Test cascade reasoning (otter → kelp → carbon)
- [ ] Validate all 12 bridge axioms

### Phase 5: GraphRAG Query Interface (Weeks 8-10)

**Week 8-9:**
- [ ] `maris/query_engine.py` - GraphRAG query interface (Week 8-10)
- [ ] `tests/test_query_engine.py` - Query engine tests (Week 8-10)
- [ ] Configure Semantica GraphRAG interface
- [ ] Implement multi-hop reasoning (up to 4 hops)
- [ ] Implement all 11 sample queries

**Week 10:**
- [ ] Add confidence scoring to responses
- [ ] Build provenance visualization
- [ ] Test TNFD disclosure field population
- [ ] Validate query latency <5 seconds

### Phase 5: Knowledge Graph Construction (Weeks 11-12)

**Week 11:**
- [ ] `maris/graph_builder.py` - Knowledge graph construction (Week 11-12)
- [ ] Set up graph database (Neo4j or Semantica native)
- [ ] Create entity nodes from extracted entities
- [ ] Create relationship edges

**Week 12:**
- [ ] Apply bridge axioms as graph inference rules
- [ ] Build trophic network subgraphs
- [ ] Create MPA network connectivity graphs
- [ ] Validate graph integrity

### Phase 6: CLI & Testing (Weeks 13-14)

**Week 13:**
- [ ] `maris/cli.py` - Command-line interface (Week 13-14)
- [ ] `tests/test_integration.py` - Integration tests (Week 13-14)
- [ ] Implement all CLI commands
- [ ] Test end-to-end pipeline

**Week 14:**
- [ ] Process remaining papers for entity extraction
- [ ] Run investor demo narrative
- [ ] Validate all success criteria
- [ ] Performance testing and optimization

### Phase 7: Documentation (Week 15)

**Week 15:**
- [ ] `docs/api_reference.md` - API documentation (Week 15)
- [ ] `docs/user_guide.md` - User guide (Week 15)
- [ ] `docs/developer_guide.md` - Developer guide (Week 15)
- [ ] Document API endpoints
- [ ] Finalize all documentation

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

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/validate_registry.py` | Validate registry structure and statistics |
| `scripts/enrich_abstracts.py` | Fetch abstracts via CrossRef/OpenAlex/Semantic Scholar |
| `scripts/add_papers_batch.py` | Batch paper addition to registry |
| `.claude/skills/literature-scout/scripts/verify_url.py` | URL/DOI verification |
| `.claude/skills/literature-scout/scripts/update_registry.py` | Registry management |

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
