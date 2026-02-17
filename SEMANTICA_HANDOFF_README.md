# Nereus - Semantica Integration Guide

## Overview

This document describes how the **Semantica SDK** is integrated into the Nereus platform (powered by MARIS + Semantica). The integration spans 5 priority tiers (P0-P4) with 27 modules and a 6-file bridge layer, enabling W3C PROV-O provenance tracking, multi-site scaling, cross-domain reasoning, TNFD disclosure automation, and dynamic axiom discovery.

**Integration Status:** Complete. All P0-P4 gaps are closed, validated by 910 tests (706 unit + 204 integration).

---

## Architecture

Nereus uses a 6-file adapter layer (`maris/semantica_bridge/`) that wraps the real Semantica SDK behind MARIS's existing API surface. When Semantica is installed, all operations use the SDK; when absent, MARIS gracefully degrades to its native implementations.

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

---

## Integration Modules (P0-P4)

### P0: Automated Provenance Chains

`maris/provenance/` (7 files) - W3C PROV-O entity/activity/agent tracking with SQLite persistence.

| Component | Purpose |
|-----------|---------|
| `MARISProvenanceManager` | Track extraction, axiom application, get lineage |
| `BridgeAxiomRegistry` | All 16 axioms as typed BridgeAxiom objects |
| `ProvenanceCertificate` | JSON and Markdown certificate generation |
| `InMemoryStorage` + `SQLiteStorage` | Dual storage backends |
| SHA-256 integrity verification | Checksum for all tracked entities |

**API endpoint:** `GET /api/provenance/{entity_id}` - returns lineage and certificate.

### P1: Multi-Site Scaling Pipeline

`maris/sites/` (5 files) - OBIS, WoRMS, Marine Regions API clients with hardened error handling.

| Component | Purpose |
|-----------|---------|
| `SiteCharacterizer` | 5-step pipeline: Locate, Species, Habitat, ESV, Score |
| `OBISClient` | Area resolution for geometry lookups |
| `WoRMSClient` | 204 No Content fix for empty responses |
| `MarineRegionsClient` | 404 and malformed JSON handling |
| Bronze/Silver/Gold tier model | Progressive characterization depth |

The v4 platform auto-discovers all 9 Gold-tier sites from `examples/*_case_study.json` via `maris/services/ingestion/discovery.py`.

### P2: Cross-Domain Reasoning Engine

`maris/reasoning/` (5 files) - Forward/backward chaining with bridge axiom rules.

| Component | Purpose |
|-----------|---------|
| `InferenceEngine` | Forward chaining (ecological -> financial) and backward chaining (financial -> ecological evidence) |
| `RuleCompiler` | Rule compilation extracted from InferenceEngine |
| `HybridRetriever` | Graph + keyword + Reciprocal Rank Fusion retrieval |
| `ContextBuilder` | Convert Neo4j results to Semantica ContextGraph |
| `ExplanationGenerator` | Investor-friendly explanation with DOI citations |

### P3: TNFD Disclosure Automation

`maris/disclosure/` (5 files) - Full TNFD LEAP generation with alignment scoring.

| Component | Purpose |
|-----------|---------|
| `LEAPGenerator` | 4-phase TNFD LEAP: Locate, Evaluate, Assess, Prepare |
| `LEAPGeneratorV4` | v4 variant with auto-discovered sites |
| `AlignmentScorer` | 14-disclosure gap analysis |
| Renderers | Markdown, JSON, and executive summary output |

**API endpoint:** `POST /api/disclosure/tnfd-leap` - generate LEAP disclosure for any site.

### P4: Dynamic Axiom Discovery

`maris/discovery/` (6 files) - Cross-paper pattern detection and axiom formation.

| Component | Purpose |
|-----------|---------|
| `PatternDetector` | Regex-based cross-paper quantitative pattern detection |
| `LLMPatternDetector` | LLM-enhanced detection with regex fallback, retry logic, numeric confidence |
| `PatternAggregator` | Multi-study aggregation with conflict detection (3+ sources required) |
| `CandidateAxiom` | Formation compatible with `bridge_axiom_templates.json` |
| `AxiomReviewer` | Human-in-the-loop accept/reject workflow |

### Semantica SDK Bridge Layer

`maris/semantica_bridge/` (6 files) - Adapter layer wrapping the real Semantica SDK.

