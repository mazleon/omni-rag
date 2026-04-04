from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db import async_session_factory
from core.logging import get_logger
from core.models import Chunk, Document, DocumentStatus
from services.ingestion.chunker import get_chunker_service
from services.ingestion.embedder import get_embedder_service
from services.ingestion.parser import get_parser_service
from services.storage import get_storage_service

log = get_logger(__name__)


class IngestJobInput(BaseModel):
    document_id: uuid.UUID
    org_id: uuid.UUID
    user_id: uuid.UUID
    file_path: str
    collection_id: uuid.UUID | None = None


class IngestJobResult(BaseModel):
    document_id: uuid.UUID
    num_chunks: int
    status: str
    error: str | None = None


async def process_ingest_job(ctx: dict[str, Any], input_data: IngestJobInput | dict[str, Any]) -> IngestJobResult:
    if isinstance(input_data, dict):
        input_data = IngestJobInput(**input_data)
    parser_svc = get_parser_service()
    chunker_svc = get_chunker_service()
    embedder_svc = get_embedder_service()
    storage_svc = get_storage_service()

    async with async_session_factory() as session:
        document: Document | None = None

        try:
            doc_result = await session.execute(
                select(Document).where(Document.id == input_data.document_id)
            )
            document = doc_result.scalar_one_or_none()
            if not document:
                log.error("ingest.document_not_found", document_id=str(input_data.document_id))
                return IngestJobResult(
                    document_id=input_data.document_id,
                    num_chunks=0,
                    status="failed",
                    error="Document not found",
                )

            document.status = DocumentStatus.PROCESSING
            await session.commit()

            log.info("ingest.started", document_id=str(input_data.document_id))

            file_content = await storage_svc.download_file(input_data.file_path)

            parsed = await parser_svc.parse_document(input_data.file_path, file_content)

            chunks_data = chunker_svc.chunk(
                text=parsed.text,
                document_id=parsed.document_id,
                elements=parsed.elements,
            )

            chunk_dicts = [
                {
                    "chunk_id": c.chunk_id,
                    "chunk_index": c.chunk_index,
                    "content": c.content,
                    "content_hash": c.content_hash,
                    "page_numbers": c.page_numbers,
                    "section": c.section,
                }
                for c in chunks_data
            ]

            embeddings = await embedder_svc.embed_document_chunks(chunk_dicts)

            embedding_map = {e.chunk_id: e.embedding for e in embeddings}

            qdrant = AsyncQdrantClient(url=settings.QDRANT_URL)
            collection_name = f"chunks_{input_data.org_id}"

            try:
                collection_exists = await qdrant.collection_exists(collection_name)
                if not collection_exists:
                    await qdrant.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                    )
                    log.info("ingest.qdrant_collection_created", collection_name=collection_name)
            except Exception as e:
                if "already exists" not in str(e):
                    raise
                log.info("ingest.qdrant_collection_exists", collection_name=collection_name)

            # Idempotency: fetch existing chunk hashes for this document to skip duplicates
            existing_hashes_result = await session.execute(
                select(Chunk.content_hash).where(Chunk.document_id == document.id)
            )
            existing_hashes = {row[0] for row in existing_hashes_result.fetchall()}

            points = []
            for chunk in chunks_data:
                if chunk.content_hash in existing_hashes:
                    log.debug(
                        "ingest.chunk_skipped_duplicate",
                        content_hash=chunk.content_hash,
                    )
                    continue

                chunk_db = Chunk(
                    id=chunk.chunk_id,
                    document_id=document.id,
                    org_id=input_data.org_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    content_hash=chunk.content_hash,
                    page_numbers=",".join(map(str, chunk.page_numbers)) if chunk.page_numbers else None,
                    section=chunk.section,
                    vector_id=str(chunk.chunk_id),
                )
                session.add(chunk_db)

                embedding = embedding_map.get(chunk.chunk_id)
                if embedding:
                    points.append({
                        "id": str(chunk.chunk_id),
                        "vector": embedding,
                        "payload": {
                            "document_id": str(document.id),
                            "org_id": str(input_data.org_id),
                            "chunk_index": chunk.chunk_index,
                            "content": chunk.content[:500],
                            "content_hash": chunk.content_hash,
                        },
                    })

            if points:
                await qdrant.upsert(
                    collection_name=collection_name,
                    points=points,
                )

            document.num_chunks = len(chunks_data)
            document.status = DocumentStatus.COMPLETED
            document.num_pages = parsed.num_pages
            document.processed_at = datetime.now(timezone.utc).replace(tzinfo=None)

            await session.commit()

            log.info(
                "ingest.completed",
                document_id=str(input_data.document_id),
                num_chunks=len(chunks_data),
            )

            return IngestJobResult(
                document_id=input_data.document_id,
                num_chunks=len(chunks_data),
                status="completed",
            )

        except Exception as e:
            log.error(
                "ingest.failed",
                document_id=str(input_data.document_id),
                error=str(e),
            )
            try:
                if document:
                    document.status = DocumentStatus.FAILED
                    document.error_message = str(e)[:500]
                    await session.commit()
            except Exception:
                pass

            return IngestJobResult(
                document_id=input_data.document_id,
                num_chunks=0,
                status="failed",
                error=str(e),
            )
