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
        self._check_empty_recursive(data, "", failures)
        return failures

    def _check_empty_recursive(self, obj, path: str, failures: list[ValidationFailure]):
        """Recursively check for null/empty values in nested dicts and lists.

        Catches empty sacred_capacity inside StudyForce, empty chapter_body
        inside TimingCurrent, etc. -- the exact issue that caused yogas to
        render as title-only in the birth chart.
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_path = f"{path}.{key}" if path else key
                if value is None:
                    failures.append(ValidationFailure("empty", full_path, f"'{full_path}' is null"))
                elif isinstance(value, str) and not value.strip():
                    # Skip fields that are intentionally optional/empty
                    skip_fields = {"subtitle", "distortion", "purified_expression",
                                   "shadow", "age_range", "cta", "closing_anchor",
                                   "invitation", "time_note"}
                    field_name = key.split(".")[-1] if "." in key else key
                    if field_name not in skip_fields:
                        failures.append(ValidationFailure("empty", full_path, f"'{full_path}' is empty string"))
                elif isinstance(value, (dict, list)):
                    self._check_empty_recursive(value, full_path, failures)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                full_path = f"{path}[{i}]"
                if isinstance(item, dict):
                    # For nested objects (StudyForce, TimingCurrent, LifePhase),
                    # check that at least the primary content field has text
                    content_fields = ["sacred_capacity", "chapter_body", "body"]
                    has_content = any(
                        isinstance(item.get(f), str) and item.get(f, "").strip()
                        for f in content_fields
                    )
                    if not has_content and any(f in item for f in content_fields):
                        name = item.get("name", item.get("title", f"item {i}"))
                        failures.append(ValidationFailure(
                            "empty", full_path,
                            f"'{name}' has no body content (sacred_capacity/chapter_body/body all empty)"
                        ))
                    self._check_empty_recursive(item, full_path, failures)

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
