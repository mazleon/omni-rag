"""ASGI middleware: request-ID injection and structured access logging."""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

log = structlog.get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"

# Paths excluded from access logs (health/readiness probes spam logs)
_SILENT_PATHS = frozenset({"/v1/health", "/v1/ready", "/v1/metrics"})


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Attach a request_id to every request.
    Reads X-Request-ID from incoming headers (for tracing through a gateway)
    or generates a new UUID if absent. Always echoes the ID back in the response.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = request_id

        # Bind to structlog context so every log line in this request carries the ID
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    Emit a structured access log line after every response.
    Skips health/readiness probes to keep logs clean in production.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _SILENT_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = round((time.perf_counter() - start) * 1000)

        log.info(
            "http.access",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=latency_ms,
            request_id=getattr(request.state, "request_id", None),
        )
        return response
