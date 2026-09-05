"""Conversation-level locks that serialize one conversation, not all users."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import AbstractAsyncContextManager
from types import TracebackType

from redis.asyncio import Redis
from redis.asyncio.lock import Lock as RedisLock


class ConversationLease(AbstractAsyncContextManager[None]):
    def __init__(self, lock: asyncio.Lock) -> None:
        self._lock = lock

    async def __aenter__(self) -> None:
        await self._lock.acquire()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._lock.release()


class RedisConversationLease(AbstractAsyncContextManager[None]):
    def __init__(self, lock: RedisLock) -> None:
        self._lock = lock

    async def __aenter__(self) -> None:
        acquired = await self._lock.acquire()
        if not acquired:
            raise TimeoutError("Conversation is busy")

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._lock.release()


class ConversationLockManager:
    """Local lock fallback. Redis deployments additionally coordinate stream quotas."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._redis = Redis.from_url(redis_url, decode_responses=True) if redis_url else None

    def lease(self, conversation_id: str) -> AbstractAsyncContextManager[None]:
        if self._redis is not None:
            lock = self._redis.lock(
                f"ai:conversation-lock:{conversation_id}",
                timeout=120,
                blocking_timeout=30,
            )
            return RedisConversationLease(lock)
        return ConversationLease(self._locks[conversation_id])

    async def aclose(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()


class StreamQuota:
    """Per-user concurrent stream counter with Redis or local atomic storage."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis = Redis.from_url(redis_url, decode_responses=True) if redis_url else None
        self._counts: defaultdict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def acquire(self, user_id: str, limit: int) -> bool:
        if self._redis is not None:
            key = f"ai:streams:{user_id}"
            count = int(await self._redis.incr(key))
            await self._redis.expire(key, 600)
            if count > limit:
                await self._redis.decr(key)
                return False
            return True
        async with self._lock:
            if self._counts[user_id] >= limit:
                return False
            self._counts[user_id] += 1
            return True

    async def release(self, user_id: str) -> None:
        if self._redis is not None:
            key = f"ai:streams:{user_id}"
            value = int(await self._redis.decr(key))
            if value <= 0:
                await self._redis.delete(key)
            return
        async with self._lock:
            self._counts[user_id] = max(0, self._counts[user_id] - 1)

    async def aclose(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
