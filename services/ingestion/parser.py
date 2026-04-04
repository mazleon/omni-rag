from __future__ import annotations

import hashlib
import io
import uuid
from pathlib import Path
from typing import Any

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.io import DocumentStream
from pydantic import BaseModel

from core.logging import get_logger

log = get_logger(__name__)


class ParsedDocument(BaseModel):
    document_id: uuid.UUID
    content_hash: str
    text: str
    num_pages: int
    elements: list[dict[str, Any]]
    metadata: dict[str, Any]


class DocumentParser:
    def __init__(self) -> None:
        pipeline_options = PdfPipelineOptions(
            do_ocr=True,
            do_table_structure=True,
        )
        self._converter = DocumentConverter(
            format_options={
                "pdf": PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    async def parse(
        self,
        file_path: str,
        file_content: bytes,
    ) -> ParsedDocument:
        content_hash = hashlib.sha256(file_content).hexdigest()
        doc_id = uuid.uuid4()

        ext = Path(file_path).suffix.lower()

        if ext in (".pdf",):
            result = await self._convert_pdf(file_content)
        elif ext in (".docx", ".doc"):
            result = await self._convert_docx(file_content)
        elif ext in (".pptx", ".ppt"):
            result = await self._convert_pptx(file_content)
        elif ext in (".xlsx", ".xls"):
            result = await self._convert_xlsx(file_content)
        elif ext in (".html", ".htm"):
            result = await self._convert_html(file_content)
        elif ext in (".md", ".markdown"):
            result = await self._convert_markdown(file_content)
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"):
            result = await self._convert_image(file_content)
        else:
            result = await self._convert_pdf(file_content)

        text_parts: list[str] = []
        elements: list[dict[str, Any]] = []

        doc = result.document

        for text_item in doc.texts:
            text_str = text_item.text.strip() if hasattr(text_item, "text") else ""
            if text_str:
                text_parts.append(text_str)
                elem_type = type(text_item).__name__.replace("Item", "").lower()
                page_num = None
                if hasattr(text_item, "prov") and text_item.prov:
                    page_num = text_item.prov[0].page_no if text_item.prov else None
                elements.append({
                    "text": text_str,
                    "type": elem_type,
                    "page": page_num,
                })

        for table in doc.tables:
            if hasattr(table, "text") and table.text:
                text_parts.append(table.text)
                elements.append({
                    "text": table.text,
                    "type": "table",
                    "page": table.prov[0].page_no if hasattr(table, "prov") and table.prov else None,
                })

        full_text = "\n\n".join(text_parts)
        num_pages = len(result.pages) if result.pages else 1

        return ParsedDocument(
            document_id=doc_id,
            content_hash=content_hash,
            text=full_text,
            num_pages=num_pages,
            elements=elements,
            metadata={
                "filename": Path(file_path).name,
                "source": file_path,
            },
        )

    async def _convert_pdf(self, content: bytes) -> Any:
        return self._converter.convert(
            DocumentStream(
                stream=io.BytesIO(content),
                name="document.pdf",
            )
        )

    async def _convert_docx(self, content: bytes) -> Any:
        return self._converter.convert(
            DocumentStream(
                stream=io.BytesIO(content),
                name="document.docx",
            )
        )

    async def _convert_pptx(self, content: bytes) -> Any:
        return self._converter.convert(
            DocumentStream(
                stream=io.BytesIO(content),
                name="document.pptx",
            )
        )

    async def _convert_xlsx(self, content: bytes) -> Any:
        return self._converter.convert(
            DocumentStream(
                stream=io.BytesIO(content),
                name="document.xlsx",
            )
        )

    async def _convert_html(self, content: bytes) -> Any:
        return self._converter.convert(
            DocumentStream(
                stream=io.BytesIO(content),
                name="document.html",
            )
        )

    async def _convert_markdown(self, content: bytes) -> Any:
        return self._converter.convert(
            DocumentStream(
                stream=io.BytesIO(content),
                name="document.md",
            )
        )

    async def _convert_image(self, content: bytes) -> Any:
        return self._converter.convert(
            DocumentStream(
                stream=io.BytesIO(content),
                name="document.png",
            )
        )


class ParserService:
    def __init__(self) -> None:
        self._parser = DocumentParser()

    async def parse_document(
        self,
        file_path: str,
        file_content: bytes,
    ) -> ParsedDocument:
        return await self._parser.parse(file_path, file_content)


def get_parser_service() -> ParserService:
    return ParserService()
