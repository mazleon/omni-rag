import hashlib
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.ingestion.chunker import ChunkerService, SemanticChunker, ChunkerConfig
from services.ingestion.chunker import Chunk


class TestSemanticChunker:
    def test_chunk_text_basic(self):
        config = ChunkerConfig(max_tokens=100, overlap_percent=0.15)
        chunker = SemanticChunker(config)
        
        text = "This is a test document. " * 20
        doc_id = uuid.uuid4()
        
        chunks = chunker.chunk_document(text, doc_id, [])
        
        assert len(chunks) > 0
        assert all(isinstance(c, Chunk) for c in chunks)
        assert all(c.content for c in chunks)

    def test_empty_text_returns_empty(self):
        chunker = SemanticChunker()
        doc_id = uuid.uuid4()
        
        chunks = chunker.chunk_document("", doc_id, [])
        
        assert chunks == []

    def test_content_hash_unique(self):
        chunker = SemanticChunker()
        doc_id = uuid.uuid4()
        
        chunk1 = chunker.chunk_document("Hello world", doc_id, [])[0]
        chunk2 = chunker.chunk_document("Hello world", doc_id, [])[0]
        
        assert chunk1.content_hash == chunk2.content_hash
        
        chunk3 = chunker.chunk_document("Different text", doc_id, [])[0]
        assert chunk1.content_hash != chunk3.content_hash

    def test_overlap_injection(self):
        config = ChunkerConfig(max_tokens=20, overlap_percent=0.2)
        chunker = SemanticChunker(config)
        
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence. Sixth sentence. Seventh sentence."
        doc_id = uuid.uuid4()
        
        chunks = chunker.chunk_document(text, doc_id, [])
        
        assert len(chunks) >= 1

    def test_layout_based_splitting(self):
        chunker = SemanticChunker()
        doc_id = uuid.uuid4()
        
        elements = [
            {"text": "Introduction", "type": "Header", "page": 1},
            {"text": "This is the intro text", "type": "Text", "page": 1},
            {"text": "Results", "type": "Header", "page": 2},
            {"text": "The results are...", "type": "Text", "page": 2},
        ]
        
        chunks = chunker.chunk_document("Introduction\nThis is the intro text\nResults\nThe results are...", doc_id, elements)
        
        assert len(chunks) >= 1
        sections = [c.section for c in chunks if c.section]
        assert "Introduction" in sections or "Results" in sections


class TestChunkerService:
    def test_service_returns_chunks(self):
        service = ChunkerService()
        doc_id = uuid.uuid4()
        
        chunks = service.chunk("Test content here", doc_id, [])
        
        assert isinstance(chunks, list)
        assert all(isinstance(c, Chunk) for c in chunks)


class TestChunkModel:
    def test_chunk_fields(self):
        chunk = Chunk(
            chunk_id=uuid.uuid4(),
            chunk_index=0,
            content="Test content",
            content_hash="abc123",
            page_numbers=[1, 2],
            section="Introduction"
        )
        
        assert chunk.chunk_index == 0
        assert chunk.content == "Test content"
        assert chunk.page_numbers == [1, 2]
        assert chunk.section == "Introduction"