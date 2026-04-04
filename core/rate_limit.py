from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.cache import get_cache_service
from core.logging import get_logger

log = get_logger(__name__)


@dataclass
class RateLimitConfig:
    requests: int = 100
    window_seconds: int = 60


DEFAULT_CONFIG = {
    "default": RateLimitConfig(requests=100, window_seconds=60),
    "query": RateLimitConfig(requests=50, window_seconds=60),
    "query_stream": RateLimitConfig(requests=30, window_seconds=60),
    "documents_upload": RateLimitConfig(requests=10, window_seconds=60),
    "auth": RateLimitConfig(requests=5, window_seconds=60),
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, config: dict[str, RateLimitConfig] | None = None) -> None:
        super().__init__(app)
        self.config = config or DEFAULT_CONFIG

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_id = self._get_client_id(request)
        endpoint = self._get_endpoint_key(request)
        
        config = self.config.get(endpoint) or self.config["default"]
        
        allowed, remaining, reset_time = await self._check_rate_limit(
            client_id,
            endpoint,
            config,
        )
        
        if not allowed:
            log.warning(
                "rate_limit.exceeded",
                client_id=client_id,
                endpoint=endpoint,
                limit=config.requests,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": config.requests,
                    "window_seconds": config.window_seconds,
                    "retry_after": max(0, int(reset_time - time.time())),
                },
                headers={
                    "X-RateLimit-Limit": str(config.requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_time)),
                    "Retry-After": str(max(0, int(reset_time - time.time()))),
                },
            )
        
        response = await call_next(request)
        
        response.headers["X-RateLimit-Limit"] = str(config.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        
        return response

    def _get_client_id(self, request: Request) -> str:
        auth_header = request.headers.get("authorization")
        if auth_header:
            return f"token:{auth_header[:20]}"
        
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        return f"ip:{request.client.host if request.client else 'unknown'}"

    def _get_endpoint_key(self, request: Request) -> str:
        path = request.url.path
        
        if "/query/stream" in path:
            return "query_stream"
        if "/query" in path:
            return "query"
        if "/documents/upload" in path:
            return "documents_upload"
        if "/auth" in path and request.method == "POST":
            return "auth"
        
        return "default"

    async def _check_rate_limit(
        self,
        client_id: str,
        endpoint: str,
        config: RateLimitConfig,
    ) -> tuple[bool, int, float]:
        cache = get_cache_service()
        
        key = f"ratelimit:{endpoint}:{client_id}"
        
        current_time = time.time()
        window_start = current_time - config.window_seconds
        
        try:
            cached_data = await cache.get(key)
            
            if cached_data is None:
                await cache.set(key, {
                    "count": 1,
                    "reset_time": current_time + config.window_seconds,
                }, ttl=config.window_seconds + 10)
                return True, config.requests - 1, current_time + config.window_seconds
            
            count = cached_data.get("count", 0)
            reset_time = cached_data.get("reset_time", current_time + config.window_seconds)
            
            if current_time > reset_time:
                await cache.set(key, {
                    "count": 1,
                    "reset_time": current_time + config.window_seconds,
                }, ttl=config.window_seconds + 10)
                return True, config.requests - 1, current_time + config.window_seconds
            
            if count >= config.requests:
                return False, 0, reset_time
            
            await cache.set(key, {
                "count": count + 1,
                "reset_time": reset_time,
            }, ttl=config.window_seconds + 10)
            
            return True, config.requests - count - 1, reset_time
            
        except Exception as e:
            log.warning("rate_limit.check_error", error=str(e))
            return True, config.requests, current_time + config.window_seconds


async def check_rate_limit(
    client_id: str,
    endpoint: str,
    limit: int = 100,
    window: int = 60,
) -> tuple[bool, int, float]:
    cache = get_cache_service()
    
    key = f"ratelimit:{endpoint}:{client_id}"
    
    current_time = time.time()
    
    try:
        cached_data = await cache.get(key)
        
        if cached_data is None:
            await cache.set(key, {
                "count": 1,
                "reset_time": current_time + window,
            }, ttl=window + 10)
            return True, limit - 1, current_time + window
        
        count = cached_data.get("count", 0)
        reset_time = cached_data.get("reset_time", current_time + window)
        
        if current_time > reset_time:
            await cache.set(key, {
                "count": 1,
                "reset_time": current_time + window,
            }, ttl=window + 10)
            return True, limit - 1, current_time + window
        
        if count >= limit:
            return False, 0, reset_time
        
        await cache.set(key, {
            "count": count + 1,
            "reset_time": reset_time,
        }, ttl=window + 10)
        
        return True, limit - count - 1, reset_time
        
    except Exception as e:
        log.warning("rate_limit.check_error", error=str(e))
        return True, limit, current_time + window


def get_rate_limit_config(endpoint: str) -> RateLimitConfig:
    return DEFAULT_CONFIG.get(endpoint, DEFAULT_CONFIG["default"])
