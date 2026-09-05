"""Bounded LangGraph workflow used only for tool/agent requests."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any, NotRequired, TypedDict, cast

from langgraph.graph import END, START, StateGraph

from app.core.observability import TOOL_CALLS, span
from app.providers.base import LLMProvider
from app.providers.types import TokenUsage
from app.schemas.chat import ChatMessage, ChatToolCall
from app.services.model_router import ModelRouter
from app.tools.base import ToolContext, ToolRegistry

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    conversation_id: str
    user_id: str
    messages: list[ChatMessage]
    tool_calls: list[dict[str, Any]]
    tool_results: list[dict[str, Any]]
    iteration: int
    usage: dict[str, int]
    answer: str
    route: str
    model: NotRequired[str]


class AgentWorkflow:
    def __init__(self, provider: LLMProvider, tools: ToolRegistry, router: ModelRouter, max_iterations: int) -> None:
        self._provider = provider
        self._tools = tools
        self._router = router
        self._max_iterations = max_iterations
        graph = StateGraph(AgentState)
        graph.add_node("classify", self._classify)
        graph.add_node("agent", self._agent)
        graph.add_node("tool", self._tool)
        graph.add_edge(START, "classify")
        graph.add_edge("classify", "agent")
        graph.add_conditional_edges("agent", self._next, {"tool": "tool", "answer": END})
        graph.add_edge("tool", "agent")
        self.graph = graph.compile()

    async def _classify(self, state: AgentState) -> dict[str, str]:
        return {"route": "agent"}

    async def _agent(self, state: AgentState) -> dict[str, Any]:
        with span("agent.llm", conversation_id=state["conversation_id"]):
            model_config = self._router.for_task("reasoning")
            if state.get("model"):
                model_config = model_config.model_copy(update={"model": state["model"]})
            result = await self._provider.tool_calling(state["messages"], self._tools.definitions, model_config)
        usage = _merge_usage(state["usage"], result.usage)
        next_iteration = state["iteration"] + 1
        calls = [call.model_dump() for call in result.tool_calls]
        answer = result.content
        if calls and next_iteration >= self._max_iterations:
            calls = []
            answer = "I could not complete the tool workflow within the safe iteration limit."
        messages = list(state["messages"])
        if calls:
            messages.append(
                ChatMessage(
                    role="assistant",
                    content=result.content,
                    toolCalls=[ChatToolCall.model_validate(call) for call in calls],
                )
            )
        return {
            "messages": messages,
            "tool_calls": calls,
            "answer": answer,
            "usage": usage,
            "iteration": next_iteration,
        }

    def _next(self, state: AgentState) -> str:
        if state["tool_calls"]:
            return "tool"
        return "answer"

    async def _tool(self, state: AgentState) -> dict[str, Any]:
        results = list(state["tool_results"])
        appended = list(state["messages"])
        for call in state["tool_calls"]:
            name = str(call["name"])
            try:
                with span("agent.tool", tool=name):
                    value = await self._tools.execute(
                        name, dict(call["arguments"]), ToolContext(user_id=state["user_id"])
                    )
                TOOL_CALLS.labels(tool=name, status="ok").inc()
                result = {"tool": name, "callId": call["id"], "result": value}
            except Exception:
                TOOL_CALLS.labels(tool=name, status="error").inc()
                logger.exception("tool execution failed", extra={"tool": name, "userId": state["user_id"]})
                result = {"tool": name, "callId": call["id"], "error": "Tool execution failed"}
            results.append(result)
            appended.append(
                ChatMessage(
                    role="tool",
                    content=json.dumps(result, ensure_ascii=False),
                    toolCallId=str(call["id"]),
                )
            )
        return {"messages": appended, "tool_results": results, "tool_calls": []}

    async def run(self, state: AgentState) -> AgentState:
        return cast(AgentState, await self.graph.ainvoke(state))

    async def stream(self, state: AgentState) -> AsyncIterator[dict[str, Any]]:
        """Expose graph node progress without leaking model reasoning."""
        current: dict[str, Any] = dict(state)
        emitted_results = 0
        async for chunk in self.graph.astream(state, stream_mode="updates"):
            for node, update_value in chunk.items():
                update = cast(dict[str, Any], update_value)
                current.update(update)
                if node == "agent":
                    for call in update.get("tool_calls", []):
                        yield {
                            "type": "tool_start",
                            "tool": call["name"],
                            "callId": call["id"],
                        }
                elif node == "tool":
                    results = cast(list[dict[str, Any]], update.get("tool_results", []))
                    for result in results[emitted_results:]:
                        yield {"type": "tool_result", **result}
                    emitted_results = len(results)
        yield {"type": "answer", "state": cast(AgentState, current)}


def _merge_usage(current: dict[str, int], usage: TokenUsage) -> dict[str, int]:
    return {
        "promptTokens": current.get("promptTokens", 0) + usage.prompt_tokens,
        "completionTokens": current.get("completionTokens", 0) + usage.completion_tokens,
        "totalTokens": current.get("totalTokens", 0) + usage.total_tokens,
    }
