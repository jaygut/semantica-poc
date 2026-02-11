#!/usr/bin/env python3
"""
Populate Neo4j with MARIS curated data.

Usage:
    python scripts/populate_neo4j.py [--validate]

Idempotent - safe to run multiple times.
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from maris.config import get_config
from maris.graph.connection import get_driver, close_driver
from maris.graph.schema import ensure_schema
from maris.graph.population import populate_graph
from maris.graph.validation import validate_graph


def main():
    parser = argparse.ArgumentParser(description="Populate MARIS Neo4j graph")
    parser.add_argument("--validate", action="store_true", help="Run validation after population")
    parser.add_argument("--validate-only", action="store_true", help="Only run validation")
    args = parser.parse_args()

    cfg = get_config()
    print(f"Neo4j: {cfg.neo4j_uri} (database: {cfg.neo4j_database})")
    print()

    try:
        if not args.validate_only:
            # 1. Schema
            print("Step 1: Applying schema (constraints + indexes)...")
            ensure_schema()
            print()

            # 2. Population
            print("Step 2: Populating graph...")
            populate_graph()
            print()

        if args.validate or args.validate_only:
            # 3. Validation
            print("Step 3: Validating graph...")
            result = validate_graph(verbose=True)
            sys.exit(0 if result["all_pass"] else 1)

    except Exception as e:
        print(f"\nERROR: {e}")
        print("Make sure Neo4j is running and accessible.")
        sys.exit(1)
    finally:
        close_driver()


if __name__ == "__main__":
    main()
