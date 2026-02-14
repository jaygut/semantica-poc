# Semantica × MARIS Knowledge Graph POC

## Handoff Bundle for Mohd Kaif & Semantica Team

**Prepared by:** Jay Gutierrez, Chief Architect - MARIS
**Date:** January 22, 2026
**Bundle Version:** 1.0

---

## 🎯 Executive Summary

This bundle contains everything needed to build a **proof-of-concept Knowledge Graph and GraphRAG system** that demonstrates the "Translation Layer" between marine ecological science and blue finance. The goal is to create a compelling demo for **major partners and investors** in the sustainable ocean finance space.

### The Big Picture

**Problem:** Investors want to fund ocean conservation but can't trust or verify ecological claims.

**Solution:** An AI-powered knowledge graph that provides:
- **Audit-grade provenance** for every ecological claim
- **Quantitative bridges** between ecological metrics and financial outcomes
- **Multi-hop reasoning** across ecology → services → finance domains

### Demo Target Outcome

A query like:
> *"If we protect Site X as a no-take marine reserve, what ecosystem services will improve, by how much, and what is the expected financial return?"*

Returns a structured, sourced answer with confidence intervals and full provenance chain.

---

## 📦 Bundle Contents

```
semantica-poc/
├── SEMANTICA_HANDOFF_README.md          # This file
├── Semantica_POC_Conceptual_Framework.md # Full conceptual architecture
│
├── maris/
│   ├── api/
│   │   ├── main.py                      # FastAPI app factory
│   │   ├── models.py                    # Pydantic v2 request/response schemas
│   │   ├── auth.py                      # Bearer token authentication + rate limiting
│   │   └── routes/                      # health, query, graph endpoints
│   ├── query/
│   │   ├── classifier.py               # NL question classifier (keyword + LLM)
│   │   ├── cypher_templates.py          # Parameterized Cypher templates
│   │   └── validators.py               # LLM response validation pipeline
│   ├── axioms/
│   │   ├── engine.py                    # Bridge axiom computation
│   │   ├── confidence.py               # Multiplicative CI propagation
│   │   ├── monte_carlo.py              # 10,000-run ESV simulation
│   │   └── sensitivity.py              # OAT sensitivity analysis + tornado plots
│   └── graph/                           # Neo4j connection, population, validation
│
├── schemas/
│   ├── entity_schema.json               # JSON-LD entity definitions
│   ├── relationship_schema.json         # Relationship type definitions
│   └── bridge_axiom_templates.json      # Ecological -> Financial bridges (v1.3, 16 axioms)
│
├── data/
│   ├── document_manifest.json           # Prioritized literature list (195 papers)
│   ├── key_papers_for_extraction/       # High-priority papers (manual download)
│   └── sample_extractions/              # Example entity extractions
│
├── examples/
│   ├── cabo_pulmo_case_study.json       # Reference site calibration data
│   └── sample_queries.md                # GraphRAG query examples
│
├── tests/                               # 910-test suite (706 unit + 204 integration)
│
├── investor_demo/
│   └── demo_narrative.md                # Investor pitch narrative
│
├── Dockerfile.api                       # Multi-stage API build (non-root)
├── Dockerfile.dashboard                 # Multi-stage dashboard build (non-root)
└── .github/workflows/ci.yml            # GitHub Actions CI pipeline
```

---

## 🌊 Why This Matters (For Investors)

### Market Opportunity

| Metric | Value |
|--------|-------|
| Global blue economy | $3 trillion/year |
| Blue bond market (2024) | $5.6 billion issued |
| Projected blue finance gap | $175 billion/year by 2030 |
| TNFD adoption | 1,200+ companies committed |

### The Trust Problem

- **Greenwashing concerns** block capital flow to marine conservation
- **No standardized metrics** for ocean asset valuation
- **Fragmented data** across ecology, economics, and finance domains
- **Audit trail gap** - claims can't be independently verified

