"""LLM toolkit for the agent loop.

Wraps execution logic for exposed schemas.
"""

from __future__ import annotations

import json


def get_available_tools() -> list[dict]:
    """Return JSON schema lists for the LLM to inspect."""
    return [
        {
            "type": "function",
            "function": {
                "name": "search_knowledge_base",
                "description": "Query hybrid dense/sparse results for relevant facts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Lexical or semantic keywords",
                        }
                    },
                    "required": ["query"],
                },
            },
        }
    ]


async def execute_tool(name: str, args: str) -> str:
    """Safely parse input string and route execution to appropriate wrapper."""
    # Phase 1 stub
    try:
        parsed = json.loads(args)
    except json.JSONDecodeError:
        return "Error parsing function args as JSON."

    if name == "search_knowledge_base":
        return f"[Tool result stub] Looked up '{parsed.get('query')}'."

    return "Error: Unknown tool."
