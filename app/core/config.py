"""Application settings.

Values come from the environment, optionally seeded from a `.env` file.
Settings are validated eagerly: an unsafe combination fails at import time
rather than at the first request, so a broken deployment never serves traffic.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholder secret accepted in development so that a fresh clone runs with no
# setup. Startup refuses to boot with it once AI_AUTH_REQUIRED is on in
# production, because every token minted with it would be forgeable.
DEVELOPMENT_JWT_PLACEHOLDER = "dev-only-change-me-before-production"

ServiceEnv = Literal["development", "test", "production"]
AIProviderName = Literal["mock", "openai-compatible"]


class Settings(BaseSettings):
    """Runtime configuration of the AI service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Service identity -------------------------------------------------
    app_name: str = "Vue H5 AI Service"
    app_env: ServiceEnv = "development"
    debug: bool = False
    docs_enabled: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # `json` for production log shipping, `text` for local development.
    log_format: Literal["json", "text"] = "text"

    # --- HTTP surface -----------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    trusted_hosts: str = "localhost,127.0.0.1,testserver"

    # --- Security ---------------------------------------------------------
    # Shared secret used by the browser gateway or BFF. When set, a matching
    # Bearer token is accepted as an internal service principal.
    service_token: str | None = None
    # When false (the default) anonymous access is allowed, which keeps local
    # development friction-free. Enable it before exposing the service.
    ai_auth_required: bool = False
    # Must match the business service so access tokens minted there validate here.
    jwt_secret: str = DEVELOPMENT_JWT_PLACEHOLDER
    jwt_issuer: str = "vue-h5-template"
    jwt_audience: str = "vue-h5-template-api"

    # --- Provider ---------------------------------------------------------
    ai_provider: AIProviderName = "mock"
    ai_base_url: str = "https://api.openai.com/v1"
    ai_api_key: str | None = None
    ai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    # Hard ceiling on a single conversation turn, in characters.
    ai_max_output_chars: int = Field(default=20_000, ge=1, le=200_000)

    # --- Rate limiting ----------------------------------------------------
    ai_rate_limit_per_minute: int = Field(default=20, ge=1, le=1000)
    # Empty means "use the in-process limiter"; suitable for single instances.
    redis_url: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        """Parsed CORS allow-list."""
        return _split(self.cors_origins)

    @property
    def trusted_host_list(self) -> list[str]:
        """Parsed trusted-host allow-list."""
        return _split(self.trusted_hosts)

    @property
    def is_production(self) -> bool:
        """Whether the service runs with production semantics."""
        return self.app_env == "production"

    @model_validator(mode="after")
    def validate_production(self) -> Self:
        """Reject configurations that would be unsafe in production."""
        if not self.is_production:
            return self

        if self.debug:
            raise ValueError("DEBUG must be false in production")
        if self.docs_enabled:
            raise ValueError("DOCS_ENABLED must be false in production")
        if self.log_format != "json":
            raise ValueError("LOG_FORMAT must be json in production")
        if not self.service_token:
            raise ValueError("SERVICE_TOKEN is required in production")
        if self.jwt_secret == DEVELOPMENT_JWT_PLACEHOLDER:
            raise ValueError("JWT_SECRET must be replaced with a random value in production")
        if self.ai_provider == "openai-compatible" and not self.ai_api_key:
            raise ValueError("AI_API_KEY is required when AI_PROVIDER is openai-compatible")
        if "*" in self.cors_origin_list:
            raise ValueError("CORS_ORIGINS must not contain * in production")
        return self

    @model_validator(mode="after")
    def validate_auth(self) -> Self:
        """Require a real JWT secret whenever authentication is enforced."""
        if self.ai_auth_required and self.jwt_secret == DEVELOPMENT_JWT_PLACEHOLDER:
            raise ValueError(
                "JWT_SECRET must be replaced when AI_AUTH_REQUIRED is enabled; "
                "otherwise anyone can mint a token this service accepts"
            )
        return self


def _split(value: str) -> list[str]:
    """Split a comma separated setting into trimmed, non-empty entries."""
    return [part.strip() for part in value.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()


def constant_time_compare(left: str, right: str) -> bool:
    """Compare two secret strings without leaking their length or content."""
    return secrets.compare_digest(left, right)
