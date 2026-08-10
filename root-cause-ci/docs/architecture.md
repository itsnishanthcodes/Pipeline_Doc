# Architecture

## Phase 1

Phase 1 establishes the repository skeleton and runtime foundation for the later evidence-driven pipeline.

### Why these modules exist

- `backend/app/main.py` exposes the FastAPI application and mounts the first operational endpoint.
- `backend/app/core/config.py` centralizes settings so later phases can add PostgreSQL, GitHub, LLM, and sandbox configuration without scattering environment access.
- `backend/app/core/database.py` establishes a SQLAlchemy entry point for PostgreSQL health checks and future persistence.
- `backend/app/services/health.py` keeps response construction out of the route layer.
- `frontend/src/App.tsx` provides a minimal dashboard shell that will later surface diagnosis, evidence, patch, and verification views.
- `docker-compose.yml` binds the backend, frontend, and PostgreSQL services into a single local development topology.

## Planned phases

Later phases will add ingestion, classification, attribution, evidence chaining, patching, sandbox execution, and verification. Those capabilities are intentionally not enabled yet in Phase 1.
