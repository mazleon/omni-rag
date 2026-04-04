import re
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel


class QueryIntent(str, Enum):
    SIMPLE = "simple"
    COMPARATIVE = "comparative"
    EXPLANATORY = "explanatory"
    ANALYTICAL = "analytical"
    FACTUAL = "factual"
    DEFINITIONAL = "definitional"


class QueryComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DocumentTypeFilter(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    IMAGE = "image"
    HTML = "html"
    MARKDOWN = "markdown"


@dataclass
class ExtractedEntity:
    type: str
    value: Any
    raw_text: str


@dataclass
class QueryAnalysis:
    intent: QueryIntent
    complexity: QueryComplexity
    entities: list[ExtractedEntity]
    collection_ids: list[uuid.UUID] | None
    date_range: dict[str, str] | None
    doc_types: list[str] | None
    should_use_agent: bool
    should_rewrite_query: bool
    original_query: str
    rewritten_query: str | None


class QueryAnalyzerConfig(BaseModel):
    complex_keywords: list[str] = [
        "compare", "contrast", "difference between", "similarities between",
        "how does", "why does", "explain how", "what is the relationship",
        "step by step", "walk me through", "analyze", "versus", "vs",
        "advantages", "disadvantages", "pros", "cons", "benefits", "risks",
    ]
    explanatory_keywords: list[str] = [
        "how", "why", "explain", "describe", "demonstrate", "illustrate",
        "show me", "what happens", "what causes", "mechanism",
    ]
    analytical_keywords: list[str] = [
        "analyze", "evaluate", "assess", "review", "examine", "investigate",
        "study", "explore", "determine", "calculate", "compute",
    ]
    definitional_keywords: list[str] = [
        "what is", "what are", "define", "definition", "meaning of",
        "what does", "who is", "who was", "when did",
    ]
    min_complex_query_length: int = 30
    min_questions_for_multi_hop: int = 2


class QueryAnalyzer:
    def __init__(self, config: QueryAnalyzerConfig | None = None) -> None:
        self.config = config or QueryAnalyzerConfig()

    def analyze(self, query: str, collection_ids: list[uuid.UUID] | None = None) -> QueryAnalysis:
        query_lower = query.lower().strip()
        
        intent = self._classify_intent(query_lower)
        complexity = self._score_complexity(query_lower)
        entities = self._extract_entities(query)
        
        date_range = self._extract_date_range(query)
        doc_types = self._extract_doc_types(query_lower)
        
        should_use_agent = self._should_use_agent(query_lower, complexity)
        should_rewrite = self._should_rewrite_query(query_lower, entities)
        
        rewritten_query = None
        if should_rewrite:
            rewritten_query = self._rewrite_query(query, entities)
        
        return QueryAnalysis(
            intent=intent,
            complexity=complexity,
            entities=entities,
            collection_ids=collection_ids,
            date_range=date_range,
            doc_types=doc_types,
            should_use_agent=should_use_agent,
            should_rewrite_query=should_rewrite,
            original_query=query,
            rewritten_query=rewritten_query,
        )

    def _classify_intent(self, query: str) -> QueryIntent:
        if any(kw in query for kw in self.config.complex_keywords):
            return QueryIntent.COMPARATIVE
        if any(kw in query for kw in self.config.explanatory_keywords):
            return QueryIntent.EXPLANATORY
        if any(kw in query for kw in self.config.analytical_keywords):
            return QueryIntent.ANALYTICAL
        if any(kw in query for kw in self.config.definitional_keywords):
            return QueryIntent.DEFINITIONAL
        
        question_words = ["who", "what", "where", "when", "which"]
        if any(query.startswith(qw) for qw in question_words):
            return QueryIntent.FACTUAL
        
        return QueryIntent.SIMPLE

    def _score_complexity(self, query: str) -> QueryComplexity:
        score = 0
        
        if query.count("?") > 1:
            score += 2
        
        if any(kw in query for kw in self.config.complex_keywords):
            score += 2
        if any(kw in query for kw in self.config.analytical_keywords):
            score += 2
        
        if len(query.split()) > self.config.min_complex_query_length:
            score += 1
        
        comparative_patterns = [
            r"\b(?:vs|versus|compared to)\b",
            r"\b(?:or|and)\b.*\?",
            r"\b(?:first|then|finally)\b",
        ]
        for pattern in comparative_patterns:
            if re.search(pattern, query):
                score += 1
        
        if score >= 4:
            return QueryComplexity.HIGH
        if score >= 2:
            return QueryComplexity.MEDIUM
        return QueryComplexity.LOW

    def _extract_entities(self, query: str) -> list[ExtractedEntity]:
        entities: list[ExtractedEntity] = []
        
        date_patterns = [
            (r"\b(\d{4}-\d{2}-\d{2})\b", "date"),
            (r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b", "date"),
            (r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,4}\b", "date"),
            (r"\bQ[1-4]\s*\d{4}\b", "quarter"),
            (r"\b\d{4}\b", "year"),
        ]
        
        for pattern, entity_type in date_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                entities.append(ExtractedEntity(
                    type=entity_type,
                    value=match,
                    raw_text=match,
                ))
        
        return entities

    def _extract_date_range(self, query: str) -> dict[str, str] | None:
        patterns = {
            "from": r"(?:from|between)\s+(\d{4}-\d{2}-\d{2})",
            "to": r"(?:to|until)\s+(\d{4}-\d{2}-\d{2})",
        }
        
        date_range = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                date_range[key] = match.group(1)
        
        return date_range if date_range else None

    def _extract_doc_types(self, query: str) -> list[str] | None:
        doc_type_map = {
            "pdf": [r"\bpdf\b", r"\b\.pdf\b"],
            "docx": [r"\bdocx?\b", r"\bdocument\b"],
            "pptx": [r"\bpptx?\b", r"\bslides?\b", r"\bpresentation\b"],
            "xlsx": [r"\bxlsx?\b", r"\bspreadsheet\b", r"\bexcel\b"],
            "image": [r"\bimage\b", r"\bphoto\b", r"\bpicture\b"],
            "html": [r"\bhtml?\b", r"\bweb\s*page\b"],
        }
        
        found_types = []
        for doc_type, patterns in doc_type_map.items():
            if any(re.search(p, query) for p in patterns):
                found_types.append(doc_type)
        
        return found_types if found_types else None

    def _should_use_agent(self, query: str, complexity: QueryComplexity) -> bool:
        if complexity == QueryComplexity.HIGH:
            return True
        
        if query.count("?") > 1:
            return True
        
        multi_hop_indicators = [
            "first", "then", "also", "additionally", "furthermore",
            "next", "finally", "after that",
        ]
        if any(ind in query for ind in multi_hop_indicators):
            return True
        
        return False

    def _should_rewrite_query(self, query: str, entities: list[ExtractedEntity]) -> bool:
        if len(query.split()) < 5:
            return True
        
        if any(e.type == "year" for e in entities) and len(query.split()) < 10:
            return True
        
        return False

    def _rewrite_query(self, query: str, entities: list[ExtractedEntity]) -> str:
        rewritten = query
        
        for entity in entities:
            if entity.type == "quarter":
                quarter = entity.value.upper()
                year_match = re.search(r"\d{4}", quarter)
                if year_match:
                    q_num = quarter[1]
                    year = year_match.group()
                    q_map = {"1": "first", "2": "second", "3": "third", "4": "fourth"}
                    rewritten = rewritten.replace(
                        entity.raw_text,
                        f"the {q_map.get(q_num, q_num)} quarter of {year}",
                    )
        
        return rewritten


class QueryAnalyzerService:
    def __init__(self) -> None:
        self._analyzer = QueryAnalyzer()

    def analyze(
        self,
        query: str,
        collection_ids: list[uuid.UUID] | None = None,
    ) -> QueryAnalysis:
        return self._analyzer.analyze(query, collection_ids)


def get_query_analyzer_service() -> QueryAnalyzerService:
    return QueryAnalyzerService()
