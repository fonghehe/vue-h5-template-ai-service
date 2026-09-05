"""Persistence, ownership, and streamed conversation tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import auth_header, make_token, parse_sse


def _create(client: TestClient, subject: str = "user-a") -> tuple[str, dict[str, str]]:
    headers = auth_header(make_token(subject=subject))
    response = client.post("/api/conversations", json={"title": "Architecture"}, headers=headers)
    assert response.status_code == 200
    return response.json()["data"]["id"], headers


def test_conversation_crud_and_message_persistence(client: TestClient) -> None:
    conversation_id, headers = _create(client)

    streamed = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "Explain SSE", "mode": "chat"},
        headers=headers,
    )

    assert streamed.status_code == 200
    events = parse_sse(streamed.text)
    assert events[0] == {"type": "start", "id": conversation_id}
    assert events[-1] == {"type": "finish", "reason": "stop"}
    detail = client.get(f"/api/conversations/{conversation_id}", headers=headers).json()["data"]
    assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["tokenUsage"]["totalTokens"] > 0
    usage = client.get("/api/usage/me", headers=headers).json()["data"]
    assert usage["requests"] == 1
    assert usage["byModel"][0]["key"] == "gpt-4o-mini"
    assert usage["byConversation"][0]["key"] == conversation_id
    assert usage["byDate"]

    assert client.delete(f"/api/conversations/{conversation_id}", headers=headers).status_code == 200
    assert client.get(f"/api/conversations/{conversation_id}", headers=headers).status_code == 404


def test_cross_user_conversation_access_is_denied(client: TestClient) -> None:
    conversation_id, _ = _create(client, "owner")
    other = auth_header(make_token(subject="other"))

    assert client.get(f"/api/conversations/{conversation_id}", headers=other).status_code == 403
    assert client.delete(f"/api/conversations/{conversation_id}", headers=other).status_code == 403
    assert (
        client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"content": "steal context"},
            headers=other,
        ).status_code
        == 403
    )


def test_persistent_conversation_requires_user_jwt(client: TestClient) -> None:
    assert client.post("/api/conversations", json={}).status_code == 401


def test_agent_persists_tool_message_and_streams_optional_events(client: TestClient) -> None:
    conversation_id, headers = _create(client)
    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "2+3", "mode": "agent"},
        headers=headers,
    )
    events = parse_sse(response.text)
    types = [event["type"] for event in events]
    assert types.index("tool_start") < types.index("tool_result") < types.index("delta")
    detail = client.get(f"/api/conversations/{conversation_id}", headers=headers).json()["data"]
    assert [message["role"] for message in detail["messages"]] == ["user", "tool", "assistant"]


def test_daily_token_limit_rejects_another_turn(client: TestClient) -> None:
    conversation_id, headers = _create(client)
    first = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "first", "mode": "chat"},
        headers=headers,
    )
    assert first.status_code == 200
    client.app.state.settings.ai_daily_token_limit = 1
    second = client.post(
        f"/api/conversations/{conversation_id}/messages",
        json={"content": "second", "mode": "chat"},
        headers=headers,
    )
    assert second.status_code == 429


def test_cross_user_knowledge_access_is_denied(client: TestClient) -> None:
    owner = auth_header(make_token(subject="owner"))
    other = auth_header(make_token(subject="other"))
    uploaded = client.post(
        "/api/knowledge/documents",
        files={"file": ("pricing.md", b"camera price is 499", "text/markdown")},
        data={"metadata": "{}"},
        headers=owner,
    )
    assert uploaded.status_code == 200
    document_id = uploaded.json()["data"]["id"]
    assert client.get("/api/knowledge/documents", headers=other).json()["data"] == []
    assert client.delete(f"/api/knowledge/documents/{document_id}", headers=other).status_code == 403
