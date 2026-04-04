from __future__ import annotations

import hashlib
import uuid
from typing import Any

import cohere
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.config import settings
from core.logging import get_logger

log = get_logger(__name__)


class EmbeddingResult(BaseModel):
    chunk_id: uuid.UUID
    embedding: list[float]


class EmbedderConfig(BaseModel):
    model: str = "embed-v4.0"
    input_type: str = "search_document"
    truncate: str = "END"
    max_batch_size: int = 96


def _make_dummy_embedding(text: str, dim: int = 1024) -> list[float]:
    """Generate a deterministic dummy embedding for development without Cohere API key."""
    seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
    import random
    rng = random.Random(seed)
    vec = [rng.gauss(0, 1) for _ in range(dim)]
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


class CohereEmbedder:
    def __init__(self, config: EmbedderConfig | None = None) -> None:
        self.config = config or EmbedderConfig()
        self._has_api_key = bool(settings.COHERE_API_KEY and settings.COHERE_API_KEY.strip())
        if self._has_api_key:
            self._client = cohere.AsyncClient(api_key=settings.COHERE_API_KEY)
        else:
            log.warning("embedder.no_api_key", msg="COHERE_API_KEY not set, using dummy embeddings for development")

    async def embed_chunks(
        self,
        chunks: list[dict[str, Any]],
    ) -> list[EmbeddingResult]:
        if not chunks:
            return []

        if not self._has_api_key:
            return [
                EmbeddingResult(
                    chunk_id=chunks[i]["chunk_id"],
                    embedding=_make_dummy_embedding(chunks[i]["content"]),
                )
                for i in range(len(chunks))
            ]

        return await self._embed_with_retry(chunks)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _embed_with_retry(
        self,
        chunks: list[dict[str, Any]],
    ) -> list[EmbeddingResult]:
        texts = [chunk["content"] for chunk in chunks]

        response = await self._client.embed(
            texts=texts,
            model=self.config.model,
            input_type=self.config.input_type,
            truncate=self.config.truncate,
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
        if not self._has_api_key:
            return _make_dummy_embedding(query)

        return await self._embed_query_with_retry(query)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _embed_query_with_retry(self, query: str) -> list[float]:
        response = await self._client.embed(
            texts=[query],
            model=self.config.model,
            input_type="search_query",
            truncate=self.config.truncate,
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
