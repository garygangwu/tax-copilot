"""Utility functions for agent operations."""

import json
import re
from typing import Any


def parse_json_response(response_text: str) -> dict[str, Any]:
    """
    Parse JSON from LLM response, handling markdown code blocks.

    LLMs often return JSON wrapped in markdown:
    ```json
    {"key": "value"}
    ```

    This function strips markdown formatting and parses the JSON.

    Args:
        response_text: Raw response text from LLM

    Returns:
        Parsed JSON as dictionary

    Raises:
        json.JSONDecodeError: If JSON parsing fails after cleanup
    """
    # Strip leading/trailing whitespace
    text = response_text.strip()

    # Remove markdown code fences
    # Handles: ```json, ```JSON, ```, ~~~json, ~~~, etc.
    # Pattern: optional fence (``` or ~~~) + optional language + newline + content + optional fence
    code_fence_pattern = r'^```(?:json|JSON)?\s*\n(.*?)\n```$'
    match = re.search(code_fence_pattern, text, re.DOTALL)

    if match:
        # Extract JSON content from code fence
        text = match.group(1).strip()
    else:
        # Try alternative fence style (~~~ instead of ```)
        code_fence_pattern = r'^~~~(?:json|JSON)?\s*\n(.*?)\n~~~$'
        match = re.search(code_fence_pattern, text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        else:
            # Try single-line code fence: ```json ... ```
            single_line_pattern = r'^```(?:json|JSON)?\s*(.*?)\s*```$'
            match = re.search(single_line_pattern, text, re.DOTALL)
            if match:
                text = match.group(1).strip()

    # Additional cleanup: remove any leading/trailing backticks or markdown
    text = text.strip('`').strip()

    # Remove commas from numbers (LLMs often format numbers like 891,450)
    # This regex finds numbers with commas and removes the commas
    # Pattern: digit(s), comma, digit(s) - can repeat multiple times
    text = re.sub(r'(\d+),(\d+)', r'\1\2', text)
    # Need to apply multiple times for numbers like 1,234,567
    while ',\d' in text:
        text = re.sub(r'(\d+),(\d+)', r'\1\2', text)

    # Parse JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Add context to error message
        preview = text[:200] + "..." if len(text) > 200 else text
        raise json.JSONDecodeError(
            f"Failed to parse JSON after cleanup. Preview: {preview}",
            e.doc,
            e.pos,
        ) from e


def safe_parse_json(response_text: str, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Parse JSON with fallback on error.

    Args:
        response_text: Raw response text from LLM
        fallback: Dictionary to return if parsing fails (default: empty dict)

    Returns:
        Parsed JSON or fallback value
    """
    try:
        return parse_json_response(response_text)
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        return fallback if fallback is not None else {}
