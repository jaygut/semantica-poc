"""API authentication, rate limiting, and request tracing middleware.

Provides:
- Bearer token authentication via ``MARIS_API_KEY``
- Per-key in-memory sliding-window rate limiting
- ``X-Request-ID`` response header for tracing
- Request logging with hashed client IP
"""

import hashlib
import logging
import re
import threading
import time
import uuid
from collections import defaultdict

from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from maris.config import get_config

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

_AXIOM_ID_RE = re.compile(r"^BA-\d{3}$")
_SITE_NAME_RE = re.compile(r"^[A-Za-z0-9 \-'.]+$")


def validate_question(question: str) -> str:
    """Validate question length (max 500 chars)."""
    if len(question) > 500:
        raise HTTPException(status_code=400, detail="Question exceeds 500 character limit.")
    return question


def validate_site_name(name: str) -> str:
    """Validate site name: alphanumeric, spaces, hyphens, apostrophes, periods."""
    if not _SITE_NAME_RE.match(name):
        raise HTTPException(
            status_code=400,
            detail="Invalid site name. Only letters, numbers, spaces, hyphens, apostrophes, and periods are allowed.",
        )
    return name


def validate_axiom_id(axiom_id: str) -> str:
    """Validate axiom ID matches BA-NNN format."""
    if not _AXIOM_ID_RE.match(axiom_id):
        raise HTTPException(status_code=400, detail="Invalid axiom ID. Expected format: BA-NNN (e.g., BA-001).")
    return axiom_id


# ---------------------------------------------------------------------------
# API key authentication
# ---------------------------------------------------------------------------

def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """Validate the Bearer token against ``MARIS_API_KEY``.

    Raises 401 if the key is missing or invalid.  Skipped entirely when
    ``MARIS_DEMO_MODE=true`` (demo mode allows unauthenticated access).
    """
    cfg = get_config()

    if cfg.demo_mode:
        return "demo"

    if not cfg.api_key:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: MARIS_API_KEY is not set.",
        )

    if credentials is None or credentials.credentials != cfg.api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Provide 'Authorization: Bearer <key>' header.",
        )
    return credentials.credentials


# ---------------------------------------------------------------------------
# Rate limiting (in-memory sliding window)
# ---------------------------------------------------------------------------

_rate_buckets: dict[str, list[float]] = defaultdict(list)
_rate_lock = threading.Lock()

def _check_rate_limit(key: str, max_requests: int, window_seconds: int = 60):
    """Enforce a sliding-window rate limit per key.

    Raises 429 if the caller has exceeded ``max_requests`` within the
    rolling ``window_seconds`` window.
    """
    with _rate_lock:
        now = time.monotonic()
        bucket = _rate_buckets[key]
        # Prune expired entries
        _rate_buckets[key] = [ts for ts in bucket if now - ts < window_seconds]
        bucket = _rate_buckets[key]

        if len(bucket) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s.",
            )
        bucket.append(now)


def rate_limit_query(request: Request, api_key: str = Depends(require_api_key)):
    """Rate limit for /api/query: 30 requests per minute."""
    _check_rate_limit(f"query:{api_key}", max_requests=30)


def rate_limit_default(request: Request, api_key: str = Depends(require_api_key)):
    """Rate limit for non-query endpoints: 60 requests per minute."""
    _check_rate_limit(f"default:{api_key}", max_requests=60)


# ---------------------------------------------------------------------------
# Request-ID and logging middleware
# ---------------------------------------------------------------------------

def _hash_ip(ip: str | None) -> str:
    """Return a one-way hash of the client IP for privacy-safe logging."""
    if not ip:
        return "unknown"
    return hashlib.sha256(ip.encode()).hexdigest()[:12]


async def request_logging_middleware(request: Request, call_next):
    """Add X-Request-ID header and log every request with timing."""
    request_id = str(uuid.uuid4())
    start = time.monotonic()

    response: Response = await call_next(request)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "request_id=%s ip=%s method=%s path=%s status=%d duration_ms=%d",
        request_id,
        _hash_ip(request.client.host if request.client else None),
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response
