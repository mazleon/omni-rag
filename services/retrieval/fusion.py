"""Reciprocal Rank Fusion (RRF) for interleaving dense + sparse outputs.

Scores chunk occurrences without scaling relative probabilities based on
the mathematical model `k / (k + rank)`, defaulting k=60.
"""

from __future__ import annotations

from typing import Any


def reciprocal_rank_fusion(
    dense_results: list[dict[str, Any]],
    sparse_results: list[dict[str, Any]],
    k: int = 60,
    top_k: int = 50,
) -> list[dict[str, Any]]:
    """
    Fuse two independently scored ranked lists into a single deduplicated sorted list.

    Args:
        dense_results: Qdrant matches ordered by highest vector similarity.
        sparse_results: Postgres BM25 matches ordered by highest ts_rank.
        k: Smoothing constant, lower means rank matters more than magnitude.
        top_k: Limit to return for the heavy cross-encoder path.

    Returns:
        A list of chunk objects, deduplicated by chunk id, scored according to fusion.
    """
    # Phase 1 stub
    return dense_results[:top_k]
