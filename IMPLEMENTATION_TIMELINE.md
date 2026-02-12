# MARIS POC Implementation Timeline

This document provides a week-by-week implementation schedule for all files in the MARIS POC.

## Overview

**Total Duration:** 8 weeks  
**Start Date:** Week 1  
**End Date:** Week 8  
**Focus:** Semantica integration and core functionality delivery

**Four Main Phases (All Aligned with Semantica):**
1. **Phase 1:** Foundation & Semantica Integration (Weeks 1-2)
2. **Phase 2:** Knowledge Extraction & Bridge Axioms via Semantica (Weeks 3-4)
3. **Phase 3:** Graph Construction & Query Interface via Semantica (Weeks 5-6)
4. **Phase 4:** Integration, Testing & Demo via Semantica (Weeks 7-8)

---

## Phase 1: Foundation & Semantica Integration (Weeks 1-2)

### Week 1: Foundation & Semantica Integration

**Phase:** Phase 1 - Foundation & Semantica Integration  
**Priority:** Critical foundation files + Semantica connection

### Files to Implement:
- ✅ `maris/__init__.py` - Package initialization (COMPLETED)
- ✅ `maris/config.py` - Configuration management (COMPLETED)
- [ ] `maris/utils.py` - Utility functions
- [ ] `maris/schemas.py` - Schema loading utilities
- [ ] `maris/semantica_integration.py` - **Main Semantica integration** (CRITICAL)
- [ ] `config/config.yaml` - Configuration file
- [ ] `config/.env.example` - Environment variables template

### Semantica Integration Tasks:
- [ ] Establish Semantica API connection
- [ ] **Ingest `entities.jsonld` into Semantica** (via Semantica API)
- [ ] **Ingest `relationships.json` with inference rules** (via Semantica API)
- [ ] **Index `document_corpus.json` in Semantica** (via Semantica API)
- [ ] Validate Semantica connection and basic operations

### Milestones:
- System configuration working
- Semantica API connection established
- Export bundle ingested into Semantica
- Basic health checks passing

---

### Week 2: Data Loading & Entity Extraction

**Phase:** Phase 1 - Foundation & Semantica Integration (continued)  
**Priority:** Data ingestion foundation + Semantica extraction

### Files to Implement:
- [ ] `maris/data_loader.py` - Load existing Semantica export bundle
- [ ] `maris/document_processor.py` - Document ingestion via Semantica
- [ ] `maris/provenance.py` - Provenance tracking
- [ ] `maris/entity_extractor.py` - **Entity extraction using Semantica API**
- [ ] `tests/test_entity_extraction.py` - Entity extraction tests

### Semantica Integration Tasks:
- [ ] Index document corpus into Semantica
- [ ] **Extract entities from 30+ high-priority papers using Semantica**
- [ ] Load Cabo Pulmo case study into Semantica
- [ ] Validate data integrity in Semantica

### Milestones:
- Export bundle loaded successfully
- Document corpus indexed in Semantica
- Entity extraction pipeline operational using Semantica
- 30+ papers processed with >85% extraction accuracy
- Provenance tracking operational

---

## Phase 2: Knowledge Extraction & Bridge Axioms via Semantica (Weeks 3-4)

### Week 3: Relationship Extraction & Bridge Axioms Setup

**Phase:** Phase 2 - Knowledge Extraction & Bridge Axioms via Semantica  
**Priority:** Complete extraction pipeline + Bridge axioms preparation

### Files to Implement:
- [ ] `maris/relationship_extractor.py` - **Relationship extraction using Semantica API**
- [ ] `tests/test_relationship_extraction.py` - Relationship extraction tests
- [ ] `maris/bridge_axiom_engine.py` - Bridge axiom application engine (start)
- [ ] `tests/test_bridge_axioms.py` - Bridge axiom tests (start)

