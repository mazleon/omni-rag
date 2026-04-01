import uuid

import cohere
from pydantic import BaseModel

from core.config import settings
from services.retrieval.fusion import RankedChunk


class RerankResult(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    score: float
    page_numbers: list[int] | None = None


class RerankerConfig(BaseModel):
    model: str = "rerank-v3.5"
    top_n: int = 8


class CohereReranker:
    def __init__(self, config: RerankerConfig | None = None) -> None:
        self.config = config or RerankerConfig()
        self._client = cohere.AsyncClient(api_key=settings.COHERE_API_KEY)

    async def rerank(
        self,
        query: str,
        chunks: list[RankedChunk],
    ) -> list[RerankResult]:
        if not chunks:
            return []

        documents = [chunk.content for chunk in chunks]

        try:
            response = await self._client.rerank(
                query=query,
                documents=documents,
                model=self.config.model,
                top_n=min(self.config.top_n, len(chunks)),
            )

            results = []
            for r in response.results:
                chunk = chunks[r.index]
                results.append(
                    RerankResult(
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        content=chunk.content,
                        score=r.relevance_score,
                        page_numbers=chunk.page_numbers,
                    )
                )

            return results
        except Exception:
            return [
                RerankResult(
                    chunk_id=c.chunk_id,
                    document_id=c.document_id,
                    content=c.content,
                    score=c.score,
                    page_numbers=c.page_numbers,
                )
                for c in chunks[: self.config.top_n]
            ]


class RerankerService:
    def __init__(self) -> None:
        self._reranker = CohereReranker()

    async def rerank(
        self,
        query: str,
        chunks: list[RankedChunk],
    ) -> list[RerankResult]:
        return await self._reranker.rerank(query, chunks)


def get_reranker_service() -> RerankerService:
    return RerankerService()