"""Memory stream leases expire and release without scanning every identity."""

from __future__ import annotations

import asyncio
import tracemalloc

import pytest
from app.services.locks import StreamQuota


async def test_stream_quota_expiry_and_late_release_are_token_owned(monkeypatch: pytest.MonkeyPatch) -> None:
    now = 100.0
    monkeypatch.setattr("app.services.locks.time.monotonic", lambda: now)
    quota = StreamQuota(lease_seconds=10)
    first = await quota.acquire("owner", 1)
    assert first is not None
    assert await quota.acquire("owner", 1) is None
    now = 110.0
    replacement = await quota.acquire("owner", 1)
    assert replacement is not None and replacement != first
    await quota.release("owner", first)
    assert await quota.acquire("owner", 1) is None
    await quota.release("other", replacement)
    assert await quota.acquire("owner", 1) is None
    await quota.release("owner", replacement)
    await quota.release("owner", replacement)
    assert quota._leases == {}
    assert not quota._expirations


async def test_stream_quota_reclaims_stale_users_but_preserves_newer_leases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 100.0
    monkeypatch.setattr("app.services.locks.time.monotonic", lambda: now)
    quota = StreamQuota(lease_seconds=10)
    old = await quota.acquire("old", 2)
    assert old is not None
    now = 105.0
    active = await quota.acquire("active", 1)
    assert active is not None
    now = 110.0
    assert await quota.acquire("newer", 1) is not None
    assert set(quota._leases) == {"active", "newer"}
    assert await quota.acquire("active", 1) is None
    now = 115.0
    assert await quota.acquire("new", 1) is not None
    assert set(quota._leases) == {"newer", "new"}


async def test_stream_quota_concurrent_admissions_respect_limit() -> None:
    quota = StreamQuota()
    results = await asyncio.gather(*(quota.acquire("owner", 3) for _ in range(20)))
    tokens = [token for token in results if token is not None]
    assert len(tokens) == len(set(tokens)) == 3
    await asyncio.gather(*(quota.release("owner", token) for token in tokens))
    assert quota._leases == {}
    assert not quota._expirations


async def test_stream_quota_admission_does_not_copy_all_live_users() -> None:
    quota = StreamQuota(lease_seconds=3600)
    for identity in range(1000):
        assert await quota.acquire(str(identity), 1) is not None
    tracemalloc.start()
    try:
        token = await quota.acquire("new", 1)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert token is not None
    assert peak < 20_000, f"admission allocated {peak:,} bytes with 1,000 existing users"
