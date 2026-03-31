---
name: omnirag-docker
description: Docker containerization patterns for OmniRAG — Dockerfile authoring, multi-stage builds, docker-compose service orchestration, healthchecks, and local dev workflow
version: 1.0.0
source: project-spec
triggers:
  - "docker"
  - "dockerfile"
  - "container"
  - "compose"
  - "healthcheck"
  - "containerize"
  - "deploy"
  - "infra"
---

# OmniRAG Docker & Containerization

You are writing Docker configuration for **OmniRAG**. The stack has 7 services: `api`, `worker`, `postgres`, `qdrant`, `redis`, `clickhouse`, `jaeger`. Follow these patterns precisely.

---

## File Locations

```
infra/
└── docker/
    ├── Dockerfile.api        # FastAPI service
    ├── Dockerfile.worker     # Arq worker service
    └── .dockerignore         # shared ignore rules

docker-compose.yml            # local dev (all services)
docker-compose.prod.yml       # production overrides (Fly.io)
```

---

## Dockerfile.api (multi-stage)

```dockerfile
# infra/docker/Dockerfile.api
# ── Stage 1: dependency installer ────────────────────────────────────────────
FROM python:3.12-slim AS deps
WORKDIR /app

# System deps for Docling (PDF parsing) and Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install --no-cache-dir -e ".[api]"

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=deps /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=deps /usr/local/bin /usr/local/bin

COPY apps/api ./apps/api
COPY services  ./services
COPY core      ./core

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

---

## Dockerfile.worker (single-stage, no HTTP)

```dockerfile
# infra/docker/Dockerfile.worker
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install --no-cache-dir -e ".[worker]"

COPY apps/worker ./apps/worker
COPY services    ./services
COPY core        ./core

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Arq worker — no HTTP port, no HEALTHCHECK via HTTP
CMD ["python", "-m", "arq", "apps.worker.main.WorkerSettings"]
```

---

## .dockerignore

```
# infra/docker/.dockerignore  (place at repo root too)
.git
.github
.claude
**/__pycache__
**/*.pyc
**/.pytest_cache
**/.mypy_cache
**/.ruff_cache
*.egg-info
.env
.env.*
!.env.example
node_modules
apps/frontend/.next
apps/frontend/out
postgres_data
qdrant_storage
redis_data
clickhouse_data
*.log
coverage.xml
.coverage
```

---

## docker-compose.yml (local dev)

### Core principles:
- All services use **named volumes** (no bind mounts for data)
- All services have **healthchecks** — `depends_on` uses `condition: service_healthy`
- API and worker bind-mount source dirs for hot-reload in dev
- Every service declares `restart: unless-stopped`

```yaml
version: "3.9"

x-common-env: &common-env
  POSTGRES_URL: postgresql+asyncpg://omnirag:omnirag@postgres:5432/omnirag
  QDRANT_URL: http://qdrant:6333
  REDIS_URL: redis://redis:6379
  ENV: development

services:

  # ── API ────────────────────────────────────────────────────────────────────
  api:
    build:
      context: ../..
      dockerfile: infra/docker/Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      <<: *common-env
    env_file: ../../.env
    depends_on:
      postgres: { condition: service_healthy }
      qdrant:   { condition: service_healthy }
      redis:    { condition: service_healthy }
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s
    volumes:
      - ../../apps/api:/app/apps/api          # hot-reload
      - ../../services:/app/services
      - ../../core:/app/core

  # ── Worker ─────────────────────────────────────────────────────────────────
  worker:
    build:
      context: ../..
      dockerfile: infra/docker/Dockerfile.worker
    environment:
      <<: *common-env
    env_file: ../../.env
    depends_on:
      postgres: { condition: service_healthy }
      qdrant:   { condition: service_healthy }
      redis:    { condition: service_healthy }
    restart: unless-stopped
    volumes:
      - ../../apps/worker:/app/apps/worker
      - ../../services:/app/services
      - ../../core:/app/core

  # ── PostgreSQL 17 ──────────────────────────────────────────────────────────
  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: omnirag
      POSTGRES_PASSWORD: omnirag
      POSTGRES_DB: omnirag
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U omnirag -d omnirag"]
      interval: 5s
      timeout: 5s
      retries: 10

  # ── Qdrant ─────────────────────────────────────────────────────────────────
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"   # REST + UI
      - "6334:6334"   # gRPC
    volumes:
      - qdrant_storage:/qdrant/storage
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 10s

  # ── Redis 7 ────────────────────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  # ── ClickHouse (analytics + RAGAS logs) ───────────────────────────────────
  clickhouse:
    image: clickhouse/clickhouse-server:latest
    ports:
      - "8123:8123"   # HTTP interface
      - "9000:9000"   # native TCP
    volumes:
      - clickhouse_data:/var/lib/clickhouse
    restart: unless-stopped
    ulimits:
      nofile: { soft: 262144, hard: 262144 }
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8123/ping"]
      interval: 10s
      timeout: 5s
      retries: 10

  # ── Jaeger (OTEL traces) ───────────────────────────────────────────────────
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    restart: unless-stopped

