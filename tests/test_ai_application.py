"""Tool, agent, RAG, structured-output, retry, cancellation and lock tests."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import cast

import httpx
import pytest
from app.core.errors import AppError
from app.db.repositories import KnowledgeRepository
from app.db.session import Database
from app.providers.base import MockChatProvider, OpenAICompatibleProvider
from app.providers.embedding import MockEmbeddingProvider
from app.providers.types import ModelConfig, ToolCall, ToolCallingResult, ToolDefinition
from app.schemas.chat import ChatMessage
from app.schemas.knowledge import ProductRecommendation
from app.services.agent import AgentState, AgentWorkflow
from app.services.knowledge import KnowledgeService
from app.services.locks import ConversationLockManager
from app.services.model_router import ModelRouter
from app.services.streaming import cancel_aware_stream
from app.tools.base import ToolContext, ToolRegistry
from app.tools.builtin import CalculatorTool, CurrentTimeTool, ProductSearchTool

from tests.test_providers import patch_client, sse_body


async def test_structured_output_is_pydantic_validated() -> None:
    provider = MockChatProvider(answer='{"products":[{"id":"p1"}],"reason":"under budget"}')
    result = await provider.structured_output([ChatMessage(role="user", content="recommend")], ProductRecommendation)
    assert result.products[0]["id"] == "p1"

    invalid = MockChatProvider(answer="not json")
    with pytest.raises(Exception, match="structured output"):
        await invalid.structured_output([ChatMessage(role="user", content="recommend")], ProductRecommendation)


async def test_tool_registry_whitelists_and_calculator_rejects_code() -> None:
    registry = ToolRegistry([CalculatorTool()])
    value = await registry.execute("calculator", {"expression": "2 + 3 * 4"}, ToolContext(user_id="u"))
    assert value == {"result": 14.0}
    with pytest.raises(AppError, match="not registered"):
        await registry.execute("fetch_url", {"url": "http://169.254.169.254"}, ToolContext(user_id="u"))
    with pytest.raises(ValueError, match="basic arithmetic"):
        await registry.execute("calculator", {"expression": "__import__('os')"}, ToolContext(user_id="u"))


class LoopingProvider(MockChatProvider):
    async def tool_calling(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolDefinition],
        config: ModelConfig | None = None,
    ) -> ToolCallingResult:
        return ToolCallingResult(
            content="",
            model="mock",
            toolCalls=[ToolCall(id="loop", name="get_current_time", arguments={})],
        )


async def test_agent_loop_limit(settings) -> None:  # type: ignore[no-untyped-def]
    workflow = AgentWorkflow(
        LoopingProvider(delay_seconds=0),
        ToolRegistry([CurrentTimeTool()]),
        ModelRouter(settings),
        max_iterations=2,
    )
    state: AgentState = {
        "conversation_id": "c",
        "user_id": "u",
        "messages": [ChatMessage(role="user", content="loop")],
        "tool_calls": [],
        "tool_results": [],
        "iteration": 0,
        "usage": {},
        "answer": "",
        "route": "",
    }
    result = await workflow.run(state)
    assert result["iteration"] == 2
    assert "iteration limit" in result["answer"]


async def test_agent_stream_emits_tool_lifecycle_before_answer(settings) -> None:  # type: ignore[no-untyped-def]
    workflow = AgentWorkflow(
        LoopingProvider(delay_seconds=0),
        ToolRegistry([CurrentTimeTool()]),
        ModelRouter(settings),
        max_iterations=2,
    )
    state: AgentState = {
        "conversation_id": "c",
        "user_id": "u",
        "messages": [ChatMessage(role="user", content="time")],
        "tool_calls": [],
        "tool_results": [],
        "iteration": 0,
        "usage": {},
        "answer": "",
        "route": "",
    }
    events = [event async for event in workflow.stream(state)]
    assert [event["type"] for event in events] == ["tool_start", "tool_result", "answer"]


async def test_product_tool_uses_only_configured_url_and_forwards_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["Authorization"]
        captured["user"] = request.headers["X-User-ID"]
        return httpx.Response(200, json={"data": [{"id": "p1", "price": 499}]})

    patch_client(monkeypatch, httpx.MockTransport(handler))
    tool = ProductSearchTool(base_url="https://business.example.com", service_token="service-secret", timeout=2)
    result = await tool.run(
        {"query": "camera", "maxPrice": 500},
        ToolContext(user_id="user-7"),
    )
    assert result[0]["id"] == "p1"
    assert captured == {
        "url": "https://business.example.com/api/v1/products?q=camera&maxPrice=500.0&limit=10",
        "auth": "Bearer service-secret",
        "user": "user-7",
    }


async def test_rag_retrieval_is_user_scoped() -> None:
    database = Database.create("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    try:
        async with database.sessions() as session:
            service = KnowledgeService(
                KnowledgeRepository(session), MockEmbeddingProvider(64), chunk_chars=200, overlap_chars=20
            )
            await service.ingest(
                user_id="u1",
                filename="pricing.md",
                content_type="text/markdown",
                data=b"The alpine camera costs 499 yuan and includes a tripod.",
                metadata={},
            )
            assert (await service.search("u1", "alpine camera", 3))[0].citation["title"] == "pricing"
            assert await service.search("u2", "alpine camera", 3) == []
    finally:
        await database.aclose()


async def test_provider_retries_5xx_before_first_delta(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(500)
        return httpx.Response(200, content=sse_body(["ok"]))

    patch_client(monkeypatch, httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        base_url="https://api.example.com/v1",
        api_key="test",
        model="m",
        timeout=1,
        max_retries=2,
        retry_base_seconds=0,
    )
    output = "".join([part async for part in provider.stream([ChatMessage(role="user", content="hi")])])
    assert output == "ok"
    assert attempts == 3


async def test_structured_output_retries_validation_once(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        content = "not json" if attempts == 1 else '{"products":[],"reason":"validated"}'
        return httpx.Response(200, json={"model": "m", "choices": [{"message": {"content": content}}]})

    patch_client(monkeypatch, httpx.MockTransport(handler))
    provider = OpenAICompatibleProvider(
        base_url="https://api.example.com/v1",
        api_key="test",
        model="m",
        timeout=1,
        max_retries=0,
    )
    result = await provider.structured_output(
        [ChatMessage(role="user", content="recommend")],
        ProductRecommendation,
    )
    assert result.reason == "validated"
    assert attempts == 2


class DisconnectRequest:
    async def is_disconnected(self) -> bool:
        return True


class SlowProvider(MockChatProvider):
    def __init__(self) -> None:
        super().__init__(delay_seconds=0)
        self.cancelled = False

    async def _generate(self, messages: Sequence[ChatMessage]):  # type: ignore[no-untyped-def]
        try:
            await asyncio.sleep(10)
            yield "late"
        finally:
            self.cancelled = True


async def test_stream_disconnect_cancels_upstream() -> None:
    provider = SlowProvider()
    stream = cancel_aware_stream(
        cast("object", DisconnectRequest()),  # type: ignore[arg-type]
        provider,
        [ChatMessage(role="user", content="hi")],
        ModelConfig(model="mock"),
    )
    with pytest.raises(asyncio.CancelledError):
        await anext(stream)
    assert provider.cancelled


async def test_conversation_lock_serializes_same_id_only() -> None:
    manager = ConversationLockManager()
    order: list[str] = []

    async def work(key: str, label: str) -> None:
        async with manager.lease(key):
            order.append(f"{label}-start")
            await asyncio.sleep(0.01)
            order.append(f"{label}-end")

    await asyncio.gather(work("same", "a"), work("same", "b"))
    assert order in (["a-start", "a-end", "b-start", "b-end"], ["b-start", "b-end", "a-start", "a-end"])
