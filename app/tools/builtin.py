"""Small, auditable tools. No tool accepts a caller-supplied URL."""

from __future__ import annotations

import ast
import operator
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.core.observability import span
from app.tools.base import Tool, ToolContext


class TimeInput(BaseModel):
    timezone: str = "UTC"


class CurrentTimeTool(Tool):
    name = "get_current_time"
    description = "Get the current UTC time. The only supported timezone is UTC."
    input_model = TimeInput

    async def execute(self, arguments: BaseModel, context: ToolContext) -> Any:
        return {"timezone": "UTC", "iso": datetime.now(UTC).isoformat()}


class CalculatorInput(BaseModel):
    expression: str = Field(min_length=1, max_length=200)


class CalculatorTool(Tool):
    name = "calculator"
    description = "Evaluate basic arithmetic using numbers and + - * / operators."
    input_model = CalculatorInput

    async def execute(self, arguments: BaseModel, context: ToolContext) -> Any:
        value = _safe_calculate(str(arguments.expression))  # type: ignore[attr-defined]
        return {"result": value}


class ProductSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    max_price: float | None = Field(default=None, alias="maxPrice", gt=0)
    limit: int = Field(default=10, ge=1, le=50)


class ProductSearchTool(Tool):
    name = "search_product"
    description = "Search the product catalogue with an optional maximum price."
    input_model = ProductSearchInput

    def __init__(self, *, base_url: str, service_token: str | None, timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_token = service_token
        self._timeout = timeout

    async def execute(self, arguments: BaseModel, context: ToolContext) -> Any:
        values = ProductSearchInput.model_validate(arguments.model_dump(by_alias=True))
        headers = {"X-User-ID": context.user_id}
        token = self._service_token or context.service_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        with span("business_service.search_product", user_id=context.user_id):
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(
                    f"{self._base_url}/api/v1/products",
                    params={"q": values.query, "maxPrice": values.max_price, "limit": values.limit},
                    headers=headers,
                )
        response.raise_for_status()
        payload = response.json()
        # Return only data needed by the model, not business-service headers.
        return payload.get("data", payload) if isinstance(payload, dict) else payload


def _safe_calculate(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")

    def evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return float(node.value)
        if isinstance(node, ast.BinOp):
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return float(operator.add(left, right))
            if isinstance(node.op, ast.Sub):
                return float(operator.sub(left, right))
            if isinstance(node.op, ast.Mult):
                return float(operator.mul(left, right))
            if isinstance(node.op, ast.Div):
                return float(operator.truediv(left, right))
        if isinstance(node, ast.UnaryOp):
            value = evaluate(node.operand)
            if isinstance(node.op, ast.UAdd):
                return operator.pos(value)
            if isinstance(node.op, ast.USub):
                return operator.neg(value)
        raise ValueError("Only basic arithmetic is allowed")

    return evaluate(tree)
