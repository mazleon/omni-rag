import asyncio
import json
import time
import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.cache import get_cache_service
from core.config import settings
from core.db import get_db, set_rls_context
from core.models import Org, User, Query
from apps.api.routers.auth import get_current_active_user
from services.ingestion.embedder import get_embedder_service
from services.retrieval.dense import get_dense_retriever_service
from services.retrieval.sparse import get_sparse_retriever_service
from services.retrieval.fusion import get_fusion_service
from services.retrieval.reranker import get_reranker_service
from services.orchestrator.answer_generator import get_answer_generator_service
from services.orchestrator.agent import get_agent_service
from services.query_analyzer import get_query_analyzer_service
from services.evaluation.ragas_runner import get_ragas_runner

router = APIRouter(prefix="/query", tags=["query"])


_openai_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )
    return _openai_client


class QueryRequest(BaseModel):
    query: str
    collection_id: uuid.UUID | None = None
    collection_ids: list[uuid.UUID] | None = None
    filters: dict[str, Any] | None = None
    use_analyzer: bool = True


class QuerySource(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    page_numbers: list[int] | None = None
    score: float


class QueryResponse(BaseModel):
    query_id: str
    answer: str
    sources: list[QuerySource]
    latency_ms: int
    tokens_used: int | None = None
    cost_usd: float | None = None
    cached: bool = False
    query_analysis: dict[str, Any] | None = None


async def get_current_org(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Org:
    result = await session.execute(select(Org).where(Org.id == current_user.org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


async def generate_answer_stream(
    query: str,
    chunks: list[dict[str, Any]],
    query_id: str | None = None,
) -> AsyncGenerator[str, None]:
    yield "data: " + json.dumps({"type": "start"}) + "\n\n"

    if not chunks:
        client = get_openai_client()
        try:
            stream = await client.chat.completions.create(
                model=settings.OPENROUTER_DEFAULT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful AI assistant. No documents have been uploaded yet, "
                            "so answer the question using your general knowledge. "
                            "Start your response by mentioning: 'Note: No documents have been uploaded yet. "
                            "This answer is based on general knowledge, not your organization's documents.' "
                            "Then provide a helpful, comprehensive answer."
                        ),
                    },
                    {"role": "user", "content": query},
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
            error_msg = str(e)
            if "401" in error_msg or "User not found" in error_msg:
                yield "data: " + json.dumps({
                    "type": "content",
                    "content": (
                        "No documents have been uploaded yet. "
                        "Please upload documents first to enable document-grounded responses. "
                        "Once documents are uploaded, I'll be able to answer questions based on their content."
                    ),
                }) + "\n\n"
            else:
                yield "data: " + json.dumps({
                    "type": "error",
                    "error": error_msg,
                }) + "\n\n"
    else:
        context_parts = []
        for i, c in enumerate(chunks[:5], 1):
            pages = c.get("page_numbers")
            page_note = f" (pages: {', '.join(map(str, pages))})" if pages else ""
            context_parts.append(f"[{i}]{page_note}\n{c['content'][:500]}")
        context = "\n\n".join(context_parts)

        client = get_openai_client()

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
            error_msg = str(e)
            if "401" in error_msg or "User not found" in error_msg:
                yield "data: " + json.dumps({
                    "type": "content",
                    "content": (
                        "I found relevant documents but the AI service is currently unavailable. "
                        "Please try again later or contact support."
                    ),
                }) + "\n\n"
            else:
                yield "data: " + json.dumps({
                    "type": "error",
                    "error": error_msg,
                }) + "\n\n"

        sources = [
            {"chunk_id": str(c["chunk_id"]), "content": c["content"][:200]}
            for c in chunks[:3]
        ]
        yield "data: " + json.dumps({
            "type": "sources",
            "sources": sources,
            "query_id": query_id,
        }) + "\n\n"

    yield "data: " + json.dumps({"type": "end"}) + "\n\n"


@router.post("/stream")
async def query_stream(
    request: QueryRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
    org: Org = Depends(get_current_org),
):
    await set_rls_context(session, org.id)
    start_time = time.perf_counter()

    cache = get_cache_service()
    org_id_str = str(org.id)

    cached_chunks = await cache.get_cached_query_result(org_id_str, request.query)
    if cached_chunks and "chunks" in cached_chunks:
        chunks = cached_chunks["chunks"]
    else:
        embedder = get_embedder_service()
        dense_retriever = get_dense_retriever_service()
        sparse_retriever = get_sparse_retriever_service()
        fusion = get_fusion_service()
        reranker = get_reranker_service()

        cached_embedding = await cache.get_cached_embedding(org_id_str, request.query)
        if cached_embedding:
            query_embedding = cached_embedding
        else:
            query_embedding = await embedder.embed_query(request.query)
            await cache.cache_embedding(org_id_str, request.query, query_embedding, ttl=600)

        dense_results = await dense_retriever.search(org.id, query_embedding, request.filters)
        sparse_results = await sparse_retriever.search(session, org.id, request.query, request.filters)

        fused = fusion.fuse(dense_results, sparse_results)

        if fused:
            reranked = await reranker.rerank(request.query, fused)
            chunks = [
                {
                    "chunk_id": str(r.chunk_id),
                    "document_id": str(r.document_id),
                    "content": r.content,
                    "score": r.score,
                    "page_numbers": r.page_numbers,
                }
                for r in reranked
            ]
        else:
            chunks = []

        await cache.cache_query_result(
            org_id_str,
            request.query,
            {"chunks": chunks},
            ttl=300,
        )

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    query_id = uuid.uuid4()
    estimated_tokens = len(request.query.split()) * 2
    cost_usd = 0.0
    if estimated_tokens:
        cost_per_1k = 0.00035
        cost_usd = (estimated_tokens / 1000) * cost_per_1k

    query_record = Query(
        id=query_id,
        org_id=org.id,
        user_id=user.id,
        query_text=request.query,
        response_sources=json.dumps(chunks[:3]),
        latency_ms=latency_ms,
        tokens_used=estimated_tokens,
        cost_usd=cost_usd,
    )
    session.add(query_record)
    await session.commit()

    return StreamingResponse(
        generate_answer_stream(request.query, chunks, query_id=str(query_id)),
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
    await set_rls_context(session, org.id)
    start_time = time.perf_counter()

    cache = get_cache_service()
    org_id_str = str(org.id)

    cached_result = await cache.get_cached_query_result(org_id_str, request.query)
    if cached_result and "query_id" in cached_result:
        cached_result["cached"] = True
        return QueryResponse(**cached_result)

    query_analyzer = get_query_analyzer_service()
    analysis = query_analyzer.analyze(request.query, request.collection_ids)
    
    effective_query = analysis.rewritten_query or request.query

    filters = request.filters or {}
    if analysis.date_range:
        filters["date_range"] = analysis.date_range
    if analysis.doc_types:
        filters["doc_type"] = analysis.doc_types

    embedder = get_embedder_service()
    dense_retriever = get_dense_retriever_service()
    sparse_retriever = get_sparse_retriever_service()
    fusion = get_fusion_service()
    reranker = get_reranker_service()

    cached_embedding = await cache.get_cached_embedding(org_id_str, effective_query)
    if cached_embedding:
        query_embedding = cached_embedding
    else:
        query_embedding = await embedder.embed_query(effective_query)
        await cache.cache_embedding(org_id_str, effective_query, query_embedding, ttl=600)

    dense_results = await dense_retriever.search(org.id, query_embedding, filters)
    sparse_results = await sparse_retriever.search(session, org.id, effective_query, filters)

    fused = fusion.fuse(dense_results, sparse_results)

    answer = ""
    tokens_used: int | None = None
    sources: list[QuerySource] = []

    if fused:
        reranked = await reranker.rerank(effective_query, fused)
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

        if analysis.should_use_agent:
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

    cost_usd = 0.0
    if tokens_used:
        cost_per_1k = 0.00035
        cost_usd = (tokens_used / 1000) * cost_per_1k

    query_record = Query(
        id=uuid.uuid4(),
        org_id=org.id,
        user_id=user.id,
        query_text=request.query,
        response_text=answer,
        response_sources=json.dumps([s.model_dump() for s in sources]),
        latency_ms=latency_ms,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
    )
    session.add(query_record)
    await session.commit()

    if answer and sources:
        ragas_runner = get_ragas_runner()
        contexts = [s.content for s in sources]
        asyncio.create_task(
            ragas_runner.evaluate_single(
                query=request.query,
                answer=answer,
                contexts=contexts,
                ground_truth="",
            )
        )

    result_dict = {
        "query_id": str(query_record.id),
        "answer": answer,
        "sources": [s.model_dump() for s in sources],
        "latency_ms": latency_ms,
        "tokens_used": tokens_used,
        "cost_usd": query_record.cost_usd,
    }
    await cache.cache_query_result(org_id_str, request.query, result_dict, ttl=300)

    return QueryResponse(
        query_id=str(query_record.id),
        answer=answer,
        sources=sources,
        latency_ms=latency_ms,
        tokens_used=tokens_used,
        cost_usd=query_record.cost_usd,
        query_analysis={
            "intent": analysis.intent.value,
            "complexity": analysis.complexity.value,
            "should_use_agent": analysis.should_use_agent,
            "rewritten_query": analysis.rewritten_query,
        },
    )
