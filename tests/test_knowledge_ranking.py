"""SQLite retrieval preserves ranking, ties and ownership with bounded Top-K."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

import pytest
from app.db.models import Document, DocumentChunk
from app.db.repositories import KnowledgeRepository
from app.db.session import Database
from app.providers.embedding import EmbeddingProvider
from app.services.knowledge import KnowledgeService


class QueryEmbeddings(EmbeddingProvider):
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


@pytest.fixture
async def knowledge() -> AsyncIterator[KnowledgeService]:
    database = Database.create("sqlite+aiosqlite:///:memory:")
    try:
        await database.create_schema()
        async with database.sessions() as session:
            repository = KnowledgeRepository(session)
            async with session.begin():
                await repository.create(
                    Document(user_id="owner", title="Owned", source="owned.md", content="content", metadata_json={}),
                    [
                        DocumentChunk(chunk_index=index, content=text, embedding=vector)
                        for index, (text, vector) in enumerate(
                            [
                                ("first tie", [1.0, 0.0]),
                                ("second tie", [2.0, 0.0]),
                                ("orthogonal", [0.0, 1.0]),
                                ("opposite", [-1.0, 0.0]),
                                ("partial", [1.0, 1.0]),
                            ]
                        )
                    ],
                )
                await repository.create(
                    Document(
                        user_id="other", title="Private", source="private.md", content="private", metadata_json={}
                    ),
                    [DocumentChunk(chunk_index=0, content="private", embedding=[1.0, 0.0])],
                )
            yield KnowledgeService(repository, QueryEmbeddings(), chunk_chars=200, overlap_chars=20)
    finally:
        await database.aclose()


@pytest.mark.parametrize("top_k", [1, 3, 20])
async def test_top_k_preserves_descending_scores_and_stable_ties(knowledge: KnowledgeService, top_k: int) -> None:
    matches = await knowledge.search("owner", "query", top_k)
    expected = ["first tie", "second tie", "partial", "orthogonal", "opposite"][:top_k]
    assert [match.content for match in matches] == expected
    assert all(match.citation["title"] == "Owned" for match in matches)
    assert [match.score for match in matches] == sorted((match.score for match in matches), reverse=True)


async def test_top_k_returns_no_matches_for_another_owner(knowledge: KnowledgeService) -> None:
    assert await knowledge.search("missing-owner", "query", 3) == []
