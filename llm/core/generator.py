"""
Surface Generator — the single entry point for generating any reading.

Flow:
  1. Assemble prompt (core + feature + schema + user data)
  2. Call LLM with model routing
  3. Parse + validate structured output
  4. Run style guard
  5. Retry once if critical violations found
  6. Return validated result with metadata
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from llm.core.client import AstroLLMClient
from llm.core.config import Surface
from llm.guards.style_guard import AstroStyleGuard, Violation
from llm.prompts.assembler import assemble_prompt
from llm.schemas.surfaces import SURFACE_SCHEMAS
from llm.schemas.inputs import (
    NowInput,
    MandalaInput,
    MandalaDeepReadInput,
    UnionInput,
    BirthChartInput,
    PeriodOverviewInput,
)

logger = logging.getLogger("astro.generator")


@dataclass
class GenerationResult:
    """Wrapper around the generated reading with metadata."""
    surface: str
    data: dict[str, Any]
    model: str
    word_count_warnings: list[str]
    style_violations: list[Violation]
    generation_time_ms: int
    retry_count: int = 0

    @property
    def is_clean(self) -> bool:
        """A reading is clean if it has no style violations and no significant word count issues.

        Minor word count overflows (<10% over max) are tolerated -- the LLM
        produces natural language, not exact word counts, and 2-3 words over
        a target is acceptable in a premium product.
        """
        # Critical violations are never clean. Warnings are tolerated --
        # a 1400-word birth chart with 1-2 minor tone warnings is still shippable.
        if any(v.severity == "critical" for v in self.style_violations):
            return False
        for warning in self.word_count_warnings:
            match = re.search(r": (\d+) words \(max (\d+)\)", warning)
            if match:
                actual = int(match.group(1))
                maximum = int(match.group(2))
                if actual > maximum * 1.1:  # >10% over is not clean
                    return False
            match_min = re.search(r": (\d+) words \(min (\d+)\)", warning)
            if match_min:
                actual = int(match_min.group(1))
                minimum = int(match_min.group(2))
                if actual < minimum * 0.9:  # >10% under is not clean
                    return False
        return True

    @property
    def has_critical(self) -> bool:
        return any(v.severity == "critical" for v in self.style_violations)


# ── Surface → input schema mapping ────────────────────────────────

SURFACE_INPUT_SCHEMAS: dict[Surface, type[BaseModel]] = {
    Surface.NOW_COLLAPSED: NowInput,
    Surface.NOW_EXPANDED: NowInput,
    Surface.MANDALA_CARDS: MandalaInput,
    Surface.MANDALA_DEEP_READ: MandalaDeepReadInput,
    Surface.UNION_SNAPSHOT: UnionInput,
    Surface.UNION_DEEP_READ: UnionInput,
    Surface.BIRTH_CHART_CORE: BirthChartInput,
    Surface.WEEKLY_OVERVIEW: PeriodOverviewInput,
    Surface.MONTHLY_OVERVIEW: PeriodOverviewInput,
}


class AstroGenerator:
    """
    Main generator class. Initialize once, call generate() per reading.

    Usage:
        gen = AstroGenerator()
        result = gen.generate(Surface.NOW_COLLAPSED, now_input)
        print(result.data)  # validated JSON dict
    """

    def __init__(self, api_key: str | None = None):
        self.client = AstroLLMClient(api_key=api_key)
        self.guard = AstroStyleGuard()

    def generate(
        self,
        surface: Surface,
        input_data: BaseModel,
        temperature: float = 0.7,
        max_style_retries: int = 2,
    ) -> GenerationResult:
        """
        Generate a reading for any surface.

        Args:
            surface: Which product surface to generate for
            input_data: The astrological input data (NowInput, MandalaInput, etc.)
            temperature: LLM temperature (0.7 default — creative but controlled)
            max_style_retries: How many times to retry on critical style violations

        Returns:
            GenerationResult with the reading data and quality metadata
        """
        output_schema = SURFACE_SCHEMAS[surface.value]

        # Handle MandalaCards special case — schema wraps a list
        if surface == Surface.MANDALA_CARDS:
            from llm.schemas.surfaces import MandalaCards
            output_schema = MandalaCards

        system_prompt, user_message = assemble_prompt(
            surface=surface,
            input_data=input_data,
            output_schema=output_schema,
        )

        from llm.core.config import get_model
        model = get_model(surface)

        retry_count = 0
        for attempt in range(max_style_retries + 1):
            start = time.monotonic()

            # Generate
            result_obj = self.client.generate(
                surface=surface,
                system_prompt=system_prompt,
                user_message=user_message if attempt == 0 else self._add_retry_context(user_message, violations, word_warnings),
                output_schema=output_schema,
                temperature=max(0.45, temperature - (0.1 * attempt)),
            )

            elapsed_ms = int((time.monotonic() - start) * 1000)

            # Convert to dict for style guard
            result_dict = result_obj.model_dump()

            # Auto-fix em dashes -- LLMs persistently generate them despite
            # explicit instructions. Replace with comma or period instead of
            # wasting retries on a mechanical fix.
            result_dict = self._strip_em_dashes(result_dict)

            # Word count validation
            word_warnings = []
            if hasattr(result_obj, "validate_lengths"):
                word_warnings = result_obj.validate_lengths()

            # Style guard (with input data for specificity check)
            input_dict = input_data.model_dump() if input_data else None
            violations = self.guard.check(result_dict, surface.value, input_dict)

            retry_reasons = self._retry_reasons(violations, word_warnings)

            if not retry_reasons or attempt == max_style_retries:
                return GenerationResult(
                    surface=surface.value,
                    data=result_dict,
                    model=model,
                    word_count_warnings=word_warnings,
                    style_violations=violations,
                    generation_time_ms=elapsed_ms,
                    retry_count=retry_count,
                )

            # Critical violation — retry
            retry_count += 1
            logger.warning(
                f"[{surface.value}] Retry-worthy issues found, retrying ({retry_count}/{max_style_retries}): {retry_reasons}"
            )

        # Should never reach here, but just in case
        return GenerationResult(
            surface=surface.value,
            data=result_dict,
            model=model,
            word_count_warnings=word_warnings,
            style_violations=violations,
            generation_time_ms=elapsed_ms,
            retry_count=retry_count,
        )

    def _retry_reasons(self, violations: list[Violation], word_warnings: list[str]) -> list[str]:
        reasons = []
        if self.guard.has_retry_worthy(violations):
            reasons.extend([v.detail for v in violations if self.guard.has_retry_worthy([v])])
        for warning in word_warnings:
            if self._is_retry_worthy_word_warning(warning):
                reasons.append(warning)
        return reasons

    def _is_retry_worthy_word_warning(self, warning: str) -> bool:
        """Only retry for significant word count violations (>10% over/under)."""
        match = re.search(r": (\d+) words \(min (\d+)\)|: (\d+) words \(max (\d+)\)", warning)
        if not match:
            return True

        if match.group(1) and match.group(2):
            actual = int(match.group(1))
            minimum = int(match.group(2))
            # Only retry if significantly under (more than 10% below min)
            return actual < minimum * 0.9

        actual = int(match.group(3))
        maximum = int(match.group(4))
        # Only retry if significantly over (more than 10% above max)
        return actual > maximum * 1.1

    @staticmethod
    def _strip_em_dashes(data: dict) -> dict:
        """Replace em dashes (and en dashes used as em dashes) with commas.

        LLMs persistently produce em dashes despite explicit bans. Rather than
        burning retries on a mechanical issue, fix it deterministically.
        """
        def fix(value):
            if isinstance(value, str):
                # " — " or " — " (em dash with spaces) → ", "
                value = value.replace(" \u2014 ", ", ")
                # "—" without spaces → ", "
                value = value.replace("\u2014", ", ")
                # " – " (en dash as em dash) → ", "
                value = value.replace(" \u2013 ", ", ")
                return value
            elif isinstance(value, dict):
                return {k: fix(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [fix(item) for item in value]
            return value

        return fix(data)

    def _add_retry_context(self, original_message: str, violations: list[Violation], word_warnings: list[str]) -> str:
        """Add style and compression correction instructions to the retry message."""
        retry_notes = [f"- FIX: {v.detail}" for v in violations if self.guard.has_retry_worthy([v])]
        retry_notes.extend(f"- FIX: {w}" for w in word_warnings if self._is_retry_worthy_word_warning(w))
        violation_notes = "\n".join(retry_notes)
        return (
            f"{original_message}\n\n"
            f"IMPORTANT — your previous response did not meet product constraints. Please correct these:\n{violation_notes}\n\n"
            f"Remember: no deterministic predictions, no fear language, no robotic tells, no death or curse references, no em dashes, and stay exactly within every field's word-count range. Increase translated specificity using the provided chart context and interpretive anchors."
        )
