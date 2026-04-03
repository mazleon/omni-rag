import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import json
import asyncio

from core.config import settings
from core.db import get_db
from core.models import Org, User, Query
from apps.api.routers.auth import get_current_active_user
from services.ingestion.embedder import get_embedder_service
from services.retrieval.dense import get_dense_retriever_service
from services.retrieval.sparse import get_sparse_retriever_service
from services.retrieval.fusion import get_fusion_service
from services.retrieval.reranker import get_reranker_service
from services.orchestrator.answer_generator import get_answer_generator_service
from services.orchestrator.agent import get_agent_service

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


async def get_current_org(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Org:
    result = await session.execute(select(Org).where(Org.id == current_user.org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


def _is_complex_query(query: str) -> bool:
    """Heuristic: route to agent loop for multi-hop or comparative queries."""
    q = query.lower().strip()
    complex_keywords = [
        "compare", "contrast", "difference between", "similarities between",
        "how does", "why does", "explain how", "what is the relationship",
        "step by step", "walk me through", "analyze",
    ]
    has_multiple_questions = query.count("?") > 1
    has_complex_keyword = any(kw in q for kw in complex_keywords)
    is_long = len(query.split()) > 30
    return has_multiple_questions or (has_complex_keyword and is_long)


async def generate_answer_stream(query: str, chunks: list[dict[str, Any]]) -> AsyncGenerator[str, None]:
    yield "data: " + json.dumps({"type": "start"}) + "\n\n"

    if not chunks:
        yield "data: " + json.dumps({
            "type": "content",
            "content": "I don't have enough context to answer this question. Please upload some documents first.",
        }) + "\n\n"
    else:
        context_parts = []
        for i, c in enumerate(chunks[:5], 1):
            pages = c.get("page_numbers")
            page_note = f" (pages: {', '.join(map(str, pages))})" if pages else ""
            context_parts.append(f"[{i}]{page_note}\n{c['content'][:500]}")
        context = "\n\n".join(context_parts)

        client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )

        try:
            stream = await client.chat.completions.create(
                model=settings.OPENROUTER_DEFAULT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful AI assistant that answers questions based on provided "
                            "document context. Cite sources using [1], [2], etc. for each fact. "
                            "If information is not in the context, say so clearly."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:",
                    },
                ],
                temperature=0.7,
                max_tokens=1000,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield "data: " + json.dumps({"type": "content", "content": content}) + "\n\n"

        except Exception as e:
            yield "data: " + json.dumps({"type": "error", "error": str(e)}) + "\n\n"

        sources = [
            {"chunk_id": str(c["chunk_id"]), "content": c["content"][:200]}
            for c in chunks[:3]
        ]
        yield "data: " + json.dumps({"type": "sources", "sources": sources}) + "\n\n"

    yield "data: " + json.dumps({"type": "end"}) + "\n\n"


@router.post("/stream")
async def query_stream(
    request: QueryRequest,
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

    answer = ""
    tokens_used: int | None = None
    sources: list[QuerySource] = []

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
        context_dicts = [
            {
                "chunk_id": str(r.chunk_id),
                "document_id": str(r.document_id),
                "content": r.content,
                "score": r.score,
                "page_numbers": r.page_numbers,
            }
            for r in reranked
        ]

        if _is_complex_query(request.query):
            agent_svc = get_agent_service()
            result = await agent_svc.run(request.query, context_dicts, {})
            answer = result["answer"]
        else:
            answer_svc = get_answer_generator_service()
            generated = await answer_svc.generate(request.query, context_dicts)
            answer = generated.answer
            tokens_used = generated.tokens_used
    else:
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
        tokens_used=tokens_used,
    )
    session.add(query_record)
    await session.commit()

    return QueryResponse(
        answer=answer,
        sources=sources,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
    )
