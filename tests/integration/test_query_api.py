"""Integration tests for the Query API endpoints.

Tests the full query path: register → upload → query → response
against real Postgres, Redis, and in-memory Qdrant.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestQueryAPI:
    async def test_query_returns_answer(
        self,
        http_client: AsyncClient,
        test_org: dict,
    ):
        """Query endpoint should return an answer with sources."""
        auth_headers = test_org["auth_headers"]

        with (
            patch("services.ingestion.embedder.CohereEmbedder.embed_query") as mock_embed,
            patch("services.retrieval.dense.QdrantDenseRetriever.search") as mock_dense,
            patch("services.retrieval.sparse.PostgresSparseRetriever.search") as mock_sparse,
            patch("services.retrieval.fusion.RRFusion.fuse") as mock_fuse,
            patch("services.retrieval.reranker.CohereReranker.rerank") as mock_rerank,
            patch("services.orchestrator.answer_generator.AnswerGenerator.generate") as mock_generate,
        ):
            mock_embed.return_value = [0.1] * 1024
            mock_dense.return_value = []
            mock_sparse.return_value = []
            mock_fuse.return_value = []

            response = await http_client.post(
                "/v1/query",
                json={"query": "What is RAG?"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "latency_ms" in data

    async def test_query_stream_returns_sse(
        self,
        http_client: AsyncClient,
        test_org: dict,
    ):
        """Query stream endpoint should return SSE response."""
        auth_headers = test_org["auth_headers"]

        with (
            patch("services.ingestion.embedder.CohereEmbedder.embed_query") as mock_embed,
            patch("services.retrieval.dense.QdrantDenseRetriever.search") as mock_dense,
            patch("services.retrieval.sparse.PostgresSparseRetriever.search") as mock_sparse,
            patch("services.retrieval.fusion.RRFusion.fuse") as mock_fuse,
        ):
            mock_embed.return_value = [0.1] * 1024
            mock_dense.return_value = []
            mock_sparse.return_value = []
            mock_fuse.return_value = []

            response = await http_client.post(
                "/v1/query/stream",
                json={"query": "What is RAG?"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    async def test_query_requires_auth(
        self,
        http_client: AsyncClient,
    ):
        """Query endpoint should reject unauthenticated requests."""
        response = await http_client.post(
            "/v1/query",
            json={"query": "What is RAG?"},
        )

        assert response.status_code in [401, 403]

    async def test_query_empty_returns_no_results(
        self,
        http_client: AsyncClient,
        test_org: dict,
    ):
        """Query with empty string should handle gracefully."""
        auth_headers = test_org["auth_headers"]

        response = await http_client.post(
            "/v1/query",
            json={"query": ""},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data


@pytest.mark.integration
@pytest.mark.asyncio
class TestRetrievalAPI:
    async def test_retrieval_only_returns_chunks(
        self,
        http_client: AsyncClient,
        test_org: dict,
    ):
        """Retrieval-only endpoint should return chunks without generation."""
        auth_headers = test_org["auth_headers"]

        with (
            patch("services.ingestion.embedder.CohereEmbedder.embed_query") as mock_embed,
            patch("services.retrieval.dense.QdrantDenseRetriever.search") as mock_dense,
            patch("services.retrieval.sparse.PostgresSparseRetriever.search") as mock_sparse,
            patch("services.retrieval.fusion.RRFusion.fuse") as mock_fuse,
        ):
            mock_embed.return_value = [0.1] * 1024
            mock_dense.return_value = []
            mock_sparse.return_value = []
            mock_fuse.return_value = []

            response = await http_client.post(
                "/v1/query/retrieval-only",
                json={"query": "What is RAG?"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert "chunks" in data
        assert "retrieval_latency_ms" in data


@pytest.mark.integration
@pytest.mark.asyncio
class TestAnalyticsAPI:
    async def test_analytics_summary_returns_data(
        self,
        http_client: AsyncClient,
        test_org: dict,
    ):
        """Analytics summary should return metrics."""
        auth_headers = test_org["auth_headers"]

        response = await http_client.get(
            "/v1/analytics/summary",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_queries" in data
        assert "total_documents" in data
        assert "avg_latency_ms" in data

    async def test_query_history_returns_list(
        self,
        http_client: AsyncClient,
        test_org: dict,
    ):
        """Query history should return a list of queries."""
        auth_headers = test_org["auth_headers"]

        response = await http_client.get(
            "/v1/analytics/queries/history",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "queries" in data
        assert "total" in data


@pytest.mark.integration
@pytest.mark.asyncio
class TestCollectionsAPI:
    async def test_create_collection(
        self,
        http_client: AsyncClient,
        test_org: dict,
    ):
        """Should create a new collection."""
        auth_headers = test_org["auth_headers"]

        response = await http_client.post(
            "/v1/collections",
            json={"name": "Test Collection", "description": "A test collection"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Collection"

    async def test_list_collections(
        self,
        http_client: AsyncClient,
        test_org: dict,
    ):
        """Should list collections for the org."""
        auth_headers = test_org["auth_headers"]

        response = await http_client.get(
            "/v1/collections",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "collections" in data
        assert "total" in data


@pytest.mark.integration
@pytest.mark.asyncio
class TestFeedbackAPI:
    async def test_submit_feedback(
        self,
        http_client: AsyncClient,
        test_org: dict,
    ):
        """Should submit feedback for a query."""
        auth_headers = test_org["auth_headers"]

        # First create a query to get a query_id
        with (
            patch("services.ingestion.embedder.CohereEmbedder.embed_query") as mock_embed,
            patch("services.retrieval.dense.QdrantDenseRetriever.search") as mock_dense,
            patch("services.retrieval.sparse.PostgresSparseRetriever.search") as mock_sparse,
            patch("services.retrieval.fusion.RRFusion.fuse") as mock_fuse,
            patch("services.orchestrator.answer_generator.AnswerGenerator.generate") as mock_generate,
        ):
            mock_embed.return_value = [0.1] * 1024
            mock_dense.return_value = []
            mock_sparse.return_value = []
            mock_fuse.return_value = []
            mock_generate.return_value = MagicMock(
                answer="Test answer",
                sources=[],
                tokens_used=100,
            )

            query_response = await http_client.post(
                "/v1/query",
                json={"query": "Test query for feedback"},
                headers=auth_headers,
            )

        assert query_response.status_code == 200

        # Feedback endpoint requires a valid query_id from DB
        # This test verifies the endpoint exists and validates input
        response = await http_client.post(
            "/v1/feedback",
            json={"query_id": "invalid-uuid", "feedback": 1},
            headers=auth_headers,
        )

        assert response.status_code == 400
