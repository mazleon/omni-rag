from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db, set_rls_context
from core.models import Org, User, Query as QueryModel, Document
from apps.api.routers.auth import get_current_active_user

router = APIRouter(prefix="/analytics", tags=["analytics"])


class QueryHistoryItem(BaseModel):
    id: str
    query_text: str
    answer: str | None
    latency_ms: int | None
    tokens_used: int | None
    cost_usd: float | None
    created_at: str


class QueryHistoryResponse(BaseModel):
    queries: list[QueryHistoryItem]
    total: int
    limit: int
    offset: int


class AnalyticsSummary(BaseModel):
    total_queries: int
    total_documents: int
    avg_latency_ms: float
    p50_latency_ms: int
    p95_latency_ms: int
    p99_latency_ms: int
    total_tokens: int
    total_cost_usd: float
    queries_today: int
    queries_this_week: int


class UsageItem(BaseModel):
    date: str
    query_count: int
    total_tokens: int
    total_cost: float


class UsageResponse(BaseModel):
    usage: list[UsageItem]
    period_days: int


async def get_current_org(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Org:
    result = await session.execute(select(Org).where(Org.id == current_user.org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("/queries/history", response_model=QueryHistoryResponse)
async def get_query_history(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
    org: Org = Depends(get_current_org),
):
    await set_rls_context(session, org.id)
    base_query = select(QueryModel).where(QueryModel.org_id == org.id)

    count_query = select(func.count()).select_from(base_query.subquery())
    total = await session.scalar(count_query)
    
    query = (
        base_query
        .order_by(desc(QueryModel.created_at))
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(query)
    queries = result.scalars().all()
    
    return QueryHistoryResponse(
        queries=[
            QueryHistoryItem(
                id=str(q.id),
                query_text=q.query_text,
                answer=q.response_text,
                latency_ms=q.latency_ms,
                tokens_used=q.tokens_used,
                cost_usd=q.cost_usd,
                created_at=q.created_at.isoformat(),
            )
            for q in queries
        ],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    session: AsyncSession = Depends(get_db),
    org: Org = Depends(get_current_org),
):
    await set_rls_context(session, org.id)
    query_count_result = await session.execute(
        select(func.count(QueryModel.id)).where(QueryModel.org_id == org.id)
    )
    total_queries = query_count_result.scalar() or 0
    
    doc_count_result = await session.execute(
        select(func.count(Document.id)).where(Document.org_id == org.id)
    )
    total_documents = doc_count_result.scalar() or 0
    
    latency_result = await session.execute(
        select(QueryModel.latency_ms).where(
            QueryModel.org_id == org.id,
            QueryModel.latency_ms.isnot(None),
        )
    )
    latencies = [r[0] for r in latency_result.fetchall() if r[0] is not None]
    
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    
    sorted_latencies = sorted(latencies)
    p50_idx = int(len(sorted_latencies) * 0.50)
    p95_idx = int(len(sorted_latencies) * 0.95)
    p99_idx = int(len(sorted_latencies) * 0.99)
    
    p50_latency = sorted_latencies[p50_idx] if sorted_latencies else 0
    p95_latency = sorted_latencies[p95_idx] if sorted_latencies else 0
    p99_latency = sorted_latencies[p99_idx] if sorted_latencies else 0
    
    tokens_result = await session.execute(
        select(func.sum(QueryModel.tokens_used)).where(QueryModel.org_id == org.id)
    )
    total_tokens = tokens_result.scalar() or 0
    
    cost_result = await session.execute(
        select(func.sum(QueryModel.cost_usd)).where(QueryModel.org_id == org.id)
    )
    total_cost = cost_result.scalar() or 0.0
    
    today_start = datetime.now(timezone.utc).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
    today_result = await session.execute(
        select(func.count(QueryModel.id)).where(
            QueryModel.org_id == org.id,
            QueryModel.created_at >= today_start,
        )
    )
    queries_today = today_result.scalar() or 0
    
    week_start = today_start - timedelta(days=7)
    week_result = await session.execute(
        select(func.count(QueryModel.id)).where(
            QueryModel.org_id == org.id,
            QueryModel.created_at >= week_start,
        )
    )
    queries_this_week = week_result.scalar() or 0
    
    return AnalyticsSummary(
        total_queries=total_queries,
        total_documents=total_documents,
        avg_latency_ms=round(avg_latency, 2),
        p50_latency_ms=p50_latency,
        p95_latency_ms=p95_latency,
        p99_latency_ms=p99_latency,
        total_tokens=total_tokens,
        total_cost_usd=round(total_cost, 6),
        queries_today=queries_today,
        queries_this_week=queries_this_week,
    )


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    days: int = Query(default=30, le=365, ge=1),
    session: AsyncSession = Depends(get_db),
    org: Org = Depends(get_current_org),
):
    await set_rls_context(session, org.id)
    start_date = datetime.utcnow() - timedelta(days=days)

    usage_map: dict[str, dict[str, Any]] = {}
    
    result = await session.execute(
        select(QueryModel).where(
            QueryModel.org_id == org.id,
            QueryModel.created_at >= start_date,
        )
    )
    queries = result.scalars().all()
    
    for q in queries:
        date_key = q.created_at.strftime("%Y-%m-%d")
        if date_key not in usage_map:
            usage_map[date_key] = {"query_count": 0, "total_tokens": 0, "total_cost": 0.0}
        
        usage_map[date_key]["query_count"] += 1
        usage_map[date_key]["total_tokens"] += q.tokens_used or 0
        usage_map[date_key]["total_cost"] += q.cost_usd or 0.0
    
    sorted_dates = sorted(usage_map.keys())
    usage = [
        UsageItem(
            date=date,
            query_count=usage_map[date]["query_count"],
            total_tokens=usage_map[date]["total_tokens"],
            total_cost=round(usage_map[date]["total_cost"], 6),
        )
        for date in sorted_dates
    ]
    
    return UsageResponse(usage=usage, period_days=days)
