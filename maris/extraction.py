"""
Entity and relationship extraction using Semantica

Clean extraction functions using Semantica's built-in extractors:
- FileIngestor for document ingestion
- DoclingParser for PDF parsing
- NERExtractor for entity extraction
- RelationExtractor for relationship extraction
- EntityNormalizer for normalization
- EntityDeduplicator for deduplication
"""
from typing import Dict, Any, List
from pathlib import Path
from maris.semantica import get_llm
from maris.data import get_entity_types, get_relationship_types
from maris.utils import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
# DOCUMENT INGESTION
# ═══════════════════════════════════════════════════════════════════

def ingest_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Ingest PDF using Semantica's FileIngestor and DoclingParser
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dict with 'text', 'tables', 'figures'
    """
    from semantica.ingest import FileIngestor
    from semantica.parse import DoclingParser
    
    logger.info(f"Ingesting PDF: {pdf_path}")
    
    # Use Semantica's FileIngestor
    ingestor = FileIngestor()
    document = ingestor.ingest(pdf_path)
    
    # Use Semantica's DoclingParser for advanced PDF parsing
    parser = DoclingParser(
        extract_tables=True,
        extract_figures=True,
        ocr_enabled=True
    )
    parsed = parser.parse(document)
    
    logger.info(f"✓ Parsed: {len(parsed.get('text', ''))} chars, "
                f"{len(parsed.get('tables', []))} tables, "
                f"{len(parsed.get('figures', []))} figures")
    
    return {
        'text': parsed['text'],
        'tables': parsed.get('tables', []),
        'figures': parsed.get('figures', []),
        'metadata': parsed.get('metadata', {})
    }


def ingest_worms_ontology() -> Dict[str, Any]:
    """
    Import WoRMS taxonomy using Semantica's OntologyIngestor
    
    Returns:
        Imported ontology
    """
    from semantica.ontology import OntologyIngestor
    
    logger.info("Importing WoRMS taxonomy ontology...")
    
    ingestor = OntologyIngestor()
    ontology = ingestor.ingest(
        source='http://www.marinespecies.org/aphia.php?p=soap',
        format='rdf'
    )
    
    logger.info("✓ WoRMS ontology imported")
    return ontology


# ═══════════════════════════════════════════════════════════════════
# ENTITY EXTRACTION
# ═══════════════════════════════════════════════════════════════════

def extract_entities(document: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract entities using Semantica's NERExtractor
    
    Args:
        document: Parsed document with 'text' key
        
    Returns:
        List of extracted entities
    """
    from semantica.semantic_extract import NERExtractor
    
    logger.info("Extracting entities with Semantica NERExtractor...")
    
    # Get LLM from our helper
    llm = get_llm()
    
    # Get entity types from schema
    entity_types = get_entity_types()
    
    # Use Semantica's NERExtractor
    extractor = NERExtractor(
        method="llm",
        llm_provider=llm,
        entity_types=entity_types
    )
    
    entities = extractor.extract(document['text'])
    
    logger.info(f"✓ Extracted {len(entities)} entities")
    return entities


def normalize_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize entities using Semantica's EntityNormalizer
    
    Args:
        entities: List of entities
        
    Returns:
        List of normalized entities
    """
    from semantica.normalize import EntityNormalizer, NumberNormalizer
    
    logger.info("Normalizing entities...")
    
    # Use Semantica's normalizers
    entity_norm = EntityNormalizer()
    number_norm = NumberNormalizer()
    
    normalized = []
    for entity in entities:
        # Normalize entity names
        if 'name' in entity:
            entity['normalized_name'] = entity_norm.normalize(entity['name'])
        
        # Normalize numbers (biomass, area, etc.)
        if 'biomass' in entity:
            entity['biomass_normalized'] = number_norm.normalize(entity['biomass'])
        
        normalized.append(entity)
    
    logger.info(f"✓ Normalized {len(normalized)} entities")
    return normalized


def deduplicate_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate entities using Semantica's EntityDeduplicator
    
    Args:
        entities: List of entities (may contain duplicates)
        
    Returns:
        List of deduplicated entities
    """
    from semantica.deduplication import EntityDeduplicator
    
    logger.info("Deduplicating entities...")
    
    # Use Semantica's EntityDeduplicator
    deduplicator = EntityDeduplicator()
    deduplicated = deduplicator.deduplicate(entities)
    
    logger.info(f"✓ Deduplicated: {len(entities)} → {len(deduplicated)} entities")
    return deduplicated


