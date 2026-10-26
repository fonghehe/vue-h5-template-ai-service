"""Context-window compaction tests."""

from __future__ import annotations

import pytest
from app.core.config import Settings
from app.db.models import Conversation, Message
from app.providers.base import MockChatProvider
from app.services.context import ContextBuilder
from app.services.model_router import ModelRouter
from app.services.prompts import PromptRegistry


async def test_one_hundred_messages_stay_within_token_budget(settings) -> None:  # type: ignore[no-untyped-def]
    conversation = Conversation(user_id="u1", title="long", model="mock")
    messages = [
        Message(
            conversation_id="c1",
            sequence=index,
            role="user" if index % 2 else "assistant",
            content=f"message {index} " + "x" * 80,
        )
        for index in range(1, 101)
    ]
    builder = ContextBuilder(
        MockChatProvider(delay_seconds=0), ModelRouter(settings), PromptRegistry(), token_budget=300
    )

    context = await builder.build(conversation, messages)

    assert conversation.summary is not None
    assert builder.count_tokens(context) <= 300
    assert len(context) < len(messages)


@pytest.mark.parametrize("budget", [512, 8_000])
async def test_long_retrieval_context_preserves_newest_user_message(settings: Settings, budget: int) -> None:
    builder = ContextBuilder(MockChatProvider(), ModelRouter(settings), PromptRegistry(), token_budget=budget)
    messages = [Message(role="user", content="What is the document about?")]
    conversation = Conversation(user_id="u", title="test", model="mock")
    result = await builder.build(conversation, messages, retrieved_documents=["retrieved text " * 3000])
    assert result[-1].role == "user"
    assert result[-1].content == messages[-1].content
    assert builder.count_tokens(result) <= budget
