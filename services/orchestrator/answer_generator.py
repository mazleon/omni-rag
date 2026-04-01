import uuid
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from core.config import settings


class AnswerConfig(BaseModel):
    model: str = settings.OPENROUTER_DEFAULT_MODEL
    temperature: float = 0.7
    max_tokens: int = 2000


class GeneratedAnswer(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    tokens_used: int | None = None


class AnswerGenerator:
    def __init__(self, config: AnswerConfig | None = None) -> None:
        self.config = config or AnswerConfig()
        self._client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )

    async def generate(
        self,
        query: str,
        context: list[dict[str, Any]],
    ) -> GeneratedAnswer:
        if not context:
            return GeneratedAnswer(
                answer="I don't have enough context to answer your question. Please upload some documents first.",
                sources=[],
            )

        context_text = self._build_context(context)

        prompt = self._build_prompt(query, context_text)

        try:
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            answer = response.choices[0].message.content or "No answer generated"
            tokens_used = response.usage.total_tokens if response.usage else None

            sources = [
                {
                    "chunk_id": str(c.get("chunk_id", "")),
                    "document_id": str(c.get("document_id", "")),
                    "content": c.get("content", "")[:200],
                    "score": c.get("score", 0),
                }
                for c in context[:5]
            ]

            return GeneratedAnswer(
                answer=answer,
                sources=sources,
                tokens_used=tokens_used,
            )
        except Exception as e:
            return GeneratedAnswer(
                answer=f"Error generating answer: {str(e)}",
                sources=[],
            )

    def _build_context(self, context: list[dict[str, Any]]) -> str:
        parts = []
        for i, c in enumerate(context, 1):
            content = c.get("content", "")
            page_nums = c.get("page_numbers")
            pages = f" (pages: {', '.join(map(str, page_nums))})" if page_nums else ""
            parts.append(f"[{i}]{pages}\n{content[:500]}")
        return "\n\n".join(parts)

    def _build_prompt(self, query: str, context: str) -> str:
        return f"""Based on the following context from documents, answer the user's question.

Context:
{context}

Question: {query}

Instructions:
- Use only information from the provided context
- Cite sources using [1], [2], etc. format
- If the answer cannot be determined from the context, say so clearly
- Keep the answer concise but informative

Answer:"""

    def _get_system_prompt(self) -> str:
        return """You are a helpful AI assistant that generates accurate answers based on provided document context.

Your characteristics:
- Always cite your sources
- If information is not in the context, clearly state that
- Be concise and accurate
- Use a conversational but professional tone"""


class AnswerGeneratorService:
    def __init__(self) -> None:
        self._generator = AnswerGenerator()

    async def generate(
        self,
        query: str,
        context: list[dict[str, Any]],
    ) -> GeneratedAnswer:
        return await self._generator.generate(query, context)


def get_answer_generator_service() -> AnswerGeneratorService:
    return AnswerGeneratorService()