### Semantica Integration Tasks:
- [ ] **Extract relationships using Semantica API**
- [ ] **Build trophic network subgraph in Semantica**
- [ ] Extract habitat-service links
- [ ] Extract MPA-effectiveness relationships
- [x] Define BA-001 through BA-012 with coefficients ✅
- [ ] **Register bridge axioms as Semantica inference rules**

### Milestones:
- Relationship extraction operational using Semantica
- Trophic networks built in Semantica graph
- Service networks constructed
- Bridge axioms registered in Semantica
- Extraction pipeline complete

---

### Week 4: Bridge Axioms & Validation

**Phase:** Phase 2 - Knowledge Extraction & Bridge Axioms via Semantica (continued)  
**Priority:** Core translation layer + validation

### Files to Implement:
- [ ] `maris/bridge_axiom_engine.py` - Bridge axiom application engine (complete)
- [ ] `maris/validators.py` - Validation utilities
- [ ] `tests/test_bridge_axioms.py` - Bridge axiom tests (complete)
- [ ] `tests/test_cabo_pulmo_validation.py` - Cabo Pulmo validation tests

### Semantica Integration Tasks:
- [ ] **Implement bridge axioms as Semantica inference rules**
- [ ] Test axiom pattern matching in Semantica
- [x] Validate Cabo Pulmo metrics (463% ±20% tolerance) ✅
- [ ] **Test cascade reasoning (otter → kelp → carbon) via Semantica**
- [ ] Validate all 16 bridge axioms

### Milestones:
- All 16 bridge axioms implemented as Semantica inference rules (12 core + 4 blue carbon)
- Axiom pattern matching working
- Coefficient calculations implemented
- Cabo Pulmo validation passing (±20% tolerance)
- Cascade reasoning functional
- Uncertainty propagation working

---

## Phase 3: Graph Construction & Query Interface via Semantica (Weeks 5-6)

### Week 5: GraphRAG Query Interface

**Phase:** Phase 3 - Graph Construction & Query Interface via Semantica  
**Priority:** Query functionality using Semantica GraphRAG

### Files to Implement:
- [ ] `maris/query_engine.py` - **GraphRAG query interface using Semantica**
- [ ] `tests/test_query_engine.py` - Query engine tests

### Semantica Integration Tasks:
- [ ] **Configure Semantica GraphRAG interface**
- [ ] **Implement multi-hop reasoning (up to 4 hops) via Semantica**
- [ ] **Implement all 11 sample queries using Semantica GraphRAG**
- [ ] Add confidence scoring to responses
- [ ] Build provenance visualization
- [ ] Test TNFD disclosure field population
- [ ] Validate query latency <5 seconds

### Milestones:
- GraphRAG interface configured in Semantica
- Multi-hop reasoning working
- All 11 sample queries working
- Provenance chains generated
- Confidence scoring working
- Query latency <5 seconds

---

### Week 6: Knowledge Graph Construction

**Phase:** Phase 3 - Graph Construction & Query Interface via Semantica (continued)  
**Priority:** Build complete knowledge graph using Semantica

### Files to Implement:
- [ ] `maris/graph_builder.py` - **Knowledge graph construction via Semantica**

### Semantica Integration Tasks:
- [ ] **Use Semantica's native graph database** (or configure Neo4j integration)
- [ ] **Create entity nodes from extracted entities in Semantica**
- [ ] **Create relationship edges in Semantica**
- [ ] **Apply bridge axioms as graph inference rules in Semantica**
- [ ] Build trophic network subgraphs
- [ ] Create MPA network connectivity graphs
- [ ] Validate graph integrity

### Milestones:
- Graph database connected (Semantica native or Neo4j)
- Entity nodes created in Semantica
- Relationship edges created in Semantica
- Bridge axioms applied as inference rules
- Subgraphs built (trophic, MPA networks)
- Graph integrity validated
- Graph indexing optimized

---

## Phase 4: Integration, Testing & Demo via Semantica (Weeks 7-8)

### Week 7: Integration Testing & CLI

