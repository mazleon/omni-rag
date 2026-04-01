import uuid
from typing import Any

import cohere
from pydantic import BaseModel

from core.config import settings


class EmbeddingResult(BaseModel):
    chunk_id: uuid.UUID
    embedding: list[float]


class EmbedderConfig(BaseModel):
    model: str = "embed-v4.0"
    input_type: str = "search_document"
    truncation: str = "END"


class CohereEmbedder:
    def __init__(self, config: EmbedderConfig | None = None) -> None:
        self.config = config or EmbedderConfig()
        self._client = cohere.AsyncClient(api_key=settings.COHERE_API_KEY)

    async def embed_chunks(
        self,
        chunks: list[dict[str, Any]],
    ) -> list[EmbeddingResult]:
        if not chunks:
            return []

        texts = [chunk["content"] for chunk in chunks]

        response = await self._client.embed(
            texts=texts,
            model=self.config.model,
            input_type=self.config.input_type,
            truncation=self.config.truncation,
        )

        results: list[EmbeddingResult] = []
        for i, embedding in enumerate(response.embeddings):
            results.append(
                EmbeddingResult(
                    chunk_id=chunks[i]["chunk_id"],
                    embedding=embedding,
                )
            )

        return results

    async def embed_query(self, query: str) -> list[float]:
        response = await self._client.embed(
            texts=[query],
            model=self.config.model,
            input_type="search_query",
            truncation=self.config.truncation,
        )
        return response.embeddings[0]


class EmbedderService:
    def __init__(self) -> None:
        self._embedder = CohereEmbedder()

    async def embed_document_chunks(
        self,
        chunks: list[dict[str, Any]],
    ) -> list[EmbeddingResult]:
        return await self._embedder.embed_chunks(chunks)

    async def embed_query(self, query: str) -> list[float]:
        return await self._embedder.embed_query(query)


def get_embedder_service() -> EmbedderService:
    return EmbedderService()