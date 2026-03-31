"""Unit tests for RRF fusion — the only retrieval component with pure logic."""

import pytest

from services.retrieval.fusion import reciprocal_rank_fusion, rrf_score


def _chunk(chunk_id: str, score: float = 1.0) -> dict:
    return {"chunk_id": chunk_id, "content": f"text for {chunk_id}", "score": score}


# ── rrf_score ─────────────────────────────────────────────────────────────────

def test_rrf_score_rank_1_k60() -> None:
    assert rrf_score(1, k=60) == pytest.approx(1 / 61)


def test_rrf_score_rank_1_beats_rank_2() -> None:
    assert rrf_score(1) > rrf_score(2)


def test_rrf_score_always_positive() -> None:
    for rank in range(1, 100):
        assert rrf_score(rank) > 0


# ── reciprocal_rank_fusion ────────────────────────────────────────────────────

def test_fusion_deduplicates_overlap() -> None:
    dense = [_chunk("a"), _chunk("b"), _chunk("c")]
    sparse = [_chunk("b"), _chunk("c"), _chunk("d")]
    result = reciprocal_rank_fusion(dense, sparse)
    ids = [r["chunk_id"] for r in result]
    assert len(ids) == len(set(ids)), "Duplicate chunk_ids found in fused output"


def test_fusion_item_appearing_in_both_lists_ranks_higher() -> None:
    """A chunk in both lists must outscore one that appears in only one."""
    dense = [_chunk("shared"), _chunk("dense_only")]
    sparse = [_chunk("shared"), _chunk("sparse_only")]
    result = reciprocal_rank_fusion(dense, sparse)
    ids = [r["chunk_id"] for r in result]
    assert ids[0] == "shared", "Chunk in both lists should rank first"


def test_fusion_preserves_rrf_score_field() -> None:
    dense = [_chunk("a"), _chunk("b")]
    sparse = [_chunk("b"), _chunk("c")]
    result = reciprocal_rank_fusion(dense, sparse)
    for item in result:
        assert "rrf_score" in item
        assert isinstance(item["rrf_score"], float)
        assert item["rrf_score"] > 0


def test_fusion_respects_top_k() -> None:
    dense = [_chunk(f"d{i}") for i in range(30)]
    sparse = [_chunk(f"s{i}") for i in range(30)]
    result = reciprocal_rank_fusion(dense, sparse, top_k=10)
    assert len(result) <= 10


def test_fusion_empty_dense_returns_sparse_order() -> None:
    sparse = [_chunk("x"), _chunk("y"), _chunk("z")]
    result = reciprocal_rank_fusion([], sparse)
    ids = [r["chunk_id"] for r in result]
    assert ids == ["x", "y", "z"]


def test_fusion_empty_both_returns_empty() -> None:
    assert reciprocal_rank_fusion([], []) == []


def test_fusion_scores_descending() -> None:
    dense = [_chunk(f"d{i}") for i in range(10)]
    sparse = [_chunk(f"s{i}") for i in range(10)]
    result = reciprocal_rank_fusion(dense, sparse)
    scores = [r["rrf_score"] for r in result]
    assert scores == sorted(scores, reverse=True)
