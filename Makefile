.DEFAULT_GOAL := help
COMPOSE = docker compose

.PHONY: help up down logs shell migrate lint format typecheck test test-int eval clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Docker ──────────────────────────────────────────────────────────────────

up: ## Start all services (detached)
	$(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) down

logs: ## Tail all service logs
	$(COMPOSE) logs -f

shell: ## Open psql shell into Postgres
	$(COMPOSE) exec postgres psql -U omnirag -d omnirag

# ── Database ─────────────────────────────────────────────────────────────────

migrate: ## Run Alembic migrations (head)
	alembic upgrade head

migration: ## Generate a new migration (usage: make migration MSG="add users table")
	alembic revision --autogenerate -m "$(MSG)"

rollback: ## Roll back one migration
	alembic downgrade -1

# ── Code Quality ─────────────────────────────────────────────────────────────

lint: ## Run ruff linter
	ruff check .

format: ## Run ruff formatter
	ruff format .

lint-fix: ## Run ruff with auto-fix
	ruff check --fix .

typecheck: ## Run mypy type checker
	mypy apps/ services/ core/

# ── Testing ───────────────────────────────────────────────────────────────────

test: ## Run unit tests
	pytest tests/unit/ -v --tb=short

test-int: ## Run integration tests (requires Docker services)
	pytest tests/integration/ -v --tb=short

eval: ## Run RAGAS evaluation suite
	pytest tests/eval/ -v --tb=short

test-all: ## Run all tests
	pytest tests/ -v --tb=short

coverage: ## Run tests with coverage report
	pytest tests/unit/ --cov=apps --cov=services --cov=core --cov-report=term-missing

# ── Utilities ─────────────────────────────────────────────────────────────────

clean: ## Remove Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -name "*.pyc" -delete; \
	find . -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null; \
	find . -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null; \
	find . -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null; \
	echo "Cleaned."
