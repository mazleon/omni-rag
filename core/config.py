import os
from typing import Any, Dict, List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, PostgresDsn, RedisDsn

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # App
    PROJECT_NAME: str = "OmniRAG"
    ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/v1"

    # Database
    POSTGRES_URL: str = Field(..., env="POSTGRES_URL")
    DATABASE_URL: Optional[str] = None
    DIRECT_URL: Optional[str] = None

    # Vector Store
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # AI APIs
    COHERE_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_DEFAULT_MODEL: str = "anthropic/claude-3.5-sonnet"

    # Storage
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "omnirag-documents"

    # Observability
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_BASE_URL: str = "https://us.cloud.langfuse.com"

    # Auth
    JWT_SECRET: str = Field(default="dev-secret-change-in-production", env="JWT_SECRET")

settings = Settings()
