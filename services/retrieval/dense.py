import uuid
from typing import Any

from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from core.config import settings


class SearchResult(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    score: float
    page_numbers: list[int] | None = None


class DenseRetrieverConfig(BaseModel):
    top_k: int = 50
    score_threshold: float = 0.5


class QdrantDenseRetriever:
    def __init__(self, config: DenseRetrieverConfig | None = None) -> None:
        self.config = config or DenseRetrieverConfig()
        self._client = AsyncQdrantClient(url=settings.QDRANT_URL)

    async def search(
        self,
        org_id: uuid.UUID,
        query_embedding: list[float],
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        collection_name = f"chunks_{org_id}"

        try:
            search_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=str(value))))
                if conditions:
                    search_filter = Filter(must=conditions)

            results = await self._client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=self.config.top_k,
                score_threshold=self.config.score_threshold,
                query_filter=search_filter,
                with_payload=True,
            )

            return [
                SearchResult(
                    chunk_id=uuid.UUID(r.id),
                    document_id=uuid.UUID(r.payload["document_id"]),
                    content=r.payload.get("content", ""),
                    score=r.score,
                    page_numbers=self._parse_page_numbers(r.payload.get("page_numbers")),
                )
                for r in results
            ]
        except Exception:
            return []

    def _parse_page_numbers(self, page_str: str | None) -> list[int] | None:
        if not page_str:
            return None
        try:
            return [int(p) for p in page_str.split(",")]
        except ValueError:
            return None


class DenseRetrieverService:
    def __init__(self) -> None:
        self._retriever = QdrantDenseRetriever()

    async def search(
        self,
        org_id: uuid.UUID,
        query_embedding: list[float],
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        return await self._retriever.search(org_id, query_embedding, filters)


def get_dense_retriever_service() -> DenseRetrieverService:
    return DenseRetrieverService()