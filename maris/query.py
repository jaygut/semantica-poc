"""
GraphRAG queries using Semantica

Clean query functions using Semantica's built-in query classes:
- AgentContext for GraphRAG with reasoning
- HybridSearch for vector + graph search
- AgentMemory for conversation context
- ContextRetriever for context retrieval
"""
from typing import Dict, Any, List
from maris.semantica import get_agent_context, get_llm, get_vector_store
from maris.utils import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
# CORE QUERY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def query_graphrag(question: str, max_hops: int = 4) -> Dict[str, Any]:
    """
    Run GraphRAG query using Semantica's AgentContext
    
    Args:
        question: Natural language query
        max_hops: Maximum graph traversal hops (default: 4)
        
    Returns:
        Query response with answer and provenance
    """
    logger.info(f"GraphRAG query: {question}")
    
    # Use our helper to get AgentContext
    agent = get_agent_context()
    
    # Use Semantica's AgentContext.query_with_reasoning
    response = agent.query_with_reasoning(
        query=question,
        max_hops=max_hops,
        include_provenance=True
    )
    
    logger.info("✓ Query completed")
    return response


def query_with_hybrid_search(question: str, top_k: int = 10) -> Dict[str, Any]:
    """
    Query using Semantica's HybridSearch and ContextRetriever
    
    Args:
        question: Natural language query
        top_k: Number of results to retrieve
        
    Returns:
        Query response with context-enhanced answer
    """
    from semantica.vector_store import HybridSearch
    from semantica.context import ContextRetriever
    
    logger.info(f"Hybrid search query: {question}")
    
    # Get components
    vector_store = get_vector_store()
    
    # Use Semantica's HybridSearch
    hybrid = HybridSearch(
        vector_store=vector_store,
        metadata_filters=['tier', 'domain', 'year']
    )
    
    # Use Semantica's ContextRetriever
    retriever = ContextRetriever(hybrid_search=hybrid)
    context = retriever.retrieve(question, top_k=top_k)
    
    # Query with enhanced context
    agent = get_agent_context()
    response = agent.query_with_reasoning(
        query=question,
        context=context,
        max_hops=4
    )
    
    logger.info("✓ Hybrid query completed")
    return response


def query_with_memory(question: str, session_id: str = 'default') -> Dict[str, Any]:
    """
    Query with Semantica's AgentMemory for conversation context
    
    Args:
        question: Natural language query
        session_id: Session identifier for memory persistence
        
    Returns:
        Query response with memory-aware context
    """
    from semantica.context import AgentMemory
    
    logger.info(f"Memory-aware query (session: {session_id}): {question}")
    
    # Use Semantica's AgentMemory
    memory = AgentMemory(persistence_path=f'data/memory/{session_id}')
    
    # Query with memory
    agent = get_agent_context()
    response = agent.query_with_reasoning(
        query=question,
        memory=memory,
        max_hops=4
    )
    
    logger.info("✓ Memory query completed")
    return response


# ═══════════════════════════════════════════════════════════════════
# QUERY TEMPLATES (11 sample queries from POC)
# ═══════════════════════════════════════════════════════════════════

def cabo_pulmo_queries() -> List[str]:
    """
    Cabo Pulmo validation queries
    
    Returns:
        List of Cabo Pulmo-focused queries
    """
    return [
        "What ecological factors explain Cabo Pulmo's 463% biomass recovery?",
        "Does Cabo Pulmo meet NEOLI criteria for MPA effectiveness?",
        "What is the trophic cascade mechanism at Cabo Pulmo?",
        "What species drove the recovery at Cabo Pulmo?",
        "How does Cabo Pulmo compare to other successful MPAs?"
    ]


def blue_bond_queries() -> List[str]:
    """
    Blue bond structuring queries
    
    Returns:
        List of blue finance queries
    """
    return [
        "What ecological KPIs should a $50M blue bond for mangrove restoration use?",
        "How much carbon credit revenue could a 1,000 ha seagrass restoration project generate?",
        "What is the expected benefit-cost ratio for coral reef protection?",
        "What TNFD disclosure fields are required for marine conservation?",
        "What verification standards should be used for blue carbon credits?"
    ]


def trophic_cascade_queries() -> List[str]:
    """
    Trophic cascade mechanism queries
    
    Returns:
        List of trophic ecology queries
    """
    return [
        "How does sea otter presence affect kelp forest carbon sequestration?",
        "Explain the California sheephead's role in protecting kelp forests",
        "What happens to ecosystem services if apex predators are removed?",
        "What is the otter-kelp-carbon cascade mechanism?",
        "How do trophic cascades affect ecosystem service provision?"
    ]


def mpa_impact_queries() -> List[str]:
    """
    MPA impact assessment queries
    
    Returns:
        List of MPA effectiveness queries
    """
    return [
        "If we establish a no-take MPA, what biomass recovery can we expect?",
        "What timeline is needed for measurable recovery in a no-take MPA?",
        "How does MPA size affect recovery outcomes?",
        "What enforcement mechanisms are most effective for MPAs?"
    ]


def all_demo_queries() -> List[str]:
    """
    Get all demo queries for investor presentation
    
    Returns:
        Combined list of all query types (11 total)
    """
    return (
        cabo_pulmo_queries()[:3] +  # Top 3 Cabo Pulmo
        blue_bond_queries()[:3] +   # Top 3 blue finance
        trophic_cascade_queries()[:2] +  # Top 2 mechanisms
        mpa_impact_queries()[:3]  # Top 3 impact
    )  # Total: 11 queries


# ═══════════════════════════════════════════════════════════════════
# BATCH QUERY EXECUTION
# ═══════════════════════════════════════════════════════════════════

def run_query_batch(queries: List[str], use_hybrid: bool = False) -> List[Dict[str, Any]]:
    """
    Run a batch of queries
    
    Args:
        queries: List of query strings
        use_hybrid: Whether to use hybrid search (default: False)
        
    Returns:
        List of query responses
    """
    logger.info(f"Running batch of {len(queries)} queries (hybrid={use_hybrid})")
    
    results = []
    for i, query in enumerate(queries, 1):
        logger.info(f"Query {i}/{len(queries)}: {query[:80]}...")
        
        if use_hybrid:
            response = query_with_hybrid_search(query)
        else:
            response = query_graphrag(query)
        
        results.append({
            'query': query,
            'response': response
        })
    
    logger.info(f"✓ Batch query completed: {len(results)} results")
    return results


def run_demo_queries(use_hybrid: bool = False) -> List[Dict[str, Any]]:
    """
    Run all 11 demo queries for investor presentation
    
    Args:
        use_hybrid: Whether to use hybrid search
        
    Returns:
        List of demo query responses
    """
    logger.info("Running investor demo queries...")
    
    demo_queries = all_demo_queries()
    return run_query_batch(demo_queries, use_hybrid=use_hybrid)
