from __future__ import annotations

import hashlib
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from arq import create_pool
from arq.connections import RedisSettings

from core.config import settings
from core.db import get_db, set_rls_context
from core.models import Document, Org, User, DocumentStatus
from apps.api.routers.auth import get_current_active_user
from services.storage import get_storage_service
from core.cache import get_cache_service

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentCreateResponse(BaseModel):
    document_id: uuid.UUID
    upload_url: str
    status: str


class DocumentStatusResponse(BaseModel):
    document_id: uuid.UUID
    status: str
    num_chunks: int | None = None
    error: str | None = None


class DocumentDetailResponse(BaseModel):
    id: str
    filename: str
    file_path: str
    file_size: int | None
    mime_type: str | None
    content_hash: str
    status: str
    num_pages: int | None
    num_chunks: int
    error_message: str | None
    collection_id: str | None
    created_at: str
    updated_at: str
    processed_at: str | None


class DocumentUpdateRequest(BaseModel):
    filename: str | None = None
    collection_id: uuid.UUID | None = None


async def get_current_org(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Org:
    result = await session.execute(select(Org).where(Org.id == current_user.org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.post("/upload", response_model=DocumentCreateResponse)
async def upload_document(
    file: UploadFile = File(...),
    collection_id: str | None = Form(None),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    org: Org = Depends(get_current_org),
):
    await set_rls_context(session, org.id)

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    parsed_collection_id: uuid.UUID | None = None
    if collection_id:
        try:
            parsed_collection_id = uuid.UUID(collection_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid collection_id format")

    file_content = await file.read()
    content_hash = hashlib.sha256(file_content).hexdigest()

    existing = await session.execute(
        select(Document).where(Document.content_hash == content_hash)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Document already exists")

    document = Document(
        id=uuid.uuid4(),
        org_id=org.id,
        user_id=user.id,
        collection_id=parsed_collection_id,
        filename=file.filename,
        file_path=f"documents/{org.id}/{file.filename}",
        file_size=len(file_content),
        mime_type=file.content_type or "application/octet-stream",
        content_hash=content_hash,
        status=DocumentStatus.PENDING,
    )
    session.add(document)
    await session.commit()

    storage = get_storage_service()
    await storage.upload_file(
        file_path=document.file_path,
        content=file_content,
        content_type=file.content_type or "application/octet-stream",
    )

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    arq_pool = await create_pool(redis_settings)
    await arq_pool.enqueue_job(
        "process_ingest_job",
        {
            "document_id": str(document.id),
            "org_id": str(org.id),
            "user_id": str(user.id),
            "file_path": document.file_path,
            "collection_id": str(parsed_collection_id) if parsed_collection_id else None,
        },
    )
    await arq_pool.aclose()

    return DocumentCreateResponse(
        document_id=document.id,
        upload_url="",
        status="pending",
    )


class BatchUploadResponse(BaseModel):
    documents: list[DocumentCreateResponse]
    failed: list[dict[str, str]]


@router.post("/upload/batch", response_model=BatchUploadResponse)
async def batch_upload_documents(
    files: list[UploadFile] = File(...),
    collection_id: str | None = Form(None),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    org: Org = Depends(get_current_org),
):
    await set_rls_context(session, org.id)

    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch")

    parsed_collection_id: uuid.UUID | None = None
    if collection_id:
        try:
            parsed_collection_id = uuid.UUID(collection_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid collection_id format")

    successful: list[DocumentCreateResponse] = []
    failed: list[dict[str, str]] = []

    storage = get_storage_service()
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    arq_pool = await create_pool(redis_settings)

    for file in files:
        if not file.filename:
            failed.append({"filename": "unknown", "error": "Filename required"})
            continue

        try:
            file_content = await file.read()
            content_hash = hashlib.sha256(file_content).hexdigest()

            existing = await session.execute(
                select(Document).where(Document.content_hash == content_hash)
            )
            if existing.scalar_one_or_none():
                failed.append({"filename": file.filename, "error": "Document already exists"})
                continue

            document = Document(
                id=uuid.uuid4(),
                org_id=org.id,
                user_id=user.id,
                collection_id=parsed_collection_id,
                filename=file.filename,
                file_path=f"documents/{org.id}/{file.filename}",
                file_size=len(file_content),
                mime_type=file.content_type or "application/octet-stream",
                content_hash=content_hash,
                status=DocumentStatus.PENDING,
            )
            session.add(document)
            await session.flush()

            await storage.upload_file(
                file_path=document.file_path,
                content=file_content,
                content_type=file.content_type or "application/octet-stream",
            )

            await arq_pool.enqueue_job(
                "process_ingest_job",
                {
                    "document_id": str(document.id),
                    "org_id": str(org.id),
                    "user_id": str(user.id),
                    "file_path": document.file_path,
                    "collection_id": str(parsed_collection_id) if parsed_collection_id else None,
                },
            )

            successful.append(DocumentCreateResponse(
                document_id=document.id,
                upload_url="",
                status="pending",
            ))

        except Exception as e:
            failed.append({"filename": file.filename, "error": str(e)})

    await session.commit()
    await arq_pool.aclose()

    return BatchUploadResponse(documents=successful, failed=failed)


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    await set_rls_context(session, user.org_id)
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.org_id == user.org_id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentStatusResponse(
        document_id=document.id,
        status=document.status.value,
        num_chunks=document.num_chunks,
        error=document.error_message,
    )


@router.get("/", response_model=list[DocumentDetailResponse])
async def list_documents(
    collection_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    org: Org = Depends(get_current_org),
):
    await set_rls_context(session, org.id)

    query = select(Document).where(Document.org_id == org.id)
    if collection_id:
        query = query.where(Document.collection_id == collection_id)

    query = query.order_by(Document.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    documents = result.scalars().all()

    return [
        DocumentDetailResponse(
            id=str(doc.id),
            filename=doc.filename,
            file_path=doc.file_path,
            file_size=doc.file_size,
            mime_type=doc.mime_type,
            content_hash=doc.content_hash,
            status=doc.status.value,
            num_pages=doc.num_pages,
            num_chunks=doc.num_chunks,
            error_message=doc.error_message,
            collection_id=str(doc.collection_id) if doc.collection_id else None,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
            processed_at=doc.processed_at.isoformat() if doc.processed_at else None,
        )
        for doc in documents
    ]


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    await set_rls_context(session, user.org_id)
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.org_id == user.org_id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentDetailResponse(
        id=str(document.id),
        filename=document.filename,
        file_path=document.file_path,
        file_size=document.file_size,
        mime_type=document.mime_type,
        content_hash=document.content_hash,
        status=document.status.value,
        num_pages=document.num_pages,
        num_chunks=document.num_chunks,
        error_message=document.error_message,
        collection_id=str(document.collection_id) if document.collection_id else None,
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat(),
        processed_at=document.processed_at.isoformat() if document.processed_at else None,
    )


@router.put("/{document_id}", response_model=DocumentDetailResponse)
async def update_document(
    document_id: uuid.UUID,
    request: DocumentUpdateRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    await set_rls_context(session, user.org_id)
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.org_id == user.org_id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if request.filename is not None:
        document.filename = request.filename
    if request.collection_id is not None:
        document.collection_id = request.collection_id

    await session.commit()
    await session.refresh(document)

    cache = get_cache_service()
    await cache.invalidate_org_cache(str(user.org_id))

    return DocumentDetailResponse(
        id=str(document.id),
        filename=document.filename,
        file_path=document.file_path,
        file_size=document.file_size,
        mime_type=document.mime_type,
        content_hash=document.content_hash,
        status=document.status.value,
        num_pages=document.num_pages,
        num_chunks=document.num_chunks,
        error_message=document.error_message,
        collection_id=str(document.collection_id) if document.collection_id else None,
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat(),
        processed_at=document.processed_at.isoformat() if document.processed_at else None,
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    await set_rls_context(session, user.org_id)
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.org_id == user.org_id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    document.status = DocumentStatus.FAILED
    await session.commit()

    cache = get_cache_service()
    await cache.invalidate_org_cache(str(user.org_id))

    return {"message": "Document marked for deletion", "document_id": str(document_id)}


class ReprocessResponse(BaseModel):
    document_id: uuid.UUID
    message: str
    job_id: str | None = None


@router.post("/{document_id}/reprocess", response_model=ReprocessResponse)
async def reprocess_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    await set_rls_context(session, user.org_id)
    result = await session.execute(
        select(Document).where(
            Document.id == document_id,
            Document.org_id == user.org_id,
        )
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.status == DocumentStatus.PROCESSING:
        raise HTTPException(
            status_code=400,
            detail="Document is already being processed"
        )

    document.status = DocumentStatus.PENDING
    document.error_message = None
    await session.commit()

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    arq_pool = await create_pool(redis_settings)
    job = await arq_pool.enqueue_job(
        "process_ingest_job",
        {
            "document_id": str(document.id),
            "org_id": str(user.org_id),
            "user_id": str(user.id),
            "file_path": document.file_path,
            "collection_id": str(document.collection_id) if document.collection_id else None,
        },
    )
    await arq_pool.aclose()

    return ReprocessResponse(
        document_id=document_id,
        message="Document queued for reprocessing",
        job_id=job.job_id if job else None,
    )
