# Semantica × MARIS Handoff Bundle Checklist

**Prepared for:** Mohd Kaif (Semantica Lead Developer)
**Prepared by:** Jay Gutierrez (MARIS Chief Architect)
**Date:** January 22, 2026
**Bundle Version:** 1.0

---

## Quick Start Guide

### 1. Read First (5 minutes)
- [ ] `SEMANTICA_HANDOFF_README.md` - Full vision and implementation guidance

### 2. Understand the Schemas (15 minutes)
- [ ] `schemas/entity_schema.json` - 8 entity types with JSON-LD definitions
- [ ] `schemas/relationship_schema.json` - 14 relationship types with inference rules
- [ ] `schemas/bridge_axiom_templates.json` - 12 core translation axioms

### 3. Review the Examples (20 minutes)
- [ ] `examples/cabo_pulmo_case_study.json` - AAA reference site (this is our calibration target)
- [ ] `examples/sample_queries.md` - GraphRAG query patterns and expected outputs
- [ ] `data/sample_extractions/edgar_2014_extraction.json` - Example entity extraction format

### 4. Plan the Extraction (10 minutes)
- [ ] `data/document_manifest.json` - Prioritized paper list (start with Phase 1 CRITICAL papers)

### 5. Investor Demo Context (10 minutes)
- [ ] `investor_demo/demo_narrative.md` - The pitch we're building toward

---

## Bundle Contents Summary

```
semantica-poc/
├── SEMANTICA_HANDOFF_README.md    # Main documentation (START HERE)
├── BUNDLE_CHECKLIST.md            # This file
├── SYSTEM_OVERVIEW.md             # Original system architecture
│
├── schemas/                       # JSON-LD schemas for Semantica
│   ├── entity_schema.json         # 8 entity types (Species, Habitat, MPA, etc.)
│   ├── relationship_schema.json   # 14 relationship types with inference rules
│   └── bridge_axiom_templates.json # 12 ecological→financial translation rules
│
├── data/
│   ├── document_manifest.json     # 195 papers prioritized for extraction
│   └── sample_extractions/
│       └── edgar_2014_extraction.json  # Example output format
│
├── examples/
│   ├── cabo_pulmo_case_study.json # Reference AAA site (calibration target)
│   └── sample_queries.md          # GraphRAG query patterns
│
└── investor_demo/
    └── demo_narrative.md          # 10-minute investor pitch
```

---

## Key Metrics at a Glance

| Metric | Value |
|--------|-------|
| Total curated papers | 195 |
| Peer-reviewed (T1) | 179 (92%) |
| Entity types defined | 8 |
| Relationship types | 14 |
| Bridge axioms | 12 |
| Habitats covered | 4 (coral, kelp, seagrass, mangrove) |
| Calibration site | Cabo Pulmo (AAA rating) |

---

## Document Library by Habitat

| Habitat | Papers | Key Axioms |
|---------|--------|------------|
| Coral Reef | 21 | BA-001, BA-004, BA-012 |
| Kelp Forest | 20 | BA-003, BA-010, BA-011 |
| Seagrass | 15 | BA-008 |
| Mangrove | 18 | BA-005, BA-006, BA-007, BA-009 |
| Cross-cutting | 121 | BA-002, BA-011 |

---

## Phase 1 Priority Papers (Extract First)

These 5 papers establish the foundational axioms:

1. **Edgar et al. 2014** (Nature) - NEOLI criteria, MPA effectiveness
   - DOI: 10.1038/nature13022
   - Axioms: BA-002, BA-011
   - Sample extraction provided in `data/sample_extractions/`

2. **Aburto-Oropeza et al. 2011** (PLOS ONE) - Cabo Pulmo recovery
   - DOI: 10.1371/journal.pone.0023601
   - Axioms: BA-002
   - Calibration site data

3. **Costanza et al. 2014** (Global Env Change) - Ecosystem service values
   - DOI: 10.1016/j.gloenvcha.2014.04.002
   - Axioms: BA-005, BA-010

4. **Hopf et al. 2024** (Ecological Applications) - No-take MPA biomass
   - DOI: 10.1002/eap.3027
   - Axioms: BA-002

5. **Beck et al. 2018** (Nature Communications) - Coral flood protection
   - DOI: 10.1038/s41467-018-04568-z
   - Axioms: BA-004

---

## Expected Deliverables

### Week 1-2: Schema Validation
- [ ] Import entity/relationship schemas into Semantica
- [ ] Extract entities from Phase 1 papers
- [ ] Validate against Cabo Pulmo case study structure

### Week 3-4: Bridge Axiom Implementation
- [ ] Implement BA-001 through BA-012 as inference rules
- [ ] Test multi-hop queries on Cabo Pulmo data

### Week 5-6: GraphRAG Integration
- [ ] Build query engine for sample queries
- [ ] Achieve <5 second response time for 3-4 hop queries

### Week 7-8: Demo Preparation
- [ ] Complete extraction of all 195 papers
- [ ] Validate investor demo narrative with live queries

---

## External Identifier Registries

For entity linking, use these authoritative sources:

| Entity Type | Registry | URL |
|-------------|----------|-----|
| Species | WoRMS | https://www.marinespecies.org |
| Species | FishBase | https://www.fishbase.org |
| Species | GBIF | https://www.gbif.org |
| MPAs | WDPA | https://www.protectedplanet.net |
| Locations | GeoNames | https://www.geonames.org |

---

## Success Criteria

The system is ready for investor demo when it can:

1. **Answer the Cabo Pulmo query** with full provenance:
   > "What ecosystem services does Cabo Pulmo provide, and what drove its recovery?"

2. **Predict MPA outcomes** using NEOLI + bridge axioms:
   > "If we establish a no-take reserve here, what's the expected ROI?"

3. **Generate Blue Bond KPIs** with literature support:
   > "What metrics should a $50M mangrove bond track?"

4. **Provide audit-grade citations** for every claim:
   > Every number links to DOI + page + quote

---

## Contact

**Questions about the science/business case:**
Jay Gutierrez - green-intel@technetium-ia.com

**Questions about Semantica integration:**
Mohd Kaif - [Hawksight AI]

---

*"The ocean has a trust problem. We're building the solution."*
