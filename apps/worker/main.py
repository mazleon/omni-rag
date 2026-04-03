import asyncio
from typing import Any

from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from core.config import settings
from apps.worker.jobs.ingest import process_ingest_job


engine = create_async_engine(
    settings.POSTGRES_URL,
    echo=False,
    pool_pre_ping=True,
)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def startup(ctx: dict[str, Any]) -> None:
    ctx["session_factory"] = AsyncSessionLocal


async def shutdown(ctx: dict[str, Any]) -> None:
    await engine.dispose()


async def get_db_session(ctx: dict[str, Any]) -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


class WorkerSettings:
    functions = [process_ingest_job]
    redis_settings = RedisSettings(
        host=settings.REDIS_URL.split("://")[1].split(":")[0],
        port=int(settings.REDIS_URL.split(":")[-1])
    )
    on_startup = startup
    on_shutdown = shutdown