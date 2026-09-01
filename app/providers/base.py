"""Chat providers.

A provider turns a conversation into an async stream of text fragments. Adding
a vendor means implementing :class:`ChatProvider` and registering it in
:mod:`app.providers.factory`; no route, schema or client change is required.
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence

import httpx

from app.core.errors import ProviderError, ProviderTimeoutError
from app.schemas.chat import ChatMessage

# Answer returned by the mock provider. Deliberately mentions the streaming
# design so a first-run demo explains what the user is looking at.
MOCK_ANSWER = """Streaming keeps the UI honest.

The Vue composable sends a typed message list, FastAPI validates it,
and a provider-neutral async generator yields tokens. The route only
translates those tokens into Server-Sent Events, so swapping the mock
provider for a hosted model changes no client code.

Each event is one of: start, delta, finish or error."""


class ChatProvider(ABC):
    """Interface every model backend must implement."""

    #: Name reported by `/health` so operators can confirm what is wired up.
    name: str = "unknown"

    @abstractmethod
    def stream(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        """Yield text fragments of the assistant reply.

        Implementations must clean up their own resources and must not raise
        after the first fragment has been yielded: a failure mid-stream is
        reported to the caller as an `error` event.
        """
        raise NotImplementedError  # pragma: no cover

    async def aclose(self) -> None:
        """Release any resources held by the provider."""
        return None


class MockChatProvider(ChatProvider):
    """Deterministic provider used for development, demos and tests.

    It never calls the network, so the whole stack can be exercised offline.
    """

    name = "mock"

    def __init__(self, *, delay_seconds: float = 0.01) -> None:
        self._delay = delay_seconds

    def stream(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        return self._generate(messages)

    async def _generate(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        last = messages[-1].content.strip() if messages else ""
        answer = MOCK_ANSWER if last else "Please send a message to begin."
        for word in answer.split(" "):
            await asyncio.sleep(self._delay)
            yield f"{word} "


class OpenAICompatibleProvider(ChatProvider):
    """Provider for any OpenAI-compatible `/chat/completions` endpoint.

    Works unchanged with OpenAI, Azure OpenAI, Together, Groq, Ollama and
    vLLM, all of which expose the same streaming shape.
    """

    name = "openai-compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float,
        max_output_chars: int = 20_000,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_output_chars = max_output_chars

    def stream(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        return self._generate(messages)

    async def _generate(self, messages: Sequence[ChatMessage]) -> AsyncIterator[str]:
        body = {
            "model": self._model,
            "stream": True,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        emitted = 0
        try:
            async with (
                httpx.AsyncClient(timeout=self._timeout) as client,
                client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    json=body,
                    headers=headers,
                ) as response,
            ):
                if response.status_code >= 400:
                    # The upstream body may contain account details; only the
                    # status code is safe to forward.
                    raise ProviderError(f"AI provider returned HTTP {response.status_code}")

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
                        # Stop rather than stream unbounded output.
                        return
                    yield delta

        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError() from exc
        except httpx.HTTPError as exc:
            raise ProviderError("AI provider unavailable") from exc
        except ProviderError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise ProviderError("AI provider stream failed") from exc


def _extract_delta(payload: str) -> str | None:
    """Pull the text fragment out of one SSE data line."""
    try:
        value = json.loads(payload)
        delta = value["choices"][0]["delta"].get("content")
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise ProviderError("Malformed AI provider stream") from exc

    # Some providers emit `null` content frames (e.g. tool-call preamble).
    return delta if isinstance(delta, str) else None
