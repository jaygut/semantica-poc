"""
Graph export using Semantica

Clean export functions using Semantica's built-in exporters:
- OWLExporter for OWL format
- RDFExporter for RDF/Turtle format
- GraphMLExporter for GraphML format
"""
from typing import Dict, Any
from pathlib import Path
from maris.utils import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
# EXPORT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def export_to_owl(graph: Any, output_path: str = 'data/exports/maris.owl') -> None:
    """
    Export graph to OWL format using Semantica's OWLExporter
    
    Args:
        graph: Knowledge graph
        output_path: Output file path
    """
    from semantica.export import OWLExporter
    
    logger.info(f"Exporting graph to OWL: {output_path}")
    
    # Ensure directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Use Semantica's OWLExporter
    exporter = OWLExporter()
    exporter.export(graph, output_path)
    
    logger.info(f"✓ Exported to {output_path}")


def export_to_rdf(graph: Any, output_path: str = 'data/exports/maris.ttl') -> None:
    """
    Export graph to RDF Turtle format using Semantica's RDFExporter
    
    Args:
        graph: Knowledge graph
        output_path: Output file path
    """
    from semantica.export import RDFExporter
    
    logger.info(f"Exporting graph to RDF: {output_path}")
    
    # Ensure directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Use Semantica's RDFExporter
    exporter = RDFExporter()
    exporter.export(graph, output_path, format='turtle')
    
    logger.info(f"✓ Exported to {output_path}")


def export_to_graphml(graph: Any, output_path: str = 'data/exports/maris.graphml') -> None:
    """
    Export graph to GraphML format using Semantica's GraphMLExporter
    
    Args:
        graph: Knowledge graph
        output_path: Output file path
    """
    from semantica.export import GraphMLExporter
    
    logger.info(f"Exporting graph to GraphML: {output_path}")
    
    # Ensure directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Use Semantica's GraphMLExporter
    exporter = GraphMLExporter()
    exporter.export(graph, output_path)
    
    logger.info(f"✓ Exported to {output_path}")


def export_tnfd_disclosure(site_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Export TNFD disclosure using Semantica's RDFExporter
    
    Args:
        site_data: Site data for TNFD disclosure
        
    Returns:
        TNFD disclosure in JSON-LD format
    """
    from semantica.export import RDFExporter
    
    logger.info("Exporting TNFD disclosure...")
    
    # Use Semantica's RDFExporter with TNFD context
    exporter = RDFExporter()
    disclosure = exporter.export(site_data, format='json-ld', context='tnfd')
    
    logger.info("✓ TNFD disclosure generated")
    return disclosure


# ═══════════════════════════════════════════════════════════════════
# ONTOLOGY EXPORT
# ═══════════════════════════════════════════════════════════════════

def generate_maris_ontology() -> Any:
    """
    Generate MARIS ontology using Semantica's OntologyGenerator
    
    Returns:
        Generated ontology
    """
    from semantica.ontology import OntologyGenerator, OWLGenerator
    from maris.data import load_entity_schema, load_relationship_schema
    
    logger.info("Generating MARIS ontology...")
    
    # Load schemas
    entity_schema = load_entity_schema()
    rel_schema = load_relationship_schema()
    
    # Use Semantica's OntologyGenerator
    ontology_gen = OntologyGenerator(domain='marine_ecology')
    ontology = ontology_gen.generate(
        classes=entity_schema['entities'],
        properties=rel_schema['relationships']
    )
    
    # Export to OWL using Semantica's OWLGenerator
    output_path = Path("data/ontologies/maris.owl")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    owl_gen = OWLGenerator()
    owl_gen.export(ontology, output_path=str(output_path))
    
    logger.info(f"✓ MARIS ontology generated and exported to {output_path}")
    return ontology