### Our Solution: The Translation Layer

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ECOLOGICAL DATA LAYER                             │
│  eDNA • Acoustic Surveys • Satellite Imagery • Visual Census        │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                    Semantica Knowledge Graph
                    (Entity Extraction + GraphRAG)
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    BRIDGE AXIOM LAYER                                │
│  "10% biomass increase → 3.46% tourism premium" (with CI & source)  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                    MARIS Translation Pipelines
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FINANCIAL OUTPUT LAYER                            │
│  Blue Bond KPIs • TNFD Disclosure • Biodiversity Credits            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📚 Document Library Summary

### Coverage Statistics

| Category | Papers | Quality |
|----------|--------|---------|
| **Total Documents** | 195 | 92% T1 (peer-reviewed) |
| **Coral Reef** | 21 | Trophic, services, connectivity, climate |
| **Kelp Forest** | 20 | California focus, carbon, restoration |
| **Seagrass** | 15 | Blue carbon, nursery, valuation |
| **Mangrove** | 18 | Carbon, coastal protection, fisheries |
| **Cross-cutting** | 121 | Connectivity, MPA effectiveness, finance |

### Key Papers by Domain

#### Foundational Ecological-Financial Links
1. **Edgar et al. 2014** (Nature) - NEOLI framework for MPA effectiveness
2. **Costanza et al. 1997/2014** (Nature) - Global ecosystem service valuation
3. **Aburto-Oropeza et al. 2011** (PLOS ONE) - Cabo Pulmo 463% biomass recovery
4. **Cowen & Sponaugle 2009** (ARMS) - Marine larval connectivity

#### Critical Value Quantifications
5. **Beck et al. 2018** (Nat Comm) - Coral reefs prevent $272B flood damages
6. **Eger et al. 2023** (Nat Comm) - Kelp forests worth $500B/year globally
7. **Menendez et al. 2020** (Sci Rep) - Mangroves provide $65B/year flood protection
8. **Wilmers et al. 2012** (FEE) - Sea otters generate $205-408M carbon value

#### Blue Finance Mechanisms
9. **Zeng et al. 2025** (Nat Comm) - Mangrove restoration BCR 6.35-15.0
10. **Duarte et al. 2025** (npj Ocean Sust) - Seagrass carbon credits $198-$15,337/ha

---

## 🧬 Entity Extraction Schema

### Core Entity Types

```json
{
  "Species": {
    "external_ids": ["WoRMS_AphiaID", "FishBase_SpecCode", "GBIF_taxonKey"],
    "properties": ["scientific_name", "common_name", "trophic_level", "functional_group"],
    "relationships": ["PREYS_ON", "HABITAT_OF", "INDICATOR_OF"]
  },
  "Habitat": {
    "types": ["coral_reef", "kelp_forest", "seagrass", "mangrove", "rocky_reef"],
    "properties": ["extent_km2", "condition_score", "protection_status"],
    "relationships": ["SUPPORTS_SERVICE", "CONTAINS_SPECIES", "CONNECTED_TO"]
  },
  "EcosystemService": {
    "categories": ["provisioning", "regulating", "cultural", "supporting"],
    "properties": ["value_usd_per_ha_yr", "valuation_method", "confidence_interval"],
    "relationships": ["DEPENDS_ON_HABITAT", "PROVIDES_TO_SECTOR", "MEASURED_BY"]
  },
  "FinancialInstrument": {
    "types": ["blue_bond", "carbon_credit", "biodiversity_credit", "parametric_insurance"],
    "properties": ["value_usd", "term_years", "issuer", "verification_standard"],
    "relationships": ["FUNDED_BY", "PROTECTS_HABITAT", "REPORTS_TO_FRAMEWORK"]
  }
}
```

### Relationship Types

