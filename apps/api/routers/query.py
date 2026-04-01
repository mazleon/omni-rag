import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
import json
import asyncio

from core.db import get_db_session
from core.models import Org, User, Query
from services.ingestion.embedder import get_embedder_service
from services.retrieval.dense import get_dense_retriever_service
from services.retrieval.sparse import get_sparse_retriever_service
from services.retrieval.fusion import get_fusion_service
from services.retrieval.reranker import get_reranker_service

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    query: str
    collection_id: uuid.UUID | None = None
    filters: dict[str, Any] | None = None


class QuerySource(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    page_numbers: list[int] | None = None
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[QuerySource]
    latency_ms: int
    tokens_used: int | None = None


async def get_current_user(
    session: AsyncSession = Depends(get_db_session),
) -> User:
    from sqlalchemy import select
    result = await session.execute(
        select(User).where(User.email == "admin@omnirag.local")
    )
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            id=uuid.uuid4(),
            org_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="admin@omnirag.local",
            full_name="Admin",
            role="admin",
        )
        session.add(user)
        await session.commit()
    return user


async def get_current_org(
    session: AsyncSession = Depends(get_db_session),
) -> Org:
    from sqlalchemy import select
    result = await session.execute(
        select(Org).where(Org.slug == "default")
    )
    org = result.scalar_one_or_none()
    if not org:
        org = Org(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            name="Default Organization",
            slug="default",
        )
        session.add(org)
        await session.commit()
    return org


async def generate_answer_stream(query: str, chunks: list[dict[str, Any]]) -> AsyncGenerator[str, None]:
    yield "data: " + json.dumps({"type": "start"}) + "\n\n"
    await asyncio.sleep(0.1)

    if not chunks:
        yield "data: " + json.dumps({
            "type": "content",
            "content": "I don't have enough context to answer this question. Please upload some documents first."
        }) + "\n\n"
    else:
        context = "\n\n".join([f"[{i+1}] {c['content'][:300]}..." for i, c in enumerate(chunks[:5])])
        
        prompt = f"""Based on the following context, answer the user's question concisely and accurately. Include citations like [1], [2], etc. for each fact.

Context:
{context}

Question: {query}

Answer:"""

        words = prompt.split()
        for i in range(0, min(len(words), 50), 3):
            chunk = " ".join(words[i:i+3])
            yield "data: " + json.dumps({"type": "content", "content": chunk}) + "\n\n"
            await asyncio.sleep(0.05)

        sources = [
            {"chunk_id": str(c["chunk_id"]), "content": c["content"][:200]}
            for c in chunks[:3]
        ]
        yield "data: " + json.dumps({"type": "sources", "sources": sources}) + "\n\n"

    yield "data: " + json.dumps({"type": "end"}) + "\n\n"


@router.post("/stream")
async def query_stream(
    request: QueryRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
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

    if fused:
        reranked = await reranker.rerank(request.query, fused)
        chunks = [
            {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "content": r.content,
                "score": r.score,
                "page_numbers": r.page_numbers,
            }
            for r in reranked
        ]
    else:
        chunks = []

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    query_record = Query(
        id=uuid.uuid4(),
        org_id=org.id,
        user_id=user.id,
        query_text=request.query,
        response_sources=json.dumps(chunks[:3]),
        latency_ms=latency_ms,
    )
    session.add(query_record)
    await session.commit()

    return StreamingResponse(
        generate_answer_stream(request.query, chunks),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    session: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
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

    if fused:
        reranked = await reranker.rerank(request.query, fused)
        sources = [
            QuerySource(
                chunk_id=str(r.chunk_id),
                document_id=str(r.document_id),
                content=r.content[:200],
                page_numbers=r.page_numbers,
                score=r.score,
            )
            for r in reranked[:8]
        ]
        context = "\n\n".join([f"[{i+1}] {s.content}" for i, s in enumerate(sources[:3])])
        answer = f"Based on the retrieved context:\n\n{context}\n\nI can answer: {request.query}\n\n(This is a placeholder - integrate OpenRouter for actual LLM generation)"
    else:
        sources = []
        answer = "No relevant documents found. Please upload documents first."

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    query_record = Query(
        id=uuid.uuid4(),
        org_id=org.id,
        user_id=user.id,
        query_text=request.query,
        response_text=answer,
        response_sources=json.dumps([s.model_dump() for s in sources]),
        latency_ms=latency_ms,
    )
    session.add(query_record)
    await session.commit()

    return QueryResponse(
        answer=answer,
        sources=sources,
        latency_ms=latency_ms,
    )


from typing import AsyncGenerator