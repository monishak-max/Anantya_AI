"""
Prompt Assembler — loads core + feature prompts from 1.0/ and assembles
the full system prompt + user message for each surface.

Assembly order (from prompt_stack_example.yaml):
  1. Core prompts (identity, knowledge, translation, ethics, reasoning)
  2. Feature prompt (surface-specific instructions)
  3. Structured input data (user's astrological data as JSON)
  4. Schema constraints (output format requirements)
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from llm.core.config import (
    CORE_PROMPTS_DIR,
    FEATURE_PROMPTS_DIR,
    Surface,
    SURFACE_TO_PROMPT_FILE,
)


# ── Prompt loading ─────────────────────────────────────────────────

CORE_PROMPT_FILES = [
    "01_core_identity.txt",
    "02_knowledge_framework.txt",
    "03_global_translation_layer.txt",
    "04_ethics_guardrails.txt",
    "05_reasoning_contract.txt",
]


@lru_cache(maxsize=1)
def load_core_prompts() -> str:
    """Load and concatenate all 5 core prompts. Cached after first call."""
    parts = []
    for filename in CORE_PROMPT_FILES:
        path = CORE_PROMPTS_DIR / filename
        if path.exists():
            parts.append(path.read_text().strip())
        else:
            raise FileNotFoundError(f"Core prompt missing: {path}")
    return "\n\n---\n\n".join(parts)


@lru_cache(maxsize=16)
def load_feature_prompt(surface: Surface) -> str:
    """Load the feature-specific prompt for a surface."""
    filename = SURFACE_TO_PROMPT_FILE[surface]
    path = FEATURE_PROMPTS_DIR / filename
    if path.exists():
        return path.read_text().strip()
    raise FileNotFoundError(f"Feature prompt missing: {path}")


# ── Schema instruction builder ─────────────────────────────────────

def build_schema_instruction(schema_class: type[BaseModel]) -> str:
    """Convert a Pydantic model into a clear output instruction for the LLM."""
    fields_desc = []
    for name, field_info in schema_class.model_fields.items():
        desc = field_info.description or ""
        required = "required" if field_info.is_required() else "optional"
        fields_desc.append(f'  - "{name}" ({required}): {desc}')

    return (
        "You MUST respond with valid JSON matching this exact schema.\n"
        "Do not include any text outside the JSON object.\n\n"
        "CRITICAL: Respect the word count ranges in each field description. "
        "These are not suggestions. They are hard constraints that ensure the reading fits the UI. "
        "Count your words. If a field says 18-45 words, do not write 60. Any overflow or underflow is a failure.\n\n"
        "Before producing the final JSON, silently plan the reading using: dominant signals, active life areas, why now, likely felt experience, likely resistance, and wise posture. Do not output that scaffold.\n\n"
        f"Schema: {schema_class.__name__}\n"
        f"Fields:\n" + "\n".join(fields_desc)
    )


# ── Full assembly ──────────────────────────────────────────────────

def assemble_prompt(
    surface: Surface,
    input_data: BaseModel,
    output_schema: type[BaseModel],
) -> tuple[str, str]:
    """
    Assemble the full prompt for a surface.

    Returns:
        (system_prompt, user_message) — ready to send to the LLM.
    """
    # 1. Core prompts (cacheable — same across all surfaces)
    core = load_core_prompts()

    # 2. Feature prompt
    feature = load_feature_prompt(surface)

    # 3. Schema constraints
    schema_instruction = build_schema_instruction(output_schema)

    # System prompt = core + feature + schema
    system_prompt = f"{core}\n\n---\n\n{feature}\n\n---\n\n{schema_instruction}"

    # 4. User message = structured input data
    user_message = (
        "Generate the reading for this member based on the following astrological data.\n\n"
        f"```json\n{input_data.model_dump_json(indent=2)}\n```"
    )

    return system_prompt, user_message