**Phase:** Phase 4 - Integration, Testing & Demo via Semantica  
**Priority:** End-to-end testing and user interface

### Files to Implement:
- [ ] `maris/cli.py` - Command-line interface
- [ ] `tests/test_integration.py` - Integration tests
- [ ] `maris/validators.py` - Validation utilities (complete all validations)

### Semantica Integration Tasks:
- [ ] Test end-to-end pipeline with Semantica
- [ ] **Process remaining papers for entity extraction (batch via Semantica)**
- [ ] Performance testing and optimization
- [ ] Validate all success criteria

### Milestones:
- CLI commands implemented
- End-to-end pipeline tested with Semantica
- Integration tests passing
- All CLI commands functional
- Performance optimized

---

### Week 8: Demo & Documentation

**Phase:** Phase 4 - Integration, Testing & Demo via Semantica (continued)  
**Priority:** Final validation, demo, and documentation

### Files to Implement:
- [ ] `docs/api_reference.md` - API documentation
- [ ] `docs/user_guide.md` - User guide
- [ ] `docs/developer_guide.md` - Developer guide

### Semantica Integration Tasks:
- [ ] **Run investor demo narrative using Semantica queries**
- [ ] Validate all success criteria
- [ ] Document Semantica integration patterns

### Milestones:
- Investor demo complete (10-min narrative without gaps)
- All success criteria validated
- API reference complete
- User guide complete
- Developer guide complete
- Semantica integration documented
- All documentation finalized
- POC ready for handoff

---

## Summary by File

### Foundation Files (Week 1)
- `maris/__init__.py` - Week 1 ✅
- `maris/config.py` - Week 1 ✅
- `maris/utils.py` - Week 1
- `maris/schemas.py` - Week 1
- `maris/semantica_integration.py` - Week 1 (CRITICAL)
- `config/config.yaml` - Week 1
- `config/.env.example` - Week 1

### Data Loading Files (Week 2)
- `maris/data_loader.py` - Week 2
- `maris/document_processor.py` - Week 2
- `maris/provenance.py` - Week 2
- `maris/entity_extractor.py` - Week 2 (uses Semantica)
- `tests/test_entity_extraction.py` - Week 2

### Extraction Files (Week 3)
- `maris/relationship_extractor.py` - Week 3 (uses Semantica)
- `tests/test_relationship_extraction.py` - Week 3
- `maris/bridge_axiom_engine.py` - Week 3-4
- `tests/test_bridge_axioms.py` - Week 3-4

### Bridge Axiom Files (Week 4)
- `maris/bridge_axiom_engine.py` - Week 3-4 (complete)
- `maris/validators.py` - Week 4
- `tests/test_bridge_axioms.py` - Week 3-4 (complete)
- `tests/test_cabo_pulmo_validation.py` - Week 4

### Query Files (Week 5)
- `maris/query_engine.py` - Week 5 (uses Semantica GraphRAG)
- `tests/test_query_engine.py` - Week 5

### Graph Files (Week 6)
- `maris/graph_builder.py` - Week 6 (uses Semantica)

### CLI & Testing Files (Week 7)
- `maris/cli.py` - Week 7
- `tests/test_integration.py` - Week 7
- `maris/validators.py` - Week 4, Week 7 (complete)

### Documentation Files (Week 8)
- `docs/api_reference.md` - Week 8
- `docs/user_guide.md` - Week 8
- `docs/developer_guide.md` - Week 8

---

## Critical Path

The critical path for implementation (8-week compressed timeline with 4 Semantica-aligned phases):

**Phase 1: Foundation & Semantica Integration (Weeks 1-2)**
1. **Week 1:** Foundation + Semantica API connection → Required by all modules
2. **Week 2:** Data loading + Entity extraction via Semantica → Required before relationships

**Phase 2: Knowledge Extraction & Bridge Axioms via Semantica (Weeks 3-4)**
3. **Week 3:** Relationship extraction + Bridge axioms setup via Semantica → Required for graph
4. **Week 4:** Bridge axioms implementation + validation via Semantica → Required for query translations

