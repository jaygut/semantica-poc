"""
Data loader for existing Semantica export bundle

TIMELINE: Week 2 (Phase 1: Foundation & Semantica Integration)
IMPLEMENTATION PRIORITY: High - Load existing export bundle before extraction

This module loads the pre-built Semantica export bundle into the MARIS system.
The export bundle (entities.jsonld, relationships.json, bridge_axioms.json, document_corpus.json)
is ingested into Semantica via the Semantica API.

EXPORT BUNDLE FILES:
• data/semantica_export/entities.jsonld
  - 14 pre-extracted entities in JSON-LD format
  - Includes: NEOLI Criteria concept, Cabo Pulmo MPA, Species (Lutjanus, Mycteroperca), 
    Ecosystem Services (flood protection, coastal wetland services), Habitats (coral reef, 
    kelp forest, seagrass, mangrove), Financial Instruments (blue bond, parametric insurance),
    Frameworks (TNFD LEAP, SEEA Ecosystem Accounting)
  - JSON-LD @context with WoRMS, FishBase, TNFD URI mappings
  - External identifier links (WoRMS AphiaID, FishBase codes)

• data/semantica_export/relationships.json
  - 15 pre-extracted relationships with provenance
  - Includes: DETERMINES_OUTCOME, MULTIPLICATIVE_EFFECT, RECOVERY_DRIVER, PROVIDES_SERVICE,
    DEGRADATION_IMPACT, VALUE_CONTRIBUTION, HABITAT_OF, TROPHIC_LINK, MODIFIES_EFFECT,
    CARBON_SEQUESTRATION, SUPPORTS_FISHERIES, CLIMATE_IMPACT, FINANCIAL_MECHANISM,
    DISCLOSURE_REQUIRES
  - Each relationship includes: type, subject, object, strength, quantification, sources, confidence

• data/semantica_export/bridge_axioms.json
  - 12 bridge axioms (BA-001 through BA-012) with evidence sources
  - Each axiom includes: axiom_id, name, domain_from, domain_to, description, formula,
    coefficients, evidence_sources (with doc_id, support_type), confidence, validation notes
  - Average 3.1 sources per axiom

• data/semantica_export/document_corpus.json
  - Summary of 195-paper document corpus
  - Includes: total count, evidence tier distribution, DOI coverage, abstract coverage,
    domain breakdown, habitat breakdown

KEY FUNCTIONS TO IMPLEMENT:

Data Loading:
• load_entities(export_dir: Path) -> list[dict]
  - Load entities.jsonld file
  - Parse JSON-LD with context resolution
  - Resolve external identifier URIs (WoRMS, FishBase)
  - Validate entity structure against schema
  - Return list of entity dictionaries
  - Handle missing file gracefully (return empty list with warning)

• load_relationships(export_dir: Path) -> list[dict]
  - Load relationships.json file
  - Parse relationship structure
  - Validate relationship types against schema
  - Check subject/object entity references
  - Return list of relationship dictionaries

• load_bridge_axioms(export_dir: Path) -> list[dict]
  - Load bridge_axioms.json file
  - Parse axiom definitions
  - Validate axiom structure (axiom_id, coefficients, sources)
  - Check coefficient types and ranges
  - Validate evidence source references
  - Return list of bridge axiom dictionaries

• load_document_corpus(export_dir: Path) -> dict
  - Load document_corpus.json file
  - Parse corpus summary statistics
  - Return corpus metadata dictionary
  - Includes: document_count, tier_distribution, domain_breakdown, etc.

Data Validation:
• validate_entities(entities: list[dict]) -> dict
  - Validate entity list integrity
  - Check: All required fields present, External IDs valid format, 
    Entity types match schema, No duplicate entity IDs
  - Return validation result with errors/warnings

• validate_relationships(relationships: list[dict], entities: list[dict]) -> dict
  - Validate relationship list integrity
  - Check: Relationship types valid, Subject/object entities exist,
    Cardinality constraints satisfied, Properties valid
  - Return validation result with errors/warnings

• validate_bridge_axioms(axioms: list[dict]) -> dict
  - Validate bridge axiom list integrity
  - Check: Axiom IDs unique and valid format (BA-XXX), Coefficients numeric,
    Evidence sources have required fields, Confidence scores valid range
  - Return validation result with errors/warnings

• validate_data_consistency(entities: list[dict], relationships: list[dict]) -> dict
  - Check cross-reference consistency
  - Verify: Relationship subjects/objects reference valid entities,
    Bridge axiom evidence sources reference valid documents,
    External IDs resolve correctly
  - Return consistency check result

Data Transformation:
• transform_entities_for_graph(entities: list[dict]) -> list[dict]
  - Transform entities to graph database format
  - Add graph-specific properties
  - Prepare for Neo4j/Semantica ingestion
  - Return transformed entity list

• transform_relationships_for_graph(relationships: list[dict]) -> list[dict]
  - Transform relationships to graph database format
  - Add edge properties
  - Prepare for graph ingestion
  - Return transformed relationship list

Data Accessors:
• get_entity_by_id(entity_id: str, entities: list[dict]) -> Optional[dict]
  - Find entity by ID
  - Return entity dictionary or None

• get_entities_by_type(entity_type: str, entities: list[dict]) -> list[dict]
  - Filter entities by type
  - Return list of matching entities

• get_relationships_by_type(rel_type: str, relationships: list[dict]) -> list[dict]
  - Filter relationships by type
  - Return list of matching relationships

• get_bridge_axiom_by_id(axiom_id: str, axioms: list[dict]) -> Optional[dict]
  - Find bridge axiom by ID (e.g., "BA-001")
  - Return axiom dictionary or None

Statistics:
• get_data_statistics(entities: list[dict], relationships: list[dict], 
                     axioms: list[dict]) -> dict
  - Calculate data statistics
  - Includes: Entity count by type, Relationship count by type,
    Axiom count, External ID coverage, Provenance coverage
  - Return statistics dictionary

Caching:
• _data_cache: dict
  - Cache loaded data to avoid repeated file I/O
  - Key: file path, Value: parsed data
  - Clear cache on file modification

• clear_cache() -> None
  - Clear all cached data
  - Force reload on next access

Incremental Loading:
• detect_changes(export_dir: Path) -> dict
  - Detect changes in export files
  - Compare file modification times
  - Return dict of changed files

• load_incremental(changed_files: list[str]) -> dict
  - Load only changed files
  - Merge with existing data
  - Return updated data dictionary

Error Handling:
• handle_missing_file(file_path: Path) -> None
  - Handle missing export file gracefully
  - Log warning
  - Return empty data structure

• handle_corrupted_file(file_path: Path, error: Exception) -> None
  - Handle corrupted file gracefully
  - Log error with details
  - Attempt recovery if possible
  - Raise DataLoadError if unrecoverable

INTEGRATION POINTS:
• Used by: maris.graph_builder (to load initial graph data)
• Used by: maris.bridge_axiom_engine (to load axiom templates)
• Used by: maris.entity_extractor (to validate against existing entities)
• Configuration: Uses maris.config.Config for export directory path
• Validation: Uses maris.schemas for schema validation
• Error Handling: Uses maris.utils for file I/O and error handling
"""
