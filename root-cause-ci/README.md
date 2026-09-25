# Root Cause Driven CI/CD Pipeline Automation

Evidence-first CI/CD failure diagnosis prototype for GitHub Actions.

## Current implementation

The current prototype includes:
- FastAPI health, authentication, repository, analysis, webhook, and patch routes
- Signed expiring auth tokens and protected API middleware
- GitHub Actions run/job/log retrieval and webhook signature validation
- Persistent webhook delivery records with duplicate-delivery replay
- Deterministic failure classification and in-memory flaky-test scoring
- Local Git metadata, diff, blame, and candidate scoring services
- Python Tree-sitter parsing and NetworkX graph primitives
- Evidence-chain generation and explainable candidate contributions
- Evidence-gated LLM summaries and unified-diff patch requests
- Unified-diff scope validation and a persisted verification gate before PR creation
- React dashboard for repository analysis, history, evidence, and explicit stage status

The following remain incomplete and are intentionally shown as skipped in the UI:
- Durable normalized failure/test/candidate/evidence domain storage
- Complete AST/import/dependency analysis connected to GitHub analysis
- Docker sandbox execution and test-result capture
- Patch application, verification orchestration, and verified Fix PR creation
- Research dataset, evaluation metrics, and ablation runner

## Quick start

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Start PostgreSQL, backend, and frontend:

```bash
docker compose up --build
```

3. Backend health endpoint:

```bash
curl http://localhost:8000/health
```

4. Frontend dashboard:

Open `http://localhost:5173`

## Repository layout

- `backend/` - FastAPI application and tests
- `frontend/` - React dashboard shell
- `sandbox/` - reserved for isolated patch verification
- `demo-repository/` - small GitHub Actions test repository
- `docs/` - architecture, security, API, and research notes

## Validation

Run backend tests from `backend/`:

```bash
pytest
```

Run frontend build from `frontend/`:

```bash
npm install
npm run build
```

## Environment variables

See `.env.example` for the current settings. `AUTH_SECRET` and GitHub/LLM credentials must be set outside source control.