| Relationship | Domain → Range | Cardinality | Example |
|--------------|----------------|-------------|---------|
| `PREYS_ON` | Species → Species | Many:Many | Sheephead → Sea Urchin |
| `CONTROLS_VIA_CASCADE` | Species → Habitat | One:Many | Sea Otter → Kelp Forest |
| `PROVIDES_SERVICE` | Habitat → EcosystemService | One:Many | Mangrove → Coastal Protection |
| `QUANTIFIED_BY` | EcosystemService → Value | One:One | Carbon Seq → $213B at risk |
| `INFORMS_INSTRUMENT` | EcosystemService → FinancialInstrument | Many:Many | Fisheries → Blue Bond KPI |

---

## 🔗 Bridge Axiom Templates (v1.2)

These are the critical **ecological -> financial translation rules** that power the system. Version 1.2 added uncertainty quantification fields to all axiom coefficients: `ci_low`, `ci_high`, `distribution`, `study_sample_size`, and `effect_size_type`. These fields enable Monte Carlo propagation and sensitivity analysis across the full ESV computation.

### Template 1: MPA Biomass-Tourism Link
```json
{
  "axiom_id": "BA-001",
  "name": "fish_biomass_tourism_premium",
  "pattern": "IF biomass_increase(Site, X%) THEN tourism_revenue_increase(Site, Y%)",
  "coefficients": {
    "elasticity": 0.346,
    "confidence_interval": [0.28, 0.41],
    "r_squared": 0.67
  },
  "source": "Wielgus et al. 2010, Ecological Economics",
  "evidence_tier": "T1",
  "applicable_habitats": ["coral_reef", "rocky_reef"]
}
```

### Template 2: Mangrove Flood Protection
```json
{
  "axiom_id": "BA-002",
  "name": "mangrove_flood_protection_value",
  "pattern": "IF mangrove_extent(Site, X_ha) THEN flood_protection_value(Site, Y_usd/yr)",
  "coefficients": {
    "value_per_ha_yr": 4185,
    "range": [239, 10000],
    "decay_rate_cm_per_km": 18
  },
  "source": "Salem & Mercer 2012, Menendez et al. 2020",
  "evidence_tier": "T1",
  "applicable_habitats": ["mangrove"]
}
```

### Template 3: Kelp Carbon-Otter Cascade
```json
{
  "axiom_id": "BA-003",
  "name": "sea_otter_kelp_carbon_cascade",
  "pattern": "IF otter_presence(Site, TRUE) THEN carbon_storage_multiplier(Site, 12x)",
  "coefficients": {
    "carbon_increase_tg": [4.4, 8.7],
    "value_usd_million": [205, 408],
    "npp_with_otters_g_c_m2_yr": [313, 900],
    "npp_without_otters_g_c_m2_yr": [25, 70]
  },
  "source": "Wilmers et al. 2012",
  "evidence_tier": "T1",
  "applicable_habitats": ["kelp_forest"]
}
```

### Template 4: No-Take MPA Effectiveness
```json
{
  "axiom_id": "BA-004",
  "name": "notake_mpa_biomass_multiplier",
  "pattern": "IF mpa_type(Site, 'no_take') AND age_years(Site, >10) THEN biomass_ratio(Site, X)",
  "coefficients": {
    "biomass_ratio_vs_unprotected": 6.7,
    "biomass_ratio_vs_partial": 3.43,
    "recovery_rate_per_year": 0.42
  },
  "source": "Hopf et al. 2024, Sala & Giakoumi 2018",
  "evidence_tier": "T1",
  "applicable_habitats": ["all"]
}
```

---

## 🎓 Calibration Site: Cabo Pulmo

### Why Cabo Pulmo?

Cabo Pulmo National Park (Gulf of California, Mexico) is the **reference AAA condition** for the system because:

1. **Best-documented recovery** - 463% biomass increase in 10 years
2. **Complete protection** - Full NEOLI criteria met
3. **Quantified economic benefits** - Tourism, fisheries spillover data
4. **Research-dense** - Multiple peer-reviewed studies

### Calibration Data

