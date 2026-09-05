"""Embedding providers used by the knowledge service."""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from collections.abc import Sequence

import httpx

from app.core.errors import ProviderError


class EmbeddingProvider(ABC):
    name: str = "unknown"

    @abstractmethod
    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise NotImplementedError  # pragma: no cover

    async def aclose(self) -> None:
        return None


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic local embeddings suitable for tests and development."""

    name = "mock"

    def __init__(self, dimensions: int = 64) -> None:
        self._dimensions = dimensions

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [_hashed_embedding(text, self._dimensions) for text in texts]


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    name = "openai-compatible"

    def __init__(self, *, base_url: str, api_key: str, model: str, timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(timeout=timeout)

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        try:
            response = await self._client.post(
                f"{self._base_url}/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model, "input": list(texts)},
            )
            if response.status_code >= 400:
                raise ProviderError(f"Embedding provider returned HTTP {response.status_code}")
            payload = response.json()
            ordered = sorted(payload["data"], key=lambda item: int(item["index"]))
            return [[float(value) for value in item["embedding"]] for item in ordered]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise ProviderError("Embedding provider unavailable") from exc

    async def aclose(self) -> None:
        await self._client.aclose()


def _hashed_embedding(text: str, dimensions: int) -> list[float]:
    values = [0.0] * dimensions
    for word in text.lower().split():
        digest = hashlib.sha256(word.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        values[index] += -1.0 if digest[4] & 1 else 1.0
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]
