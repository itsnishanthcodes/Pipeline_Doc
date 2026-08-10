# Root Cause Driven CI/CD Pipeline Automation

Evidence-first CI/CD failure diagnosis and verified remediation prototype.

## Phase 1 status

Implemented:
- Monorepo skeleton
- FastAPI backend with a `GET /health` endpoint
- GitHub webhook ingestion scaffold for workflow failure events
- PostgreSQL service via Docker Compose
- React + TypeScript frontend shell
- Shared environment configuration
- Starter documentation for the research prototype

Not implemented yet:
- Failure classification, attribution, patch generation, sandbox verification, and fix PR automation

## Phase 2 status

Phase 2 adds the first GitHub integration layer:
- GitHub Actions workflow for the demo repository
- `POST /webhooks/github` ingestion endpoint
- Normalized failure and pipeline models for incoming webhook payloads

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
- `sandbox/` - isolated execution placeholder for later phases
- `demo-repository/` - controlled failure scenarios for later evaluation
- `docs/` - architecture, security, API, and research notes

## Phase 1 validation

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

See `.env.example` for the current Phase 1 settings.

## What comes next

Phase 2 will add GitHub Actions integration, webhook ingestion, and failure event capture.
