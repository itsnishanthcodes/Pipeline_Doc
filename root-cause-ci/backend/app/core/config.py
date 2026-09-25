from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(ROOT_ENV_PATH), "../.env", ".env"),
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
    auth_secret: str = Field(default="change-this-auth-secret", alias="AUTH_SECRET")
    auth_token_expire_minutes: int = Field(default=60, alias="AUTH_TOKEN_EXPIRE_MINUTES")
    patch_confidence_threshold: float = Field(default=0.75, alias="PATCH_CONFIDENCE_THRESHOLD")
    sandbox_image: str = Field(default="python:3.12-slim", alias="SANDBOX_IMAGE")
    sandbox_timeout_seconds: int = Field(default=300, alias="SANDBOX_TIMEOUT_SECONDS")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str = Field(default="llama-3.1-8b-instant", alias="LLM_MODEL")
    llm_api_url: str = Field(default="https://api.groq.com/openai/v1/chat/completions", alias="LLM_API_URL")
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
