"""OpenRouter tool-calling ReAct agent loop wrapper.

Custom orchestration layer replacing brittle LangChain workflows.
Maintains history, checks constraints (budget, iterations), and calls retrieval tools.
"""

from __future__ import annotations

import uuid

from core.config import settings
from core.logging import get_logger

log = get_logger(__name__)


async def run_query_agent(query_text: str, org_id: uuid.UUID) -> str:
    """
    Drive the full multi-hop retrieval and answer generation loop.

    Args:
        query_text: User's intent-extracted query string.
        org_id: Execution context boundaries for LLM tasks.

    Returns:
        The markdown-formatted, parsed string output of the language model
        with document citations populated correctly.
    """
    # Phase 1 stub — bypass agent loop until retrieval + DB pipelines are wired
    log.info(
        "agent.run",
        org_id=str(org_id),
        max_iter=settings.agent_max_iterations,
        budget=settings.agent_max_cost_usd,
    )
    return "[Phase 1 stub] Agent loop generation."
