import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.models import Org, User
from apps.api.routers.auth import get_current_active_user
from services.ingestion.embedder import get_embedder_service
from services.retrieval.dense import get_dense_retriever_service
from services.retrieval.sparse import get_sparse_retriever_service
from services.retrieval.fusion import get_fusion_service
from services.retrieval.reranker import get_reranker_service

router = APIRouter(prefix="/query", tags=["query"])


class RetrievalRequest(BaseModel):
    query: str
    collection_id: uuid.UUID | None = None
    filters: dict[str, Any] | None = None
    top_k: int = 8
    use_reranker: bool = True


class RetrievalSource(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    page_numbers: list[int] | None = None
    score: float


class RetrievalResponse(BaseModel):
    query: str
    chunks: list[RetrievalSource]
    retrieval_latency_ms: int


async def get_current_org(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Org:
    result = await session.execute(select(Org).where(Org.id == current_user.org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.post("/retrieval-only", response_model=RetrievalResponse)
async def retrieval_only(
    request: RetrievalRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    org: Org = Depends(get_current_org),
):
    import time
    start_time = time.perf_counter()

    embedder = get_embedder_service()
    dense_retriever = get_dense_retriever_service()
    sparse_retriever = get_sparse_retriever_service()
    fusion = get_fusion_service()
    reranker = get_reranker_service()

    query_embedding = await embedder.embed_query(request.query)

    dense_results = await dense_retriever.search(org.id, query_embedding, request.filters)
    sparse_results = await sparse_retriever.search(session, org.id, request.query, request.filters)

    fused = fusion.fuse(dense_results, sparse_results)

    if request.use_reranker and fused:
        reranked = await reranker.rerank(request.query, fused)
        chunks = [
            RetrievalSource(
                chunk_id=str(r.chunk_id),
                document_id=str(r.document_id),
                content=r.content,
                page_numbers=r.page_numbers,
                score=r.score,
            )
            for r in reranked[:request.top_k]
        ]
    elif fused:
        chunks = [
            RetrievalSource(
                chunk_id=str(r.chunk_id),
                document_id=str(r.document_id),
                content=r.content[:500],
                page_numbers=r.page_numbers,
                score=r.score,
            )
            for r in fused[:request.top_k]
        ]
    else:
        chunks = []

    retrieval_latency_ms = int((time.perf_counter() - start_time) * 1000)

    return RetrievalResponse(
        query=request.query,
        chunks=chunks,
        retrieval_latency_ms=retrieval_latency_ms,
    )
