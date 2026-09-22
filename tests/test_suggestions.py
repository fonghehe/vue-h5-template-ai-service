"""Starter prompts are localized, public and never invoke a provider."""

import pytest
from app.services.suggestions import get_suggestions
from fastapi.testclient import TestClient


@pytest.mark.parametrize("prefix", ["/api", "/api/v1"])
@pytest.mark.parametrize("locale", ["en-US", "zh-CN", "ja-JP"])
def test_localized_suggestions(client: TestClient, prefix: str, locale: str) -> None:
    response = client.get(f"{prefix}/ai/suggestions", params={"locale": locale})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["requestId"]
    assert len(body["data"]) == 3
    assert all(isinstance(text, str) and text.strip() for text in body["data"])
    if locale == "zh-CN":
        assert "下单" in body["data"][1]
    elif locale == "ja-JP":
        assert "注文" in body["data"][1]


def test_suggestions_default_validation_and_copy(client: TestClient) -> None:
    assert client.get("/api/ai/suggestions").json()["data"] == get_suggestions("en-US")
    assert client.get("/api/ai/suggestions?locale=invalid").status_code == 422
    prompts = get_suggestions("en-US")
    prompts.clear()
    assert len(get_suggestions("en-US")) == 3
