"""
Bridge axiom reasoning using Semantica

Clean reasoning functions using Semantica's built-in reasoning engines:
- RuleEngine for rule management
- ReteEngine for efficient pattern matching
- ForwardChaining for inference
"""
from typing import Dict, Any, List
from maris.data import load_bridge_axioms
from maris.utils import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
# AXIOM APPLICATION
# ═══════════════════════════════════════════════════════════════════

def apply_bridge_axioms(knowledge_graph: Any) -> Dict[str, Any]:
    """
    Apply bridge axioms using Semantica's ReteEngine and ForwardChaining
    
    Args:
        knowledge_graph: Built knowledge graph
        
    Returns:
        Inferred facts from axiom application
    """
    from semantica.reasoning import ReteEngine, ForwardChaining
    
    logger.info("Applying bridge axioms...")
    
    # Load axioms from schema
    axioms = load_bridge_axioms()
    
    # Use Semantica's ReteEngine for efficient pattern matching
    rete = ReteEngine()
    
    # Register all 12 axioms
    axiom_count = 0
    for axiom in axioms.get('axioms', []):
        rete.add_rule(
            rule_id=axiom['axiom_id'],
            pattern=axiom['pattern'],
            action=axiom.get('consequent'),
            evidence=axiom.get('sources', [])
        )
        axiom_count += 1
    
    logger.info(f"Registered {axiom_count} bridge axioms")
    
    # Use Semantica's ForwardChaining for inference
    forward_chain = ForwardChaining(rule_engine=rete)
    inferred_facts = forward_chain.infer(
        knowledge_base=knowledge_graph,
        max_iterations=10
    )
    
    logger.info(f"✓ Inferred {len(inferred_facts)} new facts")
    return inferred_facts


def get_axiom_evidence(axiom_id: str) -> List[Dict[str, Any]]:
    """
    Get evidence sources for a specific axiom
    
    Args:
        axiom_id: Bridge axiom ID (e.g., "BA-001")
        
    Returns:
        List of evidence sources
    """
    logger.info(f"Getting evidence for axiom: {axiom_id}")
    
    axioms = load_bridge_axioms()
    
    for axiom in axioms.get('axioms', []):
        if axiom['axiom_id'] == axiom_id:
            sources = axiom.get('sources', [])
            logger.info(f"✓ Found {len(sources)} evidence sources")
            return sources
    
    logger.warning(f"Axiom {axiom_id} not found")
    return []


def validate_axiom(axiom_id: str, test_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate an axiom against test data
    
    Args:
        axiom_id: Bridge axiom ID
        test_data: Test data for validation
        
    Returns:
        Validation results
    """
    from semantica.reasoning import RuleEngine
    
    logger.info(f"Validating axiom: {axiom_id}")
    
    # Get axiom details
    evidence = get_axiom_evidence(axiom_id)
    
    # Use Semantica's RuleEngine
    engine = RuleEngine()
    
    # Add rule
    axioms = load_bridge_axioms()
    for axiom in axioms.get('axioms', []):
        if axiom['axiom_id'] == axiom_id:
            engine.add_rule(
                rule_id=axiom['axiom_id'],
                pattern=axiom['pattern']
            )
            break
    
    # Apply to test data
    results = engine.apply(test_data)
    
    logger.info("✓ Axiom validation complete")
    
    return {
        'axiom_id': axiom_id,
        'evidence_count': len(evidence),
        'results': results
    }
