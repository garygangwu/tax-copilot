"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, Literal
from pydantic import BaseModel


class Message(BaseModel):
    """Represents a single message in a conversation."""

    role: Literal["user", "assistant", "system"]
    content: str


class LLMResponse(BaseModel):
    """Response from an LLM provider."""

    content: str
    model: str
    usage: dict[str, int] | None = None
    raw_response: Any | None = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    Implementations should provide a unified interface for different
    LLM backends (Anthropic Claude, OpenAI GPT, etc.)
    """

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Generate a completion from the LLM.

        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt to set context
            response_schema: Optional JSON schema for structured output
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse containing the generated text and metadata

        Raises:
            Exception: If the API call fails
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the name of the model being used."""
        pass
