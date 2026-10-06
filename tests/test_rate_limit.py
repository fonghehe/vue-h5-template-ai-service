"""Fixed-window counts and expiry cleanup without wall-clock sleeps."""

from __future__ import annotations

import asyncio

import pytest
from app.services.rate_limit import MemoryRateLimiter


async def test_window_does_not_slide_and_resets_at_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    now = 100.0
    monkeypatch.setattr("app.services.rate_limit.time.monotonic", lambda: now)
    limiter = MemoryRateLimiter()
    assert await limiter.hit("owner", 60) == 1
    now = 159.0
    assert await limiter.hit("owner", 60) == 2
    now = 160.0
    assert await limiter.hit("owner", 60) == 1
    assert await limiter.hit("other", 60) == 1
    now = 161.0
    assert await limiter.hit("owner", 60) == 2


async def test_expired_identities_are_reclaimed_even_below_ten_thousand(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 100.0
    monkeypatch.setattr("app.services.rate_limit.time.monotonic", lambda: now)
    limiter = MemoryRateLimiter()
    await limiter.hit("short", 1)
    await limiter.hit("long", 60)
    now = 101.0
    assert await limiter.hit("new", 60) == 1
    # Resource retention is observable even when no identity is near its quota.
    assert set(limiter._counters) == {"long", "new"}
    assert await limiter.hit("long", 60) == 2


async def test_mixed_windows_expire_in_deadline_order(monkeypatch: pytest.MonkeyPatch) -> None:
    now = 100.0
    monkeypatch.setattr("app.services.rate_limit.time.monotonic", lambda: now)
    limiter = MemoryRateLimiter()
    await limiter.hit("long", 60)
    await limiter.hit("short", 1)
    now = 101.0
    assert await limiter.hit("short", 10) == 1
    now = 111.0
    assert await limiter.hit("short", 10) == 1
    assert await limiter.hit("long", 60) == 2


async def test_concurrent_hits_have_distinct_counts_and_close_clears_state() -> None:
    limiter = MemoryRateLimiter()
    counts = await asyncio.gather(*(limiter.hit("shared", 60) for _ in range(100)))
    assert sorted(counts) == list(range(1, 101))
    await limiter.aclose()
    assert limiter._counters == {}
    assert await limiter.hit("shared", 60) == 1
