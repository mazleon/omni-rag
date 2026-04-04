# AGENTS.md - OmniRAG Agent Instructions

## Project Overview
Enterprise multimodal RAG platform. FastAPI + Arq + Qdrant + Postgres 17 + Next.js 14.
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
uv run pytest tests/unit/test_chunker.py -v

# Run specific test function
uv run pytest tests/unit/test_chunker.py::test_semantic_overlap -v

# Run with verbose output and short traceback
uv run pytest tests/unit/test_chunker.py::test_semantic_overlap -v --tb=short

# Run tests matching pattern
uv run pytest -k "test_semantic" -v

# Skip integration tests (when Docker unavailable)
OMNIRAG_SKIP_INTEGRATION=1 uv run pytest tests/ -v
```

### Frontend
```bash
cd apps/frontend && npm run dev      # Next.js dev server (localhost:3000)
cd apps/frontend && npm run build    # Production build
cd apps/frontend && npm run lint     # ESLint check
cd apps/frontend && npm run start    # Production server
```

## Code Style

### Python Imports
- Order: stdlib → third-party → first-party (`apps`, `services`, `core`)
- Use `isort` profile (configured in pyproject.toml). Ruff handles this via `I` rule.
- Always use absolute imports. No relative imports across package boundaries.
- Example: `from services.ingestion.chunker import Chunker` not `from .chunker import Chunker`
- Use `from __future__ import annotations` at top of new files

### Python Formatting
- Line length: 100 characters
- Target: Python 3.12
- Run `make format` before committing. Ruff handles all formatting.
- Use trailing commas in multi-line calls/imports

### Python Types
- `mypy --strict` enforced on `apps/`, `services/`, `core/`
- All function signatures must have type annotations (params + return)
- Use `async`/`await` everywhere — no sync I/O in API/worker code
- Prefer `typing.Protocol` over ABCs for interfaces
- Use Pydantic v2 models for all request/response schemas
- Use `str | None` instead of `Optional[str]`

### Python Naming
- `snake_case` for functions, variables, modules
- `PascalCase` for classes, Pydantic models
- `UPPER_SNAKE_CASE` for constants and env var names
- Private helpers prefixed with `_`
- Test files: `test_<module>.py`, test functions: `test_<behavior>()`
- Database table names: `snake_case`, e.g., `organization`, `document_chunk`

### Python Error Handling
- Use custom exception classes in `core/exceptions.py` for domain errors
- Never expose stack traces in API responses — use structured error responses
- Retry external calls (Cohere, Qdrant, Supabase) with `tenacity` backoff
- Log errors with `structlog` (JSON structured logging, see `core/logging.py`)
- Arq jobs: raise exceptions to trigger retry; use DLQ for poison messages

### Python Database
- Use SQLAlchemy 2.0 with async engines (`create_async_engine`)
- Never use sync SQLAlchemy in API/worker code
- Use Alembic for migrations (see `infra/migrations/`)
- Multi-tenancy: Postgres RLS per org + one Qdrant collection per org (`chunks_{org_slug}`)
- Use context-aware connection pooling (see `core/db.py`)

### Python API Design
- Use FastAPI with Pydantic v2 models for request/response schemas
- Use dependency injection for org context (`get_current_org`)
- Return structured error responses with `ErrorResponse` schema
- Use background tasks for long-running operations (Arq)

### Python Testing
- Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- Use `pytest` with `pytest-asyncio` for async tests
- Mock external services (Cohere, Qdrant) in unit tests
- Use testcontainers for real service testing in integration tests
- Mark integration tests with `@pytest.mark.integration`

### Architecture Rules
- **No LangChain/LlamaIndex** — custom thin orchestrator only
- **Qdrant for vectors, Postgres for OLTP** — never pgvector
- **Arq for task queue** — not Celery
- **OpenRouter for LLM** — not direct Anthropic/OpenAI SDKs
- **Supabase Storage** — not AWS S3
- Keep orchestrator < 300 lines. Full observability, no hidden state.

### Frontend (Next.js 14)
- React 18 with TypeScript strict mode
- App Router with route groups: `(auth)`, `(app)`
- State management: TanStack Query for server state, React Context for auth
- Styling: Tailwind CSS 3 with `clsx` + `tailwind-merge` utilities
- Components in `components/`, hooks in `hooks/`, types in `types/`
- API client in `lib/api.ts`, auth utils in `lib/auth.ts`
- Use `lucide-react` for icons
- No `any` types — use proper TypeScript interfaces

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

### Adding a Frontend Page
1. Create route in `apps/frontend/app/(app)/<feature>/page.tsx`
2. Add components in `apps/frontend/components/<feature>/`
3. Add hooks in `apps/frontend/hooks/use<Feature>.ts`
4. Add types in `apps/frontend/types/api.ts`

### Database Migrations
```bash
make migration MSG="add column status to documents"
# Edit generated migration file
make migrate
```
