"""Wire schemas for the chat API.

These models are the contract with `@vh5/ai-chat`. The SSE event shapes mirror
the `ChatChunk` union consumed by `parseEventStream`, and the request shape
mirrors what `FetchChatProvider` sends. Changing a field name here is a
breaking change for the frontend.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

ChatRole = Literal["system", "user", "assistant"]

# A single turn is capped well below the provider context window so that one
# request cannot exhaust the upstream quota.
MAX_MESSAGES = 100
MAX_CONTENT_CHARS = 20_000
MAX_CONVERSATION_ID_CHARS = 120


class ChatMessage(BaseModel):
    """One message in a conversation.

    `id` and `createdAt` are produced by the frontend and are accepted but not
    required, so the service also works with minimal hand-written payloads.
    """

    role: ChatRole
    content: str = Field(min_length=1, max_length=MAX_CONTENT_CHARS)
    id: str | None = None
    created_at: int | None = Field(default=None, alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class ChatRequest(BaseModel):
    """Request body of `POST /api/ai/chat`."""

    model_config = ConfigDict(populate_by_name=True)

    messages: Annotated[list[ChatMessage], Field(min_length=1, max_length=MAX_MESSAGES)]
    conversation_id: str | None = Field(default=None, alias="conversationId", max_length=MAX_CONVERSATION_ID_CHARS)


class StartChunk(BaseModel):
    """Emitted once, before the first token, to bind the conversation."""

    type: Literal["start"] = "start"
    id: str | None = None


class DeltaChunk(BaseModel):
    """One incremental piece of the assistant reply."""

    type: Literal["delta"] = "delta"
    delta: str


class FinishChunk(BaseModel):
    """Emitted once, after the last token, or when the stream ends early."""

    type: Literal["finish"] = "finish"
    reason: Literal["stop", "abort", "error"] | None = None


class ErrorChunk(BaseModel):
    """Emitted in place of a failed stream; the client raises on this."""

    type: Literal["error"] = "error"
    message: str


ChatChunk = StartChunk | DeltaChunk | FinishChunk | ErrorChunk


def encode_sse(chunk: BaseModel) -> str:
    """Serialise a chunk as one Server-Sent Events frame."""
    return f"data: {chunk.model_dump_json(by_alias=True, exclude_none=True)}\n\n"
