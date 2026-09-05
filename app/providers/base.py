"""Provider-neutral LLM interface and concrete offline/HTTP adapters."""

from __future__ import annotations

import asyncio
import json
import random
import re
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from typing import TypeVar
from uuid import uuid4

import httpx
from pydantic import BaseModel, ValidationError

from app.core.errors import ProviderError, ProviderTimeoutError
from app.providers.types import CompletionResult, ModelConfig, TokenUsage, ToolCall, ToolCallingResult, ToolDefinition
from app.schemas.chat import ChatMessage

StructuredT = TypeVar("StructuredT", bound=BaseModel)

MOCK_ANSWER = """Streaming keeps the UI honest.

The Vue composable sends a typed message list, FastAPI validates it,
and a provider-neutral async generator yields tokens. The route only
translates those tokens into Server-Sent Events, so swapping the mock
provider for a hosted model changes no client code.

Each event is one of: start, delta, finish or error."""


class LLMProvider(ABC):
    """Application-facing model interface; vendor SDK objects never escape it."""

    name: str = "unknown"

    @abstractmethod
    def stream(self, messages: Sequence[ChatMessage], config: ModelConfig | None = None) -> AsyncIterator[str]:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    async def complete(self, messages: Sequence[ChatMessage], config: ModelConfig | None = None) -> CompletionResult:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    async def structured_output(
        self,
        messages: Sequence[ChatMessage],
        schema: type[StructuredT],
        config: ModelConfig | None = None,
    ) -> StructuredT:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    async def tool_calling(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolDefinition],
        config: ModelConfig | None = None,
    ) -> ToolCallingResult:
        raise NotImplementedError  # pragma: no cover

    async def aclose(self) -> None:
        return None


ChatProvider = LLMProvider


class MockChatProvider(LLMProvider):
    name = "mock"

    def __init__(self, *, delay_seconds: float = 0.01, answer: str | None = None) -> None:
        self._delay = delay_seconds
        self._answer = answer

    def stream(self, messages: Sequence[ChatMessage], config: ModelConfig | None = None) -> AsyncIterator[str]:
        return self._generate(messages)

    async def _generate(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        last = messages[-1].content.strip() if messages else ""
        answer = self._answer or (MOCK_ANSWER if last else "Please send a message to begin.")
        for word in answer.split(" "):
            await asyncio.sleep(self._delay)
            yield f"{word} "

    async def complete(self, messages: Sequence[ChatMessage], config: ModelConfig | None = None) -> CompletionResult:
        content = self._answer or (messages[-1].content if messages else "")
        return CompletionResult(
            content=content,
            model=config.model if config else "mock",
            usage=_estimated_usage(messages, content),
        )

    async def structured_output(
        self,
        messages: Sequence[ChatMessage],
        schema: type[StructuredT],
        config: ModelConfig | None = None,
    ) -> StructuredT:
        content = self._answer or (messages[-1].content if messages else "{}")
        try:
            return schema.model_validate_json(content)
        except ValidationError as exc:
            raise ProviderError("Model returned invalid structured output") from exc

    async def tool_calling(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolDefinition],
        config: ModelConfig | None = None,
    ) -> ToolCallingResult:
        last = messages[-1].content.lower() if messages else ""
        if messages and messages[-1].role == "tool":
            content = f"I used the registered tool. Result: {messages[-1].content}"
            return ToolCallingResult(
                content=content,
                model="mock",
                usage=_estimated_usage(messages, content),
            )
        available = {tool.name for tool in tools}
        calls: list[ToolCall] = []
        if ("product" in last or "商品" in last) and "search_product" in available:
            arguments: dict[str, object] = {"query": last}
            prices = re.findall(r"\d+(?:\.\d+)?", last)
            if prices:
                arguments["maxPrice"] = float(prices[0])
            calls.append(ToolCall(id=f"call-{uuid4().hex}", name="search_product", arguments=arguments))
        elif any(char.isdigit() for char in last) and "calculator" in available:
            calls.append(ToolCall(id=f"call-{uuid4().hex}", name="calculator", arguments={"expression": last}))
        content = "" if calls else (self._answer or MOCK_ANSWER)
        return ToolCallingResult(
            content=content,
            model="mock",
            toolCalls=calls,
            usage=_estimated_usage(messages, content),
        )


