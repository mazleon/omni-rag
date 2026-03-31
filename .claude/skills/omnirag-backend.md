---
name: omnirag-backend
description: Backend development patterns for OmniRAG — FastAPI, Arq workers, Qdrant, PostgreSQL, Redis, Cohere embeddings/reranker, OpenRouter LLM, and Supabase Storage
version: 1.0.0
source: project-spec
triggers:
  - "implement"
  - "add endpoint"
  - "create router"
  - "write worker"
  - "ingest"
  - "retrieval"
  - "embedding"
  - "backend"
---

# OmniRAG Backend Development

You are implementing backend code for **OmniRAG**, a production-grade enterprise RAG platform. Follow these patterns precisely — they are derived directly from the architecture spec.

---

## Project Layout (always write files here)

```
apps/api/
  main.py              # FastAPI app factory
  dependencies.py      # DI: db session, qdrant client, redis pool
  routers/
    documents.py       # /v1/documents/*
    query.py           # /v1/query + /v1/query/retrieval-only
    health.py          # /v1/health, /v1/metrics

apps/worker/
  main.py              # Arq WorkerSettings
  jobs/
    ingest.py          # Document ingestion job
    reindex.py         # Reindex / backfill job

services/
  ingestion/
    parser.py          # Docling wrapper + Tesseract fallback
    chunker.py         # Three-pass semantic chunker
    embedder.py        # Cohere embed-v4 client (batched)
  retrieval/
    dense.py           # Qdrant HNSW search
    sparse.py          # Postgres BM25 (tsvector)
    fusion.py          # RRF k=60
    reranker.py        # Cohere rerank-v3.5
  orchestrator/
    agent.py           # Tool-calling loop (MAX_ITER=5, $0.05 ceiling)
    tools.py           # search_documents, summarize_document, compare_documents
    answer_generator.py
  evaluation/
    ragas_runner.py

core/
  config.py            # Pydantic Settings
  db.py                # SQLAlchemy async engine
  qdrant_client.py     # Qdrant async client wrapper
  schemas/             # Pydantic request/response models
  logging.py           # structlog JSON config
```

---

## FastAPI Conventions

### App factory (`apps/api/main.py`)
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager
from core.logging import configure_logging
from apps.api.routers import documents, query, health

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # startup: init db pool, qdrant client, redis pool
    yield
    # shutdown: close connections

def create_app() -> FastAPI:
    app = FastAPI(title="OmniRAG API", version="1.0.0", lifespan=lifespan)
    app.include_router(documents.router, prefix="/v1/documents", tags=["documents"])
    app.include_router(query.router, prefix="/v1", tags=["query"])
    app.include_router(health.router, prefix="/v1", tags=["health"])
    return app

app = create_app()
```

### Router pattern
```python
from fastapi import APIRouter, Depends, HTTPException, status
from core.schemas.documents import DocumentUploadResponse
from apps.api.dependencies import get_db, get_current_org

router = APIRouter()

@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    request: DocumentUploadRequest,
    db: AsyncSession = Depends(get_db),
    org_id: UUID = Depends(get_current_org),
) -> DocumentUploadResponse:
    ...
```

### Pydantic v2 schemas
```python
from pydantic import BaseModel, Field, UUID4
from datetime import datetime

class DocumentUploadRequest(BaseModel):
    filename: str
    doc_type: str = Field(pattern=r"^(pdf|docx|pptx|xlsx|png|jpeg|html|md)$")
    metadata: dict[str, str] = Field(default_factory=dict)

class DocumentUploadResponse(BaseModel):
    document_id: UUID4
    presigned_url: str
    expires_at: datetime
```

---

## Arq Worker Conventions

### Worker settings (`apps/worker/main.py`)
```python
from arq import create_pool
from arq.connections import RedisSettings
from core.config import settings

class WorkerSettings:
    functions = [ingest_document, reindex_document]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 10
    job_timeout = 300       # 5 min max per job
    keep_result = 3600      # keep result 1hr for dedup checks
    queue_name = "omnirag:jobs"
```

### Job pattern with idempotency
```python
from arq import ArqRedis

async def ingest_document(ctx: dict, document_id: str, org_id: str) -> dict:
    """Idempotent ingestion job — safe to retry."""
    # 1. Check if already indexed (content_hash dedup)
    # 2. Parse → chunk → embed → upsert
    # 3. Update document.status in Postgres
    return {"document_id": document_id, "status": "indexed"}
```

---

## Database Patterns

### Async SQLAlchemy (`core/db.py`)
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(settings.postgres_url, echo=False, pool_size=10)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

### Always use `UUID` primary keys, `TIMESTAMPTZ`, and `JSONB` for metadata:
```python
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import Text, UUID, TIMESTAMPTZ
import uuid, datetime

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("organizations.id"))
    content_hash: Mapped[str] = mapped_column(Text, unique=True)  # SHA-256 for dedup
    status: Mapped[str] = mapped_column(Text, default="pending")   # pending|processing|indexed|error
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMPTZ, default=datetime.datetime.utcnow)
```

---

## Qdrant Patterns

### Collection naming: always `chunks_{org_slug}`
### Point structure:
```python
from qdrant_client.models import PointStruct