**Phase 3: Graph Construction & Query Interface via Semantica (Weeks 5-6)**
5. **Week 5:** GraphRAG query interface via Semantica → Core functionality
6. **Week 6:** Knowledge graph construction via Semantica → Required for query execution

**Phase 4: Integration, Testing & Demo via Semantica (Weeks 7-8)**
7. **Week 7:** CLI & integration testing with Semantica → User interface and validation
8. **Week 8:** Demo & documentation using Semantica queries → Final deliverable

---

## Dependencies

**File Dependencies:**
- `maris/utils.py` → Used by all modules
- `maris/config.py` → Used by all modules
- `maris/schemas.py` → Used by extractors and validators
- `maris/semantica_integration.py` → **Used by ALL Semantica operations** (extractors, graph builder, query engine)
- `maris/provenance.py` → Used by extractors and query engine
- `maris/entity_extractor.py` → Required by relationship_extractor
- `maris/relationship_extractor.py` → Required by graph_builder
- `maris/bridge_axiom_engine.py` → Required by query_engine
- `maris/graph_builder.py` → Required by query_engine
- `maris/query_engine.py` → Used by CLI

**Semantica Integration Dependencies:**
- All entity extraction → Uses Semantica API
- All relationship extraction → Uses Semantica API
- Graph construction → Uses Semantica graph database
- Query execution → Uses Semantica GraphRAG
- Bridge axiom inference → Uses Semantica inference rules

---

## Milestones Summary

### Phase 1: Foundation & Semantica Integration (Weeks 1-2)

| Week | Milestone | Deliverable | Semantica Integration |
|------|-----------|-------------|----------------------|
| 1 | Foundation Setup | Config, utils, schemas working | **Semantica API connection established, export bundle ingested** |
| 2 | Data Loading & Entity Extraction | Export bundle loaded, documents indexed | **30+ papers processed via Semantica extraction** |

### Phase 2: Knowledge Extraction & Bridge Axioms via Semantica (Weeks 3-4)

| Week | Milestone | Deliverable | Semantica Integration |
|------|-----------|-------------|----------------------|
| 3 | Relationship Extraction | All relationships extracted | **Trophic networks built in Semantica** |
| 4 | Bridge Axioms Validated | Cabo Pulmo validation passing | **Bridge axioms registered as Semantica inference rules** |

### Phase 3: Graph Construction & Query Interface via Semantica (Weeks 5-6)

| Week | Milestone | Deliverable | Semantica Integration |
|------|-----------|-------------|----------------------|
| 5 | Query Interface Complete | All 11 sample queries working | **GraphRAG configured and operational via Semantica** |
| 6 | Graph Complete | Full knowledge graph built | **Graph constructed in Semantica with inference rules** |

### Phase 4: Integration, Testing & Demo via Semantica (Weeks 7-8)

| Week | Milestone | Deliverable | Semantica Integration |
|------|-----------|-------------|----------------------|
| 7 | Integration Complete | CLI commands functional | **End-to-end pipeline tested with Semantica** |
| 8 | Demo & Documentation | All documentation complete | **Investor demo using Semantica queries** |

---

## Semantica Integration Priorities

**Week 1 (Critical):**
- Establish Semantica API connection
- Ingest export bundle (entities, relationships, bridge axioms, corpus)

**Week 2-3 (High):**
- Use Semantica for entity extraction
- Use Semantica for relationship extraction
- Build graphs in Semantica

**Week 4 (High):**
- Register bridge axioms as Semantica inference rules
- Test inference via Semantica

**Week 5 (Critical):**
- Configure Semantica GraphRAG interface
- Execute queries via Semantica

**Week 6 (High):**
- Use Semantica's native graph database
- Apply inference rules in Semantica

**Week 7-8 (Medium):**
- End-to-end testing with Semantica
- Document Semantica integration patterns
