# Nereus POC - Agentic System

This directory contains the agentic workflow system, document registry, and skills infrastructure for the Nereus knowledge graph (powered by MARIS + Semantica). It supports both the live v2 system (Neo4j + FastAPI + Streamlit) and the document curation pipeline that feeds it.

## Current Status

### v2 Live System - Deployed on main

| Component | Status | Details |
|-----------|--------|---------|
| Neo4j Knowledge Graph | Running | 893 nodes, 132 edges, bolt://localhost:7687 |
| FastAPI Query Engine | Running | 9 endpoints (7 core + provenance + disclosure), http://localhost:8000 |
| v3 Intelligence Platform | Running | Multi-tab dashboard (5 tabs), http://localhost:8503 |
| v2 Streamlit Dashboard | Running | Dark-mode dual-site investor UI, http://localhost:8501 |
| Document Library | Complete | 195 papers, 92% T1, 16 bridge axioms |
| Semantica Export | Complete | 14 entities, 15 relationships, 16 axioms |
| Characterized Sites | 2 | Cabo Pulmo ($29.27M ESV) + Shark Bay ($21.5M ESV) |
| Semantica Integration | Complete | P0-P4 on feature/semantica-integration branch (27 modules, 6-file bridge) |
| Test Suite | 910 | 706 unit + 204 integration tests |

### Document Library Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| Document Count | 195 | 195 |
| T1 (Peer-reviewed) | 92% | 92% |
| DOI Coverage | 100% | 90.3% |
| Abstract Coverage | 80% | 67.2% |
| Bridge Axioms with 3+ sources | 16 | 16 |
| Semantica Export Files | 4 | 4 |

---

## How the Agentic System Feeds the Live Graph

The agentic workflow (commands, skills, scripts) is the curation layer that produces the seven data sources consumed by the Neo4j population pipeline. The flow is:

```
Agentic Curation Layer                     Live System Layer
======================                     =================

/search-literature
/build-library          ──> document_index.json ──────┐
/validate-registry                                    │
/enrich-abstracts                                     │
/fetch-documents                                      │
                                                      │
/extract-knowledge      ──> entities.jsonld ──────────┤
                        ──> relationships.json ────────┤
                        ──> bridge_axioms.json ────────┤
                                                      │
cabo_pulmo_case_study.json ────────────────────────────┤
shark_bay_case_study.json ─────────────────────────────┤
bridge_axiom_templates.json (16 axioms) ───────────────┤
                                                      │
                                                      v
                                          scripts/populate_neo4j.py
                                                      │
                                                      v
                                          Neo4j (893 nodes, 132 edges)
                                                      │
                                                      v
                                          FastAPI ──> v3 Intelligence Platform (8503)
                                                  ──> v2 Streamlit Dashboard (8501)
```

---

## Directory Structure

```
.claude/
  CLAUDE.md                        # This file
  plans/                           # Claude Code plan files (auto-generated)
  skills/
    literature-scout/              # Literature discovery skill
      SKILL.md
      references/
        search_keywords.md
      scripts/
        verify_url.py              # URL/DOI verification + evidence tier classification
        update_registry.py         # Registry CRUD + integrity functions
    kg-architect/                  # Knowledge graph skill
      SKILL.md
  commands/
    validate-registry.md           # Registry validation command
    enrich-abstracts.md            # Abstract enrichment command
    fetch-documents.md             # Document fetching command
    search-literature.md           # Literature discovery command
    extract-knowledge.md           # Entity extraction command
    build-library.md               # Library construction command
    semantica-pipeline.md          # Pipeline orchestration command
  agents/
    literature-search-agent.md     # Autonomous literature search
    entity-extraction-agent.md     # Entity extraction agent
  registry/
    document_index.json            # Master bibliography (195 papers)
    documents/                     # Individual document metadata
    kg_ready/                      # Extracted knowledge for graph population
    reports/                       # Pipeline execution reports

tests/                               # Test suite (910 tests: 706 unit + 204 integration)
  conftest.py                        # Shared fixtures
  test_api_endpoints.py              # API route tests with auth validation
  test_auth.py                       # Auth enforcement, rate limiting, input validation
  test_bridge_axioms.py              # Bridge axiom computation tests
  test_cabo_pulmo_validation.py      # Cabo Pulmo reference data integrity
  test_classifier.py                 # Query classification accuracy
  test_confidence.py                 # Composite confidence model tests
  test_cypher_templates.py           # Template parameterization and LIMIT tests
  test_entity_extraction.py          # Entity extraction pipeline tests
  test_integration.py                # End-to-end pipeline integration tests
  test_monte_carlo.py                # Monte Carlo simulation tests
  test_population.py                 # Graph population pipeline tests
  test_query_engine.py               # Query execution and response formatting
  test_relationship_extraction.py    # Relationship extraction tests
  test_validators.py                 # LLM response validation tests
```

---

## Command Reference

### Registry Maintenance

| Command | Arguments | Purpose |
|---------|-----------|---------|
| `/validate-registry` | `--fix`, `--verbose` | Check integrity, fix statistics drift |
| `/enrich-abstracts` | `--dry-run`, `--limit N`, `--force` | Populate missing abstracts via 5-tier cascade |
| `/fetch-documents` | `--tier T1,T2`, `--limit N`, `--report` | Download document content with retry |

### Literature Discovery

