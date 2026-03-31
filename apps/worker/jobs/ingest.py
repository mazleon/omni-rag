"""Arq job: ingest_document

Enqueued by POST /v1/documents/{id}/process.
Full pipeline:
  1. Download file bytes from Supabase Storage
  2. Parse with Docling (layout-aware) + Tesseract OCR fallback
  3. Semantic chunking (layout → coherence → 15% overlap)
  4. Cohere embed-v4 (batched, async, retry with backoff)
  5. Qdrant upsert (idempotency key = content SHA-256)
  6. Postgres chunk records insert
  7. Update document status → indexed | error

Phase 1: skeleton with status lifecycle and structured logging.
Phase 2: wire up real parser, chunker, embedder, and vector store.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update

from core.db import Document
from core.logging import get_logger

log = get_logger(__name__)


async def ingest_document(ctx: dict[str, Any], *, document_id: str) -> dict[str, Any]:
    """
    Arq job handler — idempotent document ingestion pipeline.

    Args:
        ctx: Arq worker context (holds db_session_factory, qdrant, etc.)
        document_id: UUID string of the Document row to ingest.

    Returns:
        dict with job summary (chunk_count, latency_ms, etc.)
    """
    import time

    start = time.perf_counter()
    doc_uuid = uuid.UUID(document_id)
    session_factory = ctx["db_session_factory"]

    log.info("ingest.start", document_id=document_id, job_id=ctx.get("job_id"))

    async with session_factory() as db:
        # ── Fetch document ─────────────────────────────────────────────────
        result = await db.execute(select(Document).where(Document.id == doc_uuid))
        doc = result.scalar_one_or_none()

        if doc is None:
            log.error("ingest.document_not_found", document_id=document_id)
            return {"status": "error", "reason": "document_not_found"}

        if doc.status == "indexed":
            log.info("ingest.already_indexed", document_id=document_id)
            return {"status": "skipped", "reason": "already_indexed"}

        # ── Mark as processing ─────────────────────────────────────────────
        await db.execute(
            update(Document)
            .where(Document.id == doc_uuid)
            .values(status="processing")
        )
        await db.commit()

        try:
            # ── Phase 2 TODOs — each step will be a real service call ──────

            # 1. Download from Supabase Storage
            #    raw_bytes = await storage_service.download(doc.source_uri)

            # 2. Parse document
            #    from services.ingestion.parser import parse_document
            #    parsed = await parse_document(raw_bytes, doc.doc_type)

            # 3. Chunk
            #    from services.ingestion.chunker import chunk_document
            #    chunks = await chunk_document(parsed)

            # 4. Embed
            #    from services.ingestion.embedder import embed_chunks
            #    embedded = await embed_chunks(chunks)

            # 5. Upsert to Qdrant
            #    from services.retrieval.dense import upsert_chunks
            #    await upsert_chunks(embedded, org_slug=doc.organization.slug)

            # 6. Insert chunk metadata into Postgres
            #    (see services/ingestion/chunker.py for Chunk model writes)

            chunk_count = 0  # Phase 1 stub

            # ── Mark as indexed ────────────────────────────────────────────
            await db.execute(
                update(Document)
                .where(Document.id == doc_uuid)
                .values(status="indexed")
            )
            await db.commit()

            elapsed_ms = int((time.perf_counter() - start) * 1000)
            log.info(
                "ingest.complete",
                document_id=document_id,
                chunk_count=chunk_count,
                latency_ms=elapsed_ms,
            )
            return {
                "status": "indexed",
                "document_id": document_id,
                "chunk_count": chunk_count,
                "latency_ms": elapsed_ms,
            }

        except Exception as exc:  # noqa: BLE001
            log.exception("ingest.failed", document_id=document_id, error=str(exc))

            await db.execute(
                update(Document)
                .where(Document.id == doc_uuid)
                .values(status="error", error_message=str(exc)[:2048])
            )
            await db.commit()

            raise  # Arq will retry up to max_tries
