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

def _describe_model_fields(model_class: type[BaseModel], indent: int = 1) -> list[str]:
    """Recursively describe a Pydantic model's fields, including nested models."""
    lines = []
    prefix = "  " * indent
    for name, field_info in model_class.model_fields.items():
        desc = field_info.description or ""
        required = "required" if field_info.is_required() else "optional"
        lines.append(f'{prefix}- "{name}" ({required}): {desc}')

        # Check if this field's type is a list of a BaseModel subclass
        annotation = field_info.annotation
        if annotation is not None:
            origin = getattr(annotation, '__origin__', None)
            if origin is list:
                args = getattr(annotation, '__args__', ())
                if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
                    nested = args[0]
                    lines.append(f'{prefix}  Each item in "{name}" MUST be an object with these fields:')
                    lines.extend(_describe_model_fields(nested, indent + 2))
    return lines


def build_schema_instruction(schema_class: type[BaseModel]) -> str:
    """Convert a Pydantic model into a clear output instruction for the LLM.
    Includes nested model structures so the LLM knows how to fill sub-fields."""
    fields_desc = _describe_model_fields(schema_class, indent=1)

    base = (
        "You MUST respond with valid JSON matching this exact schema.\n"
        "Do not include any text outside the JSON object.\n\n"
    )

    birth_chart_section_schemas = {
        "BirthChartCore", "BirthChartYogasSection", "BirthChartForcesSection",
        "BirthChartTimingSection", "BirthChartSynthesisSection",
    }
    if schema_class.__name__ in birth_chart_section_schemas:
        constraints = (
            "CRITICAL: This is a sacred long-form study, not a compact UI card. "
            "Respect the structure and field intentions exactly, but do not compress truth merely to stay neat. "
            "Word ranges are guidance for proportion and readability, not excuses to omit meaningful factors. "
            "Preserve every meaningful factor individually and scale by depth, not omission.\n\n"
            "Before producing the final JSON, silently plan the section using the chart_essence and ledger data provided. Do not output that scaffold.\n\n"
        )
    else:
        constraints = (
            "CRITICAL: Respect the word count ranges in each field description. "
            "These are not suggestions. They are hard constraints that ensure the reading fits the UI. "
            "Count your words. If a field says 18-45 words, do not write 60. Any overflow or underflow is a failure.\n\n"
            "Before producing the final JSON, silently plan the reading using: dominant signals, active life areas, why now, likely felt experience, likely resistance, and wise posture. Do not output that scaffold.\n\n"
        )

    return base + constraints + f"Schema: {schema_class.__name__}\n" + f"Fields:\n" + "\n".join(fields_desc)


# ── Section surfaces (parallel birth chart) ──────────────────────

_SECTION_SURFACES = frozenset({
    Surface.BIRTH_CHART_YOGAS,
    Surface.BIRTH_CHART_FORCES,
    Surface.BIRTH_CHART_TIMING,
    Surface.BIRTH_CHART_SYNTHESIS,
})


def _build_voice_anchor(input_data: BaseModel) -> str:
    """Build the GLOBAL CONTEXT block from ChartEssence.

    This identical block is injected into the system prompt of every parallel
    section call. It carries both tonal anchors AND cross-referencing data
    so every section writes with full awareness of the reading's landscape.
    """
    data = input_data.model_dump()
    essence = data.get("chart_essence")
    if not essence:
        return ""

    yoga_names = essence.get("yoga_names", [])
    force_names = essence.get("force_names", [])
    recurring = essence.get("recurring_threads", [])
    current_chapter = essence.get("current_timing_chapter", "")

    lines = [
        "GLOBAL CONTEXT — This block is identical across all parallel sections of this reading.",
        "Every section must honor the identity, tone, themes, and cross-references below.",
        "",
        "═══ IDENTITY ═══",
        f"Moon: {essence.get('moon_sign', '')} / {essence.get('moon_nakshatra', '')}",
        f"Lagna: {essence.get('lagna_sign', '')}",
        f"Active chapter: {current_chapter}",
        "",
        "═══ TONAL ANCHORS ═══",
        f"Natal signature: {essence.get('natal_signature_summary', '')}",
        f"Current chapter: {essence.get('current_chapter_summary', '')}",
        f"Central knot: {essence.get('central_knot_summary', '')}",
        f"Entrusted beauty: {essence.get('entrusted_beauty_summary', '')}",
        f"Confidence: {essence.get('confidence_summary', '')}",
        "",
        "Dominant themes: " + "; ".join(essence.get("dominant_themes", [])),
    ]

    if recurring:
        lines += [
            "",
            "═══ RECURRING THREADS (appear across multiple chart factors) ═══",
            "These threads must feel present across the entire reading, not confined to one section:",
            *[f"  - {t}" for t in recurring],
        ]

    lines += [
        "",
        "═══ CROSS-REFERENCES (names every section may reference) ═══",
        f"Yogas in this chart: {', '.join(yoga_names) if yoga_names else 'none detected'}",
        f"Shaping forces: {', '.join(force_names) if force_names else 'none detected'}",
        f"Active timing: {current_chapter}",
        "",
        "When your section touches a theme that connects to one of these names, reference",
        "it naturally (e.g., 'what Hamsa Yoga carries is tested under Saturn's chapter').",
        "This ensures the final reading feels like one intelligence wrote it.",
        "",
        "═══ TONE RULES (binding) ═══",
        "- Write as one coherent intelligence speaking to one life",
        "- Match the emotional weight of the knot and beauty above",
        "- No generic spiritual language; every line must feel specific to this chart",
        "- Sacred, intimate, direct, precise — never clinical or templated",
        "- Vary rhythm and cadence; do not repeat a rigid structure across entries",
        "- When threads recur across your section, connect them — do not treat each entry as isolated",
    ]
    return "\n".join(lines)


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

    # 4. For section surfaces, inject the shared voice anchor between
    #    feature prompt and schema so it is prominent in the LLM context.
    if surface in _SECTION_SURFACES:
        voice_anchor = _build_voice_anchor(input_data)
        system_prompt = (
            f"{core}\n\n---\n\n{feature}\n\n---\n\n{voice_anchor}\n\n---\n\n{schema_instruction}"
        )
    else:
        system_prompt = f"{core}\n\n---\n\n{feature}\n\n---\n\n{schema_instruction}"

    # 5. User message = structured input data
    user_message = (
        "Generate the reading for this member based on the following astrological data.\n\n"
        f"```json\n{input_data.model_dump_json(indent=2)}\n```"
    )

    return system_prompt, user_message
