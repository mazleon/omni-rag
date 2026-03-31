"""Application configuration loaded from environment variables via Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All configuration is sourced from environment variables.
    See .env.example for the full list with descriptions.
    Sensitive values must never have defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────────────
    env: str = Field(default="development", pattern=r"^(development|staging|production)$")
    app_name: str = "OmniRAG"
    app_version: str = "0.1.0"
    debug: bool = False
    jwt_secret: str = Field(default="change-me-in-production-32-chars-min")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours

    # ── Database ───────────────────────────────────────────────────────────────
    postgres_url: str = Field(
        default="postgresql+asyncpg://omnirag:omnirag@localhost:5432/omnirag"
    )
    db_pool_size: int = 10
    db_pool_max_overflow: int = 20
    db_echo_sql: bool = False

    # ── Qdrant ─────────────────────────────────────────────────────────────────
    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_api_key: str = Field(default="")
    qdrant_grpc_port: int = 6334
    qdrant_prefer_grpc: bool = True
    qdrant_vector_size: int = 1024  # Cohere embed-v4

    # ── Redis ──────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379")
    redis_job_queue: str = "omnirag:jobs"
    cache_ttl_query_seconds: int = 300
    cache_ttl_embedding_seconds: int = 600

    # ── Cohere ─────────────────────────────────────────────────────────────────
    cohere_api_key: str = Field(default="")
    cohere_embed_model: str = "embed-english-v3.0"
    cohere_rerank_model: str = "rerank-english-v3.0"
    cohere_embed_batch_size: int = 96
    cohere_rerank_top_n: int = 8
    cohere_rerank_top_k_candidates: int = 50

    # ── OpenRouter ─────────────────────────────────────────────────────────────
    openrouter_api_key: str = Field(default="")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "anthropic/claude-3.5-sonnet"
    openrouter_site_url: str = "https://omnirag.app"
    openrouter_site_name: str = "OmniRAG"

    # ── Agent Loop Limits (hardcoded safety — do not make configurable) ────────
    agent_max_iterations: int = Field(default=5, frozen=True)
    agent_max_cost_usd: float = Field(default=0.05, frozen=True)
    agent_max_tokens_in: int = Field(default=60_000, frozen=True)

    # ── Supabase Storage ───────────────────────────────────────────────────────
    supabase_url: str = Field(default="")
    supabase_service_role_key: str = Field(default="")
    supabase_storage_bucket: str = Field(default="omnirag-documents")
    supabase_s3_endpoint: str = Field(default="")
    supabase_s3_access_key: str = Field(default="")
    supabase_s3_secret_key: str = Field(default="")
    supabase_s3_region: str = Field(default="ap-southeast-1")

    # ── Retrieval ──────────────────────────────────────────────────────────────
    retrieval_rrf_k: int = 60                 # RRF fusion parameter
    retrieval_dense_top_k: int = 50           # candidates before reranking
    retrieval_sparse_top_k: int = 50
    retrieval_final_top_k: int = 8            # after reranking
    retrieval_hyde_enabled: bool = False      # HyDE off by default (latency cost)

    # ── Observability ──────────────────────────────────────────────────────────
    langfuse_public_key: str = Field(default="")
    langfuse_secret_key: str = Field(default="")
    langfuse_host: str = "https://cloud.langfuse.com"
    otel_endpoint: str = "http://localhost:4318"
    otel_service_name: str = "omnirag-api"
    enable_telemetry: bool = True

    @field_validator("postgres_url")
    @classmethod
    def ensure_asyncpg_driver(cls, v: str) -> str:
        """Guarantee the async driver is used — fail fast rather than hang."""
        if "postgresql://" in v and "asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://")
        return v

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def qdrant_collection_prefix(self) -> str:
        return "chunks"

    def qdrant_collection_for_org(self, org_slug: str) -> str:
        return f"{self.qdrant_collection_prefix}_{org_slug}"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton — import this everywhere instead of constructing Settings()."""
    return Settings()


# Module-level alias for convenience
settings = get_settings()
