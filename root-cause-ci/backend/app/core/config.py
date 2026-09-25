import secrets
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ROOT_ENV_PATH = Path(__file__).resolve().parents[3] / ".env"
LOCAL_SECRET_PATH = Path(__file__).resolve().parents[2] / ".local_secret"


def _local_dev_secret() -> str:
    """Stable per-installation secret for development when JWT_SECRET is not configured.

    It must survive restarts: it signs access tokens and encrypts stored GitHub tokens.
    """
    try:
        if LOCAL_SECRET_PATH.exists():
            return LOCAL_SECRET_PATH.read_text(encoding="utf-8").strip()
        value = secrets.token_urlsafe(48)
        LOCAL_SECRET_PATH.write_text(value, encoding="utf-8")
        return value
    except OSError:
        return secrets.token_urlsafe(48)


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
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str = Field(default="llama-3.1-8b-instant", alias="LLM_MODEL")
    llm_api_url: str = Field(default="https://api.groq.com/openai/v1/chat/completions", alias="LLM_API_URL")
    jwt_secret: str = Field(default_factory=_local_dev_secret, alias="JWT_SECRET")
    access_token_ttl_minutes: int = Field(default=60 * 12, alias="ACCESS_TOKEN_TTL_MINUTES")
    token_encryption_key: str | None = Field(default=None, alias="TOKEN_ENCRYPTION_KEY")
    database_connect_timeout: int = Field(default=3, alias="DATABASE_CONNECT_TIMEOUT")
    # NoDecode: accept the documented comma-separated form instead of requiring a JSON list
    cors_origins: Annotated[list[str], NoDecode] = Field(
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


    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
