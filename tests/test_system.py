"""Tests for the health and readiness probes and request correlation."""

from __future__ import annotations

import pytest
from app import __version__
from app.core.config import get_settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_health_reports_service_identity(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["service"] == "ai"
    assert body["data"]["status"] == "ok"
    assert body["data"]["version"] == __version__
    assert body["data"]["provider"] == "mock"


def test_health_envelope_matches_frontend_contract(client: TestClient) -> None:
    """`@vh5/api-client` requires code, message and data on every response."""
    body = client.get("/health").json()

    assert set(body) == {"code", "message", "data", "error", "requestId"}
    assert body["code"] == 0
    assert body["error"] is None


def test_ready_reports_ready_when_limiter_is_up(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ready"
    assert response.json()["data"]["rateLimiter"] == "memory"


def test_request_id_is_echoed_back(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "trace-abc-123"})

    assert response.headers["X-Request-ID"] == "trace-abc-123"
    assert response.json()["requestId"] == "trace-abc-123"


def test_request_id_is_generated_when_absent(client: TestClient) -> None:
    response = client.get("/health")

    assert response.headers["X-Request-ID"]
    assert response.json()["requestId"]


def test_unknown_host_is_rejected(client: TestClient) -> None:
    response = client.get("/health", headers={"Host": "evil.example.com"})

    assert response.status_code == 400


def test_cors_preflight_is_answered(client: TestClient) -> None:
    response = client.options(
        "/api/ai/chat",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_unknown_origin_is_not_allowed(client: TestClient) -> None:
    response = client.options(
        "/api/ai/chat",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers


def test_docs_are_enabled_in_development(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_docs_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCS_ENABLED", "false")
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as secured:
            assert secured.get("/docs").status_code == 404
            assert secured.get("/openapi.json").status_code == 404
    finally:
        get_settings.cache_clear()
