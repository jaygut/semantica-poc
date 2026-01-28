"""
Data loading: schemas + document data

Consolidates schema loading and data loading into one simple module
"""
from pathlib import Path
from typing import Dict, Any, List
from maris.utils import read_json, get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
# SCHEMA LOADING
# ═══════════════════════════════════════════════════════════════════

def load_entity_schema() -> Dict[str, Any]:
    """Load entity schema from schemas/entity_schema.json"""
    path = Path("schemas/entity_schema.json")
    logger.info(f"Loading entity schema from {path}")
    return read_json(path)


def load_relationship_schema() -> Dict[str, Any]:
    """Load relationship schema from schemas/relationship_schema.json"""
    path = Path("schemas/relationship_schema.json")
    logger.info(f"Loading relationship schema from {path}")
    return read_json(path)


def load_bridge_axioms() -> Dict[str, Any]:
    """Load bridge axioms from schemas/bridge_axiom_templates.json"""
    path = Path("schemas/bridge_axiom_templates.json")
    logger.info(f"Loading bridge axioms from {path}")
    return read_json(path)


def load_registry_schema() -> Dict[str, Any]:
    """Load registry schema from schemas/registry_schema.json"""
    path = Path("schemas/registry_schema.json")
    logger.info(f"Loading registry schema from {path}")
    return read_json(path)


def get_entity_types() -> List[str]:
    """Get list of all entity types"""
    schema = load_entity_schema()
    return list(schema.get("entities", {}).keys())


def get_relationship_types() -> List[str]:
    """Get list of all relationship types"""
    schema = load_relationship_schema()
    return list(schema.get("relationships", {}).keys())


def get_axiom_ids() -> List[str]:
    """Get list of all bridge axiom IDs"""
    axioms = load_bridge_axioms()
    return [axiom["axiom_id"] for axiom in axioms.get("axioms", [])]


# ═══════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════

def load_document_manifest() -> Dict[str, Any]:
    """Load document manifest (195 papers)"""
    path = Path("data/document_manifest.json")
    logger.info(f"Loading document manifest from {path}")
    return read_json(path)


def load_sample_extractions() -> Dict[str, Dict[str, Any]]:
    """Load all sample extractions from data/sample_extractions/"""
    extractions = {}
    extraction_dir = Path("data/sample_extractions")
    
    if not extraction_dir.exists():
        logger.warning(f"Sample extractions directory not found: {extraction_dir}")
        return extractions
    
    for file in extraction_dir.glob("*.json"):
        extraction_id = file.stem
        logger.info(f"Loading extraction: {extraction_id}")
        extractions[extraction_id] = read_json(file)
    
    logger.info(f"Loaded {len(extractions)} sample extractions")
    return extractions


def load_cabo_pulmo() -> Dict[str, Any]:
    """Load Cabo Pulmo case study (AAA validation target)"""
    path = Path("examples/cabo_pulmo_case_study.json")
    logger.info(f"Loading Cabo Pulmo case study from {path}")
    return read_json(path)


def load_semantica_export() -> Dict[str, Any]:
    """Load Semantica export bundle"""
    export_dir = Path("data/semantica_export")
    
    return {
        "entities": read_json(export_dir / "entities.jsonld"),
        "relationships": read_json(export_dir / "relationships.json"),
        "bridge_axioms": read_json(export_dir / "bridge_axioms.json"),
        "document_corpus": read_json(export_dir / "document_corpus.json")
    }
