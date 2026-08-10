from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import ping_database
from app.schemas.health import HealthResponse
from app.services.health import HealthService

router = APIRouter(tags=["health"])
service = HealthService()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    database_status = "healthy" if ping_database() else "unavailable"
    return service.build_health_response(
        app_name=settings.app_name,
        app_env=settings.app_env,
        database_status=database_status,
    )
