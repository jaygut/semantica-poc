"""
Provenance tracking utilities for MARIS POC

TIMELINE: Week 2-3 (Phase 2: Data Loading & Processing)
IMPLEMENTATION PRIORITY: High - Required for all extraction operations

This module handles provenance tracking for all extracted data to ensure audit-grade traceability.

PROVENANCE REQUIREMENTS:
• Every entity must have provenance linking to source document
• Every relationship must have provenance showing extraction source
• Every bridge axiom application must track evidence sources
• All claims must include: DOI, page reference, direct quote
• Document hash (SHA-256) for integrity verification
• Extraction metadata: extractor, timestamp, method

PROVENANCE STRUCTURE:
• Source Document: title, authors, year, DOI, journal, tier
• Page Reference: page number, figure/table reference, quote location
• Supporting Quote: direct quote from source (max 200 chars)
• Extraction Metadata: extractor name, extraction timestamp, method (manual/LLM)
• Document Hash: SHA-256 hash of source document for integrity

KEY FUNCTIONS TO IMPLEMENT:

Provenance Creation:
• create_provenance(source_doc: dict, page_ref: str, quote: str,
                   extraction_metadata: dict = {}) -> dict
  - Create provenance object for entity/relationship
  - Parameters:
    * source_doc: Document metadata (title, DOI, authors, etc.)
    * page_ref: Page reference ("p. 123", "Figure 2", "Table S4")
    * quote: Supporting quote from document
    * extraction_metadata: Extractor, timestamp, method
  - Calculate document hash if document content available
  - Return provenance dictionary
  - Validate: DOI present, page_ref present, quote present

• create_provenance_chain(provenances: list[dict]) -> dict
  - Create provenance chain for multi-hop reasoning
  - Link multiple provenance objects in sequence
  - Track chain confidence (product of individual confidences)
  - Return provenance chain dictionary

Citation Formatting:
• format_citation(provenance: dict, style: str = "apa") -> str
  - Format provenance as academic citation
  - Styles: APA, MLA, Chicago, Nature
  - Format: "Author et al. (Year). Title. Journal. DOI. p. XX."
  - Return formatted citation string

• format_citation_with_quote(provenance: dict) -> str
  - Format citation with supporting quote
  - Format: Citation + "Quote: '...' (p. XX)"
  - Return formatted string

• format_provenance_for_display(provenance: dict) -> str
  - Format provenance for user display
  - Include: Source, page reference, quote, confidence
  - Return formatted string

Provenance Validation:
• validate_provenance_completeness(provenance: dict) -> dict
  - Validate provenance has all required fields
  - Check: DOI present, page_ref present, quote present,
    source_doc metadata complete, document_hash present
  - Return validation result with missing fields

• validate_provenance_chain(chain: dict) -> dict
  - Validate provenance chain integrity
  - Check: All links valid, Chain confidence calculated,
    No broken links, All sources accessible
  - Return validation result

Provenance Queries:
• find_claims_by_source(source_doi: str, entities: list[dict],
                       relationships: list[dict]) -> list[dict]
  - Find all claims (entities/relationships) from a source
  - Search by DOI
  - Return list of claims with provenance

• find_claims_by_page(source_doi: str, page_ref: str,
                     entities: list[dict], relationships: list[dict]) -> list[dict]
  - Find all claims from specific page
  - Return list of claims

• get_provenance_statistics(entities: list[dict], relationships: list[dict]) -> dict
  - Calculate provenance coverage statistics
  - Includes: Total claims, Claims with DOI, Claims with page ref,
    Claims with quote, Claims with document hash, Provenance completeness %
  - Return statistics dictionary

Provenance Aggregation:
• aggregate_provenance(claims: list[dict]) -> dict
  - Aggregate provenance from multiple sources for same claim
  - Combine: Multiple DOIs, Multiple page references, Multiple quotes
  - Calculate aggregated confidence (weighted average)
  - Return aggregated provenance

• merge_provenance_sources(provenance1: dict, provenance2: dict) -> dict
  - Merge two provenance objects
  - Combine sources, quotes, page references
  - Update confidence score
  - Return merged provenance

Document Hash Management:
• calculate_document_hash(document_path: Path) -> str
  - Calculate SHA-256 hash of document
  - Return hex digest string
  - Used for integrity verification

• verify_document_integrity(provenance: dict, document_path: Path) -> bool
  - Verify document hasn't changed since extraction
  - Compare stored hash with current hash
  - Return True if hash matches

Provenance Graphs:
• build_provenance_graph(entities: list[dict], relationships: list[dict]) -> dict
  - Build provenance graph showing data lineage
  - Nodes: Documents, Entities, Relationships
  - Edges: DERIVED_FROM relationships
  - Return graph structure

• visualize_provenance_chain(chain: dict) -> str
  - Generate visualization of provenance chain
  - Format: Document → Entity → Relationship → Axiom Application
  - Return visualization string (text or GraphML)

Provenance Export:
• export_provenance_for_audit(entities: list[dict], relationships: list[dict]) -> dict
  - Export provenance data for audit trail
  - Include: All claims, All sources, All quotes, All hashes
  - Return audit trail dictionary

• generate_provenance_report(entities: list[dict], relationships: list[dict]) -> dict
  - Generate provenance coverage report
  - Includes: Completeness statistics, Missing fields breakdown,
    Source distribution, Confidence score distribution
  - Return report dictionary

Confidence Tracking:
• calculate_provenance_confidence(provenance: dict) -> float
  - Calculate confidence score for provenance
  - Factors: Source tier (T1=1.0, T2=0.8, T3=0.6, T4=0.4),
    Quote quality, Page reference specificity
  - Return confidence score (0.0-1.0)

• propagate_confidence_through_chain(chain: dict) -> float
  - Propagate confidence through provenance chain
  - Multiply individual confidences
  - Return chain confidence

INTEGRATION POINTS:
• Used by: maris.entity_extractor (to attach provenance to entities)
• Used by: maris.relationship_extractor (to attach provenance to relationships)
• Used by: maris.query_engine (to format provenance in query responses)
• Used by: maris.validators (to validate provenance completeness)
• Uses: maris.utils (for hash calculation, citation formatting)
• Configuration: Uses maris.config.Config for provenance settings
"""
