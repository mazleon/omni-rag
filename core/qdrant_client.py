"""Qdrant async client singleton with collection management helpers."""

from __future__ import annotations

from functools import lru_cache

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    HnswConfigDiff,
    OptimizersConfigDiff,
    PayloadSchemaType,
    VectorParams,
)

from core.config import settings
from core.logging import get_logger

log = get_logger(__name__)


@lru_cache
def get_qdrant_client() -> AsyncQdrantClient:
    """Return a cached async Qdrant client. Call once at startup."""
    return AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
        prefer_grpc=settings.qdrant_prefer_grpc,
        grpc_port=settings.qdrant_grpc_port,
    )


async def ensure_org_collection(org_slug: str) -> str:
    """
    Idempotently create the Qdrant collection for an org if it doesn't exist.
    Returns the collection name.
    """
    collection_name = settings.qdrant_collection_for_org(org_slug)
    client = get_qdrant_client()

    existing = {c.name for c in (await client.get_collections()).collections}
    if collection_name in existing:
        log.info("qdrant.collection.exists", collection=collection_name)
        return collection_name

    await client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=settings.qdrant_vector_size,
            distance=Distance.COSINE,
            on_disk=True,             # keep index on disk, load on demand
        ),
        hnsw_config=HnswConfigDiff(
            m=16,                     # connections per node
            ef_construct=200,         # build-time accuracy
            full_scan_threshold=10_000,
        ),
        optimizers_config=OptimizersConfigDiff(
            default_segment_number=4,
        ),
    )

    # Create payload indices required for filtered search performance
    payload_indices: dict[str, PayloadSchemaType] = {
        "document_id": PayloadSchemaType.KEYWORD,
        "modality": PayloadSchemaType.KEYWORD,
        "doc_type": PayloadSchemaType.KEYWORD,
        "created_at_epoch": PayloadSchemaType.INTEGER,
    }
    for field, schema_type in payload_indices.items():
        await client.create_payload_index(
            collection_name=collection_name,
            field_name=field,
            field_schema=schema_type,
        )

    log.info("qdrant.collection.created", collection=collection_name)
    return collection_name


async def delete_org_collection(org_slug: str) -> None:
    """Drop an org's entire Qdrant collection (used when org is deleted)."""
    collection_name = settings.qdrant_collection_for_org(org_slug)
    client = get_qdrant_client()
    await client.delete_collection(collection_name)
    log.info("qdrant.collection.deleted", collection=collection_name)


async def health_check() -> bool:
    """Return True if Qdrant is reachable."""
    try:
        client = get_qdrant_client()
        await client.get_collections()
        return True
    except Exception:
        return False
