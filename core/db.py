import uuid
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from core.config import settings

class Base(DeclarativeBase):
    pass

engine = create_async_engine(settings.POSTGRES_URL, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

async def set_rls_context(session: AsyncSession, org_id: uuid.UUID) -> None:
    """Set PostgreSQL session variable for RLS row-level isolation.

    Must be called after acquiring a session and before any org-scoped query.
    Uses transaction-local scope (true) so the setting is cleared on COMMIT/ROLLBACK.
    """
    await session.execute(
        text("SELECT set_config('app.current_org_id', :org_id, true)"),
        {"org_id": str(org_id)},
    )
