import uuid
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from services.retrieval.fusion import RRFusion, FusionService, RankedChunk, FusionConfig


class TestRRFusion:
    def test_empty_results_returns_empty(self):
        fusion = RRFusion()
        result = fusion.fuse([], [])
        assert result == []

    def test_single_dense_result(self):
        fusion = RRFusion()
        dense = [
            MagicMock(
                chunk_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                content="test content",
                score=0.9,
                page_numbers=None,
            )
        ]
        result = fusion.fuse(dense, [])
        assert len(result) == 1

    def test_fusion_ranks_by_rrf(self):
        config = FusionConfig(k=60, top_n=10)
        fusion = RRFusion(config)

        dense = [
            MagicMock(
                chunk_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
                document_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                content="dense result",
                score=0.9,
                page_numbers=None,
            )
        ]

        sparse = [
            MagicMock(
                chunk_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
                document_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
                content="sparse result",
                score=0.8,
                page_numbers=None,
            )
        ]

        result = fusion.fuse(dense, sparse)
        assert len(result) == 2

    def test_deduplication_same_chunk(self):
        fusion = RRFusion()
        chunk_id = uuid.uuid4()
        doc_id = uuid.uuid4()

        dense = [
            MagicMock(
                chunk_id=chunk_id,
                document_id=doc_id,
                content="test",
                score=0.9,
                page_numbers=None,
            )
        ]

        sparse = [
            MagicMock(
                chunk_id=chunk_id,
                document_id=doc_id,
                content="test",
                score=0.8,
                page_numbers=None,
            )
        ]

        result = fusion.fuse(dense, sparse)
        assert len(result) == 1

    def test_top_n_limit(self):
        config = FusionConfig(k=60, top_n=3)
        fusion = RRFusion(config)

        dense = [
            MagicMock(
                chunk_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                content=f"content {i}",
                score=0.9 - i * 0.1,
                page_numbers=None,
            )
            for i in range(10)
        ]

        result = fusion.fuse(dense, [])
        assert len(result) == 3


class TestFusionService:
    def test_service_returns_fused(self):
        service = FusionService()
        result = service.fuse([], [])
        assert result == []


class TestRankedChunk:
    def test_chunk_creation(self):
        chunk = RankedChunk(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            content="test",
            score=0.9,
            page_numbers=[1, 2],
            source="dense",
        )
        assert chunk.source == "dense"
        assert chunk.page_numbers == [1, 2]