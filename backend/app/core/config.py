"""Application configuration.

Every setting is loaded from the environment and validated at import time, so a
misconfigured deployment fails on boot rather than on the first request that
happens to touch the missing value.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Runtime -----------------------------------------------------------
    ENVIRONMENT: Literal["local", "test", "staging", "production"] = "local"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "InterviewForge"

    # --- Security ----------------------------------------------------------
    # No default. An unset SECRET_KEY must be a hard boot failure, never a
    # silently-insecure fallback.
    SECRET_KEY: str
    ACCESS_TOKEN_TTL_MINUTES: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 30
    JWT_ALGORITHM: str = "HS256"

    # --- Datastores --------------------------------------------------------
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    REDIS_URL: RedisDsn

    # --- CORS --------------------------------------------------------------
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Third-party -------------------------------------------------------
    # Optional at boot so the API still starts for contributors who only need
    # auth/problems locally. Services that need them raise a clear error.
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-opus-5"
    # Effort trades reasoning depth against latency and cost. Interviews run at
    # "medium" for turn latency; evaluation and design review run at "high".
    ANTHROPIC_INTERVIEW_EFFORT: str = "medium"
    ANTHROPIC_EVALUATION_EFFORT: str = "high"
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None

    # --- Rate limits (requests per window, seconds) -------------------------
    RATE_LIMIT_AUTH: tuple[int, int] = (10, 60)
    RATE_LIMIT_AI: tuple[int, int] = (20, 3600)
    RATE_LIMIT_DEFAULT: tuple[int, int] = (300, 60)

    @field_validator("SECRET_KEY")
    @classmethod
    def _reject_weak_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
