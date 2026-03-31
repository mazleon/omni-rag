"""Health and readiness endpoints.

GET /v1/health   — liveness probe (fast, no dependency checks)
GET /v1/ready    — readiness probe (checks Postgres, Qdrant, Redis)
GET /v1/metrics  — Prometheus metrics (stub; wire up prometheus-fastapi-instrumentator in Phase 3)
"""

from __future__ import annotations

import time
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db import engine
from core.logging import get_logger
from core.qdrant_client import health_check as qdrant_health

log = get_logger(__name__)
router = APIRouter()


async def _check_postgres() -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "latency_ms": round((time.perf_counter() - t0) * 1000)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def _check_qdrant() -> dict[str, Any]:
    t0 = time.perf_counter()
    ok = await qdrant_health()
    return {
        "status": "ok" if ok else "error",
        "latency_ms": round((time.perf_counter() - t0) * 1000),
    }


async def _check_redis() -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await client.ping()
        await client.aclose()
        return {"status": "ok", "latency_ms": round((time.perf_counter() - t0) * 1000)}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.get("/health", tags=["ops"])
async def liveness() -> dict[str, str]:
    """Liveness probe — always returns 200 if the process is alive."""
    return {"status": "ok", "version": settings.app_version}


@router.get("/ready", tags=["ops"])
async def readiness() -> dict[str, Any]:
    """
    Readiness probe — checks all downstream dependencies.
    Returns 200 if all healthy, 503 if any dependency is unhealthy.
    Used by Kubernetes / Fly.io to gate traffic.
    """
    postgres, qdrant, redis_dep = await _check_postgres(), await _check_qdrant(), await _check_redis()

    all_ok = all(
        dep["status"] == "ok" for dep in [postgres, qdrant, redis_dep]
    )

    payload: dict[str, Any] = {
        "status": "ok" if all_ok else "degraded",
        "version": settings.app_version,
        "dependencies": {
            "postgres": postgres,
            "qdrant": qdrant,
            "redis": redis_dep,
        },
    }

    if not all_ok:
        from fastapi import Response
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=payload)

    return payload


@router.get("/metrics", tags=["ops"])
async def metrics() -> dict[str, str]:
    """Prometheus metrics — stub until prometheus-fastapi-instrumentator is wired up (Phase 3)."""
    return {"info": "Prometheus metrics endpoint — Phase 3 deliverable"}
