"""Integration tests for the ingestion pipeline.

Tests the full path: ingest job → parse → chunk → embed → Qdrant upsert → DB insert.
Calls process_ingest_job directly (bypasses Arq queue) to keep tests synchronous.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from core.models import Chunk, Document, DocumentStatus, Org, User


@pytest.mark.integration
@pytest.mark.asyncio
class TestIngestionPipeline:
    async def test_ingest_job_creates_chunks_in_db(
        self,
        session_factory,
        test_org: dict,
        qdrant_client,
    ):
        """Full ingest job run: document → chunks in DB and vectors in Qdrant."""
        from apps.worker.jobs.ingest import IngestJobInput, process_ingest_job

        org_id = test_org["org_id"]
        user_id = test_org["user_id"]
        document_id = uuid.uuid4()
        file_path = f"documents/{org_id}/test_doc.pdf"

        # Seed Document row in PENDING state
        async with session_factory() as session:
            doc = Document(
                id=document_id,
                org_id=org_id,
                user_id=user_id,
                filename="test_doc.pdf",
                file_path=file_path,
                file_size=1024,
                mime_type="application/pdf",
                content_hash=f"hash_{uuid.uuid4().hex}",
                status=DocumentStatus.PENDING,
            )
            session.add(doc)
            await session.commit()

        sample_text = (
            "This is the first section of the test document. "
            "It contains information about enterprise RAG systems. " * 10
            + "The second section describes retrieval methods including dense and sparse search. " * 10
        )

        mock_parsed = MagicMock()
        mock_parsed.document_id = document_id
        mock_parsed.text = sample_text
        mock_parsed.num_pages = 1
        mock_parsed.elements = []
        mock_parsed.content_hash = f"hash_{uuid.uuid4().hex}"
        mock_parsed.metadata = {}

        mock_chunk = MagicMock()
        mock_chunk.chunk_id = uuid.uuid4()
        mock_chunk.chunk_index = 0
        mock_chunk.content = sample_text[:200]
        mock_chunk.content_hash = uuid.uuid4().hex
        mock_chunk.page_numbers = [1]
        mock_chunk.section = "Introduction"

        mock_embedding_result = MagicMock()
        mock_embedding_result.chunk_id = mock_chunk.chunk_id
        mock_embedding_result.embedding = [0.1] * 1024

        with (
            patch("apps.worker.jobs.ingest.get_storage_service") as mock_storage_factory,
            patch("apps.worker.jobs.ingest.get_parser_service") as mock_parser_factory,
            patch("apps.worker.jobs.ingest.get_chunker_service") as mock_chunker_factory,
            patch("apps.worker.jobs.ingest.get_embedder_service") as mock_embedder_factory,
            patch("apps.worker.jobs.ingest.AsyncQdrantClient") as mock_qdrant_cls,
        ):
            mock_storage = AsyncMock()
            mock_storage.download_file.return_value = b"fake pdf content"
            mock_storage_factory.return_value = mock_storage

            mock_parser = AsyncMock()
            mock_parser.parse_document.return_value = mock_parsed
            mock_parser_factory.return_value = mock_parser

            mock_chunker = MagicMock()
            mock_chunker.chunk.return_value = [mock_chunk]
            mock_chunker_factory.return_value = mock_chunker

            mock_embedder = AsyncMock()
            mock_embedder.embed_document_chunks.return_value = [mock_embedding_result]
            mock_embedder_factory.return_value = mock_embedder

            mock_qdrant = AsyncMock()
            mock_qdrant.collection_exists.return_value = False
            mock_qdrant_cls.return_value = mock_qdrant

            input_data = IngestJobInput(
                document_id=document_id,
                org_id=org_id,
                user_id=user_id,
                file_path=file_path,
            )

            result = await process_ingest_job({}, input_data)

        assert result.status == "completed", f"Expected completed, got {result.status}: {result.error}"
        assert result.num_chunks == 1
        assert result.document_id == document_id

        # Verify DB state
        async with session_factory() as session:
            doc_result = await session.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = doc_result.scalar_one()
            assert doc.status == DocumentStatus.COMPLETED
            assert doc.num_chunks == 1

            chunk_result = await session.execute(
                select(Chunk).where(Chunk.document_id == document_id)
            )
            chunks = chunk_result.scalars().all()
            assert len(chunks) == 1
            assert chunks[0].org_id == org_id
            assert chunks[0].vector_id is not None

        # Verify Qdrant upsert was called
        mock_qdrant.create_collection.assert_called_once()
        mock_qdrant.upsert.assert_called_once()
        upsert_args = mock_qdrant.upsert.call_args
        assert upsert_args.kwargs["collection_name"] == f"chunks_{org_id}"
        assert len(upsert_args.kwargs["points"]) == 1

    async def test_ingest_job_deduplicates_chunks(
        self,
        session_factory,
        test_org: dict,
    ):
        """Re-running ingest on same document must skip already-indexed chunks."""
        from apps.worker.jobs.ingest import IngestJobInput, process_ingest_job

        org_id = test_org["org_id"]
        user_id = test_org["user_id"]
        document_id = uuid.uuid4()
        existing_hash = uuid.uuid4().hex

        async with session_factory() as session:
            doc = Document(
                id=document_id,
                org_id=org_id,
                user_id=user_id,
                filename="reprocess_doc.pdf",
                file_path=f"documents/{org_id}/reprocess_doc.pdf",
                file_size=512,
                mime_type="application/pdf",
                content_hash=f"hash_{uuid.uuid4().hex}",
                status=DocumentStatus.PENDING,
            )
            session.add(doc)

            existing_chunk = Chunk(
                id=uuid.uuid4(),
                document_id=document_id,
                org_id=org_id,
                chunk_index=0,
                content="Already indexed content",
                content_hash=existing_hash,
                vector_id=str(uuid.uuid4()),
            )
            session.add(existing_chunk)
            await session.commit()

        mock_parsed = MagicMock()
        mock_parsed.document_id = document_id
        mock_parsed.text = "Already indexed content"
        mock_parsed.num_pages = 1
        mock_parsed.elements = []

        # Chunk with same hash as existing DB chunk
        mock_chunk = MagicMock()
        mock_chunk.chunk_id = uuid.uuid4()
        mock_chunk.chunk_index = 0
        mock_chunk.content = "Already indexed content"
        mock_chunk.content_hash = existing_hash
        mock_chunk.page_numbers = [1]
        mock_chunk.section = None

        mock_embedding_result = MagicMock()
        mock_embedding_result.chunk_id = mock_chunk.chunk_id
        mock_embedding_result.embedding = [0.2] * 1024

        with (
            patch("apps.worker.jobs.ingest.get_storage_service") as ms,
            patch("apps.worker.jobs.ingest.get_parser_service") as mp,
            patch("apps.worker.jobs.ingest.get_chunker_service") as mc,
            patch("apps.worker.jobs.ingest.get_embedder_service") as me,
            patch("apps.worker.jobs.ingest.AsyncQdrantClient") as mq,
        ):
            ms.return_value = AsyncMock(download_file=AsyncMock(return_value=b"content"))
            mp.return_value = AsyncMock(parse_document=AsyncMock(return_value=mock_parsed))
            mc.return_value = MagicMock(chunk=MagicMock(return_value=[mock_chunk]))
            me.return_value = AsyncMock(embed_document_chunks=AsyncMock(return_value=[mock_embedding_result]))

            mock_qdrant = AsyncMock()
            mock_qdrant.collection_exists.return_value = True
            mq.return_value = mock_qdrant

            result = await process_ingest_job(
                {},
                IngestJobInput(
                    document_id=document_id,
                    org_id=org_id,
                    user_id=user_id,
                    file_path=f"documents/{org_id}/reprocess_doc.pdf",
                ),
            )

        assert result.status == "completed"
        # Duplicate chunk was skipped — Qdrant upsert must NOT have been called
        mock_qdrant.upsert.assert_not_called()

    async def test_ingest_job_marks_document_failed_on_parse_error(
        self,
        session_factory,
        test_org: dict,
    ):
        """Parser failure should mark document as FAILED with error message."""
        from apps.worker.jobs.ingest import IngestJobInput, process_ingest_job

        org_id = test_org["org_id"]
        document_id = uuid.uuid4()

        async with session_factory() as session:
            doc = Document(
                id=document_id,
                org_id=org_id,
                user_id=test_org["user_id"],
                filename="bad_doc.pdf",
                file_path=f"documents/{org_id}/bad_doc.pdf",
                file_size=0,
                mime_type="application/pdf",
                content_hash=f"hash_{uuid.uuid4().hex}",
                status=DocumentStatus.PENDING,
            )
            session.add(doc)
            await session.commit()

        with (
            patch("apps.worker.jobs.ingest.get_storage_service") as ms,
            patch("apps.worker.jobs.ingest.get_parser_service") as mp,
            patch("apps.worker.jobs.ingest.get_chunker_service"),
            patch("apps.worker.jobs.ingest.get_embedder_service"),
            patch("apps.worker.jobs.ingest.AsyncQdrantClient"),
        ):
            ms.return_value = AsyncMock(download_file=AsyncMock(return_value=b"bad"))
            mp.return_value = AsyncMock(
                parse_document=AsyncMock(side_effect=ValueError("Unsupported format"))
            )

            result = await process_ingest_job(
                {},
                IngestJobInput(
                    document_id=document_id,
                    org_id=org_id,
                    user_id=test_org["user_id"],
                    file_path=f"documents/{org_id}/bad_doc.pdf",
                ),
            )

        assert result.status == "failed"
        assert "Unsupported format" in (result.error or "")

        async with session_factory() as session:
            doc_result = await session.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = doc_result.scalar_one()
            assert doc.status == DocumentStatus.FAILED
            assert doc.error_message is not None
