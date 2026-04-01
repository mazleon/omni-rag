import uuid
from typing import Any

from pydantic import BaseModel


class Chunk(BaseModel):
    chunk_id: uuid.UUID
    chunk_index: int
    content: str
    content_hash: str
    page_numbers: list[int]
    section: str | None


class ChunkerConfig(BaseModel):
    max_tokens: int = 512
    overlap_percent: float = 0.15
    min_chunk_length: int = 50


class SemanticChunker:
    def __init__(self, config: ChunkerConfig | None = None) -> None:
        self.config = config or ChunkerConfig()

    def chunk_document(
        self,
        text: str,
        document_id: uuid.UUID,
        elements: list[dict[str, Any]],
    ) -> list[Chunk]:
        if not text.strip():
            return []

        structured_chunks = self._split_by_layout(text, elements)
        semantic_chunks = self._merge_with_overlap(structured_chunks)

        chunks: list[Chunk] = []
        for idx, chunk_text in enumerate(semantic_chunks):
            content_hash = self._compute_hash(chunk_text)
            chunk = Chunk(
                chunk_id=uuid.uuid4(),
                chunk_index=idx,
                content=chunk_text,
                content_hash=content_hash,
                page_numbers=self._extract_page_numbers(chunk_text, elements),
                section=self._extract_section(chunk_text),
            )
            chunks.append(chunk)

        return chunks

    def _split_by_layout(self, text: str, elements: list[dict[str, Any]]) -> list[str]:
        sections: list[str] = []
        current_section: list[str] = []
        current_heading = "intro"

        for element in elements:
            text = element.get("text", "")
            element_type = element.get("type", "")

            if not text.strip():
                continue

            if "Header" in element_type or "Title" in element_type:
                if current_section:
                    sections.append("\n".join(current_section))
                current_heading = text[:50]
                current_section = [f"## {text}"]
            elif "Table" in element_type:
                if current_section:
                    sections.append("\n".join(current_section))
                sections.append(f"[Table: {text[:200]}...]")
                current_section = []
            else:
                current_section.append(text)

        if current_section:
            sections.append("\n".join(current_section))

        if not sections:
            return [text] if text.strip() else []
        return sections

    def _merge_with_overlap(self, sections: list[str]) -> list[str]:
        if not sections:
            return []

        if len(sections) == 1:
            return self._split_into_chunks(sections[0])

        merged: list[str] = []
        for i, section in enumerate(sections):
            if i > 0 and sections[i - 1]:
                overlap_text = sections[i - 1][-200:]
                section = overlap_text + "\n\n" + section

            chunked = self._split_into_chunks(section)
            merged.extend(chunked)

        return merged

    def _split_into_chunks(self, text: str) -> list[str]:
        words = text.split()
        if len(words) < self.config.min_chunk_length:
            return [text] if text.strip() else []

        max_words = self.config.max_tokens * 0.75
        chunks: list[str] = []
        current: list[str] = []

        for word in words:
            current.append(word)
            if len(current) >= max_words:
                chunks.append(" ".join(current))
                overlap_count = int(len(current) * self.config.overlap_percent)
                current = current[-overlap_count:] if overlap_count > 0 else []

        if current:
            chunks.append(" ".join(current))

        return chunks if chunks else [text]

    def _compute_hash(self, text: str) -> str:
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()

    def _extract_page_numbers(self, chunk_text: str, elements: list[dict[str, Any]]) -> list[int]:
        page_nums = set()
        for element in elements:
            if element.get("text", "") in chunk_text:
                if page := element.get("page"):
                    page_nums.add(page)
        return sorted(list(page_nums)[:3])

    def _extract_section(self, chunk_text: str) -> str | None:
        lines = chunk_text.split("\n")
        for line in lines:
            if line.startswith("## "):
                return line.replace("## ", "").strip()[:100]
        return None


class ChunkerService:
    def __init__(self, config: ChunkerConfig | None = None) -> None:
        self._chunker = SemanticChunker(config)

    def chunk(
        self,
        text: str,
        document_id: uuid.UUID,
        elements: list[dict[str, Any]],
    ) -> list[Chunk]:
        return self._chunker.chunk_document(text, document_id, elements)


def get_chunker_service() -> ChunkerService:
    return ChunkerService()