volumes:
  postgres_data:
  qdrant_storage:
  redis_data:
  clickhouse_data:
```

---

## docker-compose.prod.yml (Fly.io overrides)

```yaml
# Override for production — no source bind-mounts, no local ports, no Jaeger
version: "3.9"

services:
  api:
    volumes: []        # remove dev bind-mounts
    environment:
      ENV: production

  worker:
    volumes: []

  # External services on Fly.io — managed separately, not in compose
  postgres:   { deploy: { replicas: 0 } }
  qdrant:     { deploy: { replicas: 0 } }
  redis:      { deploy: { replicas: 0 } }
  clickhouse: { deploy: { replicas: 0 } }
  jaeger:     { deploy: { replicas: 0 } }
```

---

## Makefile Targets (docker)

```makefile
COMPOSE = docker compose -f docker-compose.yml

up:      ## Start all services (detached)
	$(COMPOSE) up -d

down:    ## Stop all services
	$(COMPOSE) down

restart: ## Restart a service (usage: make restart svc=api)
	$(COMPOSE) restart $(svc)

build:   ## Rebuild images without cache
	$(COMPOSE) build --no-cache

logs:    ## Tail all logs (or: make logs svc=api)
	$(COMPOSE) logs -f $(svc)

shell:   ## psql into Postgres
	$(COMPOSE) exec postgres psql -U omnirag -d omnirag

redis-cli: ## Redis CLI
	$(COMPOSE) exec redis redis-cli

qdrant-ui: ## Open Qdrant dashboard in browser
	open http://localhost:6333/dashboard

jaeger-ui: ## Open Jaeger trace UI in browser
	open http://localhost:16686

ps:      ## Show service status
	$(COMPOSE) ps
```

---

## Healthcheck Cheat Sheet

| Service | Healthcheck command |
|---|---|
| API | `curl -f http://localhost:8000/v1/health` |
| Postgres | `pg_isready -U omnirag -d omnirag` |
| Qdrant | `curl -f http://localhost:6333/healthz` |
| Redis | `redis-cli ping` |
| ClickHouse | `curl -f http://localhost:8123/ping` |

---

## Troubleshooting Runbook

### Service won't start
```bash
docker compose logs <service> --tail=50   # read actual error
docker compose ps                          # see exit codes
```

### Qdrant storage permission error
```bash
docker compose down -v    # wipe volume — OK in dev, NOT in prod
docker compose up -d qdrant
```

### Postgres "role does not exist"
```bash
docker compose down postgres
docker volume rm omni-rag_postgres_data   # full reset
docker compose up -d postgres
make migrate
```

### API can't reach Postgres/Qdrant/Redis
- Service names ARE the hostnames inside Docker network (`postgres`, `qdrant`, `redis`)
- Never use `localhost` in service environment vars — use service names
- Check `depends_on` has `condition: service_healthy` (not just `service_started`)

### Worker not picking up jobs
```bash
docker compose exec redis redis-cli LLEN omnirag:jobs   # queue depth
docker compose logs worker --tail=50
```

---

## Rules to Never Break

- **All `depends_on` entries must use `condition: service_healthy`** — `service_started` is not sufficient for production services
- **Never use `localhost` in container environment variables** — use Docker service names (`postgres`, `qdrant`, `redis`)
- **Named volumes only** — never bind-mount data directories (`postgres_data`, `qdrant_storage`, etc.)
- **Multi-stage builds for API** — keeps the runtime image slim; dev dependencies stay in the `deps` stage
- **Worker has no `HEALTHCHECK`** — it's a background process; monitor via Arq's Redis queue depth instead
- **`.env` is bind-mounted via `env_file`** — never hard-code secrets in `docker-compose.yml`
- **Always set `--maxmemory` and `--maxmemory-policy` on Redis** — prevents unbounded memory growth
- **`PYTHONUNBUFFERED=1`** must be set in all Python containers — ensures logs stream to Docker immediately
