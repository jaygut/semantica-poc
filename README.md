# Semantica × MARIS POC

**Marine Asset Risk Intelligence System** — Translating ecological complexity into investment-grade natural capital assets.

[![Status](https://img.shields.io/badge/Status-Design%20Phase-blue)]()
[![Papers](https://img.shields.io/badge/Literature-195%20Papers-green)]()
[![Evidence](https://img.shields.io/badge/T1%20Sources-92%25-brightgreen)]()

---

## Executive Summary

This repository contains the **complete design specification** for a proof-of-concept knowledge graph system that bridges marine ecological science with blue finance frameworks. The goal: enable investors, asset managers, and conservation organizations to make data-driven decisions about marine natural capital with full scientific provenance.

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
| 1 | [`BUNDLE_CHECKLIST.md`](./BUNDLE_CHECKLIST.md) | Quick-start checklist with critical papers |
| 2 | [`schemas/entity_schema.json`](./schemas/entity_schema.json) | JSON-LD entity definitions for ingestion |
| 3 | [`schemas/relationship_schema.json`](./schemas/relationship_schema.json) | Relationship types + inference rules |
| 4 | [`examples/cabo_pulmo_case_study.json`](./examples/cabo_pulmo_case_study.json) | AAA reference site for validation |
| 5 | [`data/sample_extractions/`](./data/sample_extractions/) | Example entity extractions |

### Day 1 Tasks

```bash
# 1. Ingest the entity schema
semantica ingest schemas/entity_schema.json

# 2. Load the reference case study
semantica load examples/cabo_pulmo_case_study.json

# 3. Test a simple query
semantica query "What ecological factors explain Cabo Pulmo's recovery?"

# 4. Validate bridge axiom BA-001 (biomass → tourism)
semantica validate --axiom BA-001 --site cabo_pulmo
```

### Critical Papers for Week 1 Extraction

| Paper | Why Critical | Target Axioms |
|-------|--------------|---------------|
| Edgar et al. 2014 | NEOLI framework (MPA effectiveness) | BA-002 |
| Aburto-Oropeza et al. 2011 | Cabo Pulmo recovery data | BA-001, BA-002 |
| Costanza et al. 2014 | Global ES valuation methods | All service axioms |
| Hopf et al. 2024 | No-take MPA biomass multipliers | BA-002 |
| Beck et al. 2018 | Coral reef flood protection | BA-004 |

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
| Entity Schema | `schemas/entity_schema.json` | JSON-LD | 8 entity types with external IDs |
| Relationship Schema | `schemas/relationship_schema.json` | JSON | 14 relationship types + inference rules |
| Bridge Axioms | `schemas/bridge_axiom_templates.json` | JSON | 12 ecological→financial translations |
| Document Library | `.claude/registry/document_index.json` | JSON | 195 indexed papers with metadata |
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
│   └── sample_extractions/
│       ├── aburto_2011_extraction.json    # Cabo Pulmo extraction
│       └── edgar_2014_extraction.json     # NEOLI framework extraction
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

### Composition

```
Total Papers:        195
Evidence Quality:    92% T1 (peer-reviewed), 8% T2 (institutional)

By Domain:
├── Trophic Ecology      42 papers   (food webs, cascades, keystone species)
├── Connectivity         35 papers   (larval dispersal, MPA networks)
├── Blue Finance         35 papers   (bonds, credits, mechanisms)
├── Restoration          24 papers   (coral, kelp, seagrass, mangrove)
├── Ecosystem Services   28 papers   (valuation methods)
├── Blue Carbon          22 papers   (sequestration, stocks)
├── MPA Effectiveness    18 papers   (NEOLI, reserve outcomes)
├── Measurement Methods  18 papers   (eDNA, acoustic, satellite)
└── Climate Resilience   12 papers   (thermal tolerance, refugia)

By Habitat:
├── Coral Reef           21 papers
├── Kelp Forest          20 papers
├── Mangrove             18 papers
├── Seagrass             15 papers
└── General/Multiple    121 papers
```

### Evidence Tier System

| Tier | Classification | Count | Usage |
|------|----------------|-------|-------|
| **T1** | Peer-reviewed journals | 179 | Cite without qualification |
| **T2** | Institutional reports (World Bank, UN, IPBES) | 16 | Cite with context |
| **T3** | Data repositories (GBIF, OBIS) | 0 | Cite with methodology |
| **T4** | Preprints/grey literature | 0 | Cite with caveats |

---

## Registry Spec & Ingestion Agreement

This registry is the ingestion contract for Semantica. It is the single source of truth for document metadata and retrieval.

**Registry file:** `.claude/registry/document_index.json`

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

### Phase 1: Foundation (Weeks 1-2)

- [ ] Ingest `entity_schema.json` into Semantica
- [ ] Ingest `relationship_schema.json` with inference rules
- [ ] Extract entities from 5 CRITICAL papers
- [ ] Load Cabo Pulmo case study
- [ ] Validate basic queries return provenance

### Phase 2: Knowledge Graph (Weeks 3-4)

- [ ] Implement BA-001 through BA-012 as inference rules
- [ ] Extract entities from Phase 2-3 papers (15 papers)
- [ ] Build trophic network subgraph
- [ ] Test cascade reasoning (otter → kelp → carbon)

### Phase 3: GraphRAG Interface (Weeks 5-6)

- [ ] Implement all 11 sample queries
- [ ] Add confidence scoring to responses
- [ ] Build provenance visualization
- [ ] Test TNFD disclosure field population

### Phase 4: Validation & Demo (Weeks 7-8)

- [ ] Extract remaining papers (175 papers)
- [ ] Validate against Cabo Pulmo metrics (±20% tolerance)
- [ ] Run investor demo narrative
- [ ] Document API endpoints

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

### Must-Read Files

| File | Purpose | Read When |
|------|---------|-----------|
| `BUNDLE_CHECKLIST.md` | Quick-start guide | Day 1 |
| `schemas/entity_schema.json` | Entity definitions | Before ingestion |
| `schemas/relationship_schema.json` | Relationships + inference | Before ingestion |
| `examples/cabo_pulmo_case_study.json` | Validation target | During testing |
| `examples/sample_queries.md` | Query templates | During GraphRAG dev |

### Reference Files

| File | Purpose |
|------|---------|
| `Semantica_POC_Conceptual_Framework.md` | Full conceptual architecture (35KB) |
| `SYSTEM_OVERVIEW.md` | Detailed system design |
| `SEMANTICA_HANDOFF_README.md` | Integration instructions |
| `data/document_manifest.json` | 195-paper extraction priority list |
| `.claude/registry/document_index.json` | Full bibliography with metadata |

### Utility Scripts

| Script | Purpose |
|--------|---------|
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
