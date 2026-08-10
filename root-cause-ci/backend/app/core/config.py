from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Root Cause CI")
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(
        default="postgresql+psycopg://rootcause:rootcause@localhost:5432/rootcause",
        alias="DATABASE_URL",
    )
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    github_repository: str | None = Field(default=None, alias="GITHUB_REPOSITORY")
    github_webhook_secret: str | None = Field(default=None, alias="GITHUB_WEBHOOK_SECRET")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173"],
        alias="BACKEND_CORS_ORIGINS",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if value is None:
            return ["http://localhost:5173"]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return [str(value)]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
