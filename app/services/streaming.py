"""Bounded streaming primitives, independent of the HTTP framework."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Protocol, cast

import anyio

from app.core.errors import ProviderTimeoutError
from app.providers.base import LLMProvider
from app.providers.types import ModelConfig
from app.schemas.chat import ChatMessage


class DisconnectProbe(Protocol):
    async def is_disconnected(self) -> bool: ...


class ClosableIterator[T](Protocol):
    def __aiter__(self) -> ClosableIterator[T]: ...
    async def __anext__(self) -> T: ...
    async def aclose(self) -> None: ...


async def guarded_stream[T](
    source: AsyncIterator[T],
    *,
    disconnected: Callable[[], Awaitable[bool]] | None = None,
    deadline_seconds: float = 90,
    heartbeat_seconds: float = 15,
) -> AsyncIterator[T | None]:
    """One pending read provides backpressure; None requests an SSE heartbeat.

    Closing/cancelling the consumer cancels and joins the read before closing
    its generator. Shield cleanup against Starlette's disconnect cancel scope.
    """
    stream = cast(ClosableIterator[T], source)
    pending: asyncio.Future[T] | None = None
    loop = asyncio.get_running_loop()
    deadline = loop.time() + deadline_seconds
    heartbeat = loop.time() + heartbeat_seconds
    try:
        while True:
            pending = asyncio.ensure_future(anext(stream))
            while not pending.done():
                await asyncio.wait({pending}, timeout=min(0.05, max(0, deadline - loop.time())))
                if disconnected is not None and await disconnected():
                    raise asyncio.CancelledError
                if loop.time() >= deadline:
                    raise ProviderTimeoutError("AI stream deadline exceeded")
                if not pending.done() and loop.time() >= heartbeat:
                    yield None
                    heartbeat = loop.time() + heartbeat_seconds
            try:
                item = pending.result()
            except StopAsyncIteration:
                return
            yield item
            heartbeat = loop.time() + heartbeat_seconds
    finally:
        with anyio.CancelScope(shield=True):
            if pending is not None:
                if not pending.done():
                    pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)
            await stream.aclose()


async def cancel_aware_stream(
    request: DisconnectProbe,
    provider: LLMProvider,
    messages: Sequence[ChatMessage],
    config: ModelConfig | None = None,
) -> AsyncIterator[str]:
    """Compatibility helper for direct provider streams."""
    async for item in guarded_stream(provider.stream(messages, config), disconnected=request.is_disconnected):
        if item is not None:
            yield item
