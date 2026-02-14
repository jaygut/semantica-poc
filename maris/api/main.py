"""MARIS FastAPI application."""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from maris.api.auth import request_logging_middleware
from maris.config import get_config
from maris.graph.connection import close_driver

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle handler."""
    config = get_config()

    if not config.demo_mode and not config.api_key:
        logger.critical("MARIS_API_KEY is not set. Set it in .env or export it. Use MARIS_DEMO_MODE=true to skip.")
        sys.exit(1)

    if not config.neo4j_password:
        logger.critical("MARIS_NEO4J_PASSWORD is not set. Set it in .env or export it.")
        sys.exit(1)

    logger.info("MARIS API starting - Neo4j=%s, LLM=%s", config.neo4j_uri, config.llm_provider)
    yield
    close_driver()
    logger.info("MARIS API shutdown - Neo4j driver closed")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="MARIS API",
        description="Marine Asset Risk Intelligence System - graph-grounded natural capital query interface",
        version="2.0.0",
        lifespan=lifespan,
    )

    config = get_config()

    # CORS - restricted to configured origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Request logging and X-Request-ID middleware
    app.add_middleware(BaseHTTPMiddleware, dispatch=request_logging_middleware)

    # Import and include routers
    from maris.api.routes.query import router as query_router
    from maris.api.routes.graph import router as graph_router
    from maris.api.routes.health import router as health_router
    from maris.api.routes.provenance import router as provenance_router
    from maris.api.routes.disclosure import router as disclosure_router

    app.include_router(query_router)
    app.include_router(graph_router)
    app.include_router(health_router)
    app.include_router(provenance_router)
    app.include_router(disclosure_router)

    return app


app = create_app()
