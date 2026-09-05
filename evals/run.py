"""Deterministic offline evaluation runner; never calls a real model API."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.providers.base import MockChatProvider
from app.schemas.chat import ChatMessage
from app.tools.base import ToolContext, ToolRegistry
from app.tools.builtin import CalculatorTool

DATASET = Path(__file__).with_name("dataset.jsonl")


async def run() -> int:
    cases = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    provider = MockChatProvider(delay_seconds=0)
    tools = ToolRegistry([CalculatorTool()])
    passed = 0
    for case in cases:
        if case["expected_tool"] == "calculator":
            value = await tools.execute("calculator", {"expression": "125 * 4"}, ToolContext(user_id="eval"))
            ok = value["result"] == 500
        else:
            result = await provider.complete([ChatMessage(role="user", content=case["question"])])
            ok = bool(result.content)
        passed += int(ok)
        print(json.dumps({"id": case["id"], "passed": ok}))
    print(json.dumps({"passed": passed, "total": len(cases)}))
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
