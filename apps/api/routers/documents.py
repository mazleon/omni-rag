import hashlib
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.models import Document, Org, User, DocumentStatus
from apps.api.routers.auth import get_current_active_user
from services.storage import get_storage_service

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
    collection_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    org: Org = Depends(get_current_org),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

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
        collection_id=collection_id,
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
    upload_url = await storage.get_presigned_upload_url(
        file_path=document.file_path,
        content_type=file.content_type or "application/octet-stream",
    )

    return DocumentCreateResponse(
        document_id=document.id,
        upload_url=upload_url,
        status="pending",
    )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
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


@router.get("/", response_model=list[dict[str, Any]])
async def list_documents(
    collection_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    org: Org = Depends(get_current_org),
):
    from sqlalchemy import func

    query = select(Document).where(Document.org_id == org.id)
    if collection_id:
        query = query.where(Document.collection_id == collection_id)

    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)

    query = query.order_by(Document.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(query)
    documents = result.scalars().all()

    return [
        {
            "id": str(doc.id),
            "filename": doc.filename,
            "status": doc.status.value,
            "num_chunks": doc.num_chunks,
            "created_at": doc.created_at.isoformat(),
        }
        for doc in documents
    ]
