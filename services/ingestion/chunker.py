"""Semantic chunker — layout → coherence → 15% overlap.

Takes a ParsedDocument and produces a list of Chunk schemas ready for
embedding and database insertion. Fixed-size chunking is explicitly rejected.

Phase 1: Stub returning a single chunk for the whole document.
Phase 2: Implement the 3-pass semantic strategy.
"""

from __future__ import annotations

from services.ingestion.parser import ParsedDocument


async def chunk_document(parsed: ParsedDocument) -> list[dict]:
    """
    Apply semantic chunking strategy to a parsed document.

    Args:
        parsed: The structured output from the Docling parser.

    Returns:
        List of dictionaries corresponding to the core.db.Chunk model.
    """
    # Phase 1 stub
    return [
        {
            "content": parsed.full_text,
            "page_number": 1,
            "chunk_index": 0,
            "token_count": len(parsed.full_text.split()),
            "modality": "text",
            "bbox": None,
        }
    ]
