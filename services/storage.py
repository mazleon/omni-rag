"""Storage service — Supabase S3-compatible storage.

Uses boto3 with Supabase S3 credentials for upload/download/delete.
Falls back to local filesystem if S3 credentials are not configured.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

from core.config import settings
from core.logging import get_logger

log = get_logger(__name__)

LOCAL_STORAGE_DIR = Path("storage/local")
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _use_s3() -> bool:
    return bool(
        settings.SUPABASE_S3_ENDPOINT
        and settings.SUPABASE_S3_ACCESS_KEY
        and settings.SUPABASE_S3_SECRET_KEY
        and settings.SUPABASE_S3_ACCESS_KEY.strip()
    )


def _get_s3_client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.SUPABASE_S3_ENDPOINT,
        aws_access_key_id=settings.SUPABASE_S3_ACCESS_KEY,
        aws_secret_access_key=settings.SUPABASE_S3_SECRET_KEY,
        region_name=settings.SUPABASE_S3_REGION or "ap-southeast-1",
        config=Config(signature_version="s3v4"),
    )


def _local_path(file_path: str) -> Path:
    return LOCAL_STORAGE_DIR / file_path


async def upload_bytes(file_path: str, content: bytes, content_type: str | None = None) -> str:
    if _use_s3():
        try:
            s3 = _get_s3_client()
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            s3.upload_fileobj(
                io.BytesIO(content),
                settings.SUPABASE_STORAGE_BUCKET,
                file_path,
                ExtraArgs=extra_args,
            )
            log.info("storage.s3.upload", path=file_path, size=len(content))
            return file_path
        except Exception as e:
            log.warning("storage.s3.upload_failed", error=str(e))

    path = _local_path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    log.info("storage.local.upload", path=file_path, size=len(content))
    return file_path


async def download_bytes(file_path: str) -> bytes:
    if _use_s3():
        try:
            s3 = _get_s3_client()
            response = s3.get_object(
                Bucket=settings.SUPABASE_STORAGE_BUCKET,
                Key=file_path,
            )
            content = response["Body"].read()
            log.info("storage.s3.download", path=file_path, size=len(content))
            return content
        except Exception as e:
            log.warning("storage.s3.download_failed", error=str(e))

    path = _local_path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    content = path.read_bytes()
    log.info("storage.local.download", path=file_path, size=len(content))
    return content


async def delete_object(file_path: str) -> None:
    if _use_s3():
        try:
            s3 = _get_s3_client()
            s3.delete_object(
                Bucket=settings.SUPABASE_STORAGE_BUCKET,
                Key=file_path,
            )
            log.info("storage.s3.delete", path=file_path)
            return
        except Exception as e:
            log.warning("storage.s3.delete_failed", error=str(e))

    path = _local_path(file_path)
    if path.exists():
        path.unlink()
        log.info("storage.local.delete", path=file_path)


async def health_check() -> bool:
    try:
        if _use_s3():
            s3 = _get_s3_client()
            s3.list_objects_v2(Bucket=settings.SUPABASE_STORAGE_BUCKET, MaxKeys=1)
            return True
        return LOCAL_STORAGE_DIR.exists()
    except Exception:
        return False


class StorageService:
    async def upload_file(self, file_path: str, content: bytes, content_type: str | None = None) -> str:
        return await upload_bytes(file_path, content, content_type)

    async def download_file(self, path: str) -> bytes:
        return await download_bytes(path)

    async def delete_object(self, path: str) -> None:
        await delete_object(path)


def get_storage_service() -> StorageService:
    return StorageService()
