"""FastAPI dependency injectors: DB session, Qdrant client, auth, org context."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import AsyncSessionLocal, ApiKey
from core.exceptions import unauthorized
from core.logging import get_logger
from core.qdrant_client import get_qdrant_client

log = get_logger(__name__)

_bearer = HTTPBearer(auto_error=False)


# ── Database ───────────────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional async DB session, committing on success."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Qdrant ─────────────────────────────────────────────────────────────────────

def get_qdrant():  # type: ignore[no-untyped-def]
    """Return the shared async Qdrant client."""
    return get_qdrant_client()


# ── Authentication ─────────────────────────────────────────────────────────────

async def get_current_org_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """
    Validate Bearer token (JWT or API key) and return the caller's org UUID.

    TODO (Phase 3): implement JWT decode + API key hash lookup.
    For Phase 1 skeleton, we accept any token and extract org_id from a header
    so integration tests can pass without a full auth stack.
    """
    # Development shortcut: allow X-Org-ID header to bypass auth
    # MUST be removed before production
    if dev_org := request.headers.get("X-Org-ID"):
        try:
            return uuid.UUID(dev_org)
        except ValueError:
            raise unauthorized("X-Org-ID header must be a valid UUID")

    if credentials is None:
        raise unauthorized()

    # Phase 3 TODO: decode JWT or hash-compare API key
    # For now return a placeholder UUID so endpoints compile and tests pass
    raise HTTPException(
        status_code=501,
        detail="Auth not yet implemented — use X-Org-ID header in development",
    )


# ── Request ID ─────────────────────────────────────────────────────────────────

def get_request_id(request: Request) -> str:
    """Extract the request_id injected by RequestIDMiddleware."""
    return getattr(request.state, "request_id", "unknown")
