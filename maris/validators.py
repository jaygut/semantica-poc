"""
Validation utilities for MARIS POC

TIMELINE: Week 4 (Phase 2: Knowledge Extraction & Bridge Axioms via Semantica) and Week 7 (Phase 4: Integration, Testing & Demo via Semantica)
IMPLEMENTATION PRIORITY: High - Validate extraction accuracy and axiom applications
MILESTONE: Validate Cabo Pulmo predictions, extraction accuracy >85%

This module provides comprehensive validation functions to ensure data quality,
extraction accuracy, and system correctness.

VALIDATION TYPES:

• Entity Extraction Validation
  - Compare extracted entities against ground truth (sample extractions)
  - Validate entity properties accuracy
  - Check external identifier resolution
  - Measure extraction accuracy (target: >85%)

• Relationship Extraction Validation
  - Validate relationship accuracy against samples
  - Check relationship cardinality constraints
  - Validate subject-object entity linking
  - Measure relationship extraction accuracy

• Bridge Axiom Validation
  - Validate axiom application results
  - Compare predictions to observed values
  - Check coefficient calculations
  - Validate uncertainty propagation

• Cabo Pulmo Case Study Validation
  - Validate predictions against Cabo Pulmo observed values
  - Check within ±20% tolerance
  - Validate NEOLI score calculation
  - Validate ecosystem service value calculations

• Schema Compliance Validation
  - Validate entities against entity schema
  - Validate relationships against relationship schema
  - Check required fields present
  - Validate field types and ranges

• Provenance Completeness Validation
  - Check all claims have DOI
  - Check all claims have page reference
  - Check all claims have supporting quote
  - Validate document hash presence

• Data Integrity Validation
  - Check no orphaned nodes in graph
  - Validate entity-relationship links
  - Check external identifier resolution
  - Validate data consistency

KEY FUNCTIONS TO IMPLEMENT:

Entity Extraction Validation:
• validate_entity_extraction(extracted: list[dict], 
                             ground_truth: list[dict]) -> dict
  - Compare extracted entities against sample extractions
  - Calculate accuracy metrics:
    * Precision: Correct extractions / Total extractions
    * Recall: Correct extractions / Total in ground truth
    * F1 Score: Harmonic mean of precision and recall
    * Entity type accuracy: Accuracy by entity type
  - Return validation result with accuracy scores
  - Target: >85% overall accuracy

• validate_entity_properties(entity: dict, ground_truth: dict) -> dict
  - Validate entity properties against ground truth
  - Compare: Property values, External IDs, Relationships
  - Return property-level validation result

• validate_external_id_resolution(entities: list[dict]) -> dict
  - Validate external identifier resolution
  - Check: WoRMS IDs resolve, FishBase codes resolve,
    WDPA IDs resolve (for MPAs)
  - Return resolution statistics

Relationship Extraction Validation:
• validate_relationship_extraction(extracted: list[dict],
                                  ground_truth: list[dict],
                                  entities: list[dict]) -> dict
  - Validate relationship extraction accuracy
  - Check: Relationship types correct, Subject-object pairs correct,
    Properties accurate, Cardinality constraints satisfied
  - Return validation result with accuracy metrics

• validate_relationship_cardinality(relationship: dict, rel_type_def: dict) -> bool
  - Validate relationship cardinality constraint
  - Check: many:many, one:many, one:one constraints
  - Return True if valid

Bridge Axiom Validation:
• validate_bridge_axiom(axiom_id: str, application_result: dict,
                       observed_value: Optional[float] = None,
                       tolerance: float = 0.20) -> dict
  - Validate bridge axiom application
  - Compare prediction to observed value if provided
  - Check within tolerance (±20% default)
  - Validate coefficient calculations
  - Return validation result

• validate_axiom_coefficients(axiom: dict, application: dict) -> dict
  - Validate coefficient calculations
  - Check: Coefficients in valid ranges, Calculations correct,
    Confidence intervals valid
  - Return validation result

Cabo Pulmo Validation:
• validate_cabo_pulmo(cabo_pulmo_data: dict, axioms_applied: list[dict]) -> dict
  - Validate predictions against Cabo Pulmo case study
  - Test axioms: BA-001 (biomass-tourism), BA-002 (NEOLI → biomass)
  - Compare predictions to observed values:
    * Biomass recovery: 463% observed
    * Tourism revenue: $25M observed
    * NEOLI score: 4/5 observed
  - Check within ±20% tolerance
  - Return validation result with pass/fail for each axiom

• validate_neoli_score(mpa_data: dict) -> dict
  - Validate NEOLI score calculation
  - Check: All 5 criteria evaluated correctly,
    Score calculation correct (count of criteria met)
  - Compare to expected score
  - Return validation result

• validate_ecosystem_service_values(cabo_pulmo_data: dict,
                                   calculated_values: dict) -> dict
  - Validate ecosystem service value calculations
  - Compare: Tourism ($25M), Fisheries spillover ($3.2M),
    Carbon sequestration ($180K), Coastal protection ($890K)
  - Check within ±20% tolerance
  - Return validation result

Schema Compliance Validation:
• validate_schema_compliance(entities: list[dict], relationships: list[dict]) -> dict
  - Validate all entities and relationships against schemas
  - Check: Required fields present, Field types correct,
    Field values in valid ranges, External IDs valid format
  - Return compliance report

• validate_entity_schema_compliance(entity: dict, entity_type: str) -> dict
  - Validate single entity against schema
  - Use maris.schemas for schema validation
  - Return compliance result

Provenance Validation:
• validate_provenance(entities: list[dict], relationships: list[dict]) -> dict
  - Validate provenance completeness
  - Check: All entities have provenance, All relationships have provenance,
    All provenance has DOI, All provenance has page reference,
    All provenance has quote, All provenance has document hash
  - Return provenance completeness statistics

• validate_provenance_completeness(provenance: dict) -> dict
  - Validate single provenance object
  - Check required fields present
  - Return validation result

Data Integrity Validation:
• validate_graph_integrity(graph: dict) -> dict
  - Validate graph structure integrity
  - Check: No orphaned nodes, All relationships link valid nodes,
    No duplicate nodes, No duplicate relationships
  - Return integrity check result

• validate_entity_relationship_links(entities: list[dict],
                                    relationships: list[dict]) -> dict
  - Validate entity-relationship links
  - Check: All relationship subjects exist, All relationship objects exist,
    Entity types match relationship domain/range
  - Return validation result

Query Response Validation:
• validate_query_response(response: dict) -> dict
  - Validate query response structure
  - Check: Answer present, Provenance chains present,
    Confidence scores present, Reasoning paths present,
    Citations formatted correctly
  - Return validation result

• validate_query_provenance(response: dict) -> dict
  - Validate provenance in query response
  - Check: All claims have provenance, Provenance chains complete,
    Citations include DOI + page + quote
  - Return validation result

Confidence Score Validation:
• validate_confidence_scores(entities: list[dict], relationships: list[dict]) -> dict
  - Validate confidence scores
  - Check: Scores in valid range (0.0-1.0), Scores calculated correctly,
    Confidence propagation correct
  - Return validation result

Report Generation:
• generate_validation_report(validation_results: dict) -> dict
  - Generate comprehensive validation report
  - Includes: Overall validation status, Accuracy metrics,
    Error breakdown, Recommendations, Pass/fail summary
  - Return report dictionary

• format_validation_report(report: dict) -> str
  - Format validation report for display
  - Create human-readable report
  - Include statistics, errors, recommendations
  - Return formatted string

INTEGRATION POINTS:
• Uses: maris.schemas (for schema validation)
• Uses: maris.provenance (for provenance validation)
• Uses: maris.bridge_axiom_engine (for axiom validation)
• Used by: maris.cli (for validate command)
• Used by: Tests (for automated validation)
• Configuration: Uses maris.config.Config for validation settings
"""
