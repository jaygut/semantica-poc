# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Semantica × MARIS POC** (Proof of Concept) - a project to build an AI-powered knowledge integration system bridging marine ecological science with blue finance. The core deliverable is **MARIS** (Marine Asset Risk Intelligence System), which translates ecological complexity into investment-grade natural capital assets.

**Current Status:** Pre-development / Design phase. The repository contains a comprehensive conceptual framework document but no source code yet.

## Architecture

The system follows a **Three-Layer Translation Model**:

1. **Layer 1 - Ecological Foundations**: Structural biodiversity, functional ecology (processes), relational ecology (networks), spatial-temporal dynamics
2. **Layer 2 - Ecosystem Services**: Provisioning (fisheries), regulating (coastal protection), cultural (tourism), supporting (habitat/nursery)
3. **Layer 3 - Financial Instruments**: Blue bonds, TNFD disclosure, biodiversity credits, parametric insurance

**Semantic Bridge**: Semantica's semantic infrastructure powers the translation between layers using knowledge graphs and GraphRAG for multi-hop reasoning.

## Key Technical Components (Planned)

- **Ontology**: Marine ecosystem ontology with entity classes (Species, Habitat, Population, Community) and relationship types linking ecology → services → finance
- **Provenance**: PROV-O schema for data lineage and cryptographic checksums
- **Data Sources**: FishBase, WoRMS (taxonomy), OBIS, GloBI (interactions), AquaMaps, BGC-Argo, dataMares, SBC LTER
- **Frameworks**: TNFD, ESRS E4, SEEA-EA, SBTN for disclosure/reporting

## Domain Context

**Calibration Sites:**
- Cabo Pulmo (Gulf of California) - reference AAA condition
- California kelp forest ecosystems (Santa Barbara Channel, Channel Islands)

**Key Metrics:**
- NRSI (Normalized Reef Status Index)
- Asset Quality Rating (AQR) pipeline
- Tourism-biodiversity elasticity model

## Implementation Phases

| Phase | Focus | Duration |
|-------|-------|----------|
| 1 | Foundation - Ontology ingestion, FishBase/WoRMS/GloBI data loading | Weeks 1-2 |
| 2 | Ecological Knowledge Layer - Trophic networks, NRSI calculation | Weeks 3-4 |
| 3 | Financial Translation Layer - TNFD mappings, AQR pipeline | Weeks 5-6 |
| 4 | Query & Validation - GraphRAG interface, provenance visualization | Weeks 7-8 |

## Success Criteria

- Traceable queries returning structured, sourced answers with confidence intervals
- Cabo Pulmo correctly classified as AAA reference condition
- Ecosystem service valuations align with published estimates (±20%)
- TNFD disclosure fields populated from ecological data
