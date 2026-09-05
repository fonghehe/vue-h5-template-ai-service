"""Provider-neutral model contracts used by application services."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelConfig(BaseModel):
    """Per-call generation controls, independent of any vendor SDK."""

    model_config = ConfigDict(populate_by_name=True)

    model: str
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=2_000, alias="maxTokens", ge=1, le=100_000)
    timeout: float = Field(default=60.0, gt=0, le=300)


class TokenUsage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    prompt_tokens: int = Field(default=0, alias="promptTokens", ge=0)
    completion_tokens: int = Field(default=0, alias="completionTokens", ge=0)
    total_tokens: int = Field(default=0, alias="totalTokens", ge=0)


class CompletionResult(BaseModel):
    content: str
    model: str
    usage: TokenUsage = Field(default_factory=TokenUsage)
    finish_reason: str = Field(default="stop", alias="finishReason")

    model_config = ConfigDict(populate_by_name=True)


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(alias="inputSchema")

    model_config = ConfigDict(populate_by_name=True)


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class ToolCallingResult(CompletionResult):
    tool_calls: list[ToolCall] = Field(default_factory=list, alias="toolCalls")
