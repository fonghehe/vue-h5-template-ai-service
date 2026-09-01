"""End-to-end tests for `POST /api/ai/chat` and the SSE contract."""

from __future__ import annotations

import pytest
from app.core.config import get_settings
from app.main import create_app
from fastapi.testclient import TestClient

from tests.conftest import auth_header, chat_body, make_token, parse_sse


def test_chat_streams_start_delta_finish(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json=chat_body())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = parse_sse(response.text)
    assert events, "the stream must contain at least one event"
    assert events[0]["type"] == "start"
    assert "id" in events[0], "start must carry the conversation id"
    assert any(event["type"] == "delta" for event in events)
    assert events[-1]["type"] == "finish"
    assert events[-1]["reason"] == "stop"


def test_chat_concatenates_into_coherent_text(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json=chat_body("Explain streaming."))

    events = parse_sse(response.text)
    text = "".join(event["delta"] for event in events if event["type"] == "delta")
    assert "Streaming keeps the UI honest." in text


def test_chat_honours_client_supplied_conversation_id(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json=chat_body(conversationId="conversation-fixed-1"))

    events = parse_sse(response.text)
    assert events[0] == {"type": "start", "id": "conversation-fixed-1"}


def test_chat_generates_conversation_id_when_absent(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json=chat_body())

    events = parse_sse(response.text)
    assert events[0]["id"].startswith("conversation-")


def test_chat_accepts_frontend_message_shape(client: TestClient) -> None:
    """The frontend sends id/createdAt alongside role/content."""
    body = {
        "messages": [
            {"id": "m1", "role": "user", "content": "Hello", "createdAt": 1_700_000_000_000},
            {"id": "m2", "role": "assistant", "content": "Hi!", "createdAt": 1_700_000_001_000},
            {"id": "m3", "role": "user", "content": "How are you?", "createdAt": 1_700_000_002_000},
        ],
        "conversationId": "conv-1",
    }

    response = client.post("/api/ai/chat", json=body)

    assert response.status_code == 200
    assert parse_sse(response.text)[0]["id"] == "conv-1"


def test_chat_generates_unique_conversation_ids(client: TestClient) -> None:
    first = parse_sse(client.post("/api/ai/chat", json=chat_body()).text)[0]["id"]
    second = parse_sse(client.post("/api/ai/chat", json=chat_body()).text)[0]["id"]
    assert first != second


def test_chat_sets_streaming_headers(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json=chat_body())

    # `no-transform` and `X-Accel-Buffering: no` stop proxies from buffering,
    # which would otherwise defeat the point of streaming.
    assert "no-transform" in response.headers["cache-control"]
    assert response.headers["x-accel-buffering"] == "no"


def test_chat_rejects_empty_messages(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json={"messages": []})
    assert response.status_code == 422


def test_chat_rejects_missing_messages(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json={})
    assert response.status_code == 422


def test_chat_rejects_empty_content(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": ""}]})
    assert response.status_code == 422


def test_chat_rejects_unknown_role(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json={"messages": [{"role": "robot", "content": "hi"}]})
    assert response.status_code == 422


def test_validation_error_uses_shared_envelope(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json={"messages": []})

    body = response.json()
    assert body["code"] == 4001
    assert body["data"] is None
    assert "message" in body
    # Field names are safe to expose; submitted values are not.
    assert body["error"]["fields"] == ["messages"]


def test_chat_works_anonymously_by_default(client: TestClient) -> None:
    """Local development must not require any setup."""
    assert client.post("/api/ai/chat", json=chat_body()).status_code == 200


def test_chat_accepts_valid_user_token(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json=chat_body(), headers=auth_header(make_token()))
    assert response.status_code == 200


def test_chat_rejects_malformed_token(client: TestClient) -> None:
    response = client.post("/api/ai/chat", json=chat_body(), headers=auth_header("not-a-jwt"))

    assert response.status_code == 401
    assert response.json()["code"] == 4010


def test_chat_rejects_token_signed_with_another_secret(client: TestClient) -> None:
    token = make_token(secret="a-completely-different-secret-value-01")

    response = client.post("/api/ai/chat", json=chat_body(), headers=auth_header(token))

    assert response.status_code == 401


def test_chat_rejects_expired_token(client: TestClient) -> None:
    from datetime import timedelta

    token = make_token(expires_in=timedelta(minutes=-5))

    response = client.post("/api/ai/chat", json=chat_body(), headers=auth_header(token))

    assert response.status_code == 401


def test_chat_rejects_token_for_another_audience(client: TestClient) -> None:
    token = make_token(audience="some-other-service")

    response = client.post("/api/ai/chat", json=chat_body(), headers=auth_header(token))

    assert response.status_code == 401


def test_auth_can_be_required(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """With AI_AUTH_REQUIRED on, anonymous access must be refused."""
    monkeypatch.setenv("AI_AUTH_REQUIRED", "true")
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as secured:
            assert secured.post("/api/ai/chat", json=chat_body()).status_code == 401
            accepted = secured.post("/api/ai/chat", json=chat_body(), headers=auth_header(make_token()))
            assert accepted.status_code == 200
    finally:
        get_settings.cache_clear()


def test_service_token_is_accepted(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A trusted gateway may call us without minting per-user tokens."""
    monkeypatch.setenv("SERVICE_TOKEN", "gateway-shared-secret")
    monkeypatch.setenv("AI_AUTH_REQUIRED", "true")
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as secured:
            response = secured.post("/api/ai/chat", json=chat_body(), headers=auth_header("gateway-shared-secret"))
            assert response.status_code == 200
    finally:
        get_settings.cache_clear()
