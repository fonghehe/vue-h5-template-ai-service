"""Chat streaming route.

The route is a thin translation layer: validate input, enforce quota, then
convert provider fragments into Server-Sent Events frames. All model-specific
logic lives in :mod:`app.providers`.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.errors import AppError, RateLimitError
from app.core.security import (
    ChatProviderDep,
    CurrentPrincipal,
    RateLimiterDep,
    SettingsDep,
)
from app.providers.base import ChatProvider
from app.schemas.chat import (
    ChatRequest,
    DeltaChunk,
    ErrorChunk,
    FinishChunk,
    StartChunk,
    encode_sse,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])
logger = logging.getLogger(__name__)

RATE_LIMIT_WINDOW_SECONDS = 60


@router.post("/chat", summary="Stream a chat completion as Server-Sent Events")
async def chat(
    payload: ChatRequest,
    request: Request,
    settings: SettingsDep,
    provider: ChatProviderDep,
    rate_limiter: RateLimiterDep,
    principal: CurrentPrincipal,
) -> StreamingResponse:
    """Stream an assistant reply for the supplied conversation.

    Emits `start`, zero or more `delta`, and finally `finish`. A failure after
    the stream has begun is reported as an `error` event, because the HTTP
    status has already been sent.
    """
    identity = _rate_limit_identity(principal.subject, principal.kind, request)
    count = await rate_limiter.hit(f"ai:{principal.kind}:{identity}", RATE_LIMIT_WINDOW_SECONDS)
    if count > settings.ai_rate_limit_per_minute:
        logger.warning("rate limit exceeded", extra={"subject": identity, "kind": principal.kind})
        raise RateLimitError()

    conversation_id = payload.conversation_id or f"conversation-{uuid4().hex}"
    logger.info(
        "chat stream started",
        extra={
            "conversationId": conversation_id,
            "subject": principal.subject,
            "kind": principal.kind,
            "messages": len(payload.messages),
            "provider": provider.name,
        },
    )

    return StreamingResponse(
        _event_stream(request, provider, payload, conversation_id),
        media_type="text/event-stream",
        headers={
            # `no-transform` stops intermediaries from buffering or recompressing.
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            # Disables proxy buffering in nginx and friends.
            "X-Accel-Buffering": "no",
        },
    )


async def _event_stream(
    request: Request,
    provider: ChatProvider,
    payload: ChatRequest,
    conversation_id: str,
) -> AsyncIterator[str]:
    """Yield SSE frames until the provider finishes or the client disconnects."""
    yield encode_sse(StartChunk(id=conversation_id))

    emitted = 0
    try:
        async for delta in provider.stream(payload.messages):
            # Stop promptly when the browser navigates away or aborts, instead
            # of paying for tokens nobody will read.
            if await request.is_disconnected():
                logger.info("client disconnected", extra={"conversationId": conversation_id})
                yield encode_sse(FinishChunk(reason="abort"))
                return

            emitted += len(delta)
            if not delta:
                continue
            yield encode_sse(DeltaChunk(delta=delta))

    except Exception as exc:
        logger.exception("chat stream failed", extra={"conversationId": conversation_id})
        # The generic message keeps provider internals out of the browser.
        yield encode_sse(ErrorChunk(message=_safe_error_message(exc)))
        return

    logger.info(
        "chat stream finished",
        extra={"conversationId": conversation_id, "characters": emitted},
    )
    yield encode_sse(FinishChunk(reason="stop"))


def _safe_error_message(exc: Exception) -> str:
    """Return a client-safe message for a stream failure.

    Application errors carry messages written for end users; anything else is
    replaced by a generic sentence so stack details cannot leak.
    """
    if isinstance(exc, AppError):
        return exc.message
    return "AI stream failed"


def _rate_limit_identity(subject: str, kind: str, request: Request) -> str:
    """Build the quota key for a request.

    Anonymous callers are keyed by client IP; authenticated callers by subject,
    so that sharing a NAT does not let one user exhaust another's quota while
    still preventing a single IP from flooding us anonymously.
    """
    if kind != "anonymous":
        return subject
    if request.client is not None:
        return request.client.host
    return "unknown"
