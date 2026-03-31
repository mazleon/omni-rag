"""Dense retrieval over Qdrant using Cohere embeddings.

Qdrant architecture note:
  We maintain one Collection per organization using the pattern `chunks_{org_slug}`.
  This provides physical multi-tenant isolation, eliminating the potential for
  cross-org leakage through compromised metadata filters or bad RLS logic.
"""

from __future__ import annotations

from typing import Any


async def search_dense(query_text: str, org_slug: str, top_k: int = 50) -> list[dict[str, Any]]:
    """
    Search Qdrant for the closest semantic chunks.

    Args:
        query_text: User's intent-extracted query string.
        org_slug: Org slug for the isolated Qdrant collection.
        top_k: Number of candidates to retrieve.

    Returns:
        List of dict matches with Qdrant payload and relevancy score.
    """
    return []


async def upsert_chunks(
    embedded_chunks: list[dict[str, Any]],
    org_slug: str,
) -> None:
    """
    Upsert embedded chunk vectors + metadata payload into Qdrant.
    The caller provides the deterministic UUID payload id.
    """
    pass
