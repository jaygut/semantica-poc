"""Neo4j driver management.

Thread Safety
-------------
The singleton driver uses double-checked locking with ``threading.Lock`` so
concurrent FastAPI workers never race on initialization. ``get_driver()``
verifies connectivity before returning and retries transient failures
automatically via the ``@retry`` decorator.
"""

import functools
import logging
import threading
import time

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, TransientError

from maris.config import get_config

logger = logging.getLogger(__name__)

_driver = None
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Retry decorator (T2-13)
# ---------------------------------------------------------------------------

def retry(max_attempts: int = 3, backoff_seconds: tuple[float, ...] = (1.0, 2.0, 4.0),
          retryable: tuple[type[Exception], ...] = (TransientError, ServiceUnavailable)):
    """Retry decorator with exponential backoff for Neo4j operations.

    Parameters
    ----------
    max_attempts : int
        Total number of attempts (1 = no retry).
    backoff_seconds : tuple[float, ...]
        Sleep durations between attempts.
    retryable : tuple
        Exception types that trigger a retry.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except retryable as exc:
                    last_exc = exc
                    if attempt < max_attempts:
                        wait = backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)]
                        logger.warning(
                            "Retry %d/%d for %s after %s: sleeping %.1fs",
                            attempt, max_attempts, fn.__name__,
                            type(exc).__name__, wait,
                        )
                        time.sleep(wait)
                    else:
                        logger.error(
                            "All %d attempts failed for %s: %s",
                            max_attempts, fn.__name__, exc,
                        )
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Driver lifecycle
# ---------------------------------------------------------------------------

def get_driver():
    """Return a singleton Neo4j driver instance (thread-safe, health-checked).

    Uses double-checked locking so only the first caller performs
    initialization while subsequent callers return immediately.
    """
    global _driver
    if _driver is None:
        with _lock:
            if _driver is None:
                cfg = get_config()
                _driver = GraphDatabase.driver(
                    cfg.neo4j_uri,
                    auth=(cfg.neo4j_user, cfg.neo4j_password),
                )
                _driver.verify_connectivity()
                logger.info("Neo4j driver initialized: %s", cfg.neo4j_uri)
    return _driver


def close_driver():
    """Close the Neo4j driver and release the singleton."""
    global _driver
    with _lock:
        if _driver is not None:
            _driver.close()
            _driver = None
            logger.info("Neo4j driver closed")


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

_QUERY_TIMEOUT = 30  # seconds

@retry(max_attempts=3, backoff_seconds=(1.0, 2.0, 4.0))
def run_query(cypher: str, parameters: dict | None = None, *, write: bool = False):
    """Execute a Cypher query and return list of record dicts.

    Retries up to 3 times on TransientError/ServiceUnavailable with
    exponential backoff (1s, 2s, 4s). Each query has a 30-second timeout.
    """
    driver = get_driver()
    cfg = get_config()
    with driver.session(database=cfg.neo4j_database) as session:
        result = session.run(cypher, parameters or {}, timeout=_QUERY_TIMEOUT)
        return [record.data() for record in result]


@retry(max_attempts=3, backoff_seconds=(1.0, 2.0, 4.0))
def run_write(cypher: str, parameters: dict | None = None):
    """Execute a write transaction with retry on transient failures."""
    driver = get_driver()
    cfg = get_config()
    with driver.session(database=cfg.neo4j_database) as session:
        session.execute_write(lambda tx: tx.run(cypher, parameters or {}))
