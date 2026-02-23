# Second Site Characterization Plan

> **Status: Completed.** This plan was written when Nereus had one characterized site (Cabo Pulmo). The system now has 9 Gold-tier sites across 4 habitat types. Retained for historical reference.

## Overview

MARIS currently has a single fully characterized reference site (Cabo Pulmo National Park). This document presents a research-backed plan for characterizing a second site to reduce single-point-of-failure risk and demonstrate the system's generalizability.

## Current Single-Site Risk

- **Biomass data**: Cabo Pulmo's flagship recovery metric is from 2009 (17 years old)
- **Tourism data**: Most current (2024 MPpA framework assessment)
- **No post-2011 published biomass survey**: Unknown whether recovery has continued, plateaued, or reversed
- **Single geographic context**: Gulf of California, Mexico - coral reef/rocky reef habitat

## Recommended Second Site: Great Barrier Reef Marine Park

### Why GBR

The Great Barrier Reef Marine Park is the strongest candidate based on five criteria:

1. **Data Availability**: Most extensively studied reef system globally. Multiple published ESV estimates using different methodologies (Deloitte 2017/2023, academic studies)
2. **Existing in MARIS**: Already a comparison site with governance metadata - requires enrichment rather than creation
3. **Bridge Axiom Applicability**: BA-001 (tourism-biomass), BA-004 (flood protection), BA-011 (climate resilience), BA-012 (reef degradation) are directly applicable
4. **Monitoring Infrastructure**: AIMS (Australian Institute of Marine Science) and GBRMPA provide ongoing monitoring data
5. **Risk Case Study**: Bleaching events and Crown of Thorns starfish damage provide real-world risk assessment test cases

### Published ESV Data

| Source | Value | Year | Methodology |
|--------|-------|------|-------------|
| Deloitte Access Economics | A$56B total asset value | 2017 | Economic contribution analysis |
| Deloitte Access Economics | A$95B total asset value | 2023 | Updated economic contribution |
| Academic ESV study | $3.48B/year ESV | 2021 | Ecosystem service valuation |
| Annual economic contribution | A$6.4B-$9B/year | 2017-2023 | Tourism + fisheries + recreation |

### OBIS/WoRMS Coverage

Australia has excellent marine species data coverage through:
- AIMS Long-Term Monitoring Program (coral, fish, invertebrates since 1983)
- GBRMPA monitoring database
- OBIS records for the GBR region
- Allen Coral Atlas satellite-derived habitat maps

### NEOLI Assessment

| Criterion | GBR Status |
|-----------|-----------|
| No-take | Partial - 33% of park is no-take "green zones" |
| Enforced | Yes - GBRMPA active enforcement |
| Old | Yes - established 1975 (51 years) |
| Large | Yes - 344,400 km2 |
| Isolated | Partial - connected reef system |
| NEOLI Score | 3-4/5 depending on zone |

### Bridge Axiom Applicability

| Axiom | Applicable | Notes |
|-------|-----------|-------|
| BA-001 | Yes | $6.4B+ tourism industry, 2M+ visitors/year |
| BA-002 | Yes | Variable by zone - green zones vs general use |
| BA-004 | Yes | Major coral reef system with coastal protection |
| BA-011 | Yes | Extensive bleaching recovery data (2016, 2017, 2020, 2024) |
| BA-012 | Yes | Crown of Thorns damage quantified |
| BA-005-007 | Partial | Some mangrove fringe habitats |

### Implementation Steps

1. **Compile ESV data** into case study JSON format (matching `examples/cabo_pulmo_case_study.json` schema)
   - Tourism: A$6.4B economic contribution (2023)
   - Fisheries: Extract from GBRMPA commercial fishing data
   - Carbon: Blue carbon stocks from published reef + seagrass studies
   - Coastal protection: Apply BA-004 to GBR coastline using Beck et al. 2018 per-km values

2. **Map zoning to NEOLI** - treat each management zone type separately
   - Green zones (no-take): NEOLI 4-5/5
   - Yellow zones (limited use): NEOLI 2-3/5
   - Aggregate park-level score

3. **Extract species data** from AIMS/GBRMPA monitoring databases
   - Key indicator species for reef health
   - Trophic structure from published food web studies

4. **Apply bridge axioms** to derive financial metrics
   - Use zone-specific parameters where available
   - Document uncertainty from benefit transfer

5. **Cross-validate** - compare derived ESV with independent published estimates

### Estimated Effort

- Data compilation: 1-2 weeks (data already published, needs synthesis)
- JSON creation: 2-3 days (following Cabo Pulmo template)
- Population pipeline: 1 day (add GBR population function to `population.py`)
- Validation: 1-2 days (compare derived vs published ESV)
- **Total: 2-3 weeks**

## Alternative Candidates Considered

### Mesoamerican Reef (Belize/Guatemala/Honduras/Mexico)
- **ESV**: $6.2B/year (IDB 2021)
- **Pros**: Recent IDB-funded valuation, transboundary comparison, mangrove habitats
- **Cons**: Multi-country governance complexity, less monitoring infrastructure than GBR
- **Effort**: Medium-High

### Raja Ampat, Indonesia
- **ESV**: Limited site-level data (national-level only)
- **Pros**: Highest marine biodiversity globally, traditional Sasi management
- **Cons**: Remote location, less quantitative ESV data, higher characterization effort
- **Effort**: High

## Data Freshness Requirements

All new site characterizations must include:
- `measurement_year` on all numerical values
- `last_validated_date` for the overall assessment
- `data_freshness_status`: "current" (<5yr), "aging" (5-10yr), "stale" (>10yr)
- Automated staleness warnings in the validation pipeline
