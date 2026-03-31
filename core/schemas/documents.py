"""Document-related request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from core.schemas.common import BaseResponse

DocType = Literal["pdf", "docx", "pptx", "xlsx", "png", "jpeg", "html", "md"]
DocStatus = Literal["pending", "processing", "indexed", "error"]


# ── Requests ───────────────────────────────────────────────────────────────────

class DocumentUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=500)
    doc_type: DocType
    title: str | None = Field(default=None, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentProcessRequest(BaseModel):
    """Trigger ingestion for an already-uploaded document."""
    force_reindex: bool = False  # ignore content_hash dedup and reprocess


class DocumentListParams(BaseModel):
    status: DocStatus | None = None
    doc_type: DocType | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


# ── Responses ──────────────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseResponse):
    document_id: uuid.UUID
    presigned_url: str
    storage_path: str
    expires_at: datetime


class DocumentSchema(BaseModel):
    """Serialised view of a Document ORM row."""

    id: uuid.UUID
    org_id: uuid.UUID
    title: str | None
    doc_type: str | None
    status: str
    page_count: int | None
    file_size_bytes: int | None
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseResponse):
    items: list[DocumentSchema]
    total: int
    page: int
    page_size: int
    has_next: bool


class DocumentStatusResponse(BaseResponse):
    document_id: uuid.UUID
    status: DocStatus
    error_message: str | None = None
    chunk_count: int | None = None
