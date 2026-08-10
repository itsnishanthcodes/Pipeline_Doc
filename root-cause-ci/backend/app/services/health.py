from app.schemas.health import HealthResponse


class HealthService:
    def build_health_response(self, app_name: str, app_env: str, database_status: str) -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=app_name,
            environment=app_env,
            database=database_status,
        )
