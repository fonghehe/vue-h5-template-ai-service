"""Opt-in integration tests: only isolated vh5_ai_test DB and Redis DB 15."""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
from app.db.models import Message, UsageRecord
from app.db.repositories import ConversationRepository, KnowledgeRepository, UsageRepository
from app.db.session import Database
from app.providers.embedding import MockEmbeddingProvider
from app.services.knowledge import KnowledgeService
from app.services.locks import ConversationLockManager, StreamQuota
from app.services.rate_limit import RedisRateLimiter
from sqlalchemy import func, select

DB_URL = os.environ.get("AI_TEST_DATABASE_URL", "")
REDIS_URL = os.environ.get("AI_TEST_REDIS_URL", "")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DB_URL or not REDIS_URL, reason="isolated infrastructure not configured"),
]


@pytest.fixture
def isolated_urls() -> tuple[str, str]:
    from urllib.parse import urlparse

    from sqlalchemy.engine import make_url

    if make_url(DB_URL).database != "vh5_ai_test" or urlparse(REDIS_URL).path != "/15":
        pytest.fail("Integration tests require vh5_ai_test database and Redis database 15")
    return DB_URL, REDIS_URL


async def test_real_postgres_atomic_reply_and_usage(isolated_urls: tuple[str, str]) -> None:
    database = Database.create(isolated_urls[0])
    user = f"test-{uuid4()}"
    try:
        async with database.sessions.begin() as session:
            conversation = await ConversationRepository(session).create(user_id=user, title="test", model="mock")
            cid = conversation.id
        with pytest.raises(RuntimeError, match="rollback"):
            async with database.sessions.begin() as session:
                conversation = await ConversationRepository(session).get_owned(cid, user)
                await ConversationRepository(session).add_message(conversation, role="assistant", content="partial")
                await UsageRepository(session).add(UsageRecord(user_id=user, model="mock"))
                raise RuntimeError("rollback")
        async with database.sessions() as session:
            assert await session.scalar(select(func.count(Message.id)).where(Message.conversation_id == cid)) == 0
            assert (await UsageRepository(session).summary(user))["requests"] == 0
        async with database.sessions.begin() as session:
            await ConversationRepository(session).delete_owned(cid, user)
    finally:
        await database.aclose()


async def test_real_pgvector_retrieval_and_cascade(isolated_urls: tuple[str, str]) -> None:
    database = Database.create(isolated_urls[0])
    user = f"test-{uuid4()}"
    try:
        async with database.sessions() as session:
            service = KnowledgeService(
                KnowledgeRepository(session), MockEmbeddingProvider(64), chunk_chars=200, overlap_chars=20
            )
            document = await service.ingest(
                user_id=user,
                filename="facts.md",
                content_type="text/markdown",
                data=b"The camera costs 499 and includes a tripod",
                metadata={},
            )
            matches = await service.search(user, "camera tripod", 3)
            assert matches and matches[0].citation["documentId"] == document.id
            assert await service.search("another-user", "camera tripod", 3) == []
        async with database.sessions.begin() as session:
            await KnowledgeRepository(session).delete_owned(document.id, user)
        async with database.sessions() as session:
            assert await KnowledgeRepository(session).chunks(user) == []
    finally:
        await database.aclose()


async def test_real_redis_multi_client_quota_and_expiry(isolated_urls: tuple[str, str]) -> None:
    one = StreamQuota(isolated_urls[1], lease_seconds=0.15)
    two = StreamQuota(isolated_urls[1], lease_seconds=0.15)
    identity = f"test-{uuid4()}"
    try:
        results = await asyncio.gather(*(quota.acquire(identity, 3) for quota in [one, two] * 10))
        tokens = [token for token in results if token]
        assert len(tokens) == 3
        await one.release(identity, tokens[0])
        await one.release(identity, tokens[0])
        replacement = await two.acquire(identity, 3)
        assert replacement and await one.acquire(identity, 3) is None
        await asyncio.sleep(0.2)
        fresh = await one.acquire(identity, 3)
        assert fresh
        # A late release of an expired lease must not delete the new stream.
        for token in tokens:
            await two.release(identity, token)
        await two.release(identity, replacement)
        await one.release(identity, fresh)
    finally:
        await one.aclose()
        await two.aclose()


async def test_real_redis_rate_counter_and_conversation_mutex(isolated_urls: tuple[str, str]) -> None:
    limiter = RedisRateLimiter.from_url(isolated_urls[1])
    one, two = ConversationLockManager(isolated_urls[1]), ConversationLockManager(isolated_urls[1])
    identity = f"test-{uuid4()}"
    order: list[str] = []
    try:
        hits = await asyncio.gather(*(limiter.hit(identity, 1) for _ in range(20)))
        assert sorted(hits) == list(range(1, 21))

        async def work(manager: ConversationLockManager, name: str) -> None:
            async with manager.lease(identity):
                order.append(f"{name}-start")
                await asyncio.sleep(0.02)
                order.append(f"{name}-end")

        await asyncio.gather(work(one, "a"), work(two, "b"))
        assert order in (["a-start", "a-end", "b-start", "b-end"], ["b-start", "b-end", "a-start", "a-end"])
    finally:
        await limiter.aclose()
        await one.aclose()
        await two.aclose()
