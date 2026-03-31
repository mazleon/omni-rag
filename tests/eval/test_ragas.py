from services.evaluation.ragas_runner import run_ragas_eval


def test_offline_ragas_metrics() -> None:
    # Phase 2 TODO: load dataset from tests/eval/golden_dataset.jsonl
    metrics = run_ragas_eval("dummy_path")

    # Assert gating conditions
    assert metrics["faithfulness"] > 0.90
    assert metrics["context_precision"] > 0.82
