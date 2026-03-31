# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OmniRAG is a production-grade enterprise multimodal RAG platform. It ingests PDFs, spreadsheets, images, and slide decks, and returns grounded, citation-backed answers at sub-second retrieval latency using a hybrid dense+sparse+structured search pipeline.

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Pydantic v2 |
| Task Queue | Arq (async, Redis Streams) — not Celery |
| Vector Store | Qdrant (HNSW, payload-filtered, per-org collections) |
| OLTP | PostgreSQL 17 (RLS for multi-tenancy, BM25 via tsvector) |
| Cache / MQ | Redis 7 |
| Embeddings | Cohere embed-v4 (1024-dim, batched) |
| Reranker | Cohere rerank-v3.5 |
| LLM | Claude 3.5 Sonnet / GPT-4o via LiteLLM proxy |
| Document Parsing | Docling (IBM) + Tesseract OCR fallback |
| Frontend | Next.js 15 (RSC + SSE streaming) + shadcn/ui + Tailwind v4 |
| Observability | OpenTelemetry + Langfuse + ClickHouse |
| Evaluation | RAGAS (offline + online sampling) |
| Infrastructure | Docker Compose (local) → Fly.io (API/worker) + Vercel (frontend) |

## Monorepo Structure

```
omni-rag/
├── apps/
│   ├── api/               # FastAPI application (routers/, dependencies.py, main.py)
│   ├── worker/            # Arq async worker (jobs/ingest.py, jobs/reindex.py)
│   └── frontend/          # Next.js 15 app
├── services/
│   ├── ingestion/         # parser.py (Docling), chunker.py, embedder.py (Cohere)
│   ├── retrieval/         # dense.py (Qdrant), sparse.py (BM25), fusion.py (RRF), reranker.py
│   ├── orchestrator/      # agent.py (tool-call loop), tools.py, answer_generator.py
│   └── evaluation/        # ragas_runner.py, golden_dataset/
├── core/                  # config.py, db.py, qdrant_client.py, schemas/, logging.py
├── infra/
│   ├── docker/
│   ├── fly/               # fly.toml
│   └── migrations/        # Alembic migrations
└── tests/
    ├── unit/
    ├── integration/       # testcontainers-based (real Qdrant + Postgres)
    └── eval/              # RAGAS eval tests
```

## Common Commands

### Docker / Local Dev
```bash
make up          # docker-compose up -d (all services)
make down        # docker-compose down
make logs        # docker-compose logs -f
make migrate     # run Alembic migrations
make shell       # open psql shell into Postgres
```

### Python Tooling
```bash
make lint        # ruff check .
make format      # ruff format .
make typecheck   # mypy apps/ services/ core/
make test        # pytest tests/unit/ -v
make test-int    # pytest tests/integration/ -v (requires Docker)
make eval        # pytest tests/eval/ -v (RAGAS eval suite)
```

### Single test
```bash
pytest tests/unit/test_chunker.py::test_semantic_overlap -v
```

### Alembic
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

### Frontend
```bash
cd apps/frontend && npm install
npm run dev       # dev server
npm run build     # production build
```

## Architecture: Key Data Flows

### Ingestion Pipeline
```
Upload (S3 presigned URL)
  → Arq job queue (Redis Streams)
  → Docling parse (layout-aware: headers, tables, OCR)
  → Semantic chunker (3-pass: layout → coherence → 15% overlap)
  → Cohere embed-v4 (batched, async, retry with backoff)
  → Qdrant upsert (idempotency key = content SHA-256)
  → Postgres insert (metadata + chunk records)
```

### Query Pipeline
```
User query
  → Redis cache check (TTL=300s)
  → Query analyzer (intent classification)
  → [Simple] Direct retrieval
  → [Complex] Query decomposition agent (max 5 iterations, $0.05 cost ceiling)
  → Hybrid retrieval: dense (Qdrant HNSW) + sparse (Postgres BM25) + structured filter
  → RRF fusion (k=60) → top-50 candidates
  → Cohere rerank-v3.5 → top-8
  → LiteLLM generation (Claude/GPT-4o) with citation injection
  → Faithfulness check (RAGAS inline)
  → SSE streaming response
```

## Critical Design Decisions

- **Qdrant over pgvector**: Qdrant is used for vectors; Postgres is OLTP only. pgvector at scale competes with OLTP I/O and lacks per-tenant index isolation.
- **Arq over Celery**: Arq is async-native with Redis Streams (consumer groups, DLQ). Celery's prefork model wastes RAM on I/O-bound workloads.
- **No LangChain/LlamaIndex**: Custom thin orchestrator (<300 lines) built directly on Anthropic/OpenAI SDKs via LiteLLM. Full observability, no hidden state.
- **Three-channel hybrid retrieval**: Dense + BM25 + structured filter fused via RRF — not single-channel dense alone.
- **Multi-tenancy**: Postgres row-level security (RLS) per org + one Qdrant collection per org (`chunks_{org_slug}`).
- **Chunking strategy**: Layout segmentation → semantic coherence → 15% overlap injection. Fixed-size chunking is explicitly rejected.

## Git Branching

| Branch | Purpose |
|---|---|
| `main` | Protected. Deployable state only. Merges via PR from `dev`. |
| `dev` | Integration branch. All feature branches merge here first. |
| `feature/*` | Cut from `dev`. e.g. `feature/ingestion-pipeline` |
| `hotfix/*` | Cut from `main`, merged back to `main` and `dev`. |
| `release/*` | Cut from `dev` to stabilise a phase milestone. |

## Environment Variables

All config is loaded via Pydantic Settings (`core/config.py`). Copy `.env.example` to `.env` for local dev. Never commit `.env` files. Key variables:

```
POSTGRES_URL=postgresql+asyncpg://...
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379
COHERE_API_KEY=...
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...       # optional, for LiteLLM fallback
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
S3_BUCKET=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

## Evaluation Targets (RAGAS)

| Metric | Target |
|---|---|
| Faithfulness | > 0.90 |
| Answer Relevancy | > 0.85 |
| Context Precision | > 0.82 |
| Context Recall | > 0.80 |
| NDCG@10 | > 0.82 |

CI blocks merge to `main` if Faithfulness drops > 3% from baseline.

## SLOs

- End-to-end query P95 < 3s, P99 < 8s
- Retrieval-only P95 < 200ms
- Ingestion P95 < 60s for docs under 50 pages
- Cost per query < $0.002 average