```json
{
  "site_id": "cabo_pulmo_np",
  "coordinates": {"lat": 23.42, "lon": -109.42},
  "protection_status": {
    "no_take": true,
    "enforced": true,
    "old": true,
    "large": false,
    "isolated": true,
    "neoli_score": 4
  },
  "ecological_metrics": {
    "biomass_1999_tonnes_per_ha": 0.5,
    "biomass_2009_tonnes_per_ha": 2.8,
    "recovery_rate": 4.63,
    "apex_predator_density_per_ha": 12.4,
    "trophic_structure": "intact"
  },
  "economic_metrics": {
    "tourism_revenue_usd_per_yr": 25000000,
    "fishing_spillover_value_usd": 3200000,
    "asset_quality_rating": "AAA"
  },
  "sources": [
    "Aburto-Oropeza et al. 2011 PLOS ONE",
    "Aburto-Oropeza et al. 2024 Frontiers"
  ]
}
```

---

## 🔍 Sample GraphRAG Queries

### Query 1: Impact Assessment
```
INPUT: "What happens to ecosystem services if we establish a no-take marine reserve
        in a degraded coral reef area?"

EXPECTED OUTPUT:
Based on 87 MPA studies (Edgar et al. 2014) and meta-analyses:

1. FISH BIOMASS: Expected 670% increase vs. unprotected (95% CI: 450-890%)
   - Timeline: Measurable within 3 years, substantial by 10 years
   - Source: Hopf et al. 2024, T1 evidence

2. TOURISM REVENUE: Expected 25-40% increase
   - Elasticity: 0.346 (biomass → tourism)
   - Source: Wielgus et al. 2010, T1 evidence

3. COASTAL PROTECTION: Reef structural recovery improves wave attenuation
   - Avoided flood damages: Up to $272B globally from coral reefs
   - Source: Beck et al. 2018, T1 evidence

4. CARBON SEQUESTRATION: Reef-associated blue carbon enhancement
   - Dependent on herbivore recovery and algae reduction
   - Source: Mumby et al. 2007, T1 evidence

CONFIDENCE: HIGH (multiple T1 sources, well-documented mechanism)
PROVENANCE: [SHA-256 hashes of source documents]
```

### Query 2: Investment Structuring
```
INPUT: "What ecological KPIs should a $50M blue bond for mangrove restoration use?"

EXPECTED OUTPUT:
Based on blue finance literature and TNFD guidance:

RECOMMENDED KPIs:
1. Mangrove extent (ha) - Baseline + target (Source: Bunting et al. 2022, GMW v3)
2. Carbon stock (Mg C/ha) - Mean 1,023 ± 300 (Source: Donato et al. 2011)
3. Juvenile fish density (ind/m²) - Nursery function proxy (Source: Carrasquilla-Henao 2025)
4. Storm surge attenuation (cm/km) - Coastal protection (Source: Montgomery et al. 2019)

VERIFICATION FRAMEWORK: Verra Nature Framework or Gold Standard
EXPECTED BCR: 6.35-15.0 over 20 years (Source: Zeng et al. 2025)
PERMANENCE RISK: 85% of SE Asian mangroves face some risk (Lovelock et al. 2025)
```

### Query 3: Trophic Cascade Reasoning
```
INPUT: "How does sea otter presence affect kelp forest carbon sequestration?"

EXPECTED OUTPUT:
CAUSAL CHAIN:
1. Sea otters prey on sea urchins (Estes et al. 2021)
2. Urchin populations decline 10-100x in otter-present areas
3. Kelp released from grazing pressure → 12x biomass increase (Wilmers 2012)
4. NPP increases from 25-70 to 313-900 g C/m²/yr
5. Carbon sequestration value: $205-408 million (European Carbon Exchange)

CONTEXT DEPENDENCY: Effect varies by site
- Vancouver Island: Classic cascade observed
- San Nicolas Island: Muted cascade, coexistence at intermediate densities
- Source: Selden et al. 2024 PNAS

FINANCIAL IMPLICATION: Otter conservation → Potential kelp carbon credits
```

---

