"""Summary input retains the same tail without allocating the whole history."""

from __future__ import annotations

import tracemalloc
from collections.abc import Sequence

import pytest
from app.core.config import Settings
from app.db.models import Conversation, Message
from app.providers.base import MockChatProvider
from app.providers.types import CompletionResult, ModelConfig
from app.schemas.chat import ChatMessage
from app.services.context import ContextBuilder
from app.services.model_router import ModelRouter
from app.services.prompts import PromptRegistry


class SummaryProvider(MockChatProvider):
    def __init__(self) -> None:
        super().__init__(delay_seconds=0)
        self.transcript = ""

    async def complete(self, messages: Sequence[ChatMessage], config: ModelConfig | None = None) -> CompletionResult:
        self.transcript = messages[-1].content
        return CompletionResult(content="summary", model="mock")


@pytest.mark.parametrize(
    ("contents", "expected"),
    [
        (["hello", "world"], "user: hello\nuser: world"),
        (["x" * 20_000, "end"], "x" * 15_990 + "\nuser: end"),
        (["old", "x" * 15_996], "er: " + "x" * 15_996),
        (["old", "x" * 15_994], "user: " + "x" * 15_994),
        (["old", "x" * 15_993], "\nuser: " + "x" * 15_993),
        (["旧记录", "你好" * 8_001], "你好" * 8_000),
        (["", ""], "user: \nuser: "),
    ],
)
async def test_summary_transcript_preserves_exact_tail(settings: Settings, contents: list[str], expected: str) -> None:
    provider = SummaryProvider()
    builder = ContextBuilder(provider, ModelRouter(settings), PromptRegistry(), token_budget=300)
    messages = [Message(role="user", content=content) for content in contents]
    conversation = Conversation(user_id="owner", title="test", model="mock")
    await builder._summarize(conversation, messages)
    assert provider.transcript == expected
    assert conversation.summary == "summary"


async def test_summary_temporary_memory_is_bounded_by_input_tail(settings: Settings) -> None:
    provider = SummaryProvider()
    builder = ContextBuilder(provider, ModelRouter(settings), PromptRegistry(), token_budget=300)
    messages = [Message(role="user", content="x" * 8_000) for _ in range(200)]
    conversation = Conversation(user_id="owner", title="long", model="mock")
    tracemalloc.start()
    try:
        await builder._summarize(conversation, messages)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert len(provider.transcript) == 16_000
    assert peak < 250_000, f"summary allocated {peak:,} bytes for a 16,000-character tail"
