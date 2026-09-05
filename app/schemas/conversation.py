"""Public conversation and usage contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=200)
    model: str | None = Field(default=None, max_length=120)


class ConversationMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    mode: Literal["auto", "chat", "agent"] = "auto"
    use_rag: bool = Field(default=False, alias="useRag")

    model_config = ConfigDict(populate_by_name=True)


class MessageView(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    conversation_id: str = Field(alias="conversationId")
    role: str
    content: str
    tool_call_id: str | None = Field(default=None, alias="toolCallId")
    token_usage: dict[str, Any] | None = Field(default=None, alias="tokenUsage")
    latency_ms: float | None = Field(default=None, alias="latencyMs")
    citations: list[dict[str, Any]] | None = None
    created_at: datetime = Field(alias="createdAt")


class ConversationView(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    user_id: str = Field(alias="userId")
    title: str
    model: str
    summary: str | None = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    messages: list[MessageView] | None = None


class UsageBreakdown(BaseModel):
    key: str
    prompt_tokens: int = Field(alias="promptTokens")
    completion_tokens: int = Field(alias="completionTokens")
    total_tokens: int = Field(alias="totalTokens")
    requests: int

    model_config = ConfigDict(populate_by_name=True)


class UsageView(BaseModel):
    prompt_tokens: int = Field(alias="promptTokens")
    completion_tokens: int = Field(alias="completionTokens")
    total_tokens: int = Field(alias="totalTokens")
    requests: int
    by_model: list[UsageBreakdown] = Field(default_factory=list, alias="byModel")
    by_conversation: list[UsageBreakdown] = Field(default_factory=list, alias="byConversation")
    by_date: list[UsageBreakdown] = Field(default_factory=list, alias="byDate")

    model_config = ConfigDict(populate_by_name=True)
