"""Configuration-driven model selection."""

from __future__ import annotations

from typing import Literal

from app.core.config import Settings
from app.providers.types import ModelConfig

ModelTask = Literal["simple_chat", "reasoning", "summarization", "embedding"]


class ModelRouter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def for_task(self, task: ModelTask) -> ModelConfig:
        model = {
            "simple_chat": self._settings.model_simple_chat,
            "reasoning": self._settings.model_reasoning,
            "summarization": self._settings.model_summarization,
            "embedding": self._settings.model_embedding,
        }[task]
        return ModelConfig(
            model=model or self._settings.ai_model,
            temperature=0.0 if task in {"summarization", "embedding"} else 0.2,
            maxTokens=self._settings.ai_summary_token_budget if task == "summarization" else 2_000,
            timeout=self._settings.ai_timeout_seconds,
        )
