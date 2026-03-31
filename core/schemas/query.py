"""Query request/response schemas — including SSE streaming payloads."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from core.schemas.common import BaseResponse


# ── Sub-schemas ────────────────────────────────────────────────────────────────

class DateRangeFilter(BaseModel):
    from_date: datetime | None = Field(default=None, alias="from")
    to_date: datetime | None = Field(default=None, alias="to")

    model_config = {"populate_by_name": True}


class MetadataFilter(BaseModel):
    doc_type: list[str] | None = None
    date_range: DateRangeFilter | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    collection_ids: list[str] | None = None


class RetrievalOptions(BaseModel):
    top_k: int = Field(default=8, ge=1, le=20)
    use_reranker: bool = True
    use_hyde: bool = False            # HyDE: Hypothetical Document Embeddings


class GenerationOptions(BaseModel):
    model: str = Field(default="")   # empty = use OPENROUTER_DEFAULT_MODEL
    stream: bool = True
    max_tokens: int = Field(default=1500, ge=1, le=8192)
    temperature: float = Field(default=0.1, ge=0.0, le=2.0)


# ── Requests ───────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4096)
    filters: MetadataFilter = Field(default_factory=MetadataFilter)
    retrieval: RetrievalOptions = Field(default_factory=RetrievalOptions)
    generation: GenerationOptions = Field(default_factory=GenerationOptions)


class RetrievalOnlyRequest(BaseModel):
    """Return ranked chunks without generation — for debugging/evaluation."""
    query: str = Field(min_length=1, max_length=4096)
    filters: MetadataFilter = Field(default_factory=MetadataFilter)
    retrieval: RetrievalOptions = Field(default_factory=RetrievalOptions)


class FeedbackRequest(BaseModel):
    query_trace_id: uuid.UUID
    feedback: int = Field(ge=-1, le=1)   # -1 = thumbs down, 0 = neutral, 1 = thumbs up


# ── Responses ──────────────────────────────────────────────────────────────────

class Citation(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str | None
    page_number: int | None
    relevance_score: float
    excerpt: str


class ChunkResult(BaseModel):
    """A single retrieved and reranked chunk."""
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str | None
    content: str
    modality: str
    page_number: int | None
    relevance_score: float
    rrf_score: float


class RetrievalOnlyResponse(BaseResponse):
    query: str
    results: list[ChunkResult]
    retrieval_latency_ms: int
    dense_count: int
    sparse_count: int


class QueryDonePayload(BaseResponse):
    """Sent as the final 'done' SSE event after all tokens are streamed."""
    query_trace_id: uuid.UUID
    answer: str
    citations: list[Citation]
    retrieval_latency_ms: int
    total_latency_ms: int
    cost_usd: float
    model_used: str


# ── SSE event types (for documentation / type-safety in consumers) ─────────────

class SSETokenEvent(BaseModel):
    token: str
    index: int


class SSEDoneEvent(BaseModel):
    payload: QueryDonePayload
