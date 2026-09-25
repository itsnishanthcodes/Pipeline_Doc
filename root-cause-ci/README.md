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

## Phase 1 functionality (evidence-first diagnosis)

A failed GitHub Actions run is analysed in this order; the LLM is only used after the evidence exists.

1. **Every failed job** is analysed: logs are cleaned, and the failing tests, repository-relative stack
   frames and the decisive error line are extracted, then each job is classified.
2. **Run history** of the same job on the same branch gives a real flaky-test score. A rerun of the same
   commit that passed is a strong flaky signal; likely flaky failures get no patch.
3. **Commit attribution** compares the failing commit with the last green run and ranks every commit in
   between by recency, stack-trace and file overlap, changed functions, test imports and `git blame`.
4. **Constrained patch generation** sends the real content of the target file, the culprit diff and the
   evidence to the LLM. Output that edits another file, changes nothing or breaks Python syntax is rejected.
   The UI shows a unified diff.
5. **Fix pull request and verification**: the PR is created from the stored, validated patch (the client
   cannot send file content). The fix is marked *verified* only when CI passes on the fix commit.
6. **Webhooks**: a completed, failed `workflow_run` event is analysed automatically for users linked to the
   repository (its owner or anyone who analysed it before). For local development, forward GitHub webhooks
   to `http://localhost:8000/webhooks/github` with a tool such as smee.io and set `GITHUB_WEBHOOK_SECRET`.

### Tests and offline evaluation

```bash
cd backend
pytest
python -m evaluation.run_evaluation
```

The evaluation runs the deterministic pipeline on 13 labelled, synthetic failure scenarios and writes
`evaluation/results/results.md`. It compares commit attribution with the naive baseline of blaming the
latest commit. It does not measure LLM patch quality or real-world accuracy.

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
