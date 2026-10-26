"""Graph resource ownership and configured iteration bounds."""

from collections.abc import AsyncGenerator, Sequence

import pytest
from app.core.config import Settings
from app.providers.base import MockChatProvider
from app.providers.types import ModelConfig, ToolCall, ToolCallingResult, ToolDefinition
from app.schemas.chat import ChatMessage
from app.services.agent import AgentState, AgentWorkflow
from app.services.model_router import ModelRouter
from app.tools.base import ToolRegistry
from app.tools.builtin import CalculatorTool


def state() -> AgentState:
    return {
        "conversation_id": "c",
        "user_id": "u",
        "messages": [ChatMessage(role="user", content="2+3")],
        "tool_calls": [],
        "tool_results": [],
        "iteration": 0,
        "usage": {},
        "answer": "",
        "route": "",
    }


@pytest.mark.parametrize("streaming", [False, True])
async def test_configured_twenty_iterations_reaches_service_limit(streaming: bool) -> None:
    class RepeatingProvider(MockChatProvider):
        async def tool_calling(
            self, messages: Sequence[ChatMessage], tools: Sequence[ToolDefinition], config: ModelConfig | None = None
        ) -> ToolCallingResult:
            return ToolCallingResult(
                content="",
                model="mock",
                toolCalls=[ToolCall(id="call", name="calculator", arguments={"expression": "2+3"})],
            )

    workflow = AgentWorkflow(RepeatingProvider(), ToolRegistry([CalculatorTool()]), ModelRouter(Settings()), 20)
    if streaming:
        events = [event async for event in workflow.stream(state())]
        result = events[-1]["state"]
    else:
        result = await workflow.run(state())
    assert result["iteration"] == 20
    assert "safe iteration limit" in result["answer"]
    assert len(result["tool_results"]) == 19


async def test_closing_at_tool_start_closes_nested_graph_iterator(monkeypatch: pytest.MonkeyPatch) -> None:
    closed = False

    async def graph_events(*_: object, **__: object) -> AsyncGenerator[dict[str, object], None]:
        nonlocal closed
        try:
            yield {"agent": {"tool_calls": [{"name": "calculator", "id": "call"}]}}
        finally:
            closed = True

    workflow = AgentWorkflow(MockChatProvider(), ToolRegistry([]), ModelRouter(Settings()), 2)
    monkeypatch.setattr(workflow.graph, "astream", graph_events)
    stream = workflow.stream(state())
    assert (await anext(stream))["type"] == "tool_start"
    await stream.aclose()
    assert closed
