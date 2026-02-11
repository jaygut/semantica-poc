#!/usr/bin/env python3
"""
Validate MARIS Neo4j graph integrity.

Usage:
    python scripts/validate_graph.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from maris.graph.connection import close_driver
from maris.graph.validation import validate_graph


def main():
    try:
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
