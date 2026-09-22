from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import pytest
from app.core.errors import ProviderTimeoutError
from app.services.locks import ConversationLockManager, StreamQuota
from app.services.streaming import guarded_stream


async def test_parent_cancellation_joins_upstream_read() -> None:
    entered, closed = asyncio.Event(), asyncio.Event()

    async def source() -> AsyncIterator[str]:
        try:
            entered.set()
            await asyncio.Event().wait()
            yield "unreachable"
        finally:
            closed.set()

    stream = guarded_stream(source())
    task = asyncio.create_task(anext(stream))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed.is_set()


async def test_closing_after_delta_closes_provider() -> None:
    closed = asyncio.Event()

    async def source() -> AsyncIterator[str]:
        try:
            yield "first"
            await asyncio.Event().wait()
        finally:
            closed.set()

    stream = guarded_stream(source())
    assert await anext(stream) == "first"
    await stream.aclose()
    assert closed.is_set()


async def test_heartbeat_does_not_cancel_pending_read_and_deadline_closes_it() -> None:
    closed = asyncio.Event()

    async def source() -> AsyncIterator[str]:
        try:
            await asyncio.Event().wait()
            yield "unreachable"
        finally:
            closed.set()

    stream = guarded_stream(source(), deadline_seconds=0.12, heartbeat_seconds=0.01)
    assert await anext(stream) is None
    with pytest.raises(ProviderTimeoutError):
        async for _ in stream:
            pass
    assert closed.is_set()


async def test_quota_release_is_owned_idempotent_and_reclaims_keys() -> None:
    quota = StreamQuota()
    one, two = await quota.acquire("u", 2), await quota.acquire("u", 2)
    assert one and two
    assert await quota.acquire("u", 2) is None
    await quota.release("u", one)
    await quota.release("u", one)
    three = await quota.acquire("u", 2)
    assert three and await quota.acquire("u", 2) is None
    await quota.release("u", two)
    await quota.release("u", three)
    assert quota._leases == {}


async def test_lock_waiter_cancellation_and_key_reclamation() -> None:
    manager = ConversationLockManager()
    async with manager.lease("same"):

        async def waiter() -> None:
            async with manager.lease("same"):
                pytest.fail("waiter unexpectedly acquired")

        task = asyncio.create_task(waiter())
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert manager._locks == {}


async def test_response_releases_quota_when_sending_headers_fails() -> None:
    from app.api.streaming import QuotaStreamingResponse

    quota = StreamQuota()
    token = await quota.acquire("user:u", 1)
    assert token

    async def source() -> AsyncIterator[str]:
        yield "start"

    response = QuotaStreamingResponse(
        source(), quota=quota, identity="user:u", token=token, timeout=1, heartbeat=0.1, request_id="test"
    )

    async def receive() -> dict[str, object]:
        return {"type": "http.disconnect"}

    async def send(_: object) -> None:
        raise OSError("connection closed")

    from starlette.requests import ClientDisconnect

    with pytest.raises(ClientDisconnect):
        await response({"type": "http", "asgi": {"spec_version": "2.4"}}, receive, send)
    assert quota._leases == {}
