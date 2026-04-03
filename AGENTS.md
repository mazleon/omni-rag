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
make shell       # psql shell into postgres container
make migrate     # alembic upgrade head
make migration MSG="description"  # alembic revision --autogenerate -m "description"
make rollback    # alembic downgrade -1
```

### Python
```bash
make lint        # ruff check .
make format      # ruff format .
make lint-fix    # ruff check --fix .
make typecheck   # mypy apps/ services/ core/ --strict
make test        # pytest tests/unit/ -v --tb=short
make test-int    # pytest tests/integration/ -v --tb=short (requires Docker)
make eval        # pytest tests/eval/ -v --tb=short (RAGAS eval suite)
make test-all    # pytest tests/ -v --tb=short
make coverage    # pytest with coverage report (coverage run + coverage report)
make clean       # remove __pycache__, .pyc, .pytest_cache, .mypy_cache, .ruff_cache
```

### Single Test
```bash
# Run specific test file
pytest tests/unit/test_chunker.py -v

# Run specific test function
pytest tests/unit/test_chunker.py::test_semantic_overlap -v

# Run with verbose output and short traceback
pytest tests/unit/test_chunker.py::test_semantic_overlap -v --tb=short

# Run tests matching pattern
pytest -k "test_semantic" -v
```

### Frontend
```bash
cd apps/frontend && npm run dev
cd apps/frontend && npm run build
cd apps/frontend && npm run lint
```

## Code Style

### Imports
- Order: stdlib → third-party → first-party (`apps`, `services`, `core`)
- Use `isort` profile (configured in pyproject.toml). Ruff handles this via `I` rule.
- Always use absolute imports. No relative imports across package boundaries.
- Example: `from services.ingestion.chunker import Chunker` not `from .chunker import Chunker`

### Formatting
- Line length: 100 characters
- Target: Python 3.12
- Run `make format` before committing. Ruff handles all formatting.
- Use trailing commas in multi-line calls/imports

### Types
- `mypy --strict` enforced on `apps/`, `services/`, `core/`
- All function signatures must have type annotations (params + return)
- Use `async`/`await` everywhere — no sync I/O in API/worker code
- Prefer `typing.Protocol` over ABCs for interfaces
- Use Pydantic v2 models for all request/response schemas
- Explicit `None` type hints (not `Optional[x]`), e.g., `name: str | None`

### Naming
- `snake_case` for functions, variables, modules
- `PascalCase` for classes, Pydantic models
- `UPPER_SNAKE_CASE` for constants and env var names
- Private helpers prefixed with `_`
- Test files: `test_<module>.py`, test functions: `test_<behavior>()`
- Database table names: `snake_case`, e.g., `organization`, `document_chunk`

### Error Handling
- Use custom exception classes in `core/exceptions.py` for domain errors
- Never expose stack traces in API responses — use structured error responses
- Retry external calls (Cohere, Qdrant, Supabase) with `tenacity` backoff
- Log errors with `structlog` (JSON structured logging, see `core/logging.py`)
- Arq jobs: raise exceptions to trigger retry; use DLQ for poison messages

### Database
- Use SQLAlchemy 2.0 with async engines (`create_async_engine`)
- Never use sync SQLAlchemy in API/worker code
- Use Alembic for migrations (see `infra/migrations/`)
- Multi-tenancy: Postgres RLS per org + one Qdrant collection per org (`chunks_{org_slug}`)
- Use context-aware connection pooling (see `core/db.py`)

### API Design
- Use FastAPI with Pydantic v2 models for request/response schemas
- Use dependency injection for org context (`get_current_org`)
- Return structured error responses with `ErrorResponse` schema
- Use background tasks for long-running operations (Arq)

### Testing
- Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- Use `pytest` with `pytest-asyncio` for async tests
- Mock external services (Cohere, Qdrant) in unit tests
- Use testcontainers for real service testing in integration tests

### Architecture Rules
- **No LangChain/LlamaIndex** — custom thin orchestrator only
- **Qdrant for vectors, Postgres for OLTP** — never pgvector
- **Arq for task queue** — not Celery
- **OpenRouter for LLM** — not direct Anthropic/OpenAI SDKs
- **Supabase Storage** — not AWS S3
- Keep orchestrator < 300 lines. Full observability, no hidden state.

### Git
- Branch from `dev`. Feature branches: `feature/*`, hotfixes: `hotfix/*`
- Never commit `.env` files or secrets
- CI blocks merge if RAGAS Faithfulness drops > 3% from baseline

## Common Patterns

### Adding a New Service
1. Create module under `services/<domain>/`
2. Add type-safe config in `core/config.py`
3. Register client in `core/` (e.g., `qdrant_client.py`)
4. Add unit tests in `tests/unit/`
5. Update `CLAUDE.md` if architecture changes

### Adding a New API Endpoint
1. Create router in `apps/api/routers/<feature>.py`
2. Add Pydantic schemas in `core/schemas/`
3. Add dependencies in `apps/api/dependencies.py`
4. Register router in `apps/api/main.py`

### Database Migrations
```bash
make migration MSG="add column status to documents"
# Edit generated migration file
make migrate
```