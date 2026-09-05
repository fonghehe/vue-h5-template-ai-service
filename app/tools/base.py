"""Safe tool abstraction and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from app.core.errors import AppError
from app.providers.types import ToolDefinition


class ToolContext(BaseModel):
    user_id: str
    service_token: str | None = None


class Tool(ABC):
    name: str
    description: str
    input_model: type[BaseModel]

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema=self.input_model.model_json_schema(),
        )

    async def run(self, arguments: dict[str, Any], context: ToolContext) -> Any:
        validated = self.input_model.model_validate(arguments)
        return await self.execute(validated, context)

    @abstractmethod
    async def execute(self, arguments: BaseModel, context: ToolContext) -> Any:
        raise NotImplementedError  # pragma: no cover


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    @property
    def definitions(self) -> list[ToolDefinition]:
        return [tool.definition for tool in self._tools.values()]

    async def execute(self, name: str, arguments: dict[str, Any], context: ToolContext) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise AppError("Tool is not registered", status_code=400)
        return await tool.run(arguments, context)
