"""HTTP streaming owns quota release even if sending the start frame fails."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import cast

import anyio
from starlette.responses import StreamingResponse
from starlette.types import Receive, Scope, Send

from app.core.errors import AppError
from app.schemas.chat import ErrorChunk, encode_sse
from app.services.locks import StreamQuota
from app.services.streaming import ClosableIterator, guarded_stream


class QuotaStreamingResponse(StreamingResponse):
    def __init__(
        self,
        source: AsyncIterator[str],
        *,
        quota: StreamQuota,
        identity: str,
        token: str,
        timeout: float,
        heartbeat: float,
        request_id: str,
        disconnected: Callable[[], Awaitable[bool]] | None = None,
    ) -> None:
        self._source = source
        self._disconnected = disconnected
        self._quota, self._identity, self._token = quota, identity, token
        self._timeout, self._heartbeat, self._request_id = timeout, heartbeat, request_id
        super().__init__(
            self._frames(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
        )

    async def _frames(self) -> AsyncIterator[str]:
        try:
            async for frame in guarded_stream(
                self._source,
                deadline_seconds=self._timeout,
                heartbeat_seconds=self._heartbeat,
                disconnected=self._disconnected,
            ):
                yield ": heartbeat\n\n" if frame is None else frame
        except AppError as exc:
            yield encode_sse(ErrorChunk(message=exc.message, code=exc.code, requestId=self._request_id))

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            async with asyncio.timeout(self._timeout + 5):
                await super().__call__(scope, receive, send)
        finally:
            with anyio.CancelScope(shield=True):
                try:
                    await cast(ClosableIterator[str], self.body_iterator).aclose()
                    await cast(ClosableIterator[str], self._source).aclose()
                finally:
                    await self._quota.release(self._identity, self._token)
