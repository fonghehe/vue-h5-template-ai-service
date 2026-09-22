"""Bounded conversation mutexes and token-owned concurrent stream leases."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from typing import cast
from uuid import uuid4

import anyio
from redis.asyncio import Redis

from app.core.errors import RateLimitError


class ConversationLockManager:
    def __init__(self, redis_url: str | None = None, *, lease_seconds: float = 120, redis: Redis | None = None) -> None:
        self._locks: dict[str, tuple[asyncio.Lock, int]] = {}
        self._lease_seconds = lease_seconds
        self._owns_client = redis is None
        self._redis = redis or (
            Redis.from_url(redis_url, decode_responses=True, socket_timeout=3, socket_connect_timeout=3)
            if redis_url
            else None
        )

    @asynccontextmanager
    async def lease(self, conversation_id: str) -> AsyncIterator[None]:
        if self._redis is not None:
            lock = self._redis.lock(
                f"ai:conversation-lock:{conversation_id}",
                timeout=self._lease_seconds,
                blocking_timeout=5,
                thread_local=False,
            )
            if not await lock.acquire():
                raise RateLimitError("Conversation is busy")
            try:
                yield
            finally:
                with anyio.CancelScope(shield=True):
                    await lock.release()
            return
        lock, users = self._locks.get(conversation_id, (asyncio.Lock(), 0))
        self._locks[conversation_id] = (lock, users + 1)
        try:
            async with lock:
                yield
        finally:
            _, users = self._locks[conversation_id]
            if users == 1:
                del self._locks[conversation_id]
            else:
                self._locks[conversation_id] = (lock, users - 1)

    async def aclose(self) -> None:
        if self._redis is not None and self._owns_client:
            await self._redis.aclose()


# Redis TIME keeps replicas with different clocks on the same timeline. A
# unique token makes release idempotent and unable to delete another lease.
_ACQUIRE = """
local now = redis.call('TIME')
local seconds = tonumber(now[1]) + tonumber(now[2]) / 1000000
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', seconds)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[1]) then return 0 end
redis.call('ZADD', KEYS[1], seconds + tonumber(ARGV[2]), ARGV[3])
redis.call('EXPIRE', KEYS[1], math.ceil(tonumber(ARGV[2])))
return 1
"""


class StreamQuota:
    def __init__(self, redis_url: str | None = None, *, lease_seconds: float = 120, redis: Redis | None = None) -> None:
        self._owns_client = redis is None
        self._redis = redis or (
            Redis.from_url(redis_url, decode_responses=True, socket_timeout=3, socket_connect_timeout=3)
            if redis_url
            else None
        )
        self._leases: dict[str, dict[str, float]] = {}
        self._lease_seconds = lease_seconds
        self._lock = asyncio.Lock()

    async def acquire(self, user_id: str, limit: int) -> str | None:
        token = uuid4().hex
        if self._redis is not None:
            acquired = await cast(
                Awaitable[object],
                self._redis.eval(
                    _ACQUIRE, 1, f"ai:stream-leases:{user_id}", str(limit), str(self._lease_seconds), token
                ),
            )
            return token if acquired else None
        async with self._lock:
            now = time.monotonic()
            # Bound stale identities as well as per-identity leases.
            for identity, entries in list(self._leases.items()):
                active = {key: expiry for key, expiry in entries.items() if expiry > now}
                if active:
                    self._leases[identity] = active
                else:
                    del self._leases[identity]
            entries = self._leases.setdefault(user_id, {})
            if len(entries) >= limit:
                return None
            entries[token] = now + self._lease_seconds
            return token

    async def release(self, user_id: str, token: str) -> None:
        if self._redis is not None:
            await self._redis.zrem(f"ai:stream-leases:{user_id}", token)
            return
        async with self._lock:
            entries = self._leases.get(user_id, {})
            entries.pop(token, None)
            if not entries:
                self._leases.pop(user_id, None)

    async def aclose(self) -> None:
        if self._redis is not None and self._owns_client:
            await self._redis.aclose()
