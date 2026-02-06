"""FastAPI application entry point.

Provides REST API endpoints for:
- /api/v1/query: Natural language queries against the hypergraph
- /api/v1/entities: Entity CRUD operations
- /api/v1/hyperedges: Hyperedge CRUD operations
- /api/v1/connectors: Connector management

From ARCHITECTURE_PLAN.md Section 5.1.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import connectors, entities, hyperedges, query
from src.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifecycle: connect to TypeDB on startup, disconnect on shutdown."""
    settings = get_settings()
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Hypergraph Context Graph API",
        description=(
            "Enterprise decision context graph using TypeDB hypergraphs. "
            "Supports n-ary relations, s-path traversal, and multi-agent reasoning."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(query.router, prefix="/api/v1", tags=["query"])
    app.include_router(entities.router, prefix="/api/v1", tags=["entities"])
    app.include_router(hyperedges.router, prefix="/api/v1", tags=["hyperedges"])
    app.include_router(connectors.router, prefix="/api/v1", tags=["connectors"])

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy", "version": "0.1.0"}

    return app


app = create_app()


def run() -> None:
    """Run the API server (used by hcg-api CLI entry point)."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.debug,
    )