## 🛠️ Technical Implementation Notes

### API Authentication

All API endpoints except `GET /api/health` require Bearer token authentication. Set `MARIS_API_KEY` in your environment and include the header:

```
Authorization: Bearer <your-api-key>
```

Authentication is skipped when `MARIS_DEMO_MODE=true`. Rate limits apply: 30 queries/minute and 60 other requests/minute per API key.

### Semantica SDK Integration (Implemented)

The Semantica framework (v0.2.7+) is integrated through a 6-file bridge layer in `maris/semantica_bridge/` that wraps the real Semantica SDK behind MARIS's existing API surface. When Semantica is installed, all operations use the SDK; when absent, MARIS gracefully degrades to its native implementations. All P0-P4 integration gaps have been closed on the `feature/semantica-integration` branch, including LLM-enhanced axiom discovery, rule compilation, hardened API clients (WoRMS 204 fix, OBIS area resolution, Marine Regions 404 handling), enhanced multi-signal habitat characterization, and classifier regex gap fixes.

**Bridge Architecture:**

```python
from maris.semantica_bridge import SemanticaBackedManager, SEMANTICA_AVAILABLE

# Drop-in replacement for MARISProvenanceManager with SQLite persistence
manager = SemanticaBackedManager(
    templates_path="schemas/bridge_axiom_templates.json",
    db_path="provenance.db",
)

# Track entity extraction with dual-write (MARIS + Semantica)
manager.track_extraction("cabo_pulmo_esv", "EcosystemService", "10.1371/...")

# Execute translation chains through Semantica's chain system
result = manager.execute_chain(
    axiom_ids=["BA-002", "BA-001"],
    input_data={"biomass_ratio": 4.63, "base_tourism": 25_000_000},
)

# Get provenance certificate (JSON or Markdown)
cert = manager.get_certificate("cabo_pulmo_esv")
```

**Implemented Integration Modules (P0-P4):**

| Module | Package | Key Classes | Status |
|--------|---------|-------------|--------|
| P0: Provenance | `maris/provenance/` (7 files) | `MARISProvenanceManager`, `BridgeAxiomRegistry`, `ProvenanceCertificate` | Complete |
| P1: Site Scaling | `maris/sites/` (5 files) | `SiteCharacterizer`, `OBISClient` (area resolution), `WoRMSClient` (204 fix), `SiteRegistry` | Complete |
| P2: Reasoning | `maris/reasoning/` (5 files) | `InferenceEngine`, `RuleCompiler`, `HybridRetriever`, `ExplanationGenerator` | Complete |
| P3: Disclosure | `maris/disclosure/` (4 files) | `LEAPGenerator`, `AlignmentScorer`, `TNFDLocate/Evaluate/Assess/Prepare` | Complete |
| P4: Discovery | `maris/discovery/` (6 files) | `PatternDetector`, `LLMPatternDetector`, `PatternAggregator`, `AxiomReviewer`, `DiscoveryPipeline` | Complete |
| Bridge | `maris/semantica_bridge/` (6 files) | `SemanticaBackedManager`, `SemanticaStorage`, `SemanticaProvenanceAdapter` | Complete |

---

## Security and Testing

### Authentication and Rate Limiting

- Bearer token authentication on all API endpoints (except health check)
- Rate limiting: 30 queries/minute, 60 other requests/minute per API key
- Authentication is bypassed in demo mode (`MARIS_DEMO_MODE=true`)

### Test Suite

- **910 tests** covering unit and integration scenarios (706 unit + 204 integration)
- 0 ruff lint errors
- CI pipeline via GitHub Actions (`.github/workflows/ci.yml`)
- Unit tests validate graph population, query classification (hardened regex patterns), axiom computation, API endpoints, response formatting, provenance tracking, site scaling (OBIS area resolution, WoRMS 204), reasoning (rule compilation), disclosure, axiom discovery (LLM-enhanced detection), and Semantica SDK bridge adapters
- Integration tests (7 phases) validate SDK availability, graph integrity, external APIs, query pipeline, disclosure generation, stress scenarios, and LLM-enhanced discovery (phase 6 - 7 tests against live DeepSeek)
- 63 precomputed investor demo responses (expanded from 35)

