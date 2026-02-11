"""Neo4j driver management."""

from neo4j import GraphDatabase
from maris.config import get_config

_driver = None


def get_driver():
    """Return a singleton Neo4j driver instance."""
    global _driver
    if _driver is None:
        cfg = get_config()
        _driver = GraphDatabase.driver(
            cfg.neo4j_uri,
            auth=(cfg.neo4j_user, cfg.neo4j_password),
        )
    return _driver


def close_driver():
    """Close the Neo4j driver."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def run_query(cypher: str, parameters: dict | None = None, *, write: bool = False):
    """Execute a Cypher query and return list of record dicts."""
    driver = get_driver()
    cfg = get_config()
    with driver.session(database=cfg.neo4j_database) as session:
        if write:
            result = session.run(cypher, parameters or {})
        else:
            result = session.run(cypher, parameters or {})
        return [record.data() for record in result]


def run_write(cypher: str, parameters: dict | None = None):
    """Execute a write transaction."""
    driver = get_driver()
    cfg = get_config()
    with driver.session(database=cfg.neo4j_database) as session:
        session.execute_write(lambda tx: tx.run(cypher, parameters or {}))
