"""Document parser — Docling (IBM) primary, Tesseract OCR fallback.

Supported input types:
  - PDF  (.pdf)
  - Word (.docx)
  - PowerPoint (.pptx)
  - Excel (.xlsx)
  - Images (.png, .jpg, .jpeg, .tiff, .webp)

Output: ParsedDocument with a list of structured elements, each with
page_number, bounding box, element type (heading/paragraph/table/figure),
and raw text.

Phase 1: interface and data classes defined; Docling call stubbed.
Phase 2: integrate real Docling pipeline + Tesseract fallback.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ElementType(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FIGURE = "figure"
    LIST_ITEM = "list_item"
    CAPTION = "caption"
    FOOTER = "footer"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class DocumentElement:
    """A single layout-aware element extracted from a document."""

    element_type: ElementType
    text: str
    page_number: int | None = None
    bbox: dict[str, float] | None = None       # {x0, y0, x1, y1} normalised 0–1
    confidence: float = 1.0                    # OCR confidence when applicable
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedDocument:
    """Full parse result: ordered list of elements + document-level metadata."""

    source_uri: str                                    # Supabase Storage path
    content_hash: str                                  # SHA-256 of raw bytes
    doc_type: str                                      # pdf|docx|pptx|…
    page_count: int
    file_size_bytes: int
    elements: list[DocumentElement] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Concatenated text of all elements (useful for quick BM25 indexing)."""
        return "\n".join(e.text for e in self.elements if e.text)


SUPPORTED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "image/png",
        "image/jpeg",
        "image/tiff",
        "image/webp",
    }
)


def content_hash(raw_bytes: bytes) -> str:
    """Return the SHA-256 hex digest of raw file bytes (idempotency key)."""
    return hashlib.sha256(raw_bytes).hexdigest()


async def parse_document(
    raw_bytes: bytes,
    source_uri: str,
    doc_type: str | None = None,
) -> ParsedDocument:
    """
    Parse a document from raw bytes into a structured ``ParsedDocument``.

    Phase 1:  Returns a stub with a single paragraph element.
    Phase 2:  Replace with Docling pipeline + Tesseract OCR fallback:

        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        result = converter.convert_bytes(raw_bytes, mime_type=mime)
        # Map result.document.export_to_elements() → DocumentElement list

    Args:
        raw_bytes: Raw bytes of the uploaded file.
        source_uri: Supabase Storage object path (for audit logging).
        doc_type: MIME type hint; inferred from bytes if not provided.

    Returns:
        ParsedDocument
    """
    _hash = content_hash(raw_bytes)
    _type = doc_type or "application/octet-stream"

    # ── Phase 2 TODO ───────────────────────────────────────────────────────
    # from docling.document_converter import DocumentConverter, PipelineOptions
    # options = PipelineOptions(do_ocr=True, do_table_structure=True)
    # converter = DocumentConverter(pipeline_options=options)
    # docling_result = converter.convert_bytes(raw_bytes)
    # elements = _map_docling_elements(docling_result)
    # ─────────────────────────────────────────────────────────────────────

    elements = [
        DocumentElement(
            element_type=ElementType.PARAGRAPH,
            text="[Phase 1 stub] Document content will be extracted in Phase 2.",
            page_number=1,
        )
    ]

    return ParsedDocument(
        source_uri=source_uri,
        content_hash=_hash,
        doc_type=_type,
        page_count=1,
        file_size_bytes=len(raw_bytes),
        elements=elements,
    )
