"""
Simple Semantica client setup

Provides easy access to configured Semantica components.
Each function creates the component with proper configuration.
"""
from typing import Any
from maris.config import get_config
from maris.utils import get_logger

logger = get_logger(__name__)


def get_llm():
    """
    Get configured Groq LLM client
    
    Returns:
        Groq LLM instance configured from config
    """
    from semantica.llms import Groq
    
    config = get_config()
    logger.debug(f"Creating Groq LLM with model: {config.groq_model}")
    
    return Groq(
        api_key=config.groq_api_key,
        model=config.groq_model,
        temperature=config.groq_temperature
    )


def get_graph_store():
    """
    Get configured FalkorDB graph store
    
    Returns:
        FalkorDBStore instance configured from config
    """
    from semantica.graph_store import FalkorDBStore
    
    config = get_config()
    logger.debug(f"Creating FalkorDB store: {config.falkordb_graph_name}")
    
    return FalkorDBStore(
        host=config.falkordb_host,
        port=config.falkordb_port,
        graph_name=config.falkordb_graph_name
    )


def get_vector_store():
    """
    Get FAISS vector store
    
    Returns:
        FAISSStore instance
    """
    from semantica.vector_store import FAISSStore
    
    logger.debug("Creating FAISS vector store")
    return FAISSStore()


def get_agent_context():
    """
    Get AgentContext for GraphRAG queries
    
    Returns:
        AgentContext with configured stores and LLM
    """
    from semantica.context import AgentContext
    
    logger.debug("Creating AgentContext for GraphRAG")
    
    return AgentContext(
        vector_store=get_vector_store(),
        graph_store=get_graph_store(),
        llm_provider=get_llm()
    )
