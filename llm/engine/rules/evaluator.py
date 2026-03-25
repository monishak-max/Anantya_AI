"""
Core rule evaluation engine.

Supports AND (all_of), OR (any_of), and nested condition groups.
Results sorted by priority descending.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from llm.engine.rules.schema import Condition, ConditionGroup, Operator, Rule


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
            leaf_matches: list[ConditionMatch] = []
            if self._eval_node(rule.conditions, context, leaf_matches):
                matches.append(
                    RuleMatch(
                        rule=rule,
                        matched_conditions=leaf_matches,
                        priority=rule.priority,
                    )
                )
        matches.sort(key=lambda m: m.priority, reverse=True)
        return matches

    def _eval_node(
        self,
        node: ConditionGroup | Condition,
        context: dict,
        collector: list[ConditionMatch],
    ) -> bool:
        if isinstance(node, Condition):
            actual = context.get(node.field)
            matched = self._check(node, actual)
            collector.append(ConditionMatch(condition=node, actual_value=actual, matched=matched))
            return matched

        if node.all_of is not None:
            for child in node.all_of:
                if not self._eval_node(child, context, collector):
                    return False  # short-circuit AND
            return True

        if node.any_of is not None:
            for child in node.any_of:
                branch: list[ConditionMatch] = []
                if self._eval_node(child, context, branch):
                    collector.extend(branch)
                    return True  # short-circuit OR
            return False

        return False

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
        if cond.op == Operator.IN:
            if isinstance(cond.value, list):
                return actual in cond.value
            return False
        if cond.op == Operator.RANGE:
            if isinstance(actual, (int, float)) and isinstance(cond.value, list) and len(cond.value) == 2:
                return cond.value[0] <= actual <= cond.value[1]
            return False
        if cond.op == Operator.GT:
            if isinstance(actual, (int, float)) and isinstance(cond.value, (int, float)):
                return actual > cond.value
            return False
        if cond.op == Operator.LT:
            if isinstance(actual, (int, float)) and isinstance(cond.value, (int, float)):
                return actual < cond.value
            return False
        return False
