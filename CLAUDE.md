# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Semantica × MARIS POC** (Proof of Concept) - a project to build an AI-powered knowledge integration system bridging marine ecological science with blue finance. The core deliverable is **MARIS** (Marine Asset Risk Intelligence System), which translates ecological complexity into investment-grade natural capital assets.

**Current Status:** Active development. The repository contains a comprehensive conceptual framework, upgraded SKILLS system, and document registry with 195 verified papers.

## Quick Start Commands

### Registry Maintenance (Run First)

```bash
# Validate registry integrity
/validate-registry --fix --verbose

# Enrich missing abstracts
/enrich-abstracts

# Fetch document content
/fetch-documents --tier T1 --report
```

### Literature Discovery

```bash
# Search by domain
/search-literature trophic --depth deep --tiers T1,T2
/search-literature blue-finance --depth deep --tiers T1,T2

# Build comprehensive library
/build-library --mode expand --target-count 195
```

### Knowledge Extraction

```bash
# Extract from specific document
/extract-knowledge edgar_2014_nature_mpa_neoli

# Batch extraction
/extract-knowledge --batch --priority high
```

### Full Pipeline

```bash
# End-to-end Semantica preparation
/semantica-pipeline --phase all
```

## Architecture

The system follows a **Three-Layer Translation Model**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              THE TRUST BRIDGE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   LAYER 1: ECOLOGICAL       BRIDGE AXIOMS        LAYER 3: FINANCIAL        │
│   ─────────────────────     ─────────────        ─────────────────         │
│   Species, Habitats    →    12 Translation   →   Blue Bonds, TNFD          │
│   MPAs, Observations        Rules (BA-001+)      Credits, Insurance        │
│                                                                             │
│                    LAYER 2: ECOSYSTEM SERVICES                              │
│                    ───────────────────────────                              │
│                    Provisioning, Regulating, Cultural                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Command Reference

### Registry Maintenance Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/validate-registry` | Check integrity, fix statistics | After any registry changes |
| `/enrich-abstracts` | Populate missing abstracts | Before entity extraction |
| `/fetch-documents` | Download paper content | Before extraction, after discovery |

### Literature Discovery Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/search-literature` | Find papers by domain | Expanding library |
| `/build-library` | Automated library expansion | Initial setup or major expansion |

### Knowledge Extraction Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/extract-knowledge` | Extract entities from papers | After documents are fetched |

### Pipeline Commands

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/semantica-pipeline` | Full end-to-end pipeline | Final export to Semantica |

## Key Files

### Schemas (Ingest First)

| File | Purpose |
|------|---------|
| `schemas/entity_schema.json` | 8 entity types (JSON-LD) |
| `schemas/relationship_schema.json` | 14 relationship types + inference |
| `schemas/bridge_axiom_templates.json` | 12 translation rules |
| `schemas/registry_schema.json` | Document validation schema |

### Registry & Data

| File | Purpose |
|------|---------|
| `.claude/registry/document_index.json` | Master bibliography (195 papers) |
| `data/sample_extractions/` | Example entity extractions |
| `examples/cabo_pulmo_case_study.json` | AAA reference validation site |

### Scripts

| File | Purpose |
|------|---------|
| `scripts/validate_registry.py` | Registry validation with auto-fix |
| `scripts/enrich_abstracts.py` | 5-tier abstract enrichment |
| `scripts/fetch_documents.py` | Document fetcher with retry logic |

## Domain Context

**Target Library:** 195 papers across 9 domains
- Trophic Ecology (42), Connectivity (35), Blue Finance (35)
- Restoration (24), Ecosystem Services (28), Blue Carbon (22)
- MPA Effectiveness (18), Measurement Methods (18), Climate Resilience (12)

**Calibration Site:** Cabo Pulmo (Gulf of California) - AAA reference condition
- 463% biomass recovery, 4/5 NEOLI criteria, $29.27M annual ecosystem services

**Evidence Tier System:**
- T1: Peer-reviewed (cite without qualification)
- T2: Institutional reports (cite with context)
- T3: Data repositories (cite with methodology)
- T4: Preprints (cite with caveats)

## Success Criteria

| Criterion | Target | Validation |
|-----------|--------|------------|
| Document library | 195 papers, 92% T1 | `/validate-registry` |
| DOI coverage | 100% | `/validate-registry` |
| Abstract coverage | ≥80% | `/validate-registry` |
| Cabo Pulmo accuracy | ±20% of published | Query validation |
| Bridge axiom evidence | 12 axioms × 3+ sources | Provenance audit |

## Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview and quick start |
| `ai_docs/PIPELINE_RECONSTRUCTION_STRATEGY.md` | End-to-end reconstruction guide |
| `ai_docs/SKILLS_REMEDIATION_REPORT.md` | SKILLS system fixes documentation |
| `ai_docs/SKILLS_SYSTEM_AUDIT.md` | Comprehensive audit findings |
| `SEMANTICA_HANDOFF_README.md` | Integration guide for Semantica team |
