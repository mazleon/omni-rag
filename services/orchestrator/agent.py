import uuid
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from core.config import settings


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    tool_name: str
    result: Any
    success: bool


class AgentConfig(BaseModel):
    max_iterations: int = 5
    temperature: float = 0.7
    max_tokens: int = 2000


class QueryAgent:
    def __init__(self, config: AgentConfig | None = None) -> None:
        self.config = config or AgentConfig()
        self._client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )
        self._tools: list[dict[str, Any]] = []

    def register_tool(self, name: str, description: str, parameters: dict[str, Any]) -> None:
        self._tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        })

    async def run(
        self,
        query: str,
        context: list[dict[str, Any]],
        available_tools: dict[str, Any],
    ) -> dict[str, Any]:
        system_prompt = self._build_system_prompt(context)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        for iteration in range(self.config.max_iterations):
            response = await self._client.chat.completions.create(
                model=settings.OPENROUTER_DEFAULT_MODEL,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                tools=self._tools or None,
            )

            if not response.choices:
                break

            message = response.choices[0].message

            if message.tool_calls:
                for tool_call in message.tool_calls:
                    result = await self._execute_tool(
                        tool_call.name,
                        tool_call.arguments,
                        available_tools,
                    )
                    messages.append({
                        "role": "assistant",
                        "content": f"Called tool: {tool_call.name}",
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result.result),
                    })

                    if result.success and self._is_final_answer(result.result):
                        return {
                            "answer": result.result,
                            "iterations": iteration + 1,
                            "tool_calls": len(message.tool_calls),
                        }
            elif message.content:
                if self._is_final_answer(message.content):
                    return {
                        "answer": message.content,
                        "iterations": iteration + 1,
                        "tool_calls": 0,
                    }
                messages.append({"role": "assistant", "content": message.content})

        return {
            "answer": "I couldn't find a definitive answer. Please try rephrasing your question.",
            "iterations": self.config.max_iterations,
            "tool_calls": 0,
        }

    def _build_system_prompt(self, context: list[dict[str, Any]]) -> str:
        ctx_text = "\n\n".join([
            f"Document {i+1}: {c.get('content', '')[:500]}"
            for i, c in enumerate(context[:5])
        ])

        return f"""You are a helpful AI assistant that answers questions based on the provided document context.

Available context:
{ctx_text}

Guidelines:
- Only use information from the provided context
- Cite sources when making claims (e.g., [1], [2])
- If information is not in the context, say so
- Keep answers concise and focused
- Use tools only when necessary to retrieve additional information"""

    async def _execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        available_tools: dict[str, Any],
    ) -> ToolResult:
        try:
            tool_func = available_tools.get(tool_name)
            if not tool_func:
                return ToolResult(
                    tool_name=tool_name,
                    result=f"Tool '{tool_name}' not found",
                    success=False,
                )

            result = await tool_func(**arguments)
            return ToolResult(tool_name=tool_name, result=result, success=True)
        except Exception as e:
            return ToolResult(tool_name=tool_name, result=str(e), success=False)

    def _is_final_answer(self, content: str) -> bool:
        content_lower = content.lower().strip()
        return (
            len(content_lower) > 20
            and not content_lower.startswith("let me")
            and not content_lower.startswith("i need to")
        )


class AgentService:
    def __init__(self) -> None:
        self._agent = AgentConfig()

    async def run(
        self,
        query: str,
        context: list[dict[str, Any]],
        available_tools: dict[str, Any],
    ) -> dict[str, Any]:
        agent = QueryAgent()
        agent._tools = self._get_tools()
        return await agent.run(query, context, available_tools)

    def _get_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_documents",
                    "description": "Search for relevant documents using semantic search",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                        },
                        "required": ["query"],
                    },
                },
            },
        ]


def get_agent_service() -> AgentService:
    return AgentService()