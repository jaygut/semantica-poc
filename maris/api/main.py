"""MARIS FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from maris.config import get_config
from maris.graph.connection import close_driver

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle handler."""
    config = get_config()
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

    # CORS - allow all origins for POC
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Import and include routers
    from maris.api.routes.query import router as query_router
    from maris.api.routes.graph import router as graph_router
    from maris.api.routes.health import router as health_router

    app.include_router(query_router)
    app.include_router(graph_router)
    app.include_router(health_router)

    return app


app = create_app()
