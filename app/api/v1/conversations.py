"""Persistent conversation APIs and streamed assistant turns."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import RateLimitError, ValidationError
from app.core.observability import ACTIVE_STREAMS, AI_DURATION, AI_REQUESTS, AI_TOKENS, PROVIDER_ERRORS, span
from app.core.security import AuthenticatedUser, ChatProviderDep, SettingsDep
from app.db.models import Conversation, UsageRecord
from app.db.repositories import ConversationRepository, KnowledgeRepository, UsageRepository
from app.db.session import get_db_session
from app.providers.base import LLMProvider
from app.schemas.chat import (
    DeltaChunk,
    ErrorChunk,
    FinishChunk,
    SourcesChunk,
    StartChunk,
    ThinkingStatusChunk,
    ToolResultChunk,
    ToolStartChunk,
    encode_sse,
)
from app.schemas.conversation import ConversationCreate, ConversationMessageCreate, ConversationView, MessageView
from app.schemas.envelope import ApiResponse
from app.services.agent import AgentState, AgentWorkflow
from app.services.context import ContextBuilder, estimate_tokens
from app.services.knowledge import KnowledgeService
from app.services.streaming import cancel_aware_stream

router = APIRouter(prefix="/api/conversations", tags=["conversations"])
logger = logging.getLogger(__name__)
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=ApiResponse[ConversationView], summary="Create a conversation")
async def create_conversation(
    payload: ConversationCreate,
    request: Request,
    user: AuthenticatedUser,
    settings: SettingsDep,
    session: DbSession,
) -> ApiResponse[ConversationView]:
    allowed_models = {
        settings.ai_model,
        settings.model_simple_chat,
        settings.model_reasoning,
        settings.model_summarization,
    }
    if payload.model is not None and payload.model not in allowed_models:
        raise ValidationError("Requested model is not configured")
    conversation = await ConversationRepository(session).create(
        user_id=user.subject, title=payload.title, model=payload.model or settings.ai_model
    )
    return ApiResponse(data=_conversation_view(conversation), requestId=request.state.request_id)


@router.get("", response_model=ApiResponse[list[ConversationView]], summary="List my conversations")
async def list_conversations(
    request: Request, user: AuthenticatedUser, session: DbSession
) -> ApiResponse[list[ConversationView]]:
    conversations = await ConversationRepository(session).list(user.subject)
    return ApiResponse(data=[_conversation_view(item) for item in conversations], requestId=request.state.request_id)


@router.get("/{conversation_id}", response_model=ApiResponse[ConversationView], summary="Get a conversation")
async def get_conversation(
    conversation_id: str, request: Request, user: AuthenticatedUser, session: DbSession
) -> ApiResponse[ConversationView]:
    conversation = await ConversationRepository(session).get_owned(conversation_id, user.subject, messages=True)
    return ApiResponse(
        data=_conversation_view(conversation, include_messages=True),
        requestId=request.state.request_id,
    )


@router.delete("/{conversation_id}", response_model=ApiResponse[None], summary="Delete a conversation")
async def delete_conversation(
    conversation_id: str, request: Request, user: AuthenticatedUser, session: DbSession
) -> ApiResponse[None]:
    await ConversationRepository(session).delete_owned(conversation_id, user.subject)
    return ApiResponse(data=None, requestId=request.state.request_id)


@router.post("/{conversation_id}/messages", summary="Persist a user message and stream the assistant reply")
async def create_message(
    conversation_id: str,
    payload: ConversationMessageCreate,
    request: Request,
    user: AuthenticatedUser,
    settings: SettingsDep,
    provider: ChatProviderDep,
    session: DbSession,
) -> StreamingResponse:
    if len(payload.content) > settings.ai_max_input_chars:
        raise ValidationError("Message is too large")
    repository = ConversationRepository(session)
    await repository.get_owned(conversation_id, user.subject)
    request_count = await request.app.state.rate_limiter.hit(f"ai:user:{user.subject}", 60)
    if request_count > settings.ai_rate_limit_per_minute:
        raise RateLimitError()
    daily = await UsageRepository(session).summary(user.subject, datetime.now(UTC).date())
    if daily["totalTokens"] >= settings.ai_daily_token_limit:
        raise RateLimitError("Daily token limit exceeded")
    stream_quota = request.app.state.stream_quota
    if not await stream_quota.acquire(user.subject, settings.ai_concurrent_stream_limit):
        raise RateLimitError("Too many concurrent streams")
    return StreamingResponse(
        _conversation_stream(conversation_id, payload, request, user.subject, provider, session),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


async def _conversation_stream(
    conversation_id: str,
    payload: ConversationMessageCreate,
    request: Request,
    user_id: str,
    provider: LLMProvider,
    session: AsyncSession,
) -> AsyncIterator[str]:
    started = time.perf_counter()
    settings = request.app.state.settings
    repository = ConversationRepository(session)
    output: list[str] = []
    usage: dict[str, int] = {"promptTokens": 0, "completionTokens": 0, "totalTokens": 0}
    citations: list[dict[str, str]] = []
    ACTIVE_STREAMS.inc()
    logger.info(
        "conversation stream started",
        extra={
            "requestId": request.state.request_id,
            "conversationId": conversation_id,
            "userId": user_id,
            "provider": provider.name,
        },
    )
    yield encode_sse(StartChunk(id=conversation_id))
    try:
        async with request.app.state.conversation_locks.lease(conversation_id):
            conversation = await repository.get_owned(conversation_id, user_id, messages=True)
            await repository.add_message(conversation, role="user", content=payload.content)
            conversation = await repository.get_owned(conversation_id, user_id, messages=True)
            retrieved: list[str] = []
            if payload.use_rag:
                yield encode_sse(ThinkingStatusChunk(status="Retrieving documents"))
                knowledge = KnowledgeService(
                    KnowledgeRepository(session),
                    request.app.state.embedding_provider,
                    chunk_chars=settings.knowledge_chunk_chars,
                    overlap_chars=settings.knowledge_chunk_overlap_chars,
                )
                matches = await knowledge.search(user_id, payload.content, settings.knowledge_top_k)
                retrieved = [match.content for match in matches]
                citations = [match.citation for match in matches]
            agent_requested = payload.mode == "agent" or (payload.mode == "auto" and _needs_agent(payload.content))
            context: ContextBuilder = request.app.state.context_builder
            messages = await context.build(
                conversation,
                conversation.messages,
                retrieved_documents=retrieved,
                prompt_name=(
                    "assistant.agent"
                    if agent_requested
                    else "assistant.rag"
                    if payload.use_rag
                    else "assistant.default"
                ),
            )
            await session.commit()
            if agent_requested:
                yield encode_sse(ThinkingStatusChunk(status=_visible_status(payload.content)))
                workflow: AgentWorkflow = request.app.state.agent_workflow
                state: AgentState = {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "messages": messages,
                    "tool_calls": [],
                    "tool_results": [],
                    "iteration": 0,
                    "usage": usage,
                    "answer": "",
                    "route": "",
                    "model": conversation.model,
                }
                result: AgentState | None = None
                async for agent_event in workflow.stream(state):
                    event_type = agent_event["type"]
                    if event_type == "tool_start":
                        yield encode_sse(
                            ToolStartChunk(
                                tool=str(agent_event["tool"]),
                                call_id=str(agent_event["callId"]),
                            )
                        )
                    elif event_type == "tool_result":
                        tool = str(agent_event["tool"])
                        call_id = str(agent_event["callId"])
                        value = agent_event.get("result", agent_event.get("error"))
                        await repository.add_message(
                            conversation,
                            role="tool",
                            content=json.dumps(agent_event, ensure_ascii=False),
                            tool_call_id=call_id,
                        )
                        yield encode_sse(
                            ToolResultChunk(
                                tool=tool,
                                call_id=call_id,
                                result=value,
                            )
                        )
                    elif event_type == "answer":
                        result = cast(AgentState, agent_event["state"])
                if result is None:  # pragma: no cover - compiled graph always terminates
                    raise RuntimeError("Agent graph ended without an answer")
                usage = result["usage"]
                answer = result["answer"]
                for index in range(0, len(answer), 32):
                    delta = answer[index : index + 32]
                    output.append(delta)
                    yield encode_sse(DeltaChunk(delta=delta))
            else:
                with span("llm.stream", provider=provider.name, model=conversation.model):
                    model_config = request.app.state.model_router.for_task("simple_chat").model_copy(
                        update={"model": conversation.model}
                    )
                    async for delta in cancel_aware_stream(request, provider, messages, model_config):
                        output.append(delta)
                        yield encode_sse(DeltaChunk(delta=delta))
                prompt_tokens = sum(estimate_tokens(message.content) for message in messages)
                completion_tokens = estimate_tokens("".join(output))
                usage = {
                    "promptTokens": prompt_tokens,
                    "completionTokens": completion_tokens,
                    "totalTokens": prompt_tokens + completion_tokens,
                }
            if citations:
                yield encode_sse(SourcesChunk(sources=citations))
            latency_ms = (time.perf_counter() - started) * 1000
            await repository.add_message(
                conversation,
                role="assistant",
                content="".join(output),
                token_usage=usage,
                latency_ms=latency_ms,
                citations=citations or None,
            )
            await UsageRepository(session).add(
                UsageRecord(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    model=conversation.model,
                    prompt_tokens=usage["promptTokens"],
                    completion_tokens=usage["completionTokens"],
                    total_tokens=usage["totalTokens"],
                    latency_ms=latency_ms,
                    usage_date=datetime.now(UTC).date(),
                )
            )
            AI_TOKENS.labels(kind="prompt", model=conversation.model).inc(usage["promptTokens"])
            AI_TOKENS.labels(kind="completion", model=conversation.model).inc(usage["completionTokens"])
            AI_REQUESTS.labels(path="conversation_message", status="ok").inc()
            AI_DURATION.labels(path="conversation_message").observe(latency_ms / 1000)
            logger.info(
                "conversation stream finished",
                extra={
                    "requestId": request.state.request_id,
                    "conversationId": conversation_id,
                    "userId": user_id,
                    "provider": provider.name,
                    "model": conversation.model,
                    "latencyMs": round(latency_ms, 2),
                    "tokens": usage["totalTokens"],
                },
            )
            yield encode_sse(FinishChunk(reason="stop"))
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        AI_REQUESTS.labels(path="conversation_message", status="error").inc()
        PROVIDER_ERRORS.labels(provider=provider.name, kind=type(exc).__name__).inc()
        yield encode_sse(ErrorChunk(message=str(exc) if hasattr(exc, "code") else "AI stream failed"))
    finally:
        ACTIVE_STREAMS.dec()
        await request.app.state.stream_quota.release(user_id)


def _needs_agent(content: str) -> bool:
    lowered = content.lower()
    return any(marker in lowered for marker in ("商品", "product", "calculate", "计算", "current time", "几点"))


def _visible_status(content: str) -> str:
    lowered = content.lower()
    if "商品" in lowered or "product" in lowered:
        return "Searching products"
    if any(char.isdigit() for char in content):
        return "Calculating"
    return "Using tools"


def _conversation_view(conversation: Conversation, *, include_messages: bool = False) -> ConversationView:
    messages = None
    if include_messages:
        messages = [
            MessageView(
                id=message.id,
                conversation_id=message.conversation_id,
                role=message.role,
                content=message.content,
                tool_call_id=message.tool_call_id,
                token_usage=message.token_usage,
                latency_ms=message.latency_ms,
                citations=message.citations,
                created_at=message.created_at,
            )
            for message in conversation.messages
        ]
    return ConversationView(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        model=conversation.model,
        summary=conversation.summary,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )
