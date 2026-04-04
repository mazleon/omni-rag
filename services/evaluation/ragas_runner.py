from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel


class EvaluationInput(BaseModel):
    query: str
    answer: str
    contexts: list[str]
    ground_truth: str


class EvaluationResult(BaseModel):
    query: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    evaluated_at: datetime


class GoldenDatasetEntry(BaseModel):
    id: uuid.UUID
    query: str
    ground_truth: str
    contexts: list[str]
    source_document_id: uuid.UUID | None = None
    created_at: datetime


class RAGASRunner:
    def __init__(self) -> None:
        pass

    async def evaluate_single(
        self,
        query: str,
        answer: str,
        contexts: list[str],
        ground_truth: str,
    ) -> EvaluationResult:
        from core.config import settings

        if not settings.OPENROUTER_API_KEY:
            return EvaluationResult(
                query=query,
                faithfulness=0.0,
                answer_relevancy=0.0,
                context_precision=0.0,
                context_recall=0.0,
                evaluated_at=datetime.now(timezone.utc),
            )

        try:
            from ragas import evaluate
            from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
            from datasets import Dataset

            dataset = Dataset.from_dict({
                "question": [query],
                "answer": [answer],
                "contexts": [contexts],
                "ground_truth": [ground_truth],
            })

            result = evaluate(
                dataset=dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall,
                ],
            )

            scores = result.to_pandas().iloc[0]

            return EvaluationResult(
                query=query,
                faithfulness=float(scores["faithfulness"]),
                answer_relevancy=float(scores["answer_relevancy"]),
                context_precision=float(scores["context_precision"]),
                context_recall=float(scores["context_recall"]),
                evaluated_at=datetime.now(timezone.utc),
            )
        except Exception:
            return EvaluationResult(
                query=query,
                faithfulness=0.0,
                answer_relevancy=0.0,
                context_precision=0.0,
                context_recall=0.0,
                evaluated_at=datetime.now(timezone.utc),
            )

    async def evaluate_batch(
        self,
        entries: list[EvaluationInput],
    ) -> list[EvaluationResult]:
        results = []
        for entry in entries:
            result = await self.evaluate_single(
                entry.query,
                entry.answer,
                entry.contexts,
                entry.ground_truth,
            )
            results.append(result)
        return results


class GoldenDatasetService:
    def __init__(self) -> None:
        self._entries: list[GoldenDatasetEntry] = []

    async def add_entry(
        self,
        query: str,
        ground_truth: str,
        contexts: list[str],
        source_document_id: uuid.UUID | None = None,
    ) -> GoldenDatasetEntry:
        entry = GoldenDatasetEntry(
            id=uuid.uuid4(),
            query=query,
            ground_truth=ground_truth,
            contexts=contexts,
            source_document_id=source_document_id,
            created_at=datetime.now(timezone.utc),
        )
        self._entries.append(entry)
        return entry

    async def get_entries(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GoldenDatasetEntry]:
        return self._entries[offset : offset + limit]

    async def get_by_id(self, entry_id: uuid.UUID) -> GoldenDatasetEntry | None:
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None

    async def delete_entry(self, entry_id: uuid.UUID) -> bool:
        for i, entry in enumerate(self._entries):
            if entry.id == entry_id:
                self._entries.pop(i)
                return True
        return False


_ragas_runner = RAGASRunner()
_golden_dataset_service = GoldenDatasetService()


def get_ragas_runner() -> RAGASRunner:
    return _ragas_runner


def get_golden_dataset_service() -> GoldenDatasetService:
    return _golden_dataset_service