# ═══════════════════════════════════════════════════════════════════
# RELATIONSHIP EXTRACTION
# ═══════════════════════════════════════════════════════════════════

def extract_relationships(
    document: Dict[str, Any],
    entities: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Extract relationships using Semantica's RelationExtractor
    
    Args:
        document: Parsed document
        entities: List of entities
        
    Returns:
        List of extracted relationships
    """
    from semantica.semantic_extract import RelationExtractor
    
    logger.info("Extracting relationships with Semantica RelationExtractor...")
    
    # Get LLM and relationship types
    llm = get_llm()
    relation_types = get_relationship_types()
    
    # Use Semantica's RelationExtractor
    extractor = RelationExtractor(
        method="llm",
        llm_provider=llm,
        relation_types=relation_types
    )
    
    relationships = extractor.extract(document['text'], entities)
    
    logger.info(f"✓ Extracted {len(relationships)} relationships")
    return relationships


def extract_triplets(document: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract RDF triplets using Semantica's TripletExtractor
    
    Args:
        document: Parsed document
        
    Returns:
        List of RDF triplets
    """
    from semantica.semantic_extract import TripletExtractor
    
    logger.info("Extracting RDF triplets...")
    
    # Use Semantica's TripletExtractor
    extractor = TripletExtractor()
    triplets = extractor.extract(document['text'])
    
    logger.info(f"✓ Extracted {len(triplets)} triplets")
    return triplets


# ═══════════════════════════════════════════════════════════════════
# CONFLICT RESOLUTION
# ═══════════════════════════════════════════════════════════════════

def resolve_conflicts(
    entities_from_papers: List[List[Dict[str, Any]]]
) -> List[Dict[str, Any]]:
    """
    Resolve conflicts using Semantica's ConflictDetector and ConflictResolver
    
    Args:
        entities_from_papers: List of entity lists from different papers
        
    Returns:
        List of entities with conflicts resolved
    """
    from semantica.conflicts import ConflictDetector, ConflictResolver
    
    logger.info("Detecting and resolving conflicts...")
    
    # Use Semantica's ConflictDetector
    detector = ConflictDetector()
    conflicts = detector.detect(
        entities=entities_from_papers,
        properties_to_check=['biomass', 'recovery_rate', 'value_usd']
    )
    
    logger.info(f"Found {len(conflicts)} conflicts")
    
    # Use Semantica's ConflictResolver
    resolver = ConflictResolver()
    resolved = resolver.resolve(conflicts)
    
    logger.info(f"✓ Resolved {len(resolved)} entities")
    return resolved


# ═══════════════════════════════════════════════════════════════════
# FULL EXTRACTION PIPELINE
# ═══════════════════════════════════════════════════════════════════

def extract_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Complete extraction pipeline: ingest → extract → normalize → deduplicate
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Dict with 'entities' and 'relationships'
    """
    logger.info(f"Running full extraction pipeline for: {pdf_path}")
    
    # 1. Ingest PDF
    document = ingest_pdf(pdf_path)
    
    # 2. Extract entities
    raw_entities = extract_entities(document)
    
    # 3. Normalize entities
    normalized = normalize_entities(raw_entities)
    
    # 4. Deduplicate
    entities = deduplicate_entities(normalized)
    
    # 5. Extract relationships
    relationships = extract_relationships(document, entities)
    
    logger.info(f"✓ Pipeline complete: {len(entities)} entities, {len(relationships)} relationships")
    
    return {
        'entities': entities,
        'relationships': relationships,
        'document': document
    }
