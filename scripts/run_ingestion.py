#!/usr/bin/env python3
"""CLI script to run the MARIS ingestion pipeline.

Usage:
    python scripts/run_ingestion.py --paper data/papers/smith_2020.pdf
    python scripts/run_ingestion.py --batch --limit 10
    python scripts/run_ingestion.py --batch --dry-run
"""

import argparse
import logging
import sys
import time
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from maris.config import get_config
from maris.ingestion.pdf_extractor import extract_text, extract_doi, chunk_pages
from maris.ingestion.llm_extractor import LLMExtractor
from maris.ingestion.graph_merger import GraphMerger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("maris.ingestion")


def process_paper(
    pdf_path: Path,
    extractor: LLMExtractor,
    merger: GraphMerger | None,
    config,
) -> dict:
    """Process a single PDF through the ingestion pipeline.

    Returns:
        Summary dict with entity/relationship counts.
    """
    logger.info("Processing: %s", pdf_path.name)
    t0 = time.time()

    # 1. Extract text
    pages = extract_text(pdf_path)
    if not pages:
        logger.warning("  No text extracted from %s", pdf_path.name)
        return {"file": pdf_path.name, "status": "empty", "entities": 0, "relationships": 0}

    # 2. Extract DOI from first page
    doi = extract_doi(pages)
    paper_meta = {
        "title": pdf_path.stem.replace("_", " ").title(),
        "doi": doi or "",
    }
    logger.info("  Pages: %d, DOI: %s", len(pages), doi or "not found")

    # 3. Chunk
    chunks = chunk_pages(
        pages,
        chunk_size=config.extraction_chunk_size,
        overlap=config.extraction_chunk_overlap,
    )
    logger.info("  Chunks: %d", len(chunks))

    # 4. Extract entities and relationships from each chunk
    all_entities = []
    all_relationships = []

    for chunk in chunks:
        entities = extractor.extract_entities(chunk, paper_meta)
        all_entities.extend(entities)

        relationships = extractor.extract_relationships(entities, chunk, paper_meta)
        all_relationships.extend(relationships)

    logger.info(
        "  Extracted: %d entities, %d relationships",
        len(all_entities),
        len(all_relationships),
    )

    # 5. Merge into graph (unless dry-run)
    if merger is not None:
        entity_counts = merger.merge_entities(all_entities)
        rel_count = merger.merge_relationships(all_relationships)
        logger.info("  Merged: %s entities, %d relationships", entity_counts, rel_count)
    else:
        entity_counts = {}
        rel_count = 0
        logger.info("  [DRY RUN] Skipping graph merge.")

    elapsed = time.time() - t0
    logger.info("  Done in %.1fs", elapsed)

    return {
        "file": pdf_path.name,
        "status": "ok",
        "pages": len(pages),
        "chunks": len(chunks),
        "doi": doi,
        "entities": len(all_entities),
        "relationships": len(all_relationships),
        "merged_entities": sum(entity_counts.values()) if entity_counts else 0,
        "merged_relationships": rel_count,
        "elapsed_s": round(elapsed, 1),
    }


def main():
    parser = argparse.ArgumentParser(description="MARIS Ingestion Pipeline")
    parser.add_argument("--paper", type=str, help="Path to a single PDF to process")
    parser.add_argument("--batch", action="store_true", help="Process all PDFs in data/papers/")
    parser.add_argument("--limit", type=int, default=0, help="Max number of papers to process (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Extract without merging into Neo4j")
    args = parser.parse_args()

    if not args.paper and not args.batch:
        parser.error("Specify --paper <path> or --batch")

    config = get_config()
    extractor = LLMExtractor(config)
    merger = None if args.dry_run else GraphMerger(config)

    # Collect PDF paths
    pdf_paths: list[Path] = []
    if args.paper:
        p = Path(args.paper)
        if not p.exists():
            logger.error("File not found: %s", p)
            sys.exit(1)
        pdf_paths.append(p)
    elif args.batch:
        papers_dir = config.papers_dir
        if not papers_dir.exists():
            logger.error("Papers directory not found: %s", papers_dir)
            sys.exit(1)
        pdf_paths = sorted(papers_dir.glob("*.pdf"))
        if not pdf_paths:
            logger.warning("No PDFs found in %s", papers_dir)
            sys.exit(0)

    if args.limit > 0:
        pdf_paths = pdf_paths[: args.limit]

    logger.info("=" * 60)
    logger.info("MARIS Ingestion Pipeline")
    logger.info("Papers to process: %d", len(pdf_paths))
    logger.info("Dry run: %s", args.dry_run)
    logger.info("=" * 60)

    results = []
    errors = 0
    for i, pdf_path in enumerate(pdf_paths, 1):
        logger.info("[%d/%d] %s", i, len(pdf_paths), pdf_path.name)
        try:
            result = process_paper(pdf_path, extractor, merger, config)
            results.append(result)
        except Exception as e:
            logger.error("FAILED: %s - %s", pdf_path.name, e)
            results.append({"file": pdf_path.name, "status": "error", "error": str(e)})
            errors += 1

    # Summary
    logger.info("=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info("-" * 60)
    total_entities = sum(r.get("entities", 0) for r in results)
    total_rels = sum(r.get("relationships", 0) for r in results)
    total_merged_ent = sum(r.get("merged_entities", 0) for r in results)
    total_merged_rel = sum(r.get("merged_relationships", 0) for r in results)
    ok = sum(1 for r in results if r.get("status") == "ok")

    logger.info("  Papers processed: %d/%d (errors: %d)", ok, len(pdf_paths), errors)
    logger.info("  Total extracted: %d entities, %d relationships", total_entities, total_rels)
    if not args.dry_run:
        logger.info("  Total merged: %d entities, %d relationships", total_merged_ent, total_merged_rel)
    logger.info("=" * 60)

    if errors > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
