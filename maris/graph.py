"""
Knowledge graph building using Semantica

Clean graph functions using Semantica's built-in classes:
- GraphBuilder for graph construction
- EntityResolver for entity resolution
- ProvenanceTracker for source tracking
- TemporalGraphQuery for time-series data
- CommunityDetector for network analysis
- ConnectivityAnalyzer for MPA networks
"""
from typing import Dict, Any, List
from maris.semantica import get_graph_store
from maris.utils import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
# GRAPH BUILDING
# ═══════════════════════════════════════════════════════════════════

def build_knowledge_graph(
    entities: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]]
) -> Any:
    """
    Build knowledge graph using Semantica's GraphBuilder
    
    Args:
        entities: List of entities
        relationships: List of relationships
        
    Returns:
        Built knowledge graph
    """
    from semantica.kg import GraphBuilder, EntityResolver, ProvenanceTracker
    
    logger.info("Building knowledge graph...")
    
    # 1. Resolve entities using Semantica's EntityResolver
    logger.info("Resolving entities...")
    resolver = EntityResolver()
    resolved_entities = resolver.resolve(entities, use_external_ids=True)
    
    # 2. Get configured graph store
    graph_store = get_graph_store()
    
    # 3. Build graph using Semantica's GraphBuilder
    builder = GraphBuilder(graph_store=graph_store, temporal=True)
    graph = builder.build(
        entities=resolved_entities,
        relationships=relationships
    )
    
    # 4. Track provenance using Semantica's ProvenanceTracker
    logger.info("Tracking provenance...")
    provenance = ProvenanceTracker()
    for entity in resolved_entities:
        if 'source_document' in entity:
            provenance.track(entity, source=entity['source_document'])
    
    logger.info(f"✓ Graph built: {len(resolved_entities)} entities, "
                f"{len(relationships)} relationships")
    
    return graph


# ═══════════════════════════════════════════════════════════════════
# TEMPORAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def query_temporal(
    site_name: str,
    start_year: int,
    end_year: int
) -> Dict[str, Any]:
    """
    Query temporal data using Semantica's TemporalGraphQuery
    
    Args:
        site_name: MPA site name (e.g., "Cabo Pulmo")
        start_year: Start year
        end_year: End year
        
    Returns:
        Temporal query results
    """
    from semantica.kg import TemporalGraphQuery
    
    logger.info(f"Querying temporal data: {site_name} ({start_year}-{end_year})")
    
    # Use Semantica's TemporalGraphQuery
    temporal = TemporalGraphQuery()
    results = temporal.query_time_range(
        query=f"SELECT biomass, year FROM Site WHERE name='{site_name}'",
        start_time=f'{start_year}-01-01',
        end_time=f'{end_year}-12-31'
    )
    
    logger.info("✓ Temporal query complete")
    return results


def detect_recovery_pattern(site_name: str) -> Dict[str, Any]:
    """
    Detect recovery patterns using Semantica's TemporalPatternDetector
    
    Args:
        site_name: MPA site name
        
    Returns:
        Detected patterns (exponential, sigmoid, etc.)
    """
    from semantica.kg import TemporalPatternDetector
    
    logger.info(f"Detecting recovery pattern: {site_name}")
    
    # Use Semantica's TemporalPatternDetector
    detector = TemporalPatternDetector()
    patterns = detector.detect(
        entity_type='biomass_recovery',
        entity_id=site_name,
        pattern_types=['exponential_growth', 'sigmoid_recovery']
    )
    
    logger.info("✓ Pattern detection complete")
    return patterns


# ═══════════════════════════════════════════════════════════════════
# NETWORK ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def analyze_trophic_network(
    species_entities: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze trophic network using Semantica's CommunityDetector
    
    Args:
        species_entities: List of species entities
        
    Returns:
        Network analysis results
    """
    from semantica.kg import CommunityDetector
    
    logger.info("Analyzing trophic network...")
    
    # Use Semantica's CommunityDetector
    detector = CommunityDetector()
    analysis = detector.detect(entities=species_entities, edge_type='PREYS_ON')
    
    logger.info("✓ Trophic network analysis complete")
    return analysis


def analyze_mpa_connectivity(
    mpa_entities: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze MPA connectivity using Semantica's ConnectivityAnalyzer
    
    Args:
        mpa_entities: List of MPA entities
        
    Returns:
        Connectivity analysis results
    """
    from semantica.kg import ConnectivityAnalyzer
    
    logger.info("Analyzing MPA connectivity...")
    
    # Use Semantica's ConnectivityAnalyzer
    analyzer = ConnectivityAnalyzer()
    analysis = analyzer.analyze(entities=mpa_entities, edge_type='CONNECTED_TO')
    
    logger.info("✓ MPA connectivity analysis complete")
    return analysis
