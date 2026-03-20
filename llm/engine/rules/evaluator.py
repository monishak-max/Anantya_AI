"""
Core rule evaluation engine.

AND logic: all conditions must match. Short-circuits on first failure.
Results sorted by priority descending.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from llm.engine.rules.schema import Condition, Operator, Rule


@dataclass
class ConditionMatch:
    condition: Condition
    actual_value: object
    matched: bool


@dataclass
class RuleMatch:
    rule: Rule
    matched_conditions: list[ConditionMatch] = field(default_factory=list)
    priority: int = 0

    @property
    def evidence_summary(self) -> str:
        pairs = [
            f"{cm.condition.field}={cm.actual_value}"
            for cm in self.matched_conditions
            if cm.matched
        ]
        return ", ".join(pairs)


class RuleEvaluator:
    def __init__(self, rules: list[Rule]) -> None:
        self._rules = rules

    def evaluate(self, context: dict) -> list[RuleMatch]:
        matches: list[RuleMatch] = []
        for rule in self._rules:
            condition_matches: list[ConditionMatch] = []
            all_matched = True
            for cond in rule.conditions:
                actual = context.get(cond.field)
                matched = self._check(cond, actual)
                condition_matches.append(
                    ConditionMatch(condition=cond, actual_value=actual, matched=matched)
                )
                if not matched:
                    all_matched = False
                    break  # short-circuit
            if all_matched:
                matches.append(
                    RuleMatch(
                        rule=rule,
                        matched_conditions=condition_matches,
                        priority=rule.priority,
                    )
                )
        matches.sort(key=lambda m: m.priority, reverse=True)
        return matches

    @staticmethod
    def _check(cond: Condition, actual: object) -> bool:
        if actual is None:
            return False
        if cond.op == Operator.EQ:
            # Special handling: yoga_present is a list — check membership
            if cond.field == "yoga_present":
                if isinstance(actual, list):
                    return cond.value in actual
                return False
            return actual == cond.value
        return False