| Command | Arguments | Purpose |
|---------|-----------|---------|
| `/search-literature` | `<domain>`, `--depth`, `--tiers` | Find papers by domain |
| `/build-library` | `--mode`, `--target-count` | Automated library expansion |

### Knowledge Extraction and Pipeline

| Command | Arguments | Purpose |
|---------|-----------|---------|
| `/extract-knowledge` | `<doc_id>`, `--batch`, `--priority` | Extract entities from papers |
| `/semantica-pipeline` | `--phase`, `--domains` | Full end-to-end pipeline |

---

## Abstract Enrichment Cascade

The `/enrich-abstracts` command uses a 5-tier cascade to populate missing abstracts:

| Tier | Source | Method |
|------|--------|--------|
| 1 | CrossRef API | DOI lookup, JATS XML parsing |
| 2 | OpenAlex API | Inverted index reconstruction |
| 3 | Semantic Scholar | Graph API lookup |
| 4 | HTML Meta Tags | citation_abstract, og:description |
| 5 | PDF Parsing | First-page text extraction |

---

## Evidence Tier System

All 195 documents are classified by evidence quality. This tier propagates into the Neo4j graph as the `source_tier` property on Document nodes.

| Tier | Classification | Financial Usage |
|------|----------------|----------------|
| T1 | Peer-reviewed journal articles | Cite without qualification in investor materials |
| T2 | Institutional reports (World Bank, UNEP, TNFD) | Cite with institutional context |
| T3 | Data repositories (FishBase, WoRMS, OBIS) | Cite with methodology notes |
| T4 | Preprints and grey literature | Cite with explicit caveats |

---

## Validation Checks

The `/validate-registry` command performs:

1. **Document Count** - Verify count matches actual entries
2. **Statistics Integrity** - Tier/type sums match document count
3. **Orphan Files** - Detect files not in index
4. **Required Fields** - title, url, source_tier present
5. **DOI Coverage** - Current + inferrable coverage
6. **Duplicate Detection** - Find duplicate DOIs
7. **Abstract Coverage** - Percentage with abstracts

Post-population graph validation (`scripts/validate_graph.py`) checks:

1. **Node counts** by label match expected values
2. **All 16 BridgeAxiom nodes** have at least one EVIDENCED_BY edge
3. **All 4 MPA nodes** have GENERATES edges to EcosystemService nodes
4. **Relationship integrity** - no orphan edges

---

## Semantica Export Bundle

The curated data is exported in four files for Semantica ingestion and also consumed directly by the Neo4j population pipeline:

| Output | Format | Contents | Location |
|--------|--------|----------|----------|
| Entities | JSON-LD | 14 entities with WoRMS/FishBase/TNFD URIs | `data/semantica_export/entities.jsonld` |
| Relationships | JSON | 15 typed edges with provenance | `data/semantica_export/relationships.json` |
| Bridge Axioms | JSON | 16 axioms with evidence mapping | `data/semantica_export/bridge_axioms.json` |
| Document Corpus | JSON | 195-paper library summary | `data/semantica_export/document_corpus.json` |

---

## Extending the Registry

### Adding Papers

1. Use `/search-literature <domain>` to discover new papers
2. Run `/validate-registry --fix` to ensure integrity
3. Run `/enrich-abstracts` to populate abstracts
4. Run `python scripts/populate_neo4j.py` to load new documents into the graph

### Adding a New Command

1. Create `.claude/commands/new-command.md`
2. Document usage, arguments, and execution steps
3. Reference required skills and scripts
4. Update this file

### Adding a New Skill Script

1. Create script in the appropriate skill's `scripts/` directory
2. Document in the skill's `SKILL.md`
3. Reference from relevant command files

---

## Testing and CI

The project includes 910 tests (706 unit + 204 integration) in `tests/` covering query classification (with hardened regex patterns), Cypher templates, graph population, bridge axioms, Monte Carlo simulation, confidence modeling, LLM response validation, API endpoints, W3C PROV-O provenance, multi-site scaling, cross-domain reasoning, TNFD disclosure, axiom discovery (with LLM-enhanced detection), Semantica SDK bridge adapters, and LLM discovery integration. Shared fixtures are in `tests/conftest.py`.

CI runs on push/PR to `main` via GitHub Actions (`.github/workflows/ci.yml`):
1. **Lint**: `ruff check maris/ tests/`
2. **Test**: `pytest tests/ -v --tb=short`

Run locally:
```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Related Files

| File | Purpose |
|------|---------|
| `../CLAUDE.md` | Root project context (architecture, data lineage, quick start) |
| `../README.md` | Project overview and implementation roadmap |
| `../docs/developer_guide.md` | Full architecture, population pipeline, extension guide |
| `../docs/api_reference.md` | API endpoints, graph schema, query categories |
| `../docs/user_guide.md` | Dashboard usage, Ask MARIS, confidence levels |
| `../SEMANTICA_HANDOFF_README.md` | Integration guide for Semantica team |
| `../docs/investment_grade_definition.md` | Investment-grade definition and criteria |
| `../docs/second_site_characterization_plan.md` | Plan for characterizing a second MPA site |

## External Links

| Resource | URL |
|----------|-----|
| Semantica (Knowledge Framework) | https://github.com/Hawksight-AI/semantica |
| WoRMS (Marine Species) | https://www.marinespecies.org |
| FishBase (Fish Data) | https://www.fishbase.org |
| TNFD (Nature Disclosure) | https://tnfd.global |
