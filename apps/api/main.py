"""OmniRAG API — FastAPI application factory.

Entrypoint:
    uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

The app is assembled via ``create_app()`` so tests can build an isolated
instance with overridden dependencies.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.logging import get_logger, configure_logging

log = get_logger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle hook.

    - Startup: configure logging, verify external connections.
    - Shutdown: close DB engine, Qdrant client, Redis pool.
    """
    configure_logging()
    log.info(
        "app.startup",
        env=settings.env,
        version=settings.app_version,
        debug=settings.debug,
    )

    # Eagerly import to trigger engine creation and run pool_pre_ping
    from core.db import engine  # noqa: F401

    yield

    # ── Teardown ───────────────────────────────────────────────────────────
    log.info("app.shutdown")
    from core.db import engine as _engine

    await _engine.dispose()
    log.info("db.engine.disposed")


# ── Factory ────────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Enterprise Multimodal RAG Platform",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────────────
    _origins = (
        ["*"]
        if not settings.is_production
        else [
            "https://omnirag.app",
            "https://www.omnirag.app",
        ]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Middleware ──────────────────────────────────────────────────────────
    from apps.api.middleware import RequestIDMiddleware, AccessLogMiddleware

    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # ── Routers ────────────────────────────────────────────────────────────
    from apps.api.routers.health import router as health_router
    from apps.api.routers.documents import router as documents_router
    from apps.api.routers.query import router as query_router

    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(query_router)

    return app


# Module-level app instance for uvicorn
app = create_app()
