import hashlib
import io
import uuid
from pathlib import Path
from typing import Any, Optional

from docling.datamodel.base import DocumentStream
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from pydantic import BaseModel


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

        result = await self._convert_pdf(file_content)

        text_parts: list[str] = []
        elements: list[dict[str, Any]] = []

        for page in result.pages:
            for element in page.elements:
                element_text = element.text.strip()
                if element_text:
                    text_parts.append(element_text)
                    elements.append(
                        {
                            "text": element_text,
                            "type": type(element).__name__,
                            "page": page.page_nr,
                        }
                    )

        full_text = "\n\n".join(text_parts)

        return ParsedDocument(
            document_id=doc_id,
            content_hash=content_hash,
            text=full_text,
            num_pages=len(result.pages),
            elements=elements,
            metadata={
                "filename": Path(file_path).name,
                "source": file_path,
            },
        )

    async def _convert_pdf(self, content: bytes) -> Any:
        return self._converter.convert(
            DocumentStream(
                file=(io.BytesIO(content), "document.pdf")
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