class OpenAICompatibleProvider(LLMProvider):
    name = "openai-compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
        max_output_chars: int = 20_000,
        max_retries: int = 3,
        retry_base_seconds: float = 0.25,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._default_config = ModelConfig(model=model, timeout=timeout)
        self._max_output_chars = max_output_chars
        self._max_retries = max_retries
        self._retry_base_seconds = retry_base_seconds

    def stream(self, messages: Sequence[ChatMessage], config: ModelConfig | None = None) -> AsyncIterator[str]:
        return self._generate(messages, config or self._default_config)

    async def _generate(self, messages: Sequence[ChatMessage], config: ModelConfig) -> AsyncIterator[str]:
        emitted = 0
        attempt = 0
        while True:
            try:
                async with (
                    httpx.AsyncClient(timeout=config.timeout) as client,
                    client.stream(
                        "POST",
                        f"{self._base_url}/chat/completions",
                        json=self._body(messages, config, stream=True),
                        headers=self._headers,
                    ) as response,
                ):
                    if response.status_code >= 400:
                        _raise_for_status(response.status_code)
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        payload = line[5:].strip()
                        if not payload or payload == "[DONE]":
                            continue
                        delta = _extract_delta(payload)
                        if not delta:
                            continue
                        emitted += len(delta)
                        if emitted > self._max_output_chars:
                            return
                        yield delta
                    return
            except (httpx.TimeoutException, httpx.TransportError, ProviderError) as exc:
                if emitted or not _retryable(exc) or attempt >= self._max_retries:
                    if isinstance(exc, httpx.TimeoutException):
                        raise ProviderTimeoutError() from exc
                    if isinstance(exc, ProviderError):
                        raise
                    raise ProviderError("AI provider unavailable") from exc
                await self._backoff(attempt)
                attempt += 1

    async def complete(self, messages: Sequence[ChatMessage], config: ModelConfig | None = None) -> CompletionResult:
        chosen = config or self._default_config
        payload = await self._post(self._body(messages, chosen, stream=False), chosen.timeout)
        try:
            content = str(payload["choices"][0]["message"]["content"])  # type: ignore[index]
            usage = TokenUsage.model_validate(payload.get("usage", {}))
            return CompletionResult(content=content, model=str(payload.get("model", chosen.model)), usage=usage)
        except (KeyError, IndexError, TypeError, ValidationError) as exc:
            raise ProviderError("Malformed AI provider response") from exc

    async def structured_output(
        self,
        messages: Sequence[ChatMessage],
        schema: type[StructuredT],
        config: ModelConfig | None = None,
    ) -> StructuredT:
        chosen = config or self._default_config
        body = self._body(messages, chosen, stream=False)
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "strict": True, "schema": schema.model_json_schema()},
        }
        last_error: Exception | None = None
        for _ in range(2):
            payload = await self._post(body, chosen.timeout)
            try:
                choices = payload["choices"]
                assert isinstance(choices, list)
                return schema.model_validate_json(choices[0]["message"]["content"])
            except (AssertionError, KeyError, IndexError, TypeError, ValidationError) as exc:
                last_error = exc
                messages_body = body["messages"]
                assert isinstance(messages_body, list)
                body["messages"] = [
                    *messages_body,
                    {"role": "system", "content": "Return valid JSON matching the schema."},
                ]
        raise ProviderError("Model returned invalid structured output") from last_error

    async def tool_calling(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolDefinition],
        config: ModelConfig | None = None,
    ) -> ToolCallingResult:
        chosen = config or self._default_config
        body = self._body(messages, chosen, stream=False)
        body["tools"] = [
            {
                "type": "function",
                "function": {"name": tool.name, "description": tool.description, "parameters": tool.input_schema},
            }
            for tool in tools
        ]
        payload = await self._post(body, chosen.timeout)
        try:
            choices = payload["choices"]
            assert isinstance(choices, list)
            message = choices[0]["message"]
            calls = [
                ToolCall(
                    id=str(item["id"]),
                    name=str(item["function"]["name"]),
                    arguments=json.loads(item["function"]["arguments"]),
                )
                for item in message.get("tool_calls", [])
            ]
            return ToolCallingResult(
                content=str(message.get("content") or ""),
                model=str(payload.get("model", chosen.model)),
                usage=TokenUsage.model_validate(payload.get("usage", {})),
                toolCalls=calls,
            )
        except (AssertionError, KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
            raise ProviderError("Malformed tool-calling response") from exc

    async def _post(self, body: dict[str, object], request_timeout: float) -> dict[str, object]:
        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=request_timeout) as client:
                    response = await client.post(f"{self._base_url}/chat/completions", json=body, headers=self._headers)
                if response.status_code >= 400:
                    _raise_for_status(response.status_code)
                value = response.json()
                if not isinstance(value, dict):
                    raise ProviderError("Malformed AI provider response")
                return value
            except (httpx.TimeoutException, httpx.TransportError, ProviderError) as exc:
                if not _retryable(exc) or attempt >= self._max_retries:
                    if isinstance(exc, httpx.TimeoutException):
                        raise ProviderTimeoutError() from exc
                    if isinstance(exc, ProviderError):
                        raise
                    raise ProviderError("AI provider unavailable") from exc
                await self._backoff(attempt)
        raise ProviderError("AI provider unavailable")  # pragma: no cover

    def _body(self, messages: Sequence[ChatMessage], config: ModelConfig, *, stream: bool) -> dict[str, object]:
        wire_messages: list[dict[str, object]] = []
        for message in messages:
            item: dict[str, object] = {"role": message.role, "content": message.content}
            if message.tool_calls:
                item["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
                    }
                    for call in message.tool_calls
                ]
            if message.tool_call_id:
                item["tool_call_id"] = message.tool_call_id
            wire_messages.append(item)
        return {
            "model": config.model,
            "stream": stream,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "messages": wire_messages,
        }

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    async def _backoff(self, attempt: int) -> None:
        delay = self._retry_base_seconds * (2**attempt) + random.uniform(0, self._retry_base_seconds)  # noqa: S311
        await asyncio.sleep(delay)


def _raise_for_status(status_code: int) -> None:
    error = ProviderError(f"AI provider returned HTTP {status_code}")
    error.detail = {"retryable": status_code == 429 or status_code >= 500}
    raise error


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    return isinstance(exc, ProviderError) and isinstance(exc.detail, dict) and exc.detail.get("retryable") is True


def _extract_delta(payload: str) -> str | None:
    try:
        value = json.loads(payload)
        delta = value["choices"][0]["delta"].get("content")
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise ProviderError("Malformed AI provider stream") from exc
    return delta if isinstance(delta, str) else None


def _estimated_usage(messages: Sequence[ChatMessage], content: str) -> TokenUsage:
    prompt = sum(max(1, len(message.content) // 4) for message in messages)
    completion = max(1, len(content) // 4) if content else 0
    return TokenUsage(promptTokens=prompt, completionTokens=completion, totalTokens=prompt + completion)
