"""SSE Streaming generator for final LLM responses.

Uses OpenRouter (openai-python SDK) and streams out token chunks matching
the QueryStreamChunk definitions. Also capable of emitting discrete citations
found by the multi-hop loop inline.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator


async def generate_streaming_answer(
    prompt: str,
    context: str,
) -> AsyncGenerator[str, None]:
    """
    Stream Server-Sent Events with a generated LLM answer.

    Args:
        prompt: User's parsed initial question text.
        context: Concatenated raw texts of all returned retrieved chunks.

    Yields:
        Formatted data chunks ready for starlette SSE consumption.
    """
    # Phase 1 stub
    yield f"data: {json.dumps({'event': 'chunk', 'data': '[Streaming stub] '})}\n\n"
    yield f"data: {json.dumps({'event': 'chunk', 'data': 'RAG Answer'})}\n\n"
    yield f"data: {json.dumps({'event': 'done', 'data': ''})}\n\n"
