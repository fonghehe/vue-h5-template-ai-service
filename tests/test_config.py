"""Tests for configuration validation."""

from __future__ import annotations

import pytest
from app.core.config import DEVELOPMENT_JWT_PLACEHOLDER, Settings, get_settings

PRODUCTION_BASE = {
    "APP_ENV": "production",
    "SERVICE_TOKEN": "a-real-service-token",
    "JWT_SECRET": "s" * 40,
    "DOCS_ENABLED": "false",
    "LOG_FORMAT": "json",
    "CORS_ORIGINS": "https://app.example.com",
}


def configure(monkeypatch: pytest.MonkeyPatch, **overrides: str) -> None:
    """Rebuild settings from an explicit environment."""
    values = {**PRODUCTION_BASE, **overrides}
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _restore_cache() -> None:
    yield
    get_settings.cache_clear()


def test_valid_production_config_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch)

    settings = get_settings()

    assert settings.is_production
    assert settings.cors_origin_list == ["https://app.example.com"]


def test_defaults_are_development_friendly() -> None:
    settings = Settings()

    assert settings.app_env == "development"
    assert settings.ai_provider == "mock"
    assert settings.ai_auth_required is False
    assert settings.log_format == "text"
    assert "http://localhost:5173" in settings.cors_origin_list


def test_production_requires_service_token(monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, SERVICE_TOKEN="")

    with pytest.raises(ValueError, match="SERVICE_TOKEN"):
        get_settings()


def test_production_rejects_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, DEBUG="true")

    with pytest.raises(ValueError, match="DEBUG"):
        get_settings()


def test_production_rejects_enabled_docs(monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, DOCS_ENABLED="true")

    with pytest.raises(ValueError, match="DOCS_ENABLED"):
        get_settings()


def test_production_requires_json_logs(monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, LOG_FORMAT="text")

    with pytest.raises(ValueError, match="LOG_FORMAT"):
        get_settings()


def test_production_rejects_default_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, JWT_SECRET=DEVELOPMENT_JWT_PLACEHOLDER)

    with pytest.raises(ValueError, match="JWT_SECRET"):
        get_settings()


def test_production_requires_api_key_for_hosted_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure(monkeypatch, AI_PROVIDER="openai-compatible", AI_API_KEY="")

    with pytest.raises(ValueError, match="AI_API_KEY"):
        get_settings()


def test_production_rejects_wildcard_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    configure(monkeypatch, CORS_ORIGINS="*")

    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        get_settings()


def test_auth_required_rejects_placeholder_secret() -> None:
    """Otherwise anyone could mint tokens the service accepts."""
    with pytest.raises(ValueError, match="JWT_SECRET"):
        Settings(ai_auth_required=True, jwt_secret=DEVELOPMENT_JWT_PLACEHOLDER)


def test_auth_required_accepts_real_secret() -> None:
    assert Settings(ai_auth_required=True, jwt_secret="s" * 40).ai_auth_required is True


def test_timeout_is_bounded() -> None:
    with pytest.raises(ValueError):
        Settings(ai_timeout_seconds=0)
    with pytest.raises(ValueError):
        Settings(ai_timeout_seconds=10_000)


def test_rate_limit_is_bounded() -> None:
    with pytest.raises(ValueError):
        Settings(ai_rate_limit_per_minute=0)
    with pytest.raises(ValueError):
        Settings(ai_rate_limit_per_minute=10_000)


def test_origins_are_trimmed_and_empties_dropped() -> None:
    settings = Settings(cors_origins=" https://a.example.com , , https://b.example.com ")

    assert settings.cors_origin_list == ["https://a.example.com", "https://b.example.com"]


def test_trusted_hosts_are_parsed() -> None:
    assert Settings(trusted_hosts="a.example.com,b.example.com").trusted_host_list == [
        "a.example.com",
        "b.example.com",
    ]


def test_constant_time_compare() -> None:
    from app.core.config import constant_time_compare

    assert constant_time_compare("secret", "secret") is True
    assert constant_time_compare("secret", "secret2") is False
