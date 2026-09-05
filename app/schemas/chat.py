"""Wire schemas for the chat API.

These models are the contract with `@vh5/ai-chat`. The SSE event shapes mirror
the `ChatChunk` union consumed by `parseEventStream`, and the request shape
mirrors what `FetchChatProvider` sends. Changing a field name here is a
breaking change for the frontend.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ChatRole = Literal["system", "user", "assistant", "tool"]

# A single turn is capped well below the provider context window so that one
# request cannot exhaust the upstream quota.
MAX_MESSAGES = 100
MAX_CONTENT_CHARS = 20_000
MAX_CONVERSATION_ID_CHARS = 120
MAX_TOTAL_INPUT_CHARS = 100_000


class ChatToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class ChatMessage(BaseModel):
    """One message in a conversation.

    `id` and `createdAt` are produced by the frontend and are accepted but not
    required, so the service also works with minimal hand-written payloads.
    """

    role: ChatRole
    content: str = Field(max_length=MAX_CONTENT_CHARS)
    id: str | None = None
    created_at: int | None = Field(default=None, alias="createdAt")
    tool_calls: list[ChatToolCall] = Field(default_factory=list, alias="toolCalls")
    tool_call_id: str | None = Field(default=None, alias="toolCallId")

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_content_or_tool_call(self) -> ChatMessage:
        if not self.content and not self.tool_calls:
            raise ValueError("Message content must not be empty")
        if self.role == "tool" and not self.tool_call_id:
            raise ValueError("Tool messages require toolCallId")
        return self


class ChatRequest(BaseModel):
    """Request body of `POST /api/ai/chat`."""

    model_config = ConfigDict(populate_by_name=True)

    messages: Annotated[list[ChatMessage], Field(min_length=1, max_length=MAX_MESSAGES)]
    conversation_id: str | None = Field(default=None, alias="conversationId", max_length=MAX_CONVERSATION_ID_CHARS)

    @model_validator(mode="after")
    def validate_total_size(self) -> ChatRequest:
        if sum(len(message.content) for message in self.messages) > MAX_TOTAL_INPUT_CHARS:
            raise ValueError("Total message content is too large")
        return self


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


class ToolStartChunk(BaseModel):
    type: Literal["tool_start"] = "tool_start"
    tool: str
    call_id: str = Field(alias="callId")

    model_config = ConfigDict(populate_by_name=True)


class ToolResultChunk(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool: str
    call_id: str = Field(alias="callId")
    result: object

    model_config = ConfigDict(populate_by_name=True)


class ThinkingStatusChunk(BaseModel):
    type: Literal["thinking_status"] = "thinking_status"
    status: str


class SourcesChunk(BaseModel):
    type: Literal["sources"] = "sources"
    sources: list[dict[str, str]]


ChatChunk = (
    StartChunk
    | DeltaChunk
    | FinishChunk
    | ErrorChunk
    | ToolStartChunk
    | ToolResultChunk
    | ThinkingStatusChunk
    | SourcesChunk
)


def encode_sse(chunk: BaseModel) -> str:
    """Serialise a chunk as one Server-Sent Events frame."""
    return f"data: {chunk.model_dump_json(by_alias=True, exclude_none=True)}\n\n"
