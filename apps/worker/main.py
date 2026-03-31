"""Arq worker settings — entrypoint for background job processing.

Run with:
    arq apps.worker.main.WorkerSettings

This module configures:
  - Redis connection for Arq's job queue
  - Registered job functions (ingest, reindex)
  - Startup/shutdown hooks for DB and client lifecycle
  - Retry and timeout policies
"""

from __future__ import annotations

from typing import Any

from arq import cron
from arq.connections import RedisSettings

from core.config import settings
from core.logging import configure_logging, get_logger

log = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup: configure logging, init DB and Qdrant clients."""
    configure_logging()
    log.info("worker.startup", env=settings.env)

    # Lazy imports to avoid circular deps at module level
    from core.db import engine, AsyncSessionLocal
    from core.qdrant_client import get_qdrant_client

    ctx["db_engine"] = engine
    ctx["db_session_factory"] = AsyncSessionLocal
    ctx["qdrant"] = get_qdrant_client()

    log.info("worker.clients_initialized")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown: dispose of DB engine."""
    log.info("worker.shutdown")
    engine = ctx.get("db_engine")
    if engine:
        await engine.dispose()
        log.info("worker.db_engine_disposed")


async def on_job_start(ctx: dict[str, Any]) -> None:
    """Called before each job executes."""
    log.info("job.start", job_id=ctx.get("job_id"))


async def on_job_end(ctx: dict[str, Any]) -> None:
    """Called after each job completes (success or failure)."""
    log.info("job.end", job_id=ctx.get("job_id"))


def _parse_redis_url(url: str) -> RedisSettings:
    """Convert a redis:// URL to Arq's RedisSettings."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        password=parsed.password,
        database=int(parsed.path.lstrip("/") or 0),
    )


class WorkerSettings:
    """Arq worker configuration — this is the entrypoint class."""

    # Job functions are imported lazily to keep this module lightweight
    functions = [
        "apps.worker.jobs.ingest.ingest_document",
        "apps.worker.jobs.reindex.reindex_organization",
    ]

    on_startup = startup
    on_shutdown = shutdown
    on_job_start = on_job_start
    on_job_end = on_job_end

    # Connection
    redis_settings = _parse_redis_url(settings.redis_url)

    # Policies
    max_jobs = 10
    job_timeout = 600  # 10 minutes max per job
    max_tries = 3
    retry_jobs = True
    keep_result = 3600  # keep results for 1 hour
    poll_delay = 0.5  # seconds between queue polls

    # Health check key — allows external monitoring
    health_check_interval = 30
    health_check_key = "omnirag:worker:health"

    # Scheduled jobs (Phase 3: nightly re-embeddings, stale doc cleanup)
    cron_jobs = []
