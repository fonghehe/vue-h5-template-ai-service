"""Tests for the chat providers."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx
import pytest
from app.core.errors import ConfigurationError, ProviderError, ProviderTimeoutError
from app.providers.base import (
    MOCK_ANSWER,
    ChatProvider,
    MockChatProvider,
    OpenAICompatibleProvider,
)
from app.providers.factory import create_chat_provider
from app.schemas.chat import ChatMessage


def messages(content: str = "Hello") -> list[ChatMessage]:
    return [ChatMessage(role="user", content=content)]


async def collect(provider: ChatProvider, content: str = "Hello") -> str:
    """Drain a provider stream into a single string."""
    chunks: list[str] = []
    async for chunk in provider.stream(messages(content)):
        chunks.append(chunk)
    return "".join(chunks)


async def test_mock_provider_streams_full_answer() -> None:
    output = await collect(MockChatProvider(delay_seconds=0))

    assert output.strip() == MOCK_ANSWER.strip()


async def test_mock_provider_reports_its_name() -> None:
    assert MockChatProvider().name == "mock"


async def test_mock_provider_responds_to_blank_input() -> None:
    output = await collect(MockChatProvider(delay_seconds=0), content="   ")

    assert "Please send a message" in output


async def test_mock_provider_yields_multiple_fragments() -> None:
    provider = MockChatProvider(delay_seconds=0)
    count = 0
    async for _ in provider.stream(messages()):
        count += 1

    assert count > 1, "streaming implies more than one fragment"


async def test_factory_returns_mock_by_default() -> None:
    from app.core.config import Settings

    assert isinstance(create_chat_provider(Settings()), MockChatProvider)


async def test_factory_requires_api_key_for_hosted_provider() -> None:
    from app.core.config import Settings

    with pytest.raises(ConfigurationError, match="AI_API_KEY"):
        create_chat_provider(Settings(ai_provider="openai-compatible", ai_api_key=None))


async def test_factory_builds_hosted_provider() -> None:
    from app.core.config import Settings

    provider = create_chat_provider(
        Settings(
            ai_provider="openai-compatible",
            ai_api_key="sk-test",
            ai_base_url="https://api.example.com/v1/",
            ai_model="test-model",
        )
    )

    assert isinstance(provider, OpenAICompatibleProvider)
    # Trailing slashes must not produce a double slash in the request path.
    assert provider._base_url == "https://api.example.com/v1"


def sse_body(fragments: list[str]) -> bytes:
    """Build a byte stream shaped like an OpenAI streaming response."""
    lines = []
    for fragment in fragments:
        payload = {"choices": [{"delta": {"content": fragment}}]}
        lines.append(f"data: {json.dumps(payload)}")
    lines.append("data: [DONE]")
    return ("\n\n".join(lines) + "\n\n").encode()


def patch_client(monkeypatch: pytest.MonkeyPatch, transport: httpx.MockTransport) -> None:
    """Route every httpx client the provider builds onto a mock transport.

    The original class is captured first: the replacement must not call the
    patched name, or it would recurse forever.
    """
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=transport))


async def test_openai_provider_parses_deltas(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, content=sse_body(["Hello", " ", "world"]))

    patch_client(monkeypatch, httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        base_url="https://api.example.com/v1", api_key="sk-test", model="m", timeout=5.0
    )

    assert await collect(provider) == "Hello world"
    assert str(captured["url"]).endswith("/chat/completions")
    assert captured["auth"] == "Bearer sk-test"
    assert captured["body"]["model"] == "m"
    assert captured["body"]["stream"] is True


async def test_openai_provider_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_client(monkeypatch, httpx.MockTransport(lambda _: httpx.Response(500, text="boom")))
    provider = OpenAICompatibleProvider(
        base_url="https://api.example.com/v1", api_key="sk-test", model="m", timeout=5.0
    )

    with pytest.raises(ProviderError, match="HTTP 500"):
        await collect(provider)


async def test_openai_provider_raises_on_malformed_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_client(monkeypatch, httpx.MockTransport(lambda _: httpx.Response(200, content=b"data: {nope}\n\n")))
    provider = OpenAICompatibleProvider(
        base_url="https://api.example.com/v1", api_key="sk-test", model="m", timeout=5.0
    )

    with pytest.raises(ProviderError, match="Malformed"):
        await collect(provider)


async def test_openai_provider_wraps_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("too slow", request=request)

    patch_client(monkeypatch, httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        base_url="https://api.example.com/v1", api_key="sk-test", model="m", timeout=5.0
    )

    with pytest.raises((ProviderTimeoutError, ProviderError)):
        await collect(provider)


async def test_openai_provider_skips_null_deltas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Providers emit null content frames for tool-call preambles."""
    content = (
        b'data: {"choices":[{"delta":{"content":null}}]}\n\n'
        b'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n'
        b"data: [DONE]\n\n"
    )
    patch_client(monkeypatch, httpx.MockTransport(lambda _: httpx.Response(200, content=content)))
    provider = OpenAICompatibleProvider(
        base_url="https://api.example.com/v1", api_key="sk-test", model="m", timeout=5.0
    )

    assert await collect(provider) == "hi"


async def test_openai_provider_enforces_output_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_client(
        monkeypatch,
        httpx.MockTransport(lambda _: httpx.Response(200, content=sse_body(["x" * 100] * 20))),
    )
    provider = OpenAICompatibleProvider(
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        model="m",
        timeout=5.0,
        max_output_chars=150,
    )

    output = await collect(provider)
    assert len(output) <= 250, "the stream must stop instead of running unbounded"


def test_provider_stream_is_an_async_iterator() -> None:
    provider = MockChatProvider()
    assert isinstance(provider.stream(messages()), AsyncIterator)
