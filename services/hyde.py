import uuid
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from core.config import settings
from core.logging import get_logger

log = get_logger(__name__)


class HydeConfig(BaseModel):
    enabled: bool = False
    num_hypothetical_docs: int = 3
    model: str = "anthropic/claude-3.5-sonnet"


class HyDEExpander:
    def __init__(self, config: HydeConfig | None = None) -> None:
        self.config = config or HydeConfig()
        self._client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )

    async def expand_query(self, query: str) -> list[str]:
        if not self.config.enabled:
            return [query]

        prompt = f"""Generate {self.config.num_hypothetical_docs} hypothetical document passages that could help answer this question. 
Each passage should be 2-3 sentences and written as if it were extracted from a relevant document.

Question: {query}

Hypothetical passages:"""

        try:
            response = await self._client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that generates hypothetical document passages."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=500,
            )

            content = response.choices[0].message.content or ""
            
            passages = [
                line.strip() 
                for line in content.split("\n") 
                if line.strip() and not line.strip().startswith(("1.", "2.", "3.", "-", "*"))
            ]
            
            if not passages:
                passages = content.split("\n\n")
                passages = [p.strip() for p in passages if p.strip()]
            
            all_queries = [query] + passages[:self.config.num_hypothetical_docs]
            
            log.info("hyde.query_expanded", original=query, num_variations=len(all_queries))
            
            return all_queries

        except Exception as e:
            log.warning("hyde.expansion_failed", error=str(e))
            return [query]


class HydeService:
    def __init__(self) -> None:
        self._expander = HyDEExpander()

    async def expand(self, query: str) -> list[str]:
        return await self._expander.expand_query(query)

    def is_enabled(self) -> bool:
        return self._expander.config.enabled

    def enable(self) -> None:
        self._expander.config.enabled = True

    def disable(self) -> None:
        self._expander.config.enabled = False


def get_hyde_service() -> HydeService:
    return HydeService()
