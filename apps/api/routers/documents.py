"""Document management endpoints.

POST   /v1/documents/upload       — initiate upload, get presigned URL
POST   /v1/documents/{id}/process — enqueue ingestion job
GET    /v1/documents              — list documents (paginated, filtered)
GET    /v1/documents/{id}         — get document status + metadata
DELETE /v1/documents/{id}         — soft-delete + schedule vector pruning
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_org_id, get_db, get_request_id
from core.db import Document
from core.exceptions import conflict, not_found
from core.logging import get_logger
from core.schemas.documents import (
    DocStatus,
    DocType,
    DocumentListResponse,
    DocumentSchema,
    DocumentStatusResponse,
    DocumentUploadRequest,
    DocumentUploadResponse,
)

log = get_logger(__name__)
router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate document upload",
)
async def upload_document(
    body: DocumentUploadRequest,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_current_org_id),
    request_id: str = Depends(get_request_id),
) -> DocumentUploadResponse:
    """
    Returns a presigned Supabase Storage URL for the client to upload the file directly.
    Does NOT start ingestion — call POST /{id}/process after upload completes.

    TODO (Phase 1): wire up Supabase Storage presigned URL generation.
    """
    from datetime import datetime, timedelta

    # Generate deterministic storage path: org/doc_type/uuid.ext
    doc_id = uuid.uuid4()
    ext = body.filename.rsplit(".", 1)[-1].lower()
    storage_path = f"{org_id}/{body.doc_type}/{doc_id}.{ext}"

    # Placeholder content_hash — will be computed from actual file bytes after upload
    placeholder_hash = hashlib.sha256(f"{doc_id}{storage_path}".encode()).hexdigest()

    doc = Document(
        id=doc_id,
        org_id=org_id,
        title=body.title or body.filename,
        source_uri=storage_path,
        content_hash=placeholder_hash,
        doc_type=body.doc_type,
        status="pending",
        metadata_=body.metadata,
    )
    db.add(doc)
    await db.flush()

    log.info(
        "document.upload.initiated",
        document_id=str(doc_id),
        org_id=str(org_id),
        doc_type=body.doc_type,
        request_id=request_id,
    )

    # TODO (Phase 1): call services.storage.get_presigned_upload_url(storage_path)
    presigned_url = f"https://placeholder.supabase.co/storage/v1/object/{storage_path}"

    return DocumentUploadResponse(
        request_id=request_id,
        document_id=doc_id,
        presigned_url=presigned_url,
        storage_path=storage_path,
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )


@router.post(
    "/{document_id}/process",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue ingestion job for an uploaded document",
)
async def process_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_current_org_id),
    request_id: str = Depends(get_request_id),
) -> dict[str, Any]:
    """
    Enqueues an Arq job to parse → chunk → embed → upsert the document.
    Returns immediately; poll GET /{id} for status.

    TODO (Phase 1): enqueue via arq.create_pool().enqueue_job("ingest_document", ...)
    """
    doc = await _get_doc_or_404(db, document_id, org_id)

    if doc.status == "indexed":
        return {
            "message": "Document already indexed",
            "document_id": str(document_id),
            "status": "indexed",
        }

    doc.status = "processing"

    log.info(
        "document.process.enqueued",
        document_id=str(document_id),
        org_id=str(org_id),
        request_id=request_id,
    )

    # TODO (Phase 1): await redis_pool.enqueue_job("ingest_document", str(document_id), str(org_id))

    return {
        "message": "Ingestion job enqueued",
        "document_id": str(document_id),
        "status": "processing",
        "request_id": request_id,
    }


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List documents",
)
async def list_documents(
    status_filter: DocStatus | None = Query(default=None, alias="status"),
    doc_type: DocType | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_current_org_id),
    request_id: str = Depends(get_request_id),
) -> DocumentListResponse:
    """List documents for the caller's org with optional status/type filters."""
    q = select(Document).where(Document.org_id == org_id)

    if status_filter:
        q = q.where(Document.status == status_filter)
    if doc_type:
        q = q.where(Document.doc_type == doc_type)

    count_q = select(func.count()).select_from(q.subquery())
    total: int = (await db.execute(count_q)).scalar_one()

    q = q.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    docs = (await db.execute(q)).scalars().all()

    return DocumentListResponse(
        request_id=request_id,
        items=[DocumentSchema.model_validate(d) for d in docs],
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentStatusResponse,
    summary="Get document status",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_current_org_id),
    request_id: str = Depends(get_request_id),
) -> DocumentStatusResponse:
    doc = await _get_doc_or_404(db, document_id, org_id)
    chunk_count_result = await db.execute(
        select(func.count()).where(  # type: ignore[arg-type]
            __import__("core.db", fromlist=["Chunk"]).Chunk.document_id == document_id
        )
    )
    return DocumentStatusResponse(
        request_id=request_id,
        document_id=doc.id,
        status=doc.status,  # type: ignore[arg-type]
        error_message=doc.error_message,
        chunk_count=chunk_count_result.scalar_one(),
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a document",
)
async def delete_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    org_id: uuid.UUID = Depends(get_current_org_id),
    request_id: str = Depends(get_request_id),
) -> None:
    """
    Marks document as deleted in Postgres and schedules a background job
    to prune its vectors from Qdrant.

    TODO (Phase 1): enqueue reindex.prune_document_vectors job via Arq.
    """
    doc = await _get_doc_or_404(db, document_id, org_id)
    doc.status = "deleted"  # type: ignore[assignment]

    log.info(
        "document.deleted",
        document_id=str(document_id),
        org_id=str(org_id),
        request_id=request_id,
    )
    # TODO: background_tasks.add_task(enqueue_vector_pruning, document_id)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_doc_or_404(
    db: AsyncSession, document_id: uuid.UUID, org_id: uuid.UUID
) -> Document:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.org_id == org_id
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise not_found(f"Document {document_id} not found")
    return doc
