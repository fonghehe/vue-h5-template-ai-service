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
from app.providers.embedding import OpenAICompatibleEmbeddingProvider
from app.providers.factory import create_chat_provider
from app.schemas.chat import ChatMessage, ChatToolCall


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


@pytest.mark.parametrize(
    "data",
    [
        [],
        [{"index": 0, "embedding": [1.0]}, {"index": 0, "embedding": [2.0]}],
        [{"index": 0, "embedding": [1.0]}, {"index": 1, "embedding": [1.0, 2.0]}],
        [{"index": 0, "embedding": [float("nan")]}, {"index": 1, "embedding": [2.0]}],
    ],
    ids=["missing", "duplicate-index", "mixed-dimensions", "nonfinite"],
)
async def test_embedding_rejects_invalid_vectors(monkeypatch: pytest.MonkeyPatch, data: object) -> None:
    patch_client(
        monkeypatch,
        httpx.MockTransport(lambda _: httpx.Response(200, content=json.dumps({"data": data}).encode())),
    )
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://example.test/v1", api_key="fake", model="embedding", timeout=1
    )
    try:
        with pytest.raises(ProviderError, match="Malformed embedding response"):
            await provider.embed(["one", "two"])
    finally:
        await provider.aclose()


async def test_embedding_preserves_input_order(monkeypatch: pytest.MonkeyPatch) -> None:
    patch_client(
        monkeypatch,
        httpx.MockTransport(
            lambda _: httpx.Response(
                200, json={"data": [{"index": 1, "embedding": [2.0]}, {"index": 0, "embedding": [1.0]}]}
            )
        ),
    )
    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://example.test/v1", api_key="fake", model="embedding", timeout=1
    )
    try:
        assert await provider.embed(["one", "two"]) == [[1.0], [2.0]]
    finally:
        await provider.aclose()
    assert provider._client.is_closed


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


async def test_openai_provider_serializes_tool_call_protocol(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "m",
                "choices": [{"message": {"content": "done"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    patch_client(monkeypatch, httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        base_url="https://api.example.com/v1", api_key="sk-test", model="m", timeout=5.0
    )
    await provider.complete(
        [
            ChatMessage(role="user", content="2+3"),
            ChatMessage(
                role="assistant",
                content="",
                toolCalls=[ChatToolCall(id="call-1", name="calculator", arguments={"expression": "2+3"})],
            ),
            ChatMessage(role="tool", content='{"result":5}', toolCallId="call-1"),
        ]
    )
    wire = captured["body"]["messages"]  # type: ignore[index]
    assert wire[1]["tool_calls"][0]["function"]["name"] == "calculator"
    assert wire[2]["tool_call_id"] == "call-1"


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

    with pytest.raises(ProviderError, match="output limit"):
        await collect(provider)


def test_provider_stream_is_an_async_iterator() -> None:
    provider = MockChatProvider()
    assert isinstance(provider.stream(messages()), AsyncIterator)


@pytest.mark.parametrize("body", [b"", b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'])
async def test_unterminated_stream_is_error_without_replay(monkeypatch: pytest.MonkeyPatch, body: bytes) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, content=body)

    patch_client(monkeypatch, httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(base_url="https://example.test", api_key="test", model="m", timeout=1)
    try:
        with pytest.raises(ProviderError, match="terminal event"):
            await collect(provider)
        assert calls == 1
    finally:
        await provider.aclose()


async def test_finish_reason_is_terminal_and_usage_chunks_are_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    body = (
        b'data: {"choices":[],"usage":{"total_tokens":1}}\n\n'
        b'data: {"choices":[{"delta":{"content":"hi"},"finish_reason":"stop"}]}\n\n'
    )
    patch_client(monkeypatch, httpx.MockTransport(lambda _: httpx.Response(200, content=body)))
    provider = OpenAICompatibleProvider(base_url="https://example.test", api_key="test", model="m", timeout=1)
    try:
        assert await collect(provider) == "hi"
    finally:
        await provider.aclose()


@pytest.mark.parametrize("first_delta", [False, True], ids=["first-token", "idle"])
async def test_empty_frames_cannot_extend_token_timeout(monkeypatch: pytest.MonkeyPatch, first_delta: bool) -> None:
    import asyncio

    class Stream(httpx.AsyncByteStream):
        closed = False

        async def __aiter__(self) -> AsyncIterator[bytes]:
            if first_delta:
                yield b'data: {"choices":[{"delta":{"content":"hi"}}]}\n\n'
            while True:
                await asyncio.sleep(0.005)
                yield b': keepalive\n\ndata: {"choices":[{"delta":{"content":null}}]}\n\n'

        async def aclose(self) -> None:
            self.closed = True

    stream = Stream()
    patch_client(monkeypatch, httpx.MockTransport(lambda _: httpx.Response(200, stream=stream)))
    provider = OpenAICompatibleProvider(
        base_url="https://example.test", api_key="test", model="m", timeout=0.04, max_retries=0
    )
    try:
        async with asyncio.timeout(1):
            with pytest.raises(ProviderTimeoutError):
                await collect(provider)
        assert stream.closed
        assert not provider._client.is_closed  # A turn owns its response, not the shared client.
    finally:
        await provider.aclose()


async def test_cancelling_http_stream_closes_response_but_preserves_shared_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio

    entered, closed = asyncio.Event(), asyncio.Event()

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            entered.set()
            await asyncio.Event().wait()
            yield b"unreachable"

        async def aclose(self) -> None:
            closed.set()

    patch_client(monkeypatch, httpx.MockTransport(lambda _: httpx.Response(200, stream=Stream())))
    provider = OpenAICompatibleProvider(base_url="https://example.test", api_key="test", model="m", timeout=1)
    try:
        task = asyncio.create_task(collect(provider))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert closed.is_set()
        assert not provider._client.is_closed
    finally:
        await provider.aclose()


async def test_partial_transport_failure_never_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            yield b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
            raise httpx.ReadError("connection lost")

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, stream=Stream())

    patch_client(monkeypatch, httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(base_url="https://example.test", api_key="test", model="m", timeout=1)
    try:
        stream = provider.stream(messages())
        assert await anext(stream) == "partial"
        with pytest.raises(ProviderError):
            await anext(stream)
        assert calls == 1
    finally:
        await provider.aclose()


async def test_truncated_provider_maps_to_one_sse_error_without_finish(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import Settings
    from app.schemas.chat import ChatRequest
    from app.services.chat import ChatService
    from app.services.rate_limit import MemoryRateLimiter

    from tests.conftest import parse_sse

    body = b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
    patch_client(monkeypatch, httpx.MockTransport(lambda _: httpx.Response(200, content=body)))
    provider = OpenAICompatibleProvider(base_url="https://example.test", api_key="test", model="m", timeout=1)
    try:
        service = ChatService(provider, Settings(), MemoryRateLimiter())
        frames = [frame async for frame in service.stream(ChatRequest(messages=messages()), "c", "request-test")]
        events = parse_sse("".join(frames))
        assert [event["type"] for event in events] == ["start", "delta", "error"]
        assert events[-1]["code"] == 5030
        assert events[-1]["requestId"] == "request-test"
    finally:
        await provider.aclose()