point = PointStruct(
    id=str(chunk_id),          # matches chunks.qdrant_id in Postgres
    vector=embedding,           # 1024-dim float32, Cohere embed-v4
    payload={
        "document_id": str(document_id),
        "chunk_id": str(chunk_id),
        "content": chunk_text,  # for reranker context
        "modality": "text",     # text|table|image_caption
        "page_number": 3,
        "doc_type": "pdf",
        "created_at_epoch": int(datetime.now().timestamp()),
        "acl_users": [],        # null = org-wide visible
        "acl_groups": [],
    }
)
```

### Filtered search (always filter by org via collection, not payload):
```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

results = await qdrant.search(
    collection_name=f"chunks_{org_slug}",
    query_vector=query_embedding,
    limit=50,
    query_filter=Filter(
        must=[FieldCondition(key="doc_type", match=MatchValue(value="pdf"))]
    ),
    with_payload=True,
)
```

---

## Cohere Embeddings

```python
import cohere
from core.config import settings

cohere_client = cohere.AsyncClient(settings.cohere_api_key)

async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Batch size = 96. Always use input_type='search_document' for indexing."""
    response = await cohere_client.embed(
        texts=texts,
        model="embed-english-v3.0",   # embed-v4
        input_type="search_document",
        embedding_types=["float"],
    )
    return response.embeddings.float_

async def embed_query(text: str) -> list[float]:
    response = await cohere_client.embed(
        texts=[text],
        model="embed-english-v3.0",
        input_type="search_query",
        embedding_types=["float"],
    )
    return response.embeddings.float_[0]
```

---

## OpenRouter LLM Calls

```python
from openai import AsyncOpenAI
from core.config import settings

openrouter = AsyncOpenAI(
    api_key=settings.openrouter_api_key,
    base_url=settings.openrouter_base_url,  # https://openrouter.ai/api/v1
)

async def generate_answer(messages: list[dict], stream: bool = True):
    return await openrouter.chat.completions.create(
        model=settings.openrouter_default_model,  # anthropic/claude-3.5-sonnet
        messages=messages,
        stream=stream,
        max_tokens=1500,
        temperature=0.1,
        extra_headers={
            "HTTP-Referer": "https://omnirag.app",
            "X-Title": "OmniRAG",
        },
    )
```

### Agent loop (bounded — never remove limits):
```python
MAX_ITERATIONS = 5
MAX_COST_USD   = 0.05
MAX_TOKENS_IN  = 60_000

async def run_agent(query: str, context: QueryContext) -> AgentResult:
    messages = [system_prompt(context), {"role": "user", "content": query}]
    iterations, cost = 0, 0.0
    while iterations < MAX_ITERATIONS:
        response = await openrouter.chat.completions.create(
            model=settings.openrouter_default_model,
            messages=messages,
            tools=TOOLS,
        )
        # track cost from response.usage, enforce ceiling
        if cost > MAX_COST_USD:
            return AgentResult.fallback("Cost ceiling reached")
        if response.choices[0].finish_reason == "stop":
            return AgentResult.success(response.choices[0].message.content)
        # handle tool_calls, append results, loop
        iterations += 1
    return AgentResult.fallback("Max iterations reached")
```

---

## Supabase Storage

```python
from supabase import create_async_client
from core.config import settings

supabase = await create_async_client(settings.supabase_url, settings.supabase_service_role_key)

async def upload_document(file_bytes: bytes, path: str) -> str:
    """Returns the storage path. Always use the service role key server-side."""
    await supabase.storage.from_(settings.supabase_storage_bucket).upload(
        path=path,
        file=file_bytes,
        file_options={"content-type": "application/octet-stream", "upsert": "true"},
    )
    return path

async def get_signed_url(path: str, expires_in: int = 3600) -> str:
    result = await supabase.storage.from_(settings.supabase_storage_bucket).create_signed_url(
        path=path, expires_in=expires_in
    )
    return result["signedURL"]
```

---

## Hybrid Retrieval — RRF Fusion

```python
def reciprocal_rank_fusion(
    rankings: list[list[str]], k: int = 60
) -> list[tuple[str, float]]:
    """Merge N ranked lists via RRF. k=60 is the proven default."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

---

## SSE Streaming Response

```python
from fastapi.responses import StreamingResponse
import json

async def stream_answer(query: str, context: QueryContext):
    async def event_generator():
        async for chunk in generate_answer_stream(query, context):
            token = chunk.choices[0].delta.content or ""
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
        yield f"event: done\ndata: {json.dumps(final_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

---

## Config (`core/config.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    postgres_url: str
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    redis_url: str = "redis://localhost:6379"
    cohere_api_key: str
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_default_model: str = "anthropic/claude-3.5-sonnet"
    supabase_url: str
    supabase_service_role_key: str
    supabase_storage_bucket: str = "omnirag-documents"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    env: str = "development"
    jwt_secret: str

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## Rules to Never Break

- **No LangChain / LlamaIndex** — use OpenRouter directly via `openai` SDK
- **No pgvector for dense search** — Qdrant only. Postgres is OLTP + BM25 only
- **No Celery** — Arq only
- **Agent loops must have MAX_ITERATIONS=5 and MAX_COST_USD=0.05** — hardcoded, not configurable
- **All jobs must be idempotent** — use content SHA-256 as dedup key
- **Chunking**: three-pass (layout → coherence → 15% overlap). Never fixed-size
- **One Qdrant collection per org**: `chunks_{org_slug}`
- **All endpoints require JWT or API key** — no unauthenticated routes except `/v1/health`
- **Every response includes `request_id`** for distributed tracing
