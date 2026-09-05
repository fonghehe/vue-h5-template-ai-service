"""Shared fixtures for the AI service test suite."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from app.core.config import Settings, get_settings
from app.main import create_app
from fastapi.testclient import TestClient

# Long enough to satisfy production validation; tests never see real traffic.
TEST_JWT_SECRET = "test-secret-for-the-ai-service-suite-0001"
TEST_ISSUER = "vue-h5-template"
TEST_AUDIENCE = "vue-h5-template-api"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Start every test from a known environment.

    Settings are cached process-wide, so the cache is cleared around each test
    to stop configuration leaking between them.
    """
    for key in (
        "APP_ENV",
        "AI_AUTH_REQUIRED",
        "AI_PROVIDER",
        "AI_API_KEY",
        "AI_RATE_LIMIT_PER_MINUTE",
        "SERVICE_TOKEN",
        "REDIS_URL",
        "JWT_SECRET",
        "JWT_ISSUER",
        "JWT_AUDIENCE",
        "DATABASE_URL",
        "DATABASE_AUTO_CREATE",
        "LOG_FORMAT",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("JWT_SECRET", TEST_JWT_SECRET)
    monkeypatch.setenv("JWT_ISSUER", TEST_ISSUER)
    monkeypatch.setenv("JWT_AUDIENCE", TEST_AUDIENCE)
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("DATABASE_AUTO_CREATE", "true")
    monkeypatch.setenv("LOG_FORMAT", "text")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings() -> Settings:
    """The settings singleton, after the clean-environment fixture applied."""
    return get_settings()


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A test client wired to a freshly built application."""
    with TestClient(create_app()) as test_client:
        yield test_client


def make_token(
    *,
    subject: str = "1",
    name: str = "demo",
    role: str = "admin",
    plan: str = "pro",
    issuer: str = TEST_ISSUER,
    audience: str = TEST_AUDIENCE,
    secret: str = TEST_JWT_SECRET,
    expires_in: timedelta = timedelta(minutes=5),
) -> str:
    """Mint an access token shaped like one issued by the business service."""
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": subject,
            "name": name,
            "role": role,
            "plan": plan,
            "iss": issuer,
            "aud": audience,
            "iat": now,
            "exp": now + expires_in,
        },
        secret,
        algorithm="HS256",
    )


def auth_header(token: str) -> dict[str, str]:
    """Build an Authorization header for a bearer token."""
    return {"Authorization": f"Bearer {token}"}


def chat_body(content: str = "What is Vue?", **extra: Any) -> dict[str, Any]:
    """Build a minimal, contract-shaped chat request body."""
    body: dict[str, Any] = {"messages": [{"role": "user", "content": content}]}
    body.update(extra)
    return body


def parse_sse(text: str) -> list[dict[str, Any]]:
    """Parse an SSE response body into a list of decoded events."""

    events: list[dict[str, Any]] = []
    for line in text.splitlines():
        if line.startswith("data:"):
            events.append(json.loads(line[5:].strip()))
    return events
