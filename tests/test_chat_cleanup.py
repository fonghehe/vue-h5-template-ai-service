"""Provider failures must not leak streaming resources or metrics."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Sequence

import pytest
from app.core.config import Settings
from app.providers.base import MockChatProvider
from app.providers.types import ModelConfig
from app.schemas.chat import ChatMessage, ChatRequest
from app.services.chat import ChatService
from app.services.rate_limit import MemoryRateLimiter
from prometheus_client import REGISTRY


class FailingStartProvider(MockChatProvider):
    def stream(self, messages: Sequence[ChatMessage], config: ModelConfig | None = None) -> AsyncGenerator[str, None]:
        raise RuntimeError("private provider setup details")


class FailingCloseProvider(MockChatProvider):
    async def stream(
        self, messages: Sequence[ChatMessage], config: ModelConfig | None = None
    ) -> AsyncGenerator[str, None]:
        try:
            yield "first"
        finally:
            raise RuntimeError("provider cleanup failed")


def sample(name: str, labels: dict[str, str] | None = None) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0


def payload() -> ChatRequest:
    return ChatRequest(messages=[ChatMessage(role="user", content="Hello")])


async def test_provider_creation_failure_is_sanitized_and_releases_metrics() -> None:
    before = sample("active_streams")
    service = ChatService(FailingStartProvider(), Settings(), MemoryRateLimiter())
    frames = [frame async for frame in service.stream(payload(), "conversation-test", "trace-test")]
    assert '"type":"start"' in frames[0]
    assert '"type":"error"' in frames[-1]
    assert "trace-test" in frames[-1]
    assert "private provider setup details" not in "".join(frames)
    assert sample("active_streams") == before


async def test_provider_close_failure_still_releases_metrics() -> None:
    before = sample("active_streams")
    service = ChatService(FailingCloseProvider(), Settings(), MemoryRateLimiter())
    stream = service.stream(payload(), "conversation-test", "trace-test")
    await anext(stream)
    await anext(stream)
    with pytest.raises(RuntimeError, match="provider cleanup failed"):
        await stream.aclose()
    assert sample("active_streams") == before


async def test_pending_chat_cancellation_closes_provider_and_records_cancellation() -> None:
    entered, closed = asyncio.Event(), asyncio.Event()

    class PendingProvider(MockChatProvider):
        async def stream(
            self, messages: Sequence[ChatMessage], config: ModelConfig | None = None
        ) -> AsyncGenerator[str, None]:
            try:
                entered.set()
                await asyncio.Event().wait()
                yield "unreachable"
            finally:
                closed.set()

    labels = {"path": "chat", "status": "cancelled"}
    before_active = sample("active_streams")
    before_cancelled = sample("ai_requests_total", labels)
    service = ChatService(PendingProvider(), Settings(), MemoryRateLimiter())
    stream = service.stream(payload(), "conversation-test", "trace-test")
    await anext(stream)
    pending = asyncio.create_task(anext(stream))
    await entered.wait()
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    assert closed.is_set()
    assert sample("active_streams") == before_active
    assert sample("ai_requests_total", labels) == before_cancelled + 1
