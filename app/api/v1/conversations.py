"""Conversation HTTP contracts; business orchestration lives in the service."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.api.streaming import QuotaStreamingResponse
from app.core.errors import RateLimitError
from app.core.security import AuthenticatedUser, SettingsDep
from app.schemas.conversation import ConversationCreate, ConversationMessageCreate, ConversationView
from app.schemas.envelope import ApiResponse
from app.services.conversations import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_service(request: Request) -> ConversationService:
    state = request.app.state
    return ConversationService(
        state.database,
        state.settings,
        state.chat_provider,
        state.embedding_provider,
        state.context_builder,
        state.agent_workflow,
        state.model_router,
        state.conversation_locks,
        state.rate_limiter,
    )


ServiceDep = Annotated[ConversationService, Depends(get_service)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Page = Annotated[int, Query(ge=1, le=100_000)]


@router.post("", response_model=ApiResponse[ConversationView])
async def create_conversation(
    payload: ConversationCreate, request: Request, user: AuthenticatedUser, service: ServiceDep
) -> ApiResponse[ConversationView]:
    return ApiResponse(data=await service.create(user.subject, payload), requestId=request.state.request_id)


@router.get("", response_model=ApiResponse[list[ConversationView]])
async def list_conversations(
    request: Request, user: AuthenticatedUser, service: ServiceDep, page: Page = 1, page_size: PageSize = 50
) -> ApiResponse[list[ConversationView]]:
    return ApiResponse(
        data=await service.list(user.subject, limit=page_size, offset=(page - 1) * page_size),
        requestId=request.state.request_id,
    )


@router.get("/{conversation_id}", response_model=ApiResponse[ConversationView])
async def get_conversation(
    conversation_id: str,
    request: Request,
    user: AuthenticatedUser,
    service: ServiceDep,
    page_size: PageSize = 100,
    before: Annotated[int | None, Query(ge=1)] = None,
) -> ApiResponse[ConversationView]:
    return ApiResponse(
        data=await service.get(conversation_id, user.subject, limit=page_size, before=before),
        requestId=request.state.request_id,
    )


@router.delete("/{conversation_id}", response_model=ApiResponse[None])
async def delete_conversation(
    conversation_id: str, request: Request, user: AuthenticatedUser, service: ServiceDep
) -> ApiResponse[None]:
    await service.delete(conversation_id, user.subject)
    return ApiResponse(data=None, requestId=request.state.request_id)


@router.post("/{conversation_id}/messages")
async def create_message(
    conversation_id: str,
    payload: ConversationMessageCreate,
    request: Request,
    user: AuthenticatedUser,
    settings: SettingsDep,
    service: ServiceDep,
) -> StreamingResponse:
    await service.admit(conversation_id, user.subject, payload)
    quota = request.app.state.stream_quota
    identity = f"user:{user.subject}"
    token = await quota.acquire(identity, settings.ai_concurrent_stream_limit)
    if token is None:
        raise RateLimitError("Too many concurrent streams")
    return QuotaStreamingResponse(
        service.stream(conversation_id, user.subject, payload, request.state.request_id),
        quota=quota,
        identity=identity,
        token=token,
        timeout=settings.ai_stream_timeout_seconds,
        heartbeat=settings.sse_heartbeat_seconds,
        request_id=request.state.request_id,
        disconnected=request.is_disconnected,
    )
