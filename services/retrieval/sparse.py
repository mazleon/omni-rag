import uuid
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Chunk


class SparseSearchResult(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    score: float
    page_numbers: list[int] | None = None


class SparseRetrieverConfig(BaseModel):
    top_k: int = 50
    min_score: float = 0.1


class PostgresSparseRetriever:
    def __init__(self, config: SparseRetrieverConfig | None = None) -> None:
        self.config = config or SparseRetrieverConfig()

    async def search(
        self,
        session: AsyncSession,
        org_id: uuid.UUID,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> list[SparseSearchResult]:
        if not query.strip():
            return []

        ts_query = " & ".join(query.split())

        sql = text("""
            SELECT 
                id, document_id, content, 
                ts_rank(to_tsvector('english', content), to_tsquery(:query)) as rank,
                page_numbers
            FROM chunks
            WHERE org_id = :org_id
              AND to_tsvector('english', content) @@ to_tsquery(:query)
            ORDER BY rank DESC
            LIMIT :limit
        """)

        result = await session.execute(
            sql,
            {"query": ts_query, "org_id": str(org_id), "limit": self.config.top_k}
        )

        return [
            SparseSearchResult(
                chunk_id=row.id,
                document_id=row.document_id,
                content=row.content,
                score=float(row.rank),
                page_numbers=self._parse_page_numbers(row.page_numbers),
            )
            for row in result
        ]

    def _parse_page_numbers(self, page_str: str | None) -> list[int] | None:
        if not page_str:
            return None
        try:
            return [int(p) for p in page_str.split(",")]
        except ValueError:
            return None


class SparseRetrieverService:
    def __init__(self) -> None:
        self._retriever = PostgresSparseRetriever()

    async def search(
        self,
        session: AsyncSession,
        org_id: uuid.UUID,
        query: str,
        filters: dict[str, Any] | None = None,
    ) -> list[SparseSearchResult]:
        return await self._retriever.search(session, org_id, query, filters)


def get_sparse_retriever_service() -> SparseRetrieverService:
    return SparseRetrieverService()