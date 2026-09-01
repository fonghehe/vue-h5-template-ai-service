"""Fixed-window rate limiting with an in-process or Redis backend."""

from __future__ import annotations

import time
from asyncio import Lock
from typing import Protocol

from redis.asyncio import Redis


class RateLimiter(Protocol):
    """Counter backend used to enforce per-identity request quotas."""

    async def hit(self, key: str, window_seconds: int) -> int:
        """Increment `key` and return the count for the current window."""
        ...

    async def ping(self) -> bool:
        """Return whether the backend is reachable."""
        ...

    async def aclose(self) -> None:
        """Release backend resources."""
        ...


class MemoryRateLimiter:
    """In-process limiter.

    Correct for a single instance, which is how the service is meant to be
    developed. Multi-instance deployments should set `REDIS_URL` so that the
    quota is shared across replicas.
    """

    name = "memory"

    def __init__(self) -> None:
        self._counters: dict[str, tuple[int, float]] = {}
        self._lock = Lock()

    async def hit(self, key: str, window_seconds: int) -> int:
        async with self._lock:
            count, expires_at = self._counters.get(key, (0, 0.0))
            now = time.monotonic()
            if expires_at <= now:
                count, expires_at = 0, now + window_seconds
            count += 1
            self._counters[key] = (count, expires_at)
            self._evict(now)
            return count

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        self._counters.clear()

    def _evict(self, now: float) -> None:
        """Drop expired windows so the map cannot grow without bound."""
        if len(self._counters) < 10_000:
            return
        for key, (_, expires_at) in list(self._counters.items()):
            if expires_at <= now:
                del self._counters[key]


class RedisRateLimiter:
    """Redis-backed limiter shared by every replica."""

    name = "redis"

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @classmethod
    def from_url(cls, url: str) -> RedisRateLimiter:
        return cls(Redis.from_url(url, decode_responses=True))

    async def hit(self, key: str, window_seconds: int) -> int:
        async with self._redis.pipeline(transaction=True) as pipeline:
            pipeline.incr(key)
            # `nx` keeps the original window; refreshing it would let a steady
            # stream of requests reset the counter indefinitely.
            pipeline.expire(key, window_seconds, nx=True)
            result = await pipeline.execute()
        return int(result[0])

    async def ping(self) -> bool:
        return bool(await self._redis.ping())

    async def aclose(self) -> None:
        await self._redis.aclose()


class NoopRateLimiter:
    """Limiter used when the backend is unreachable.

    Failing open (rather than rejecting every request) keeps a Redis outage
    from taking down chat entirely; `/ready` still reports the degradation.
    """

    name = "noop"

    async def hit(self, key: str, window_seconds: int) -> int:
        return 0

    async def ping(self) -> bool:
        return False

    async def aclose(self) -> None:
        return None


def build_rate_limiter(redis_url: str | None) -> RateLimiter:
    """Create the limiter implied by configuration."""
    if not redis_url:
        return MemoryRateLimiter()
    try:
        return RedisRateLimiter.from_url(redis_url)
    except Exception:  # pragma: no cover - depends on driver internals
        return NoopRateLimiter()
