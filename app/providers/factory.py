"""Provider construction from configuration."""

from __future__ import annotations

from app.core.config import Settings
from app.core.errors import ConfigurationError
from app.providers.base import LLMProvider, MockChatProvider, OpenAICompatibleProvider
from app.providers.embedding import EmbeddingProvider, MockEmbeddingProvider, OpenAICompatibleEmbeddingProvider


def create_chat_provider(settings: Settings) -> LLMProvider:
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
        max_retries=settings.ai_provider_max_retries,
        retry_base_seconds=settings.ai_retry_base_seconds,
    )


def create_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build the embedding adapter paired with the configured LLM provider."""
    if settings.ai_provider == "mock":
        return MockEmbeddingProvider(min(settings.embedding_dimensions, 64))
    if not settings.ai_api_key:
        raise ConfigurationError("AI_API_KEY is required when AI_PROVIDER is openai-compatible")
    return OpenAICompatibleEmbeddingProvider(
        base_url=settings.ai_base_url,
        api_key=settings.ai_api_key,
        model=settings.model_embedding,
        timeout=settings.ai_timeout_seconds,
    )
