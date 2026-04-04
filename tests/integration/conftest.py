"""Integration test fixtures.

Uses testcontainers for real Postgres and Redis, and qdrant-client in-memory mode.
Set OMNIRAG_SKIP_INTEGRATION=1 to skip all integration tests in CI if Docker is unavailable.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Skip all integration tests if Docker is unavailable
if os.getenv("OMNIRAG_SKIP_INTEGRATION"):
    pytest.skip("Integration tests skipped (OMNIRAG_SKIP_INTEGRATION set)", allow_module_level=True)


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="session")
def postgres_container():
    """Start a real Postgres container and return the async DSN."""
    from testcontainers.postgres import PostgresContainer

    pg = PostgresContainer("postgres:16-alpine")
    pg.start()
    sync_url = pg.get_connection_url()
    async_url = sync_url.replace("psycopg2", "asyncpg").replace("postgresql://", "postgresql+asyncpg://")
    yield async_url, pg
    pg.stop()


@pytest.fixture(scope="session")
def redis_container():
    """Start a real Redis container and return the DSN."""
    from testcontainers.redis import RedisContainer

    r = RedisContainer("redis:7-alpine")
    r.start()
    host = r.get_container_host_ip()
    port = r.get_exposed_port(6379)
    yield f"redis://{host}:{port}"
    r.stop()


@pytest.fixture(scope="session")
def qdrant_client():
    """Return an in-memory Qdrant client (no container needed)."""
    from qdrant_client import QdrantClient

    return QdrantClient(":memory:")


@pytest.fixture(scope="session")
def patched_settings(postgres_container, redis_container):
    """Override Settings singleton fields with test container values."""
    from core.config import settings

    postgres_url, _ = postgres_container
    settings.POSTGRES_URL = postgres_url
    settings.REDIS_URL = redis_container
    settings.COHERE_API_KEY = "test-cohere-key"
    settings.OPENROUTER_API_KEY = "test-openrouter-key"
    settings.OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    settings.JWT_SECRET = "test-jwt-secret-for-integration-tests"
    settings.SUPABASE_URL = "https://test.supabase.co"
    settings.SUPABASE_SERVICE_ROLE_KEY = "test-key"
    return settings


@pytest.fixture(scope="session")
def db_engine(patched_settings, postgres_container):
    """Create tables on the test Postgres instance using sync SQLAlchemy."""
    from core.models import Base

    postgres_url, _ = postgres_container
    sync_url = postgres_url.replace("+asyncpg", "")

    engine = create_engine(sync_url, echo=False)
    Base.metadata.create_all(engine)
    engine.dispose()

    async_engine = create_async_engine(postgres_url, echo=False)
    yield async_engine
    asyncio.get_event_loop().run_until_complete(async_engine.dispose())


@pytest_asyncio.fixture(scope="session")
async def session_factory(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    return factory


@pytest_asyncio.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="session")
async def test_org(session_factory) -> dict:
    """Seed a test org and user, return auth data."""
    from core.models import Org, User, OrgStatus
    import bcrypt
    import jwt
    from core.config import settings

    password_hash = bcrypt.hashpw(
        "testpassword123".encode(),
        bcrypt.gensalt(),
    ).decode()

    async with session_factory() as session:
        org = Org(
            id=uuid.uuid4(),
            name="Integration Test Org",
            slug=f"test-org-{uuid.uuid4().hex[:8]}",
            status=OrgStatus.ACTIVE,
        )
        session.add(org)
        await session.flush()

        user = User(
            id=uuid.uuid4(),
            org_id=org.id,
            email=f"test-{uuid.uuid4().hex[:8]}@example.com",
            password_hash=password_hash,
            role="admin",
        )
        session.add(user)
        await session.commit()

    token_data = {
        "sub": str(user.id),
        "org_id": str(org.id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    token = jwt.encode(token_data, settings.JWT_SECRET, algorithm="HS256")

    return {
        "org_id": org.id,
        "user_id": user.id,
        "token": token,
        "auth_headers": {"Authorization": f"Bearer {token}"},
    }


@pytest_asyncio.fixture(scope="session")
async def test_app(patched_settings, db_engine):
    """Build the FastAPI app with test settings applied."""
    from apps.api.main import create_app

    app = create_app()
    return app


@pytest_asyncio.fixture
async def http_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as client:
        yield client
