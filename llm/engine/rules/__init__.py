"""
Rule engine — public API.
"""
from llm.engine.rules.schema import (
    Condition,
    ConditionGroup,
    Intensity,
    LifeArea,
    Operator,
    Rule,
    RuleCategory,
    RuleOutput,
)
from llm.engine.rules.evaluator import (
    ConditionMatch,
    RuleEvaluator,
    RuleMatch,
)
from llm.engine.rules.context import build_rule_context
from llm.engine.rules.loader import (
    RuleValidationError,
    load_rules_from_dir,
    load_rules_from_file,
)

__all__ = [
    "Condition",
    "ConditionGroup",
    "ConditionMatch",
    "Intensity",
    "LifeArea",
    "Operator",
    "Rule",
    "RuleCategory",
    "RuleEvaluator",
    "RuleMatch",
    "RuleOutput",
    "RuleValidationError",
    "build_rule_context",
    "load_rules_from_dir",
    "load_rules_from_file",
]
