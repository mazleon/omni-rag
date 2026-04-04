from __future__ import annotations

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

import redis.asyncio as redis
from redis.asyncio import Redis

from core.config import settings
from core.logging import get_logger

log = get_logger(__name__)

T = TypeVar("T")

_redis_client: Redis | None = None


async def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


def _compute_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    key_parts = [prefix]
    for arg in args:
        key_parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        key_parts.append(f"{k}={v}")
    key_string = ":".join(key_parts)
    return hashlib.sha256(key_string.encode()).hexdigest()[:32]


async def get_cached(key: str) -> Any | None:
    client = await get_redis_client()
    try:
        cached = await client.get(key)
        if cached:
            log.debug("cache.hit", key=key)
            return json.loads(cached)
        log.debug("cache.miss", key=key)
        return None
    except Exception as e:
        log.warning("cache.get_error", key=key, error=str(e))
        return None


async def set_cached(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    client = await get_redis_client()
    try:
        serialized = json.dumps(value)
        await client.setex(key, ttl_seconds, serialized)
        log.debug("cache.set", key=key, ttl=ttl_seconds)
        return True
    except Exception as e:
        log.warning("cache.set_error", key=key, error=str(e))
        return False


async def delete_cached(key: str) -> bool:
    client = await get_redis_client()
    try:
        await client.delete(key)
        log.debug("cache.delete", key=key)
        return True
    except Exception as e:
        log.warning("cache.delete_error", key=key, error=str(e))
        return False


async def delete_pattern(pattern: str) -> int:
    client = await get_redis_client()
    try:
        cursor = 0
        deleted_count = 0
        while True:
            cursor, keys = await client.scan(cursor, match=pattern, count=100)
            if keys:
                deleted = await client.delete(*keys)
                deleted_count += deleted
            if cursor == 0:
                break
        log.info("cache.delete_pattern", pattern=pattern, count=deleted_count)
        return deleted_count
    except Exception as e:
        log.warning("cache.delete_pattern_error", pattern=pattern, error=str(e))
        return 0


async def get_cache_stats() -> dict[str, Any]:
    client = await get_redis_client()
    try:
        info = await client.info("stats")
        memory = await client.info("memory")
        return {
            "total_commands_processed": info.get("total_commands_processed", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "used_memory": memory.get("used_memory_human", "0"),
        }
    except Exception as e:
        log.warning("cache.stats_error", error=str(e))
        return {"error": str(e)}


def cached(
    prefix: str,
    ttl_seconds: int = 300,
    key_builder: Callable[..., tuple[tuple[Any, ...], dict[str, Any]]] | None = None,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            if key_builder:
                args_tuple, kwargs_dict = key_builder(*args, **kwargs)
            else:
                args_tuple = args[1:] if args else ()
                kwargs_dict = kwargs
            
            cache_key = f"{prefix}:{_compute_cache_key(prefix, *args_tuple, **kwargs_dict)}"
            
            cached_value = await get_cached(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = await func(*args, **kwargs)
            
            if result is not None:
                await set_cached(cache_key, result, ttl_seconds)
            
            return result
        return wrapper
    return decorator


class CacheService:
    def __init__(self, default_ttl: int = 300) -> None:
        self.default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        return await get_cached(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return await set_cached(key, value, ttl or self.default_ttl)

    async def delete(self, key: str) -> bool:
        return await delete_cached(key)

    async def invalidate_pattern(self, pattern: str) -> int:
        return await delete_pattern(pattern)

    async def get_stats(self) -> dict[str, Any]:
        return await get_cache_stats()

    async def cache_query_result(
        self,
        org_id: str,
        query: str,
        result: dict[str, Any],
        ttl: int = 300,
    ) -> bool:
        key = f"query:{org_id}:{_compute_cache_key('query', org_id, query)}"
        return await set_cached(key, result, ttl)

    async def get_cached_query_result(
        self,
        org_id: str,
        query: str,
    ) -> dict[str, Any] | None:
        key = f"query:{org_id}:{_compute_cache_key('query', org_id, query)}"
        return await get_cached(key)

    async def invalidate_org_cache(self, org_id: str) -> int:
        return await delete_pattern(f"query:{org_id}:*")

    async def cache_embedding(
        self,
        org_id: str,
        query: str,
        embedding: list[float],
        ttl: int = 600,
    ) -> bool:
        key = f"embedding:{org_id}:{_compute_cache_key('embedding', org_id, query)}"
        return await set_cached(key, embedding, ttl)

    async def get_cached_embedding(
        self,
        org_id: str,
        query: str,
    ) -> list[float] | None:
        key = f"embedding:{org_id}:{_compute_cache_key('embedding', org_id, query)}"
        return await get_cached(key)


def get_cache_service() -> CacheService:
    return CacheService()
