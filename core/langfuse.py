from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator

from langfuse import Langfuse
from langfuse.callback import AsyncCallbackHandler
from pydantic import BaseModel

from core.config import settings
from core.logging import get_logger

log = get_logger(__name__)

_langfuse_client: Langfuse | None = None


def get_langfuse_client() -> Langfuse | None:
    global _langfuse_client
    
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        log.debug("langfuse.not_configured")
        return None
    
    if _langfuse_client is None:
        try:
            _langfuse_client = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                base_url=settings.LANGFUSE_BASE_URL,
            )
            log.info("langfuse.initialized")
        except Exception as e:
            log.warning("langfuse.init_error", error=str(e))
            return None
    
    return _langfuse_client


class LangfuseTrace(BaseModel):
    trace_id: str
    name: str
    start_time: datetime
    end_time: datetime | None = None
    metadata: dict[str, Any] | None = None
    input: str | None = None
    output: str | None = None


class LangfuseService:
    def __init__(self) -> None:
        self.client = get_langfuse_client()
        self._callback_handler: AsyncCallbackHandler | None = None
    
    def is_enabled(self) -> bool:
        return self.client is not None
    
    @asynccontextmanager
    async def trace(
        self,
        name: str,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        if not self.is_enabled():
            yield {}
            return
        
        trace_context: dict[str, Any] = {}
        
        try:
            langfuse_trace = self.client.trace(
                name=name,
                session_id=session_id,
                user_id=user_id,
                metadata=metadata,
            )
            
            trace_context["langfuse_trace"] = langfuse_trace
            trace_context["trace_id"] = langfuse_trace.id
            
            log.debug("langfuse.trace_started", trace_id=langfuse_trace.id, name=name)
            
            yield trace_context
            
        except Exception as e:
            log.warning("langfuse.trace_error", error=str(e))
            yield {}
        finally:
            try:
                if "langfuse_trace" in trace_context:
                    langfuse_trace = trace_context["langfuse_trace"]
                    langfuse_trace.end()
                    log.debug("langfuse.trace_ended", trace_id=langfuse_trace.id)
            except Exception as e:
                log.warning("langfuse.trace_end_error", error=str(e))
    
    def create_generation(
        self,
        trace_id: str,
        model: str,
        input_text: str,
        output_text: str | None = None,
        token_usage: dict[str, int] | None = None,
        latency: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self.is_enabled():
            return
        
        try:
            self.client.generations.create(
                trace_id=trace_id,
                model=model,
                input=input_text,
                output=output_text,
                token_usage=token_usage,
                latency=latency,
                metadata=metadata,
            )
            log.debug("langfuse.generation_created", trace_id=trace_id, model=model)
        except Exception as e:
            log.warning("langfuse.generation_error", error=str(e))
    
    def create_span(
        self,
        trace_id: str,
        name: str,
        input_text: str | None = None,
        output_text: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self.is_enabled():
            return
        
        try:
            self.client.spans.create(
                trace_id=trace_id,
                name=name,
                input=input_text,
                output=output_text,
                metadata=metadata,
            )
            log.debug("langfuse.span_created", trace_id=trace_id, name=name)
        except Exception as e:
            log.warning("langfuse.span_error", error=str(e))
    
    def update_trace(
        self,
        trace_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self.is_enabled():
            return
        
        try:
            self.client.traces.update(
                trace_id=trace_id,
                metadata=metadata,
            )
        except Exception as e:
            log.warning("langfuse.trace_update_error", error=str(e))


def get_langfuse_service() -> LangfuseService:
    return LangfuseService()
