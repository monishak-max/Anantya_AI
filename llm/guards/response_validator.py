"""
Response Validator — structural integrity check after generation.

Catches what the style guard doesn't: missing fields, null/empty values,
and business constraints like card counts. Runs inside the existing retry
loop in AstroGenerator.generate().
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from llm.schemas.surfaces import SURFACE_SCHEMAS

logger = logging.getLogger("astro.validator")


@dataclass
class ValidationFailure:
    check: str   # "schema", "empty", "business"
    field: str   # which field failed, or "" for top-level
    detail: str  # human-readable reason

    @property
    def is_retryable(self) -> bool:
        return self.check in ("schema", "empty")


class ResponseValidator:
    """Post-generation structural and business-rule validation."""

    def validate(self, data: dict, surface: str) -> list[ValidationFailure]:
        failures: list[ValidationFailure] = []
        failures.extend(self._check_schema_shape(data, surface))
        failures.extend(self._check_empty_fields(data, surface))
        failures.extend(self._check_business_constraints(data, surface))
        return failures

    # ── checks ────────────────────────────────────────────────────

    def _check_schema_shape(self, data: dict, surface: str) -> list[ValidationFailure]:
        schema_cls = SURFACE_SCHEMAS.get(surface)
        if schema_cls is None:
            return []
        failures = []
        for name, field_info in schema_cls.model_fields.items():
            if field_info.is_required() and name not in data:
                failures.append(ValidationFailure("schema", name, f"missing required field '{name}'"))
        return failures

    def _check_empty_fields(self, data: dict, surface: str) -> list[ValidationFailure]:
        failures = []
        for key, value in data.items():
            if value is None:
                failures.append(ValidationFailure("empty", key, f"'{key}' is null"))
            elif isinstance(value, str) and not value.strip():
                failures.append(ValidationFailure("empty", key, f"'{key}' is empty string"))
        return failures

    def _check_business_constraints(self, data: dict, surface: str) -> list[ValidationFailure]:
        failures = []
        if surface == "mandala_cards":
            cards = data.get("cards", [])
            if isinstance(cards, list) and not (3 <= len(cards) <= 7):
                failures.append(ValidationFailure(
                    "business", "cards",
                    f"mandala requires 3-7 cards, got {len(cards)}",
                ))
        if surface == "chart_reveal":
            traits = data.get("traits", [])
            if isinstance(traits, list) and len(traits) != 3:
                failures.append(ValidationFailure(
                    "business", "traits",
                    f"chart_reveal requires exactly 3 traits, got {len(traits)}",
                ))
        return failures
