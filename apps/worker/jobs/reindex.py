"""Arq job: reindex_organization

Triggered manually or on schedule to re-embed all documents for an org
(e.g., after a Cohere model upgrade).

Phase 1: skeleton that enqueues individual ingest jobs for all indexed docs.
Phase 2: support incremental reindex (only changed docs).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from core.db import Document
from core.logging import get_logger

log = get_logger(__name__)


async def reindex_organization(
    ctx: dict[str, Any],
    *,
    org_id: str,
    force: bool = False,
) -> dict[str, Any]:
    """
    Arq job handler — re-enqueue ingestion for all indexed documents in an org.

    Args:
        ctx: Arq worker context.
        org_id: UUID string of the Organization to reindex.
        force: If True, reindex even documents that are already indexed.

    Returns:
        dict with job summary (enqueued_count, skipped_count).
    """
    from arq import ArqRedis

    org_uuid = uuid.UUID(org_id)
    session_factory = ctx["db_session_factory"]

    log.info("reindex.start", org_id=org_id, force=force, job_id=ctx.get("job_id"))

    async with session_factory() as db:
        stmt = select(Document).where(Document.org_id == org_uuid)
        if not force:
            stmt = stmt.where(Document.status != "error")

        result = await db.execute(stmt)
        documents = result.scalars().all()

    if not documents:
        log.info("reindex.no_documents", org_id=org_id)
        return {"status": "complete", "enqueued_count": 0, "skipped_count": 0}

    # Get the Arq Redis pool from context to enqueue child jobs
    # Phase 2 TODO: replace raw context access with typed dependency
    redis: ArqRedis | None = ctx.get("arq_redis")

    enqueued = 0
    skipped = 0

    for doc in documents:
        if doc.status == "indexed" and not force:
            skipped += 1
            continue

        if redis:
            await redis.enqueue_job(
                "ingest_document",
                document_id=str(doc.id),
            )
        enqueued += 1

    log.info(
        "reindex.complete",
        org_id=org_id,
        enqueued_count=enqueued,
        skipped_count=skipped,
    )

    return {
        "status": "complete",
        "org_id": org_id,
        "enqueued_count": enqueued,
        "skipped_count": skipped,
    }
