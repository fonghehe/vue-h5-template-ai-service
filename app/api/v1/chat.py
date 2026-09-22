"""The legacy and versioned stateless SSE transport."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.api.streaming import QuotaStreamingResponse
from app.core.errors import RateLimitError
from app.core.security import ChatProviderDep, CurrentPrincipal, RateLimiterDep, SettingsDep
from app.schemas.chat import ChatRequest
from app.services.chat import ChatService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", summary="Stream a chat completion as Server-Sent Events")
async def chat(
    payload: ChatRequest,
    request: Request,
    settings: SettingsDep,
    provider: ChatProviderDep,
    rate_limiter: RateLimiterDep,
    principal: CurrentPrincipal,
) -> StreamingResponse:
    subject = principal.subject
    if principal.kind == "anonymous":
        subject = request.client.host if request.client is not None else "unknown"
    identity = f"{principal.kind}:{subject}"
    service = ChatService(provider, settings, rate_limiter)
    await service.admit(payload, identity)
    quota = request.app.state.stream_quota
    token = await quota.acquire(identity, settings.ai_concurrent_stream_limit)
    if token is None:
        raise RateLimitError("Too many concurrent streams")
    conversation_id = payload.conversation_id or f"conversation-{uuid4().hex}"
    return QuotaStreamingResponse(
        service.stream(payload, conversation_id, request.state.request_id),
        quota=quota,
        identity=identity,
        token=token,
        timeout=settings.ai_stream_timeout_seconds,
        heartbeat=settings.sse_heartbeat_seconds,
        request_id=request.state.request_id,
        disconnected=request.is_disconnected,
    )
