"""
Data contracts for the JSON rule engine.

Uses dataclasses for rule engine internals (not Pydantic) per project convention.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Operator(Enum):
    EQ = "eq"
    IN = "in"
    RANGE = "range"
    GT = "gt"
    LT = "lt"


class LifeArea(Enum):
    SELF = "self"
    EMOTIONS = "emotions"
    RELATIONSHIPS = "relationships"
    CAREER = "career"
    FINANCES = "finances"
    HEALTH = "health"
    SPIRITUALITY = "spirituality"
    COMMUNICATION = "communication"
    HOME = "home"
    CREATIVITY = "creativity"


class Intensity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RuleCategory(Enum):
    NATAL_MOON = "natal_moon"
    NATAL_SUN = "natal_sun"
    NATAL_PLANET = "natal_planet"
    NAKSHATRA = "nakshatra"
    YOGA = "yoga"
    DASHA = "dasha"
    TRANSIT = "transit"
    HOUSE_LORD = "house_lord"
    DIGNITY = "dignity"
    COMBINATION = "combination"


@dataclass(frozen=True)
class Condition:
    field: str
    op: Operator
    value: str | int | float | bool | list


@dataclass(frozen=True)
class ConditionGroup:
    """Recursive AND/OR grouping of conditions.

    Exactly one of all_of or any_of must be set.
    Children can be Condition leaves or nested ConditionGroup nodes.
    """
    all_of: tuple[Condition | ConditionGroup, ...] | None = None
    any_of: tuple[Condition | ConditionGroup, ...] | None = None


@dataclass(frozen=True)
class RuleOutput:
    theme: str
    life_area: str
    trait: str
    intensity: str
    shadow: str = ""


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    category: RuleCategory
    priority: int
    conditions: ConditionGroup
    output: RuleOutput
    tags: list[str] = field(default_factory=list)
