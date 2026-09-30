"""Stateless chat policy and incremental output, independent of FastAPI."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncGenerator

from app.core.config import Settings
from app.core.errors import AppError, RateLimitError, ValidationError
from app.core.observability import ACTIVE_STREAMS, AI_DURATION, AI_REQUESTS, AI_TTFT, PROVIDER_ERRORS
from app.providers.base import LLMProvider
from app.schemas.chat import ChatRequest, DeltaChunk, ErrorChunk, FinishChunk, StartChunk, encode_sse
from app.services.rate_limit import RateLimiter

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, provider: LLMProvider, settings: Settings, limiter: RateLimiter) -> None:
        self.provider, self.settings, self.limiter = provider, settings, limiter

    async def admit(self, payload: ChatRequest, identity: str) -> None:
        if sum(len(message.content) for message in payload.messages) > self.settings.ai_max_input_chars:
            raise ValidationError("Total message content is too large")
        if await self.limiter.hit(f"ai:{identity}", 60) > self.settings.ai_rate_limit_per_minute:
            raise RateLimitError()

    async def stream(self, payload: ChatRequest, conversation_id: str, request_id: str) -> AsyncGenerator[str, None]:
        started = time.perf_counter()
        ACTIVE_STREAMS.inc()
        source: AsyncGenerator[str, None] | None = None
        try:
            yield encode_sse(StartChunk(id=conversation_id))
            source = self.provider.stream(payload.messages)
            emitted = 0
            async for delta in source:
                if delta and emitted == 0:
                    AI_TTFT.labels(path="chat").observe(time.perf_counter() - started)
                emitted += len(delta)
                if emitted > self.settings.ai_max_output_chars:
                    raise ValidationError("AI output limit exceeded")
                if delta:
                    yield encode_sse(DeltaChunk(delta=delta))
            AI_REQUESTS.labels(path="chat", status="ok").inc()
            yield encode_sse(FinishChunk(reason="stop"))
        except asyncio.CancelledError:
            AI_REQUESTS.labels(path="chat", status="cancelled").inc()
            raise
        except Exception as exc:
            AI_REQUESTS.labels(path="chat", status="error").inc()
            PROVIDER_ERRORS.labels(provider=self.provider.name, kind=type(exc).__name__).inc()
            logger.exception("chat stream failed")
            yield encode_sse(
                ErrorChunk(
                    message=exc.message if isinstance(exc, AppError) else "AI stream failed",
                    code=exc.code if isinstance(exc, AppError) else 5000,
                    requestId=request_id,
                )
            )
        finally:
            try:
                if source is not None:
                    await source.aclose()
            finally:
                ACTIVE_STREAMS.dec()
                AI_DURATION.labels(path="chat").observe(time.perf_counter() - started)
