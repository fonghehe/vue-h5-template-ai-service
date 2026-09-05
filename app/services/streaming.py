"""Cancellation-aware provider streaming shared by both chat endpoints."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Protocol, cast

from fastapi import Request

from app.providers.base import LLMProvider
from app.providers.types import ModelConfig
from app.schemas.chat import ChatMessage


class _ClosableStream(Protocol):
    def __aiter__(self) -> _ClosableStream: ...

    async def __anext__(self) -> str: ...

    async def aclose(self) -> None: ...


async def cancel_aware_stream(
    request: Request,
    provider: LLMProvider,
    messages: Sequence[ChatMessage],
    config: ModelConfig | None = None,
) -> AsyncIterator[str]:
    """Cancel an in-flight upstream read as soon as the client disconnects."""
    stream = cast(_ClosableStream, provider.stream(messages, config))
    while True:
        next_item: asyncio.Future[str] = asyncio.ensure_future(anext(stream))
        while not next_item.done():
            await asyncio.wait({next_item}, timeout=0.05)
            if await request.is_disconnected():
                next_item.cancel()
                await asyncio.gather(next_item, return_exceptions=True)
                await stream.aclose()
                raise asyncio.CancelledError
        try:
            yield next_item.result()
        except StopAsyncIteration:
            return