### Production Deployment

- Multi-stage Docker builds (`Dockerfile.api`, `Dockerfile.dashboard`) with non-root runtime users
- Docker Compose orchestration for Neo4j + API + Dashboard

### LLM Response Validation

- `maris/query/validators.py` implements a validation pipeline that checks LLM-generated responses for hallucination, ensuring answers are grounded in graph evidence before returning to users

---

## Development Timeline - Completed

| Phase | Milestone | Deliverable | Status |
|-------|-----------|-------------|--------|
| Phase 0 | Document Library | 195 papers, 92% T1, 16 axioms evidenced | Complete |
| Phase 1-4 | Core System | Neo4j + FastAPI + Streamlit + 220 tests | Complete |
| Blue Carbon | Dual-Site Architecture | Shark Bay ($21.5M ESV) + BA-013 through BA-016 | Complete |
| P0 | Provenance Engine | W3C PROV-O tracking, SQLite persistence, SemanticaBackedManager wired | Complete |
| P1 | Site Scaling | Bronze/Silver/Gold characterization, 3 hardened API clients, multi-signal habitat scoring | Complete |
| P2 | Reasoning Engine | Forward/backward chaining, hybrid retrieval, rule compiler | Complete |
| P3 | TNFD Disclosure | LEAP automation, alignment scoring | Complete |
| P4 | Axiom Discovery | Pattern detection, LLM-enhanced detection, aggregation, review pipeline | Complete |
| Bridge | Semantica SDK | 6-file adapter layer, dual-write provenance | Complete |
| Gap Closure | Final Polish | Classifier regex fixes, hardened LLM detector, 2 API bug fixes, 20 ruff fixes | Complete |
| Testing | Integration Suite | 204 integration tests across 7 phases (incl. LLM discovery) | Complete |

---

## Success Criteria

### Technical
- [x] Entity extraction accuracy >85% on marine ecology domain
- [x] All claims traceable to T1/T2 sources
- [x] Multi-hop queries return in <5 seconds
- [x] Cabo Pulmo correctly rated as "AAA"
- [x] 910 tests passing (706 unit + 204 integration)
- [x] 0 ruff lint errors
- [x] Semantica SDK integration with graceful degradation
- [x] LLM-enhanced axiom discovery with regex fallback
- [x] All P0-P4 integration gaps closed
- [x] 63 precomputed investor demo responses

### Business
- [x] Demo compelling to partners - dual-site investor dashboard operational
- [x] Clear value proposition for blue bond structuring - full ESV provenance chain
- [x] Differentiation from greenwashing claims demonstrable - DOI-backed audit trails
- [x] Foundation for Series A discussion - all P0-P4 gaps closed, production-ready on feature/semantica-integration

---

## 📞 Contact

**Jay Gutierrez**
Chief Architect, MARIS
Email: green-intel@technetium-ia.com

**Mohd Kaif**
Founder, Semantica (Hawksight AI)
GitHub: github.com/Hawksight-AI/semantica

---

## 📎 Appendix: File Manifest

| File | Description | Priority |
|------|-------------|----------|
| `document_index.json` | Full 195-paper bibliography | CRITICAL |
| `entity_schema.json` | JSON-LD entity definitions | CRITICAL |
| `relationship_schema.json` | Relationship type specs | HIGH |
| `bridge_axiom_templates.json` | Ecological-financial bridges | HIGH |
| `cabo_pulmo_case_study.json` | Reference site data | HIGH |
| `sample_queries.md` | GraphRAG query examples | MEDIUM |
| `demo_narrative.md` | Investor pitch script | MEDIUM |

---

*"The ocean doesn't need more data. It needs data that investors can trust and act on."*

*— Semantica × MARIS POC Vision*
