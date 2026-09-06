from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.repositories import router as repositories_router
from app.api.routes.patches import router as patches_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.logging import setup_logging

settings = get_settings()
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    # Initialize DB in background thread so app startup is instant
    asyncio.create_task(asyncio.to_thread(init_db))
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Evidence-first CI/CD failure diagnosis prototype.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(webhooks_router)
app.include_router(auth_router)
app.include_router(analysis_router)
app.include_router(repositories_router)
app.include_router(patches_router)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "status": "running",
        "phase": "phase-1",
    }

