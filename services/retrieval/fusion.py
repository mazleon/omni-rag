import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


@dataclass
class RankedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    score: float
    page_numbers: list[int] | None = None
    source: str = ""


class FusionConfig(BaseModel):
    k: int = 60
    top_n: int = 50


class RRFusion:
    def __init__(self, config: FusionConfig | None = None) -> None:
        self.config = config or FusionConfig()

    def fuse(
        self,
        dense_results: list[Any],
        sparse_results: list[Any],
    ) -> list[RankedChunk]:
        if not dense_results and not sparse_results:
            return []

        chunk_scores: dict[uuid.UUID, tuple[float, RankedChunk]] = {}

        for rank, result in enumerate(dense_results, start=1):
            score = 1.0 / (self.config.k + rank)
            chunk_id = result.chunk_id
            if chunk_id not in chunk_scores or chunk_scores[chunk_id][0] < score:
                chunk_scores[chunk_id] = (
                    score,
                    RankedChunk(
                        chunk_id=result.chunk_id,
                        document_id=result.document_id,
                        content=result.content,
                        score=score,
                        page_numbers=result.page_numbers,
                        source="dense",
                    ),
                )

        for rank, result in enumerate(sparse_results, start=1):
            score = 1.0 / (self.config.k + rank)
            chunk_id = result.chunk_id
            if chunk_id not in chunk_scores or chunk_scores[chunk_id][0] < score:
                chunk_scores[chunk_id] = (
                    score,
                    RankedChunk(
                        chunk_id=result.chunk_id,
                        document_id=result.document_id,
                        content=result.content,
                        score=score,
                        page_numbers=result.page_numbers,
                        source="sparse",
                    ),
                )

        sorted_chunks = sorted(chunk_scores.values(), key=lambda x: x[0], reverse=True)

        final_chunks = []
        seen_docs = set()
        for score, chunk in sorted_chunks:
            if len(final_chunks) >= self.config.top_n:
                break
            if chunk.document_id not in seen_docs or len(seen_docs) < 5:
                final_chunks.append(chunk)
                seen_docs.add(chunk.document_id)

        return final_chunks


class FusionService:
    def __init__(self) -> None:
        self._fusion = RRFusion()

    def fuse(
        self,
        dense_results: list[Any],
        sparse_results: list[Any],
    ) -> list[RankedChunk]:
        return self._fusion.fuse(dense_results, sparse_results)


def get_fusion_service() -> FusionService:
    return FusionService()