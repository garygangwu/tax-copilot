"""LLM Provider Abstraction Layer."""

from .base import LLMProvider, LLMResponse, Message
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "Message",
    "AnthropicProvider",
    "OpenAIProvider",
]


def create_provider(
    provider_name: str = "anthropic",
    api_key: str | None = None,
    model: str | None = None,
) -> LLMProvider:
    """
    Factory function to create LLM provider instances.

    Args:
        provider_name: Name of the provider ('anthropic' or 'openai')
        api_key: API key for the provider (if None, loads from environment)
        model: Model name (if None, uses provider default)

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider_name is not supported
    """
    if provider_name.lower() == "anthropic":
        return AnthropicProvider(api_key=api_key, model=model)
    elif provider_name.lower() == "openai":
        return OpenAIProvider(api_key=api_key, model=model)
    else:
        raise ValueError(
            f"Unsupported provider: {provider_name}. "
            f"Supported providers: 'anthropic', 'openai'"
        )
