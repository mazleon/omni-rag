import pytest
import uuid
from datetime import datetime, timezone


class TestGoldenDatasetService:
    async def add_entry_mock(self):
        class MockEntry:
            def __init__(self):
                self.id = uuid.uuid4()
                self.query = "test query"
                self.ground_truth = "test answer"
                self.contexts = ["context"]
                self.created_at = None
        return MockEntry()

    @pytest.mark.asyncio
    async def test_service_structure(self):
        from services.evaluation.ragas_runner import GoldenDatasetService
        service = GoldenDatasetService()
        assert hasattr(service, "_entries")
        assert service._entries == []


class TestEvaluationInput:
    def test_evaluation_input_creation(self):
        from services.evaluation.ragas_runner import EvaluationInput
        
        entry = EvaluationInput(
            query="test query",
            answer="test answer",
            contexts=["ctx1", "ctx2"],
            ground_truth="ground truth",
        )
        
        assert entry.query == "test query"
        assert entry.answer == "test answer"
        assert len(entry.contexts) == 2
        assert entry.ground_truth == "ground truth"


class TestEvaluationResult:
    def test_evaluation_result_creation(self):
        from services.evaluation.ragas_runner import EvaluationResult
        
        result = EvaluationResult(
            query="test query",
            faithfulness=0.9,
            answer_relevancy=0.85,
            context_precision=0.8,
            context_recall=0.75,
            evaluated_at=datetime.now(timezone.utc),
        )
        
        assert result.query == "test query"
        assert result.faithfulness == 0.9
        assert result.answer_relevancy == 0.85


class TestGoldenDatasetEntry:
    def test_golden_entry_creation(self):
        from services.evaluation.ragas_runner import GoldenDatasetEntry
        
        entry = GoldenDatasetEntry(
            id=uuid.uuid4(),
            query="test query",
            ground_truth="test answer",
            contexts=["ctx1"],
            source_document_id=None,
            created_at=datetime.now(timezone.utc),
        )
        
        assert entry.query == "test query"
        assert entry.ground_truth == "test answer"
        assert len(entry.contexts) == 1