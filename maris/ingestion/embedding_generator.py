"""Document embedding generation for vector search.

Stub implementation: returns zero vectors. Replace with sentence-transformers
(e.g. all-MiniLM-L6-v2) for production use.
"""

import logging

from maris.graph.connection import run_write, get_driver
from maris.config import get_config

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384


def generate_embedding(text: str) -> list[float]:
    """Generate a 384-dimensional embedding vector for the given text.

    Stub implementation returns zeros. To enable real embeddings, install
    sentence-transformers and replace this function body:

        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        return model.encode(text).tolist()
    """
    return [0.0] * EMBEDDING_DIM


def update_document_embeddings(batch_size: int = 50) -> int:
    """Batch-update Document nodes with embedding vectors.

    Finds all Document nodes missing an 'embedding' property and generates
    embeddings from their title + abstract text.

    Returns:
        Number of documents updated.
    """
    cfg = get_config()
    driver = get_driver()

    # Fetch documents without embeddings
    with driver.session(database=cfg.neo4j_database) as session:
        result = session.run(
            """
            MATCH (d:Document)
            WHERE d.embedding IS NULL
            RETURN d.doi AS doi, d.title AS title, d.abstract AS abstract
            LIMIT $limit
            """,
            {"limit": batch_size},
        )
        docs = [record.data() for record in result]

    if not docs:
        logger.info("All documents already have embeddings.")
        return 0

    count = 0
    for doc in docs:
        doi = doc.get("doi", "")
        if not doi:
            continue

        text = f"{doc.get('title', '')} {doc.get('abstract', '')}".strip()
        if not text:
            continue

        embedding = generate_embedding(text)

        run_write(
            """
            MATCH (d:Document {doi: $doi})
            SET d.embedding = $embedding
            """,
            {"doi": doi, "embedding": embedding},
        )
        count += 1

    logger.info("Updated embeddings for %d documents.", count)
    return count
