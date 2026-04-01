# AGENTS.md - OmniRAG Agent Instructions

## Project Overview
Enterprise multimodal RAG platform. FastAPI + Arq + Qdrant + Postgres 17 + Next.js 15.
Full architecture in `CLAUDE.md` — read it first for data flows, design decisions, and SLOs.

## Commands

### Docker / Local Dev
```bash
make up          # docker compose up -d (postgres, qdrant, redis, clickhouse, jaeger)
make down        # docker compose down
make logs        # docker compose logs -f
make shell       # psql shell
make migrate     # alembic upgrade head
make migration MSG="description"  # alembic revision --autogenerate
make rollback    # alembic downgrade -1
```

### Python
```bash
make lint        # ruff check .
make format      # ruff format .
make lint-fix    # ruff check --fix .
make typecheck   # mypy apps/ services/ core/
make test        # pytest tests/unit/ -v --tb=short
make test-int    # pytest tests/integration/ -v --tb=short
make eval        # pytest tests/eval/ -v --tb=short
make test-all    # pytest tests/ -v --tb=short
make coverage    # pytest with coverage report
make clean       # remove __pycache__, .pyc, .pytest_cache, .mypy_cache, .ruff_cache
```

### Single Test
```bash
pytest tests/unit/test_chunker.py::test_semantic_overlap -v
```

### Frontend
```bash
cd apps/frontend && npm run dev
cd apps/frontend && npm run build
```

## Code Style

### Imports
- Order: stdlib → third-party → first-party (`apps`, `services`, `core`)
- Use `isort` profile (configured in pyproject.toml). Ruff handles this via `I` rule.
- Always use absolute imports. No relative imports across package boundaries.

### Formatting
- Line length: 100 characters
- Target: Python 3.12
- Run `make format` before committing. Ruff handles all formatting.

### Types
- `mypy --strict` enforced on `apps/`, `services/`, `core/`
- All function signatures must have type annotations (params + return)
- Use `async`/`await` everywhere — no sync I/O in API/worker code
- Prefer `typing.Protocol` over ABCs for interfaces
- Use Pydantic v2 models for all request/response schemas

### Naming
- `snake_case` for functions, variables, modules
- `PascalCase` for classes, Pydantic models
- `UPPER_SNAKE_CASE` for constants and env var names
- Private helpers prefixed with `_`
- Test files: `test_<module>.py`, test functions: `test_<behavior>()`

### Error Handling
- Use custom exception classes in `core/` for domain errors
- Never expose stack traces in API responses — use structured error responses
- Retry external calls (Cohere, Qdrant, Supabase) with `tenacity` backoff
- Log errors with `structlog` (JSON structured logging, see `core/logging.py`)
- Arq jobs: raise exceptions to trigger retry; use DLQ for poison messages

### Architecture Rules
- **No LangChain/LlamaIndex** — custom thin orchestrator only
- **Qdrant for vectors, Postgres for OLTP** — never pgvector
- **Arq for task queue** — not Celery
- **OpenRouter for LLM** — not direct Anthropic/OpenAI SDKs
- **Supabase Storage** — not AWS S3
- Multi-tenancy: Postgres RLS per org + one Qdrant collection per org (`chunks_{org_slug}`)
- Keep orchestrator < 300 lines. Full observability, no hidden state.

### Git
- Branch from `dev`. Feature branches: `feature/*`, hotfixes: `hotfix/*`
- Never commit `.env` files or secrets
- CI blocks merge if RAGAS Faithfulness drops > 3% from baseline
