"""Database engine, session factory, and ORM base.

All ORM models are defined here so Alembic's env.py can discover them
via a single import. This avoids the circular-import footgun of spreading
model definitions across services.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from core.config import settings
from core.logging import get_logger

log = get_logger(__name__)

# ── Engine ─────────────────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.postgres_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_pool_max_overflow,
    echo=settings.db_echo_sql,
    pool_pre_ping=True,  # reconnect on stale connections
)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── ORM Base ───────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """All ORM models inherit from this base."""

    type_annotation_map: dict[type[Any], Any] = {
        dict: JSONB,
        list: ARRAY(Text),
    }


# ── Models ─────────────────────────────────────────────────────────────────────

class Organization(Base):
    """Multi-tenant root. Every piece of data is scoped to an org."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    plan: Mapped[str] = mapped_column(Text, nullable=False, default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    documents: Mapped[list[Document]] = relationship(
        "Document", back_populates="organization", lazy="noload"
    )
    api_keys: Mapped[list[ApiKey]] = relationship(
        "ApiKey", back_populates="organization", lazy="noload"
    )


class Document(Base):
    """
    Represents an uploaded and optionally indexed document.
    Embeddings live in Qdrant; this table holds metadata only.

    Status lifecycle: pending → processing → indexed | error
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)       # Supabase Storage path
    content_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)  # SHA-256
    doc_type: Mapped[str | None] = mapped_column(Text, nullable=True)   # pdf|docx|pptx|…
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="documents", lazy="noload"
    )
    chunks: Mapped[list[Chunk]] = relationship(
        "Chunk", back_populates="document", lazy="noload", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_documents_org_status", "org_id", "status"),
        Index("ix_documents_org_created", "org_id", "created_at"),
    )


class Chunk(Base):
    """
    Metadata record for a single chunk.
    The actual embedding vector lives in Qdrant (qdrant_id is the foreign key).
    """

    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    qdrant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, unique=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_tsv: Mapped[Any] = mapped_column(
        TSVECTOR,
        nullable=True,
        # Populated by Postgres trigger or explicit update for BM25
    )
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    modality: Mapped[str] = mapped_column(Text, nullable=False, default="text")
    bbox: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    document: Mapped[Document] = relationship(
        "Document", back_populates="chunks", lazy="noload"
    )

    __table_args__ = (
        # GIN index on tsvector for fast BM25 full-text search
        Index("ix_chunks_content_tsv", "content_tsv", postgresql_using="gin"),
    )


class QueryTrace(Base):
    """
    Immutable audit log of every query for observability and RAGAS offline eval.
    Never update rows — always insert new ones.
    """

    __tablename__ = "query_traces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(UUID(as_uuid=False)), nullable=True
    )
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), nullable=True)
    feedback: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # -1|0|1
    model_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False, index=True
    )


class ApiKey(Base):
    """Per-org API keys with scopes and rate limits."""

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)  # bcrypt hash
    name: Mapped[str] = mapped_column(Text, nullable=False)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="api_keys", lazy="noload"
    )
