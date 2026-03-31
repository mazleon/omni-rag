# Contributing to OmniRAG

## Branch Conventions

| Branch | Purpose | Cut from | Merges into |
|---|---|---|---|
| `main` | Protected. Deployable state only. | — | — |
| `dev` | Integration branch. | `main` | `main` (via PR) |
| `feature/*` | New features or Phase work. | `dev` | `dev` (via PR) |
| `hotfix/*` | Urgent production fixes. | `main` | `main` + `dev` |
| `release/*` | Stabilise a phase milestone. | `dev` | `main` + `dev` |

### Branch Naming

```
feature/phase0-foundation
feature/ingestion-pipeline
feature/hybrid-retrieval
feature/multi-tenancy-rbac
hotfix/qdrant-connection-retry
release/phase1-ingestion-mvp
```

## Pull Request Workflow

1. Cut a branch from `dev` (or `main` for hotfixes)
2. Keep PRs focused — one logical change per PR
3. All PRs require CI to pass before merge
4. PRs to `main` additionally require the RAGAS eval gate to pass
5. At least one reviewer approval required for `main`
6. Squash-merge feature branches into `dev`; regular merge for `dev` → `main`

## CI Checks (must pass on all PRs)

- `ruff check .` — linting
- `mypy apps/ services/ core/` — type checking
- `pytest tests/unit/` — unit tests

## Additional checks on PRs to `main`

- RAGAS offline eval (Faithfulness must not drop > 3% from baseline)

## Commit Message Style

```
<type>(<scope>): <short summary>

Types: feat | fix | refactor | test | docs | chore | perf
Scope: api | worker | retrieval | ingestion | eval | infra | frontend

Examples:
feat(ingestion): add semantic chunker with 15% overlap
fix(retrieval): correct RRF k parameter to 60
test(eval): add RAGAS offline eval harness for phase 3
```

## Branch Protection (configure in GitHub)

### `main`
- Require PR before merging
- Require status checks: `lint`, `typecheck`, `test`, `eval-gate`
- Require 1 approving review
- No force-push
- No deletion

### `dev`
- Require status checks: `lint`, `typecheck`, `test`
- No force-push
