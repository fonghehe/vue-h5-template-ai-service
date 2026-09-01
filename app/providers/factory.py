"""Provider construction from configuration."""

from __future__ import annotations

from app.core.config import Settings
from app.core.errors import ConfigurationError
from app.providers.base import ChatProvider, MockChatProvider, OpenAICompatibleProvider


def create_chat_provider(settings: Settings) -> ChatProvider:
    """Build the provider selected by `AI_PROVIDER`.

    Raises:
        ConfigurationError: when the selected provider lacks its credentials.
    """
    if settings.ai_provider == "mock":
        return MockChatProvider()

    if not settings.ai_api_key:
        raise ConfigurationError("AI_API_KEY is required when AI_PROVIDER is openai-compatible")

    return OpenAICompatibleProvider(
        base_url=settings.ai_base_url,
        api_key=settings.ai_api_key,
        model=settings.ai_model,
        timeout=settings.ai_timeout_seconds,
        max_output_chars=settings.ai_max_output_chars,
    )
