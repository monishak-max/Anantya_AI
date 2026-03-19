# Astro Prompt Pack v1

This pack contains the first modular prompt system for the astrology app discussed in this thread.

It is designed around three product surfaces:
- **Now**
- **Mandala**
- **Union**

And two deeper premium experiences:
- **Birth Chart / Janam Patri**
- **Compatibility / Influence Read**

## What is included

### Prompt modules (CANONICAL SOURCE OF TRUTH)
These are the files the LLM actually sees at runtime. If there is ever a conflict between a doc and a prompt file, **the prompt file wins**.

- `prompts/core/01_core_identity.txt`
- `prompts/core/02_knowledge_framework.txt`
- `prompts/core/03_global_translation_layer.txt`
- `prompts/core/04_ethics_guardrails.txt`
- `prompts/core/05_reasoning_contract.txt`
- `prompts/features/now_collapsed.txt`
- `prompts/features/now_expanded.txt`
- `prompts/features/mandala_cards.txt`
- `prompts/features/mandala_deep_read.txt`
- `prompts/features/union_snapshot.txt`
- `prompts/features/union_deep_read.txt`
- `prompts/features/birth_chart_core.txt`
- `prompts/features/weekly_overview.txt`
- `prompts/features/monthly_overview.txt`

### Docs (reference / design intent)
These documents capture the original design thinking and product intent. They are useful for onboarding new team members and understanding the "why" behind decisions. However, the prompt files and Pydantic schemas are the operational source of truth.

- `docs/01_master_prompt_v1.md`
- `docs/02_knowledge_framework_and_surface_map.md`
- `docs/03_output_schemas.md`
- `docs/CHANGELOG.md`

### Config examples
- `config/prompt_stack_example.yaml`
- `config/output_schema_reference.json`

## Intended use

This should be treated as a **prompt architecture pack**, not a final production implementation.

Recommended runtime assembly order:
1. Core identity
2. Knowledge framework
3. Global translation layer
4. Ethics guardrails
5. Reasoning contract
6. Feature-specific prompt
7. Structured input data
8. Output schema / formatter constraints

## Key principle

Ancient source, modern expression.

The backend can think in Jyotish, nakshatras, dashas, gunas, karma, dharma, and purusharthas.
The frontend should feel modern, elegant, uplifting, emotionally intelligent, and clear for a global audience.
