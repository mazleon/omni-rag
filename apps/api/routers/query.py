"""Query endpoints — single-shot and SSE-streamed question answering.

POST /v1/query          — synchronous single-shot answer
POST /v1/query/stream   — Server-Sent Events streamed answer
GET  /v1/query/{id}     — retrieve a previously-generated query trace
"""

from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import get_current_org_id, get_db, get_request_id
from core.config import settings
from core.db import QueryTrace
from core.exceptions import not_found
from core.logging import get_logger
from core.schemas.query import (
    QueryRequest,
    QueryResponse,
    QueryStreamChunk,
    Citation,
    RetrievalDebug,
)

log = get_logger(__name__)
router = APIRouter(prefix="/v1/query", tags=["query"])


# ── Single-Shot Query ─────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=QueryResponse,
    summary="Submit a question and receive a grounded answer",
    description=(
        "Executes the full hybrid retrieval pipeline: dense (Qdrant HNSW) "
        "+ sparse (Postgres BM25) + structured filter → RRF fusion → "
        "Cohere rerank → LLM generation with citation injection."
    ),
)
async def query(
    body: QueryRequest,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> QueryResponse:
    """Run the full RAG pipeline and return a single-shot response."""
    start = time.perf_counter()

    # Phase 2 TODO: wire up orchestrator.run_query(body, org_id)
    # For Phase 1, return a stub response so the endpoint compiles.
    trace_id = uuid.uuid4()

    # Persist query trace for audit logging
    trace = QueryTrace(
        id=trace_id,
        org_id=org_id,
        query=body.query,
        answer_text="[Phase 1 stub] The RAG pipeline is not yet wired.",
        latency_ms=int((time.perf_counter() - start) * 1000),
        model_used=settings.openrouter_default_model,
        request_id=request_id,
    )
    db.add(trace)

    log.info(
        "query.completed",
        trace_id=str(trace_id),
        latency_ms=trace.latency_ms,
        org_id=str(org_id),
    )

    return QueryResponse(
        query_id=trace_id,
        answer="[Phase 1 stub] The full RAG pipeline will be wired in Phase 2.",
        citations=[],
        model=settings.openrouter_default_model,
        latency_ms=trace.latency_ms or 0,
        retrieval_debug=None,
    )


# ── Streamed Query (SSE) ──────────────────────────────────────────────────────

@router.post(
    "/stream",
    summary="Stream an answer via Server-Sent Events",
    description="Same pipeline as POST /v1/query but tokens are streamed via SSE.",
    response_class=StreamingResponse,
)
async def query_stream(
    body: QueryRequest,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> StreamingResponse:
    """Stream the RAG answer token-by-token via SSE."""

    async def _event_generator():
        """Yield SSE events.

        Phase 2 TODO: replace with real orchestrator streaming.
        """
        import json

        # Phase 1 stub: emit a single chunk
        chunk = QueryStreamChunk(
            event="chunk",
            data="[Phase 1 stub] SSE streaming will be wired in Phase 2.",
        )
        yield f"data: {json.dumps(chunk.model_dump())}\n\n"

        # Final done event
        done = QueryStreamChunk(event="done", data="")
        yield f"data: {json.dumps(done.model_dump())}\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id,
        },
    )


# ── Get Query Trace ───────────────────────────────────────────────────────────

@router.get(
    "/{query_id}",
    response_model=QueryResponse,
    summary="Retrieve a previous query result by ID",
)
async def get_query_trace(
    query_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_org_id),
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """Fetch a stored query trace for replay or audit."""
    stmt = select(QueryTrace).where(
        QueryTrace.id == query_id,
        QueryTrace.org_id == org_id,
    )
    result = await db.execute(stmt)
    trace = result.scalar_one_or_none()

    if trace is None:
        raise not_found("QueryTrace", str(query_id))

    return QueryResponse(
        query_id=trace.id,
        answer=trace.answer_text or "",
        citations=[],
        model=trace.model_used or "unknown",
        latency_ms=trace.latency_ms or 0,
        retrieval_debug=None,
    )