| File | Purpose |
|------|---------|
| `storage_adapter.py` | `SemanticaStorage` wrapping SDK storage |
| `axiom_adapter.py` | MARIS <-> Semantica axiom conversion + chaining |
| `provenance_adapter.py` | Dual-write provenance (MARIS + Semantica backends) |
| `integrity_adapter.py` | SDK-backed integrity verification |
| `manager.py` | `SemanticaBackedManager` - drop-in replacement with SQLite persistence |

---

## Semantica Export Bundle

The curated data is exported in four files for Semantica ingestion, located in `data/semantica_export/`:

| File | Format | Contents |
|------|--------|----------|
| `entities.jsonld` | JSON-LD | 14 entities with WoRMS/FishBase/TNFD URIs |
| `relationships.json` | JSON | 15 typed edges with provenance |
| `bridge_axioms.json` | JSON | 16 axioms with evidence mapping |
| `document_corpus.json` | JSON | 195-paper corpus summary |

These files are also consumed directly by the Neo4j v4 population pipeline (`scripts/populate_neo4j_v4.py`).

---

## Knowledge Foundation

### Document Library

195 papers across 9 domains, 92% peer-reviewed (T1). Full bibliography in `.claude/registry/document_index.json`.

### Bridge Axioms (16)

12 core axioms (reef, MPA, mangrove, kelp) + 4 blue carbon axioms (BA-013 through BA-016). All 16 have 3+ supporting sources. Templates with uncertainty quantification (CI, distribution, sample size) in `schemas/bridge_axiom_templates.json`.

### Site Portfolio ($1.62B)

9 Gold-tier MPA sites across 4 ocean basins and 4 habitat types:

| Site | Habitat | ESV |
|------|---------|-----|
| Cabo Pulmo National Park | Coral reef | $29.27M |
| Shark Bay World Heritage Area | Seagrass | $21.5M |
| Ningaloo Coast | Coral reef | $145.0M |
| Belize Barrier Reef | Coral reef + mangrove | $395.0M |
| Galapagos Marine Reserve | Mixed/volcanic | $285.0M |
| Raja Ampat MPA Network | Coral reef | $362.0M |
| Sundarbans Reserve Forest | Mangrove | $187.0M |
| Aldabra Atoll | Coral reef/atoll | $78.0M |
| Cispata Bay MPA | Mangrove | $139.0M |

---

## v4 Global Scaling Platform

The **v4 dashboard** (`investor_demo/streamlit_app_v4.py`) is the primary investor demo surface. It runs at `http://localhost:8504` with 6 tabs:

| Tab | Content |
|-----|---------|
| Portfolio Overview | **[NEW] Global 3D Map** + Grid of all 9 sites with ESV, rating, habitat, tier indicators |
| Analytics | **[NEW] Multi-Site Comparison** with Radar (scoring) & Bar (valuation) charts |
| Intelligence Brief | Per-site KPIs, provenance graph, axiom evidence, risk profile |
| Ask Nereus (GraphRAG) | **[NEW] Context-aware** chat with site-specific queries + pipeline transparency |
| Scenario Lab | Interactive Monte Carlo with site-aware axiom chains, tornado sensitivity |
| Site Scout | Deferred placeholder |
| TNFD Compliance | LEAP disclosure with **[NEW] PDF Export** & alignment scoring for all 9 sites |

Launch with `./launch.sh v4` or manually:

```bash
uvicorn maris.api.main:app --host 0.0.0.0 --port 8000
cd investor_demo && streamlit run streamlit_app_v4.py --server.port 8504
```

---

## Testing

910 tests (706 unit + 204 integration) validating all integration modules:

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Integration tests (`tests/integration/`) cover 7 phases: SDK availability, graph integrity, external APIs, query pipeline, disclosure/discovery, stress tests, and LLM-enhanced discovery (7 tests against live DeepSeek).
A new **Live Ingestion Test** (`tests/integration/test_live_ingestion.py`) verifies the end-to-end `CaseStudyLoader` against a real Neo4j instance.

CI runs on push/PR to `main` via GitHub Actions: ruff lint + pytest.

---

## Production Deployment

- Multi-stage Docker builds (`Dockerfile.api`, `Dockerfile.dashboard`) with non-root runtime users
- Docker Compose orchestration: `docker compose up --build`
- Unified launcher: `./launch.sh v1|v2|v3|v4|api|stop`
- Bearer token authentication + rate limiting (30 queries/min, 60 other/min)

---

## Contact

**Jay Gutierrez** - Chief Architect, Nereus
**Repository:** [github.com/jaygut/semantica-poc](https://github.com/jaygut/semantica-poc)
**Semantica:** [github.com/Hawksight-AI/semantica](https://github.com/Hawksight-AI/semantica)
