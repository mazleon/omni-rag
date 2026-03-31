"""Reciprocal Rank Fusion (RRF) for merging dense + sparse retrieval outputs.

Theory
------
RRF scores a document d across N ranked lists as:

    RRF(d) = Σ_i  1 / (k + rank_i(d))

where k=60 is the smoothing constant that controls how much rank matters
relative to magnitude. k=60 was empirically validated by Cormack et al. (2009)
and remains the standard default.

Why RRF over linear combination?
- Dense similarity scores and BM25 scores live on incomparable scales.
- Linear combination requires tuned weights that are corpus-dependent.
- RRF only cares about rank order, making it corpus-agnostic and robust.
"""

from __future__ import annotations

from typing import Any


def reciprocal_rank_fusion(
    dense_results: list[dict[str, Any]],
    sparse_results: list[dict[str, Any]],
    k: int = 60,
    top_k: int = 50,
    id_field: str = "chunk_id",
) -> list[dict[str, Any]]:
    """
    Fuse two independently ranked lists into a single deduplicated ranked list.

    Each item in both lists must contain ``id_field`` (default: ``chunk_id``).
    The function preserves all payload fields from whichever list first provided
    the item, so downstream rerankers have full context.

    Args:
        dense_results:  Qdrant matches sorted by vector similarity (highest first).
        sparse_results: Postgres BM25 matches sorted by ts_rank (highest first).
        k:              RRF smoothing constant. Lower = rank matters more.
        top_k:          Maximum candidates to return (pre-reranking pool size).
        id_field:       Key used to deduplicate items across lists.

    Returns:
        Deduplicated list sorted by descending RRF score, capped at ``top_k``.
    """
    scores: dict[str, float] = {}
    payloads: dict[str, dict[str, Any]] = {}

    def _accumulate(ranked_list: list[dict[str, Any]]) -> None:
        for rank, item in enumerate(ranked_list, start=1):
            doc_id = str(item[id_field])
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
            if doc_id not in payloads:
                payloads[doc_id] = item

    _accumulate(dense_results)
    _accumulate(sparse_results)

    sorted_ids = sorted(scores, key=lambda d: scores[d], reverse=True)

    results = []
    for doc_id in sorted_ids[:top_k]:
        item = dict(payloads[doc_id])
        item["rrf_score"] = round(scores[doc_id], 6)
        results.append(item)

    return results


def rrf_score(rank: int, k: int = 60) -> float:
    """Return the RRF contribution of a single document at the given rank."""
    return 1.0 / (k + rank)
