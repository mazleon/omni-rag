from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource

from core.config import settings
from core.logging import get_logger

log = get_logger(__name__)

_tracer_provider: TracerProvider | None = None
_tracer: trace.Tracer | None = None


def init_telemetry(service_name: str = "omnirag-api") -> None:
    global _tracer_provider, _tracer
    
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "0.1.0",
        "deployment.environment": settings.ENV,
    })
    
    _tracer_provider = TracerProvider(resource=resource)
    
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        try:
            exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
            _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
            log.info("telemetry.otlp_enabled", endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        except Exception as e:
            log.warning("telemetry.otlp_failed", error=str(e))
    
    _tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    
    trace.set_tracer_provider(_tracer_provider)
    
    _tracer = trace.get_tracer(__name__)
    log.info("telemetry.initialized", service_name=service_name)


def get_tracer() -> trace.Tracer:
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(__name__)
    return _tracer


def instrument_fastapi(app: Any) -> None:
    if _tracer_provider:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor.instrument_app(app, tracer_provider=_tracer_provider)
            log.info("telemetry.fastapi_instrumented")
        except Exception as e:
            log.warning("telemetry.fastapi_instrument_error", error=str(e))


@asynccontextmanager
async def traced_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
):
    tracer = get_tracer()
    with tracer.start_as_current_span(name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        span_context = span.get_span_context()
        span_id = format(span_context.span_id, "016x")
        trace_id = format(span_context.trace_id, "032x")
        
        log.debug(
            "trace.start",
            span_name=name,
            span_id=span_id,
            trace_id=trace_id,
        )
        
        try:
            yield span
        except Exception as e:
            span.set_status(trace.StatusCode.ERROR, str(e))
            span.record_exception(e)
            raise
        finally:
            log.debug(
                "trace.end",
                span_name=name,
                span_id=span_id,
            )


def create_trace_context(trace_id: str | None = None, span_id: str | None = None) -> dict[str, Any]:
    if trace_id and span_id:
        return {
            "trace_id": trace_id,
            "span_id": span_id,
        }
    return {}


class TracingService:
    def __init__(self, service_name: str = "omnirag") -> None:
        self.service_name = service_name
        self.tracer = get_tracer()
    
    def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
        kind: trace.SpanKind = trace.SpanKind.INTERNAL,
    ) -> trace.Span:
        return self.tracer.start_span(name, kind=kind)
    
    def trace_db_query(
        self,
        operation: str,
        table: str,
    ) -> dict[str, Any]:
        return {
            "db.system": "postgresql",
            "db.operation": operation,
            "db.name": table,
        }
    
    def trace_llm_request(
        self,
        model: str,
        operation: str = "completion",
    ) -> dict[str, Any]:
        return {
            "llm.model": model,
            "llm.operation": operation,
        }
    
    def trace_rag_operation(
        self,
        operation: str,
        document_count: int = 0,
        chunk_count: int = 0,
    ) -> dict[str, Any]:
        return {
            "rag.operation": operation,
            "rag.document_count": document_count,
            "rag.chunk_count": chunk_count,
        }


def get_tracing_service() -> TracingService:
    return TracingService()
