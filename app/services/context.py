"""Token-budgeted conversation context construction and summary compaction."""

from __future__ import annotations

from collections.abc import Sequence

from app.db.models import Conversation, Message
from app.providers.base import LLMProvider
from app.schemas.chat import ChatMessage
from app.services.model_router import ModelRouter
from app.services.prompts import PromptRegistry


def estimate_tokens(text: str) -> int:
    """Conservative dependency-free estimate for mixed Latin/CJK content."""
    return max(1, (len(text) + 2) // 3)


class ContextBuilder:
    def __init__(
        self,
        provider: LLMProvider,
        router: ModelRouter,
        prompts: PromptRegistry,
        *,
        token_budget: int,
    ) -> None:
        self._provider = provider
        self._router = router
        self._prompts = prompts
        self._token_budget = token_budget

    async def build(
        self,
        conversation: Conversation,
        messages: Sequence[Message],
        *,
        retrieved_documents: Sequence[str] = (),
        tool_results: Sequence[str] = (),
        prompt_name: str = "assistant.default",
    ) -> list[ChatMessage]:
        system_parts = [self._prompts.get(prompt_name).content]
        if conversation.summary:
            system_parts.append(f"Conversation summary:\n{conversation.summary}")
        if retrieved_documents:
            system_parts.append("Retrieved context:\n" + "\n\n".join(retrieved_documents))
        if tool_results:
            system_parts.append("Tool results:\n" + "\n".join(tool_results))

        system = self._system_message(system_parts)
        remaining = self._token_budget - estimate_tokens(system.content)
        selected: list[ChatMessage] = []
        for message in reversed(messages):
            content = message.content
            role = message.role
            # Persisted tool results remain useful context, but a later turn no
            # longer has the matching assistant tool-call frame required by
            # OpenAI-compatible protocols. Reframe them as trusted history.
            if role == "tool":
                role = "system"
                content = f"Previous registered tool result: {content}"
            cost = estimate_tokens(content) + 4
            if cost > remaining:
                break
            selected.append(ChatMessage.model_validate({"role": role, "content": content}))
            remaining -= cost
        selected.reverse()

        omitted = len(messages) - len(selected)
        if omitted > 0:
            await self._summarize(conversation, messages[:omitted])
            if conversation.summary:
                system_parts = [
                    self._prompts.get(prompt_name).content,
                    f"Conversation summary:\n{conversation.summary}",
                ]
                if retrieved_documents:
                    system_parts.append("Retrieved context:\n" + "\n\n".join(retrieved_documents))
                if tool_results:
                    system_parts.append("Tool results:\n" + "\n".join(tool_results))
                system = self._system_message(system_parts)
                while selected and self.count_tokens([system, *selected]) > self._token_budget:
                    selected.pop(0)
        return [system, *selected]

    async def _summarize(self, conversation: Conversation, messages: Sequence[Message]) -> None:
        history = "\n".join(f"{message.role}: {message.content}" for message in messages)
        transcript = f"Previous summary:\n{conversation.summary}\n\n{history}" if conversation.summary else history
        prompt = self._prompts.get("conversation.summary").content
        result = await self._provider.complete(
            [ChatMessage(role="system", content=prompt), ChatMessage(role="user", content=transcript)],
            self._router.for_task("summarization"),
        )
        # Enforce the budget locally even if a provider ignores maxTokens.
        conversation.summary = result.content[: self._token_budget]

    def _system_message(self, parts: Sequence[str]) -> ChatMessage:
        content = "\n\n".join(parts)
        max_chars = max(1, (self._token_budget - 4) * 3 - 2)
        return ChatMessage(role="system", content=content[:max_chars])

    @staticmethod
    def count_tokens(messages: Sequence[ChatMessage]) -> int:
        return sum(estimate_tokens(message.content) + 4 for message in messages)
