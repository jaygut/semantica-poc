"""
Entity extraction pipeline using Semantica LLM-based extraction

TIMELINE: Week 2 (Phase 1: Foundation & Semantica Integration) - Uses Semantica API for extraction
IMPLEMENTATION PRIORITY: Critical - Core extraction functionality
MILESTONE: Extract entities from 50+ papers with >85% accuracy

This module extracts entities from documents using Semantica API. All extraction
operations route through maris.semantica_integration.SemanticaClient for entity
extraction via Semantica's LLM-based extraction capabilities.

ENTITY TYPES TO EXTRACT:
• Species
  - Properties: scientific_name, common_name, trophic_level, functional_group,
    body_size_cm, conservation_status, commercial_importance
  - External IDs: WoRMS AphiaID (required), FishBase spec_code (optional), GBIF taxon_key (optional)
  - Relationships: PREYS_ON, PREYED_UPON_BY, HABITAT_OF, INDICATOR_OF

• Habitat
  - Properties: habitat_type (coral_reef, kelp_forest, seagrass, mangrove, etc.),
    extent_km2, condition_score, structural_complexity, protection_status,
    climate_refugia_potential
  - Relationships: SUPPORTS_SERVICE, CONTAINS_SPECIES, CONNECTED_TO

• MarineProtectedArea
  - Properties: name, designation_year, area_km2, geometry (GeoJSON),
    neoli_criteria (no_take, enforced, old, large, isolated), neoli_score,
    management_effectiveness, iucn_category
  - External IDs: WDPA ID (optional)
  - Relationships: PROTECTS_HABITAT, CONTAINS_SPECIES, CONNECTED_TO

• EcosystemService
  - Properties: service_name, service_category (provisioning, regulating, cultural, supporting),
    service_type, value_usd_per_ha_yr, value_range, valuation_method,
    beneficiary_sector, evidence_tier
  - Relationships: DEPENDS_ON_HABITAT, PROVIDES_TO_SECTOR, QUANTIFIED_BY

• FinancialInstrument
  - Properties: instrument_type (blue_bond, carbon_credit, etc.), name, issuer,
    value_usd, term_years, issuance_date, verification_standard, use_of_proceeds, kpis
  - Relationships: FUNDED_BY, PROTECTS_HABITAT, REPORTS_TO_FRAMEWORK

• DisclosureFramework
  - Properties: framework_name (TNFD, ESRS_E4, SEEA_EA, etc.), version, jurisdiction,
    mandatory, metrics_required
  - Relationships: REQUIRES_METRIC, APPLIES_TO_SECTOR

• Observation
  - Properties: observation_type, timestamp, location (GeoJSON), value, unit,
    uncertainty, method
  - Provenance: source_document, source_document_hash, extraction_timestamp,
    extracted_by, page_reference, quote

• BridgeAxiom (conceptual entities)
  - Properties: axiom_id, name, domain_from, domain_to, pattern, coefficients,
    applicable_habitats, evidence_tier, sources, confidence_score

KEY FUNCTIONS TO IMPLEMENT:

Initialization:
• __init__(semantica_client: SemanticaClient, config: Config)
  - Initialize entity extractor
  - Store Semantica client reference
  - Load MARIS entity schema
  - Configure extraction options from config
  - Initialize provenance tracker

Schema Configuration:
• load_extraction_schema() -> dict
  - Load MARIS entity schema from schemas/entity_schema.json
  - Configure Semantica extraction with schema
  - Return schema dictionary
  - Cache schema to avoid repeated loading

Entity Extraction:
• extract_from_document(document: dict, options: dict = {}) -> dict
  - Extract entities from single document
  - Parameters:
    * document: Document content and metadata
    * options: Extraction options (timeout, include_provenance, etc.)
  - Call Semantica extract_entities() API
  - Process extraction response
  - Validate extracted entities
  - Attach provenance to entities
  - Resolve external identifiers
  - Return extraction result with entities list

• extract_batch(documents: list[dict], batch_size: int = 10) -> list[dict]
  - Extract entities from multiple documents
  - Process in batches for efficiency
  - Track progress for each document
  - Handle partial failures gracefully
  - Return list of extraction results
  - Generate batch extraction report

Entity Validation:
• validate_entity(entity: dict, entity_type: str) -> dict
  - Validate extracted entity against schema
  - Check: Required properties present, Property types correct,
    Property values in valid ranges, External IDs valid format
  - Return validation result with errors/warnings

• validate_extraction_result(result: dict) -> dict
  - Validate entire extraction result
  - Check: Entities list present, All entities valid,
    Provenance attached, External IDs resolved
  - Return validation result

External Identifier Resolution:
• resolve_worms_id(species_name: str) -> Optional[str]
  - Resolve species name to WoRMS AphiaID
  - Call WoRMS API or use local lookup
  - Return AphiaID or None if not found
  - Cache results to avoid repeated API calls

• resolve_fishbase_code(species_name: str) -> Optional[int]
  - Resolve species name to FishBase spec_code
  - Call FishBase API or use local lookup
  - Return spec_code or None if not found

• resolve_external_identifiers(entity: dict) -> dict
  - Resolve all external identifiers for entity
  - Update entity with resolved IDs
  - Return updated entity

Provenance Attachment:
• attach_provenance(entity: dict, document: dict, page_ref: str, quote: str) -> dict
  - Attach provenance metadata to entity
  - Create provenance object using maris.provenance
  - Link entity to source document
  - Add page reference and quote
  - Return entity with provenance attached

• extract_quotes_for_entity(entity: dict, document_text: str) -> list[str]
  - Extract supporting quotes from document text
  - Find mentions of entity in text
  - Extract surrounding context (max 200 chars)
  - Return list of quotes

Accuracy Tracking:
• calculate_extraction_accuracy(extracted: list[dict], 
                               ground_truth: list[dict]) -> float
  - Calculate extraction accuracy against ground truth
  - Compare: Entity types, Properties, External IDs
  - Return accuracy score (0.0-1.0)
  - Target: >85% accuracy

• validate_against_samples(extracted: list[dict], 
                          sample_extractions: list[dict]) -> dict
  - Validate extraction against sample extractions
  - Compare with known good extractions
  - Return validation report with accuracy metrics

Error Handling:
• handle_extraction_error(document_id: str, error: Exception) -> dict
  - Handle extraction errors gracefully
  - Log error with document details
  - Return error record
  - Mark document for retry if transient error

• retry_failed_extractions(failed_documents: list[dict]) -> list[dict]
  - Retry extraction for failed documents
  - Use exponential backoff
  - Return retry results

Statistics and Reporting:
• generate_extraction_statistics(results: list[dict]) -> dict
  - Generate extraction statistics
  - Includes: Total documents processed, Success count, Failure count,
    Entities extracted by type, External ID resolution rate,
    Provenance coverage, Average entities per document
  - Return statistics dictionary

• generate_extraction_report(results: list[dict]) -> dict
  - Generate comprehensive extraction report
  - Includes: Statistics, Error breakdown, Accuracy metrics,
    Processing time, Recommendations
  - Return report dictionary

Caching:
• cache_extraction_result(document_id: str, result: dict) -> None
  - Cache extraction result to avoid re-processing
  - Key: document_id, Value: extraction result
  - Check cache before extraction

• get_cached_result(document_id: str) -> Optional[dict]
  - Get cached extraction result
  - Return result or None if not cached

INTEGRATION POINTS:
• Uses: maris.semantica_integration (for entity extraction API)
• Uses: maris.schemas (for entity schema validation)
• Uses: maris.provenance (for provenance tracking)
• Uses: maris.utils (for error handling, retry logic)
• Used by: maris.cli (for extract-entities command)
• Configuration: Uses maris.config.Config for extraction settings
"""
