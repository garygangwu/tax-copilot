"""OpenAI GPT LLM provider implementation."""

import os
import json
from typing import Any
from openai import AsyncOpenAI

from .base import LLMProvider, LLMResponse, Message


class OpenAIProvider(LLMProvider):
    """
    LLM provider implementation for OpenAI GPT models.

    Supports GPT-4 and other OpenAI models via the OpenAI API.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        """
        Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var
            model: Model name to use. If None, uses gpt-4-turbo-preview
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY "
                "environment variable or pass api_key parameter."
            )

        self.model = model or "gpt-4o-mini"
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Generate a completion using GPT.

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
        # Convert messages to OpenAI format
        openai_messages = []

        # Add system prompt first if provided
        if system_prompt:
            openai_messages.append({
                "role": "system",
                "content": system_prompt,
            })

        # Add conversation messages
        for msg in messages:
            openai_messages.append({
                "role": msg.role,
                "content": msg.content,
            })

        # Build request parameters
        request_params = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Handle structured output if schema provided
        # OpenAI supports JSON mode and function calling
        if response_schema:
            # Use JSON mode for structured output
            request_params["response_format"] = {"type": "json_object"}

            # Add schema instruction to the last message or system prompt
            schema_instruction = (
                f"\n\nYou must respond with valid JSON matching this schema:\n"
                f"{json.dumps(response_schema, indent=2)}"
            )

            # Append to system message if it exists
            if openai_messages and openai_messages[0]["role"] == "system":
                openai_messages[0]["content"] += schema_instruction
            else:
                # Add as system message at the beginning
                openai_messages.insert(0, {
                    "role": "system",
                    "content": schema_instruction.strip(),
                })

        # Make API call
        try:
            response = await self.client.chat.completions.create(**request_params)

            # Extract content
            content = response.choices[0].message.content or ""

            # Build response object
            usage = None
            if response.usage:
                usage = {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                }

            return LLMResponse(
                content=content.strip(),
                model=response.model,
                usage=usage,
                raw_response=response,
            )

        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}") from e

    def get_model_name(self) -> str:
        """Return the name of the GPT model being used."""
        return self.model
