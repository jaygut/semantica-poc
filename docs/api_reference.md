# MARIS POC API Reference

TIMELINE: Week 8 (Phase 4: Integration, Testing & Demo via Semantica)
IMPLEMENTATION PRIORITY: Medium - Documentation for completed implementation

## Overview
This document provides API reference for all MARIS POC modules and functions. All core operations integrate with **Semantica** for entity extraction, relationship extraction, graph construction, and GraphRAG query execution.

## Modules

### maris.config
Configuration management module:
- Config class: Main configuration class with all settings
- get_config(): Get global configuration instance
- reload_config(): Reload configuration from files

### maris.semantica_integration
**Semantica framework integration (CRITICAL - Used by all modules):**
- SemanticaClient class: Main client for Semantica API
- Methods: 
  - Connection: connect(), authenticate(), health_check()
  - Entity Extraction: extract_entities(), extract_entities_batch()
  - Relationship Extraction: extract_relationships(), extract_relationships_batch()
  - Graph Construction: build_graph(), add_entities_to_graph(), add_relationships_to_graph()
  - Inference Rules: add_inference_rule(), get_inference_rules(), remove_inference_rule()
  - Query: graphrag_query(), graphrag_query_with_context()
  - Document Indexing: index_document(), index_documents_batch(), search_documents()
  - Ontology: get_ontology(), validate_schema()

### maris.entity_extractor
Entity extraction pipeline (uses Semantica API):
- EntityExtractor class: Extract entities from documents via Semantica
- Methods: extract_from_document(), extract_batch(), validate_extraction(), generate_report()
- Integration: All extraction calls routed through maris.semantica_integration.SemanticaClient

### maris.relationship_extractor
Relationship extraction (uses Semantica API):
- RelationshipExtractor class: Extract relationships from documents via Semantica
- Methods: extract_from_document(), extract_batch(), build_trophic_network(), validate_extraction()
- Integration: All extraction calls routed through maris.semantica_integration.SemanticaClient

### maris.bridge_axiom_engine
Bridge axiom application (uses Semantica inference rules):
- BridgeAxiomEngine class: Apply bridge axioms as Semantica inference rules
- Methods: load_axioms(), apply_axiom(), apply_chain(), validate_application()
- Integration: Bridge axioms registered as Semantica inference rules via add_inference_rule()

### maris.query_engine
GraphRAG query interface (uses Semantica GraphRAG):
- QueryEngine class: Execute queries on knowledge graph via Semantica GraphRAG
- Methods: query(), query_with_provenance(), generate_reasoning_path(), format_response()
- Integration: All queries executed through Semantica GraphRAG interface (graphrag_query())

### maris.graph_builder
Knowledge graph construction (uses Semantica graph database):
- GraphBuilder class: Build knowledge graph in Semantica's native graph database
- Methods: build_graph(), add_entities(), add_relationships(), apply_axioms(), validate_graph()
- Integration: Graph construction uses Semantica's native graph database (or Neo4j integration)

### maris.data_loader
Data loading utilities:
- DataLoader class: Load Semantica export bundle
- Methods: load_entities(), load_relationships(), load_axioms(), load_corpus(), validate_data()

### maris.document_processor
Document ingestion (uses Semantica document indexing):
- DocumentProcessor class: Ingest documents into Semantica document index
- Methods: load_registry(), index_documents(), process_batch(), generate_report()
- Integration: All document indexing via Semantica API (index_document(), index_documents_batch())

### maris.provenance
Provenance tracking:
- ProvenanceTracker class: Track provenance for all data
- Methods: create_provenance(), build_chain(), format_citation(), validate_completeness()

### maris.validators
Validation utilities:
- Validation functions: validate_entity_extraction(), validate_relationship_extraction(), validate_bridge_axiom(), validate_cabo_pulmo(), validate_provenance(), generate_validation_report()

### maris.cli
Command-line interface:
- CLI commands: setup, load-data, index-docs, extract-entities, extract-relationships, apply-axioms, build-graph, query, validate, demo, status, export

## Data Structures

### Entity Types
- Species: Marine species with taxonomic and ecological attributes
- Habitat: Marine habitat types (coral reef, kelp forest, etc.)
- MarineProtectedArea: MPA with governance attributes
- EcosystemService: Ecosystem services with valuation
- FinancialInstrument: Blue finance instruments
- DisclosureFramework: Sustainability disclosure frameworks
- Observation: Scientific observations with provenance
- BridgeAxiom: Translation rules between domains

### Relationship Types
- Ecological: PREYS_ON, CONTROLS_VIA_CASCADE, HABITAT_OF, CONNECTED_TO, INDICATOR_OF
- Service: PROVIDES_SERVICE, DEPENDS_ON, QUANTIFIED_BY
- Financial: INFORMS_INSTRUMENT, FUNDED_BY, REPORTS_TO, TRANSLATES_TO
- Provenance: DERIVED_FROM, SUPPORTS_CLAIM, AGGREGATED_FROM

### Bridge Axioms
- BA-001 through BA-012: 12 translation rules with coefficients and evidence
