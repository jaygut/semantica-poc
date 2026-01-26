# MARIS POC API Reference

TIMELINE: Week 15 (Phase 7: Documentation)
IMPLEMENTATION PRIORITY: Medium - Documentation for completed implementation

## Overview
This document provides API reference for all MARIS POC modules and functions.

## Modules

### maris.config
Configuration management module:
- Config class: Main configuration class with all settings
- get_config(): Get global configuration instance
- reload_config(): Reload configuration from files

### maris.semantica_integration
Semantica framework integration:
- SemanticaClient class: Main client for Semantica API
- Methods: connect(), authenticate(), extract_entities(), extract_relationships(), build_graph(), add_inference_rule(), graphrag_query(), index_document()

### maris.entity_extractor
Entity extraction pipeline:
- EntityExtractor class: Extract entities from documents
- Methods: extract_from_document(), extract_batch(), validate_extraction(), generate_report()

### maris.relationship_extractor
Relationship extraction:
- RelationshipExtractor class: Extract relationships from documents
- Methods: extract_from_document(), extract_batch(), build_trophic_network(), validate_extraction()

### maris.bridge_axiom_engine
Bridge axiom application:
- BridgeAxiomEngine class: Apply bridge axioms as inference rules
- Methods: load_axioms(), apply_axiom(), apply_chain(), validate_application()

### maris.query_engine
GraphRAG query interface:
- QueryEngine class: Execute queries on knowledge graph
- Methods: query(), query_with_provenance(), generate_reasoning_path(), format_response()

### maris.graph_builder
Knowledge graph construction:
- GraphBuilder class: Build knowledge graph from entities/relationships
- Methods: build_graph(), add_entities(), add_relationships(), apply_axioms(), validate_graph()

### maris.data_loader
Data loading utilities:
- DataLoader class: Load Semantica export bundle
- Methods: load_entities(), load_relationships(), load_axioms(), load_corpus(), validate_data()

### maris.document_processor
Document ingestion:
- DocumentProcessor class: Ingest documents into Semantica
- Methods: load_registry(), index_documents(), process_batch(), generate_report()

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
