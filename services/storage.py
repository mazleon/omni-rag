"""Supabase Storage service — presigned upload URLs, byte downloads, deletes.

All raw-bytes I/O in the ingestion pipeline goes through this module.
Never import boto3 or AWS SDK — Supabase Storage is the exclusive object store.
"""

from __future__ import annotations

from functools import lru_cache

import httpx
from supabase._async.client import AsyncClient as AsyncSupabaseClient
from supabase import create_async_client

from core.config import settings
from core.logging import get_logger

log = get_logger(__name__)

# ── Client singleton ───────────────────────────────────────────────────────────

_supabase_client: AsyncSupabaseClient | None = None


async def get_supabase_client() -> AsyncSupabaseClient:
    """Return (or lazily create) the shared Supabase async client."""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = await create_async_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _supabase_client


# ── Public API ─────────────────────────────────────────────────────────────────

async def get_presigned_upload_url(path: str, expires_in: int = 3600) -> str:
    """
    Return a presigned URL the client can use to PUT a file directly into
    Supabase Storage without server-side proxying.

    Args:
        path:       Storage path, e.g. ``{org_id}/{doc_type}/{doc_id}.pdf``
        expires_in: URL validity in seconds (default 1 hour).

    Returns:
        Signed upload URL string.
    """
    client = await get_supabase_client()
    response = await client.storage.from_(settings.supabase_storage_bucket).create_signed_upload_url(
        path=path,
    )
    signed_url: str = response["signedURL"]
    log.info("storage.presigned_url.created", path=path, expires_in=expires_in)
    return signed_url


async def download_bytes(path: str) -> bytes:
    """
    Download a file from Supabase Storage and return its raw bytes.

    Uses httpx directly to stream the download rather than buffering through
    supabase-py, which avoids memory spikes on large documents.

    Args:
        path: Storage path of the file to download.

    Returns:
        Raw file bytes.

    Raises:
        httpx.HTTPStatusError: If the download request fails (4xx / 5xx).
    """
    client = await get_supabase_client()

    # Get a short-lived signed download URL (avoids exposing service key)
    response = await client.storage.from_(settings.supabase_storage_bucket).create_signed_url(
        path=path,
        expires_in=300,  # 5-minute window — only used immediately
    )
    signed_url: str = response["signedURL"]

    async with httpx.AsyncClient(timeout=120.0) as http:
        r = await http.get(signed_url)
        r.raise_for_status()

    log.info("storage.download.complete", path=path, size_bytes=len(r.content))
    return r.content


async def delete_object(path: str) -> None:
    """
    Remove a file from Supabase Storage.
    Called during soft-delete vector pruning (Phase 3).

    Args:
        path: Storage path to delete.
    """
    client = await get_supabase_client()
    await client.storage.from_(settings.supabase_storage_bucket).remove([path])
    log.info("storage.object.deleted", path=path)


async def health_check() -> bool:
    """Return True if Supabase Storage is reachable."""
    try:
        client = await get_supabase_client()
        await client.storage.list_buckets()
        return True
    except Exception:
        return False


class StorageService:
    """Wrapper around module-level storage functions for dependency injection."""

    async def get_presigned_upload_url(self, file_path: str, content_type: str | None = None) -> str:
        return await get_presigned_upload_url(file_path)

    async def download_file(self, path: str) -> bytes:
        return await download_bytes(path)

    async def delete_object(self, path: str) -> None:
        await delete_object(path)


def get_storage_service() -> StorageService:
    return StorageService()
