"""Regression tests for resource, transaction and HTTP behavior."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from app.core.config import Settings, get_settings
from app.core.logging import ContextFilter, request_scope
from app.db.repositories import UsageRepository
from app.main import create_app
from app.providers.base import MockChatProvider
from fastapi.testclient import TestClient

from tests.conftest import auth_header, chat_body, make_token, parse_sse


def test_versioned_aliases_and_pagination(client: TestClient) -> None:
    headers = auth_header(make_token())
    ids = [
        client.post("/api/v1/conversations", headers=headers, json={"title": str(i)}).json()["data"]["id"]
        for i in range(3)
    ]
    first = client.get("/api/conversations?page_size=1", headers=headers).json()["data"]
    second = client.get("/api/v1/conversations?page=2&page_size=1", headers=headers).json()["data"]
    assert len(first) == len(second) == 1 and first[0]["id"] != second[0]["id"]
    assert first[0]["id"] in ids
    assert client.get("/api/v1/conversations?page_size=100000", headers=headers).status_code == 422
    assert client.post("/api/v1/ai/chat", json=chat_body()).status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/api/v1/conversations/{conversation_id}/messages" in schema["paths"]


def test_completed_turn_and_usage_roll_back_together(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = auth_header(make_token())
    cid = client.post("/api/conversations", json={}, headers=headers).json()["data"]["id"]

    async def fail(*_: object) -> None:
        raise RuntimeError("private persistence failure")

    monkeypatch.setattr(UsageRepository, "add", fail)
    response = client.post(
        f"/api/conversations/{cid}/messages", json={"content": "hello", "mode": "chat"}, headers=headers
    )
    events = parse_sse(response.text)
    assert events[-1]["type"] == "error" and events[-1]["code"] == 5000
    assert events[-1]["requestId"] == response.headers["X-Request-ID"]
    assert "private persistence failure" not in response.text
    detail = client.get(f"/api/conversations/{cid}", headers=headers).json()["data"]
    assert [row["role"] for row in detail["messages"]] == ["user"]
    assert client.get("/api/usage/me", headers=headers).json()["data"]["requests"] == 0
    assert client.app.state.stream_quota._leases == {}


def test_database_and_redis_outages_return_degraded_readiness(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(type(client.app.state.database), "ping", AsyncMock(side_effect=OSError("database offline")))
    response = client.get("/ready")
    assert response.status_code == 503 and response.json()["data"]["status"] == "degraded"
    assert client.get("/health").status_code == 200


def test_health_never_exposes_redis_url(client: TestClient) -> None:
    client.app.state.settings.redis_url = "redis://private:credential@redis.internal:6379/0"
    response = client.get("/health")
    assert response.json()["data"]["rateLimiter"] == "redis"
    assert "credential" not in response.text and "internal" not in response.text


def test_http_errors_share_envelope_and_invalid_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/missing", headers={"X-Request-ID": "bad id " + "x" * 300})
    assert response.status_code == 404 and response.json()["code"] == 4040
    assert response.json()["requestId"] == response.headers["X-Request-ID"]
    assert len(response.headers["X-Request-ID"]) <= 128
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_request_body_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_REQUEST_BYTES", "1024")
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        response = client.post("/api/ai/chat", json=chat_body("x" * 2000))
        assert response.status_code == 413 and response.json()["code"] == 4000


@pytest.mark.parametrize("metadata", ["[]", '"private value"', "null", "{broken"])
def test_upload_metadata_requires_object(client: TestClient, metadata: str) -> None:
    response = client.post(
        "/api/knowledge/documents",
        headers=auth_header(make_token()),
        files={"file": ("test.txt", b"hello", "text/plain")},
        data={"metadata": metadata},
    )
    assert response.status_code == 422


def test_invalid_pdf_returns_validation_error(client: TestClient) -> None:
    response = client.post(
        "/api/knowledge/documents",
        headers=auth_header(make_token()),
        files={"file": ("test.pdf", b"%PDF-invalid", "application/pdf")},
    )
    assert response.status_code == 422
    assert "cannot be parsed" in response.json()["message"]


async def test_logging_context_does_not_cross_concurrent_tasks() -> None:
    import logging

    filter_ = ContextFilter("test", "test")

    async def worker(identity: str) -> str:
        with request_scope(requestId=identity):
            await asyncio.sleep(0)
            record = logging.LogRecord("test", logging.INFO, "", 1, "message", (), None)
            filter_.filter(record)
            return record.requestId

    assert await asyncio.gather(worker("first"), worker("second")) == ["first", "second"]


def test_startup_failure_closes_previously_allocated_resources(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.main as main

    provider = MockChatProvider()
    closed = AsyncMock()
    monkeypatch.setattr(provider, "aclose", closed)
    monkeypatch.setattr(main, "create_chat_provider", lambda _: provider)
    monkeypatch.setattr(main, "create_embedding_provider", lambda _: (_ for _ in ()).throw(RuntimeError("init failed")))
    with pytest.raises(RuntimeError, match="init failed"), TestClient(create_app()):
        pass
    closed.assert_awaited_once()


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_public_environment_requires_auth_and_redis(environment: str) -> None:
    with pytest.raises(ValueError, match="AI_AUTH_REQUIRED"):
        Settings(app_env=environment)


async def test_provider_reuses_client_and_forwards_request_context(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx
    from app.providers.base import OpenAICompatibleProvider
    from app.schemas.chat import ChatMessage

    creations = 0
    seen: list[str | None] = []
    original = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.headers.get("X-Request-ID"))
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
            },
        )

    def create_client(**kwargs: object) -> httpx.AsyncClient:
        nonlocal creations
        creations += 1
        return original(transport=httpx.MockTransport(handler))

    monkeypatch.setattr(httpx, "AsyncClient", create_client)
    provider = OpenAICompatibleProvider(base_url="https://example.test/v1", api_key="fake", model="m", timeout=1)
    try:
        with request_scope(requestId="trace-test"):
            for _ in range(2):
                result = await provider.complete([ChatMessage(role="user", content="hello")])
                assert result.usage.total_tokens == 3
        assert creations == 1 and seen == ["trace-test", "trace-test"]
    finally:
        await provider.aclose()
    assert provider._client.is_closed


async def test_agent_yields_final_delta_before_final_generation_completes(settings: Settings) -> None:
    from collections.abc import AsyncGenerator, Sequence

    from app.providers.types import ModelConfig, ToolCallingResult, ToolDefinition
    from app.schemas.chat import ChatMessage
    from app.services.agent import AgentState, AgentWorkflow
    from app.services.model_router import ModelRouter
    from app.tools.base import ToolRegistry

    released = asyncio.Event()

    class IncrementalProvider(MockChatProvider):
        async def tool_calling(
            self, messages: Sequence[ChatMessage], tools: Sequence[ToolDefinition], config: ModelConfig | None = None
        ) -> ToolCallingResult:
            return ToolCallingResult(content="not the displayed answer", model="m")

        async def _generate(self, messages: Sequence[ChatMessage]) -> AsyncGenerator[str, None]:
            yield "first"
            await released.wait()
            yield "second"

    workflow = AgentWorkflow(IncrementalProvider(), ToolRegistry([]), ModelRouter(settings), 2)
    state: AgentState = {
        "conversation_id": "c",
        "user_id": "u",
        "messages": [ChatMessage(role="user", content="hello")],
        "tool_calls": [],
        "tool_results": [],
        "iteration": 0,
        "usage": {},
        "answer": "",
        "route": "",
    }
    stream = workflow.stream(state)
    try:
        first = await asyncio.wait_for(anext(stream), 1)
        assert first == {"type": "delta", "delta": "first"} and not released.is_set()
        released.set()
        rest = [item async for item in stream]
        assert rest[0] == {"type": "delta", "delta": "second"} and rest[-1]["type"] == "answer"
    finally:
        await stream.aclose()


def test_settings_repr_and_validation_do_not_expose_secrets() -> None:
    from pydantic import ValidationError

    marker = "private-secret-marker-for-test-only"
    settings = Settings(jwt_secret=marker, ai_api_key=marker, service_token=marker)
    assert marker not in repr(settings)
    with pytest.raises(ValidationError) as error:
        Settings(jwt_secret=marker, ai_timeout_seconds=0)
    assert marker not in str(error.value) and "input_value" not in str(error.value)
