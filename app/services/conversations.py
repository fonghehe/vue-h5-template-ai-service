"""AI conversation orchestration with short sessions and explicit transactions."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from app.core.config import Settings
from app.core.errors import AppError, RateLimitError, ValidationError
from app.core.observability import ACTIVE_STREAMS, AI_DURATION, AI_REQUESTS, AI_TOKENS, AI_TTFT, PROVIDER_ERRORS
from app.db.models import Conversation, UsageRecord
from app.db.repositories import ConversationRepository, KnowledgeRepository, UsageRepository
from app.db.session import Database
from app.providers.base import LLMProvider
from app.providers.embedding import EmbeddingProvider
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
from app.services.agent import AgentState, AgentWorkflow
from app.services.context import ContextBuilder, estimate_tokens
from app.services.knowledge import KnowledgeService
from app.services.locks import ConversationLockManager
from app.services.model_router import ModelRouter
from app.services.rate_limit import RateLimiter

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ConversationService:
    database: Database
    settings: Settings
    provider: LLMProvider
    embeddings: EmbeddingProvider
    context: ContextBuilder
    workflow: AgentWorkflow
    models: ModelRouter
    locks: ConversationLockManager
    limiter: RateLimiter

    async def create(self, user_id: str, payload: ConversationCreate) -> ConversationView:
        allowed = {
            self.settings.ai_model,
            self.settings.model_simple_chat,
            self.settings.model_reasoning,
            self.settings.model_summarization,
        }
        if payload.model is not None and payload.model not in allowed:
            raise ValidationError("Requested model is not configured")
        async with self.database.sessions.begin() as session:
            conversation = await ConversationRepository(session).create(
                user_id=user_id, title=payload.title, model=payload.model or self.settings.ai_model
            )
            return self.view(conversation)

    async def list(self, user_id: str, *, limit: int, offset: int) -> list[ConversationView]:
        async with self.database.sessions() as session:
            rows = await ConversationRepository(session).list(user_id, limit=limit, offset=offset)
            return [self.view(row) for row in rows]

    async def get(self, conversation_id: str, user_id: str, *, limit: int, before: int | None) -> ConversationView:
        async with self.database.sessions() as session:
            row = await ConversationRepository(session).get_owned(
                conversation_id, user_id, messages=True, history_limit=limit, before=before
            )
            return self.view(row, include_messages=True)

    async def delete(self, conversation_id: str, user_id: str) -> None:
        async with self.locks.lease(conversation_id), self.database.sessions.begin() as session:
            await ConversationRepository(session).delete_owned(conversation_id, user_id)

    async def admit(self, conversation_id: str, user_id: str, payload: ConversationMessageCreate) -> None:
        if len(payload.content) > min(self.settings.ai_max_input_chars, 20_000):
            raise ValidationError("Message is too large")
        if estimate_tokens(payload.content) + 128 >= self.settings.ai_context_token_budget:
            raise ValidationError("Message exceeds the context token budget")
        async with self.database.sessions() as session:
            await ConversationRepository(session).get_owned(conversation_id, user_id)
            daily = await UsageRepository(session).summary(user_id, datetime.now(UTC).date())
        if daily["totalTokens"] >= self.settings.ai_daily_token_limit:
            raise RateLimitError("Daily token limit exceeded")
        if await self.limiter.hit(f"ai:user:{user_id}", 60) > self.settings.ai_rate_limit_per_minute:
            raise RateLimitError()

    async def stream(
        self, conversation_id: str, user_id: str, payload: ConversationMessageCreate, request_id: str
    ) -> AsyncGenerator[str, None]:
        started = time.perf_counter()
        output: list[str] = []
        output_chars = 0
        citations: list[dict[str, str]] = []
        tools: list[tuple[str, str]] = []
        usage = {"promptTokens": 0, "completionTokens": 0, "totalTokens": 0}
        ACTIVE_STREAMS.inc()
        try:
            yield encode_sse(StartChunk(id=conversation_id))
            async with self.locks.lease(conversation_id):
                async with self.database.sessions.begin() as session:
                    repository = ConversationRepository(session)
                    conversation = await repository.get_owned(conversation_id, user_id)
                    await repository.add_message(conversation, role="user", content=payload.content)
                    conversation = await repository.get_owned(conversation_id, user_id, messages=True)
                retrieved: list[str] = []
                if payload.use_rag:
                    yield encode_sse(ThinkingStatusChunk(status="Retrieving documents"))
                    async with self.database.sessions() as session:
                        matches = await KnowledgeService(
                            KnowledgeRepository(session),
                            self.embeddings,
                            chunk_chars=self.settings.knowledge_chunk_chars,
                            overlap_chars=self.settings.knowledge_chunk_overlap_chars,
                        ).search(user_id, payload.content, self.settings.knowledge_top_k)
                    retrieved = [match.content for match in matches]
                    citations = [match.citation for match in matches]
                agent = payload.mode == "agent" or (payload.mode == "auto" and _needs_agent(payload.content))
                previous_summary = conversation.summary
                messages = await self.context.build(
                    conversation,
                    conversation.messages,
                    retrieved_documents=retrieved,
                    prompt_name="assistant.agent"
                    if agent
                    else "assistant.rag"
                    if payload.use_rag
                    else "assistant.default",
                )
                if conversation.summary != previous_summary:
                    async with self.database.sessions.begin() as session:
                        row = await ConversationRepository(session).get_owned(conversation_id, user_id)
                        row.summary = conversation.summary
                if agent:
                    yield encode_sse(ThinkingStatusChunk(status="Using tools"))
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
                    events = self.workflow.stream(state)
                    try:
                        async for event in events:
                            kind = event["type"]
                            if kind == "tool_start":
                                yield encode_sse(ToolStartChunk(tool=str(event["tool"]), call_id=str(event["callId"])))
                            elif kind == "tool_result":
                                content = json.dumps(event, ensure_ascii=False)
                                if len(content) > 20_000:
                                    raise ValidationError("Tool result is too large")
                                tools.append((content, str(event["callId"])))
                                yield encode_sse(
                                    ToolResultChunk(
                                        tool=str(event["tool"]),
                                        call_id=str(event["callId"]),
                                        result=event.get("result", event.get("error")),
                                    )
                                )
                            elif kind == "delta":
                                delta = str(event["delta"])
                                if delta and output_chars == 0:
                                    AI_TTFT.labels(path="conversation_message").observe(time.perf_counter() - started)
                                output_chars += len(delta)
                                if output_chars > self.settings.ai_max_output_chars:
                                    raise ValidationError("AI output limit exceeded")
                                output.append(delta)
                                yield encode_sse(DeltaChunk(delta=delta))
                            elif kind == "answer":
                                usage = cast(AgentState, event["state"])["usage"]
                    finally:
                        await events.aclose()
                else:
                    config = self.models.for_task("simple_chat").model_copy(update={"model": conversation.model})
                    source = self.provider.stream(messages, config)
                    try:
                        async for delta in source:
                            if delta and output_chars == 0:
                                AI_TTFT.labels(path="conversation_message").observe(time.perf_counter() - started)
                            output_chars += len(delta)
                            if output_chars > self.settings.ai_max_output_chars:
                                raise ValidationError("AI output limit exceeded")
                            output.append(delta)
                            yield encode_sse(DeltaChunk(delta=delta))
                    finally:
                        await source.aclose()
                    prompt = sum(estimate_tokens(message.content) for message in messages)
                    completion = estimate_tokens("".join(output))
                    usage = {"promptTokens": prompt, "completionTokens": completion, "totalTokens": prompt + completion}
                latency = (time.perf_counter() - started) * 1000
                # No success frame before this transaction has committed.
                async with self.database.sessions.begin() as session:
                    repository = ConversationRepository(session)
                    current = await repository.get_owned(conversation_id, user_id)
                    for content, call_id in tools:
                        await repository.add_message(current, role="tool", content=content, tool_call_id=call_id)
                    await repository.add_message(
                        current,
                        role="assistant",
                        content="".join(output),
                        token_usage=usage,
                        latency_ms=latency,
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
                            latency_ms=latency,
                            usage_date=datetime.now(UTC).date(),
                        )
                    )
                if citations:
                    yield encode_sse(SourcesChunk(sources=citations))
                AI_TOKENS.labels(kind="prompt", model=conversation.model).inc(usage["promptTokens"])
                AI_TOKENS.labels(kind="completion", model=conversation.model).inc(usage["completionTokens"])
                AI_REQUESTS.labels(path="conversation_message", status="ok").inc()
                logger.info(
                    "conversation completed", extra={"conversationId": conversation_id, "tokens": usage["totalTokens"]}
                )
                yield encode_sse(FinishChunk(reason="stop"))
        except asyncio.CancelledError:
            AI_REQUESTS.labels(path="conversation_message", status="cancelled").inc()
            raise
        except Exception as exc:
            AI_REQUESTS.labels(path="conversation_message", status="error").inc()
            PROVIDER_ERRORS.labels(provider=self.provider.name, kind=type(exc).__name__).inc()
            logger.exception(
                "conversation stream failed", extra={"requestId": request_id, "conversationId": conversation_id}
            )
            yield encode_sse(
                ErrorChunk(
                    message=exc.message if isinstance(exc, AppError) else "AI stream failed",
                    code=exc.code if isinstance(exc, AppError) else 5000,
                    requestId=request_id,
                )
            )
        finally:
            ACTIVE_STREAMS.dec()
            AI_DURATION.labels(path="conversation_message").observe(time.perf_counter() - started)

    @staticmethod
    def view(conversation: Conversation, *, include_messages: bool = False) -> ConversationView:
        return ConversationView(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            model=conversation.model,
            summary=conversation.summary,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[MessageView.model_validate(message) for message in conversation.messages]
            if include_messages
            else None,
        )


def _needs_agent(content: str) -> bool:
    return any(marker in content.lower() for marker in ("商品", "product", "calculate", "计算", "current time", "几点"))
