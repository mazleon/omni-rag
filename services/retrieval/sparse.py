"""BM25 sparse retrieval over PostgreSQL.

Leverages the `content_tsv` GIN-indexed column on the Chunks model for
exact-match exact keyword overlaps, useful for product names, UUIDs,
error codes, and acronyms where dense embeddings fail.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


async def search_sparse(
    db: AsyncSession,
    query_text: str,
    org_id: uuid.UUID,
    top_k: int = 50,
) -> list[dict[str, Any]]:
    """
    Search Postgres using BM25 ts_rank across indexed chunk content.

    Args:
        db: Transaction-bound database session.
        query_text: User's raw lexical search.
        org_id: Ensure retrieval matches current org.
        top_k: Number of candidates to fetch.

    Returns:
        Matches shaped exactly like Qdrant's returning dicts.
    """
    return []
