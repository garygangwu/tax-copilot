"""Anthropic Claude LLM provider implementation."""

import os
import json
from typing import Any
from anthropic import Anthropic, AsyncAnthropic

from .base import LLMProvider, LLMResponse, Message


class AnthropicProvider(LLMProvider):
    """
    LLM provider implementation for Anthropic Claude models.

    Supports Claude 3.5 Sonnet and other Claude models via the Anthropic API.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        """
        Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var
            model: Model name to use. If None, uses claude-3-5-sonnet-20241022
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not provided. Set ANTHROPIC_API_KEY "
                "environment variable or pass api_key parameter."
            )

        self.model = model or os.getenv("DEFAULT_MODEL", "claude-3-5-sonnet-20241022")
        self.client = AsyncAnthropic(api_key=self.api_key)

    async def generate(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Generate a completion using Claude.

        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            response_schema: Optional JSON schema for structured output
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with generated content

        Raises:
            Exception: If the API call fails
        """
        # Convert messages to Anthropic format
        # Anthropic expects user/assistant messages only (system is separate)
        anthropic_messages = []
        for msg in messages:
            if msg.role != "system":
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        # Build request parameters
        request_params = {
            "model": self.model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add system prompt if provided
        if system_prompt:
            request_params["system"] = system_prompt

        # Handle structured output if schema provided
        # Note: Anthropic doesn't have native JSON schema enforcement yet,
        # so we append instructions to system prompt
        if response_schema:
            schema_instruction = (
                f"\n\nYou must respond with valid JSON matching this schema:\n"
                f"{json.dumps(response_schema, indent=2)}\n"
                f"Your entire response should be valid JSON, nothing else."
            )
            if "system" in request_params:
                request_params["system"] += schema_instruction
            else:
                request_params["system"] = schema_instruction.strip()

        # Make API call
        try:
            response = await self.client.messages.create(**request_params)

            # Extract text content
            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            # Build response object
            return LLMResponse(
                content=content.strip(),
                model=response.model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                raw_response=response,
            )

        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}") from e

    def get_model_name(self) -> str:
        """Return the name of the Claude model being used."""
        return self.model
