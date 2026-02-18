#!/usr/bin/env python3
"""
Reload all case studies to apply schema updates (Ecological Processes, Financial Mechanisms).
Currently scans `examples/` for `*_case_study.json`.
"""

import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from maris.settings import settings
from maris.services.ingestion.case_study_loader import CaseStudyLoader
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("Initializing Neo4j connection...")
    try:
        driver = GraphDatabase.driver(
            settings.neo4j_uri, 
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        driver.verify_connectivity()
        logger.info("Connected to Neo4j.")
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {e}")
        return

    session = driver.session()
    loader = CaseStudyLoader(session)
    
    # Locate case study files
    examples_dir = project_root / "examples"
    case_studies = list(examples_dir.glob("*_case_study.json"))
    
    if not case_studies:
        logger.warning(f"No case study files found in {examples_dir}")
        return

    logger.info(f"Found {len(case_studies)} case studies to reload.")

    # Clear existing data? Or MERGE handles updates? 
    # Current loader uses MERGE, so updates are safe. 
    # However, to be clean, we might want to detach delete specific nodes if schema changed drastically.
    # For now, we are ADDING new nodes, so MERGE is fine.

    for cs_path in case_studies:
        logger.info(f"Loading {cs_path.name}...")
        try:
            loader.load_site(cs_path)
            logger.info(f"Successfully loaded {cs_path.name}")
        except Exception as e:
            logger.error(f"Failed to load {cs_path.name}: {e}")

    session.close()
    driver.close()
    logger.info("All case studies reloaded.")

if __name__ == "__main__":
    main()
