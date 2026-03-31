# OmniRAG

**Enterprise Multimodal Knowledge Intelligence Platform**

OmniRAG is a production-grade RAG system that ingests millions of heterogeneous documents (PDFs, spreadsheets, images, slide decks) and returns grounded, citation-backed answers at sub-second retrieval latency.

## Architecture Highlights

- **Hybrid retrieval**: Dense (Qdrant HNSW) + Sparse (BM25) + Structured filters, fused via RRF
- **Semantic chunking**: Three-pass layout-aware chunking with 15% overlap — no naive fixed-size windows
- **Async ingestion**: Arq worker fleet via Redis Streams with idempotent deduplication
- **Multi-tenancy**: Postgres RLS + per-org Qdrant collections
- **Evaluation-first**: RAGAS offline eval gates every merge to `main`
- **Cost-bounded agents**: Tool-calling loop with MAX_ITERATIONS=5 and $0.05/query cost ceiling

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Pydantic v2 |
| Task Queue | Arq + Redis Streams |
| Vector Store | Qdrant |
| OLTP | PostgreSQL 17 |
| Embeddings | Cohere embed-v4 |
| Reranker | Cohere rerank-v3.5 |
| LLM | Claude 3.5 / GPT-4o via OpenRouter |
| Object Storage | Supabase Storage (S3-compatible) |
| Frontend | Next.js 15 + shadcn/ui |
| Observability | OpenTelemetry + Langfuse + ClickHouse |

## Quick Start

```bash
cp .env.example .env   # fill in API keys
make up                 # start all Docker services
make migrate            # run database migrations
make test               # run unit tests
```

API runs at `http://localhost:8000` · Qdrant UI at `http://localhost:6333/dashboard` · Jaeger UI at `http://localhost:16686`

## Development

See [CLAUDE.md](CLAUDE.md) for full architecture documentation and all `make` commands.
See [CONTRIBUTING.md](CONTRIBUTING.md) for branching conventions and PR guidelines.

## Evaluation Targets

| Metric | Target |
|---|---|
| Faithfulness | > 0.90 |
| Answer Relevancy | > 0.85 |
| Context Precision | > 0.82 |
| NDCG@10 | > 0.82 |
| Query P95 latency | < 3s |
| Cost per query | < $0.002 |

## Implementation Phases

- **Phase 0** (Foundation): Docker stack, CI, schema, observability
- **Phase 1** (Ingestion MVP): Upload API, Arq workers, Docling, chunker, embedder
- **Phase 2** (Retrieval & Query): Hybrid retrieval, RRF, reranker, SSE streaming, frontend
- **Phase 3** (Hardening): Multi-tenancy, RAGAS eval, load testing, cost tracking
- **Phase 4** (Polish): Fly.io deploy, benchmarks, ADRs, demo dataset
