"""
Schema loading utilities for MARIS POC

TIMELINE: Week 1-2 (Phase 1: Foundation)
IMPLEMENTATION PRIORITY: High - Required before entity/relationship extraction

This module handles loading, validation, and management of MARIS schemas.

SCHEMA TYPES HANDLED:
• Entity Schema (schemas/entity_schema.json)
  - 8 entity types: Species, Habitat, MarineProtectedArea, EcosystemService, FinancialInstrument, DisclosureFramework, Observation, BridgeAxiom
  - JSON-LD format with @context for semantic interoperability
  - External identifier mappings (WoRMS AphiaID, FishBase codes, TNFD URIs)
  - Property definitions with types, ranges, and validation rules
  - Required vs optional field specifications

• Relationship Schema (schemas/relationship_schema.json)
  - 14 relationship types organized by category:
    * Ecological: PREYS_ON, CONTROLS_VIA_CASCADE, HABITAT_OF, CONNECTED_TO, INDICATOR_OF
    * Service: PROVIDES_SERVICE, DEPENDS_ON, QUANTIFIED_BY
    * Financial: INFORMS_INSTRUMENT, FUNDED_BY, REPORTS_TO, TRANSLATES_TO
    * Provenance: DERIVED_FROM, SUPPORTS_CLAIM, AGGREGATED_FROM
  - Cardinality constraints (many:many, one:many, one:one)
  - Inference rules for transitive relationships
  - Relationship property definitions

• Bridge Axiom Templates (schemas/bridge_axiom_templates.json)
  - 12 bridge axioms (BA-001 through BA-012)
  - IF-THEN pattern definitions
  - Coefficient specifications with confidence intervals
  - Evidence source tracking (DOIs, citations)
  - Applicability constraints (habitat types, contexts)

• Registry Schema (schemas/registry_schema.json)
  - Document metadata validation
  - Required fields: title, url, year, source_tier, document_type, domain_tags
  - Optional fields: doi, authors, journal, access_status, retrieval metadata

KEY FUNCTIONS TO IMPLEMENT:

Schema Loading:
• load_entity_schema() -> dict
  - Read and parse schemas/entity_schema.json
  - Resolve JSON-LD @context references
  - Cache loaded schema in memory
  - Return entity type definitions with properties

• load_relationship_schema() -> dict
  - Read and parse schemas/relationship_schema.json
  - Extract relationship type definitions
  - Load inference rules
  - Return relationship schema with cardinality constraints

• load_bridge_axiom_templates() -> list[dict]
  - Read and parse schemas/bridge_axiom_templates.json
  - Extract all 12 bridge axiom definitions
  - Validate axiom structure (axiom_id, pattern, coefficients, sources)
  - Return list of axiom templates

• load_registry_schema() -> dict
  - Read and parse schemas/registry_schema.json
  - Return JSON schema for document validation

Schema Validation:
• validate_entity(entity: dict, entity_type: str) -> bool
  - Check entity properties against schema
  - Validate required fields are present
  - Validate field types and ranges
  - Validate external identifier formats (WoRMS ID, FishBase code)
  - Return True if valid, raise ValidationError if invalid

• validate_relationship(relationship: dict) -> bool
  - Check relationship type exists in schema
  - Validate subject and object entity types match domain/range
  - Check cardinality constraints
  - Validate relationship properties
  - Return True if valid, raise ValidationError if invalid

• validate_bridge_axiom(axiom: dict) -> bool
  - Check axiom_id format (BA-XXX)
  - Validate pattern structure (IF-THEN)
  - Validate coefficients are numeric and in valid ranges
  - Check evidence sources have required fields (DOI, citation)
  - Return True if valid, raise ValidationError if invalid

Schema Accessors:
• get_entity_type(entity_type: str) -> dict
  - Return entity type definition from loaded schema
  - Include all properties, relationships, external identifiers
  - Raise KeyError if entity type not found

• get_relationship_type(rel_type: str) -> dict
  - Return relationship type definition
  - Include domain, range, cardinality, properties
  - Raise KeyError if relationship type not found

• get_bridge_axiom(axiom_id: str) -> dict
  - Return bridge axiom template by ID (e.g., "BA-001")
  - Include pattern, coefficients, evidence sources
  - Raise KeyError if axiom not found

• get_all_entity_types() -> list[str]
  - Return list of all entity type names
  - Useful for iteration and validation

• get_all_relationship_types() -> list[str]
  - Return list of all relationship type names

• get_all_bridge_axioms() -> list[dict]
  - Return all 12 bridge axiom templates

JSON-LD Context Resolution:
• resolve_context(context_key: str) -> str
  - Resolve JSON-LD context keys to full URIs
  - Handle WoRMS, FishBase, TNFD, SEEA contexts
  - Return full URI for external identifier resolution

• validate_external_id(id_type: str, identifier: str) -> bool
  - Validate WoRMS AphiaID format (numeric)
  - Validate FishBase spec code format
  - Validate DOI format (10.xxxx/xxxx)
  - Return True if valid format

Caching and Performance:
• _schema_cache: dict
  - Cache loaded schemas to avoid repeated file I/O
  - Key: schema file path, Value: parsed schema dict
  - Clear cache on schema file modification

• clear_cache()
  - Clear all cached schemas
  - Force reload on next access

• get_schema_version() -> str
  - Return schema version from metadata
  - Support schema versioning for compatibility checks

INTEGRATION POINTS:
• Used by: maris.entity_extractor (for entity validation)
• Used by: maris.relationship_extractor (for relationship validation)
• Used by: maris.bridge_axiom_engine (for axiom loading)
• Used by: maris.validators (for schema compliance checks)
• Configuration: Uses maris.config.Config for schema file paths
"""
