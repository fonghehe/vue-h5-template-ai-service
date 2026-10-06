"""Reproducible local CPU/allocation benchmarks; no provider or database I/O.

Run from the repository root: uv run python -m scripts.benchmark_hot_paths
Use the same script on both revisions and compare medians, not individual runs.
"""

from __future__ import annotations

import asyncio
import json
import platform
import statistics
import time
import tracemalloc
from collections.abc import Awaitable, Callable
from functools import partial

from app.core.config import Settings
from app.db.models import Conversation, Message
from app.providers.base import MockChatProvider
from app.services.context import ContextBuilder
from app.services.locks import StreamQuota
from app.services.model_router import ModelRouter
from app.services.prompts import PromptRegistry
from app.services.rate_limit import MemoryRateLimiter


async def measure(operation: Callable[[], Awaitable[object]], iterations: int) -> dict[str, float | int]:
    await operation()
    timings = []
    for _ in range(7):
        started = time.perf_counter()
        for _ in range(iterations):
            await operation()
        timings.append((time.perf_counter() - started) * 1_000_000 / iterations)
    tracemalloc.start()
    try:
        await operation()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return {"median_us": statistics.median(timings), "peak_bytes": peak}


async def main() -> None:
    results: dict[str, object] = {"python": platform.python_version(), "platform": platform.platform()}
    for identities in (100, 10_000):
        limiter = MemoryRateLimiter()
        for identity in range(identities):
            await limiter.hit(str(identity), 3600)
        results[f"rate_limit_{identities}"] = await measure(partial(limiter.hit, "0", 3600), 1000)
        await limiter.aclose()

    quota = StreamQuota(lease_seconds=3600)
    for identity in range(1000):
        await quota.acquire(str(identity), 1)

    async def acquire_release() -> None:
        token = await quota.acquire("benchmark", 1)
        assert token is not None
        await quota.release("benchmark", token)

    results["stream_quota_1000"] = await measure(acquire_release, 1000)
    await quota.aclose()

    settings = Settings(_env_file=None)
    builder = ContextBuilder(
        MockChatProvider(delay_seconds=0), ModelRouter(settings), PromptRegistry(), token_budget=300
    )
    conversation = Conversation(user_id="benchmark", title="fictional", model="mock")
    messages = [Message(role="user", content="x" * 8_000) for _ in range(200)]
    results["summary_200x8000"] = await measure(lambda: builder._summarize(conversation, messages), 100)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
