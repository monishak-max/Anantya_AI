"""
Core LLM client — wraps Anthropic API with:
- Model routing per surface
- Prompt caching (core prompts cached, feature/user data uncached)
- JSON structured output
- Retry with exponential backoff
"""
from __future__ import annotations

import json
import time
import logging
from typing import TypeVar, Type

import anthropic
from pydantic import BaseModel

from llm.core.config import Surface, get_model, get_api_key, SURFACE_MAX_TOKENS

logger = logging.getLogger("astro.llm")

T = TypeVar("T", bound=BaseModel)


class AstroLLMClient:
    """
    The core LLM client for Astro.

    Usage:
        client = AstroLLMClient()
        result = client.generate(
            surface=Surface.NOW_COLLAPSED,
            system_prompt="...",
            user_message="...",
            output_schema=NowCollapsed,
        )
    """

    def __init__(self, api_key: str | None = None):
        self._client = anthropic.Anthropic(api_key=api_key or get_api_key())

    def generate(
        self,
        surface: Surface,
        system_prompt: str,
        user_message: str,
        output_schema: Type[T],
        max_retries: int = 2,
        temperature: float = 0.7,
    ) -> T:
        """
        Generate a reading for a surface.

        Uses prompt caching: the core prompts (first ~80% of system prompt)
        are marked as cacheable so subsequent calls reuse the cached prefix.

        Returns a validated Pydantic model instance.
        """
        model = get_model(surface)
        max_tokens = SURFACE_MAX_TOKENS[surface]

        # Split system prompt for caching:
        # Core prompts (before first feature section) get cache_control
        # Feature + schema instructions are surface-specific (not cached)
        core_end = system_prompt.find("\n\n---\n\n", system_prompt.find("clarity over spectacle"))
        if core_end > 0:
            core_part = system_prompt[:core_end]
            feature_part = system_prompt[core_end:]
            system_blocks = [
                {
                    "type": "text",
                    "text": core_part,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": feature_part,
                },
            ]
        else:
            system_blocks = [{"type": "text", "text": system_prompt}]

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                response = self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_blocks,
                    messages=[{"role": "user", "content": user_message}],
                )

                raw_text = response.content[0].text.strip()

                # Extract JSON if wrapped in markdown code fence
                if raw_text.startswith("```"):
                    lines = raw_text.split("\n")
                    json_lines = []
                    inside = False
                    for line in lines:
                        if line.startswith("```") and not inside:
                            inside = True
                            continue
                        elif line.startswith("```") and inside:
                            break
                        elif inside:
                            json_lines.append(line)
                    raw_text = "\n".join(json_lines)

                parsed = json.loads(raw_text)
                result = output_schema.model_validate(parsed)

                # Log usage
                usage = response.usage
                logger.info(
                    f"[{surface.value}] model={model} "
                    f"input={usage.input_tokens} output={usage.output_tokens} "
                    f"cache_read={getattr(usage, 'cache_read_input_tokens', 0)} "
                    f"cache_create={getattr(usage, 'cache_creation_input_tokens', 0)}"
                )

                return result

            except (json.JSONDecodeError, Exception) as e:
                last_error = e
                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.warning(f"[{surface.value}] Attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                    time.sleep(wait)

        raise RuntimeError(
            f"Failed to generate {surface.value} after {max_retries + 1} attempts. "
            f"Last error: {last_error}"
        )

    def generate_streaming(
        self,
        surface: Surface,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.7,
    ):
        """
        Stream a reading for expansion sheets (SSE-ready).
        Yields text chunks as they arrive.
        Does NOT validate against schema (streaming = raw text).
        """
        model = get_model(surface)
        max_tokens = SURFACE_MAX_TOKENS[surface]

        with self._client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                yield text
