"""
JSON rule loader with strict validation.

Fails fast: every malformed rule raises RuleValidationError with the rule id.

Supports two condition formats:
  - Legacy flat list:  "conditions": [{"field": ..., "op": ..., "value": ...}]
    → auto-wrapped into ConditionGroup(all_of=(...))
  - New grouped:       "conditions": {"all": [...]} or {"any": [...]}
    → parsed recursively, supports nesting
"""
from __future__ import annotations

import json
from pathlib import Path

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


class RuleValidationError(Exception):
    def __init__(self, message: str, rule_id: str = "unknown") -> None:
        self.rule_id = rule_id
        super().__init__(f"[rule {rule_id}] {message}")


def _parse_condition(raw: dict, label: str, rule_id: str) -> Condition:
    """Parse a single leaf condition dict into a Condition dataclass."""
    c_field = raw.get("field")
    if not c_field or not isinstance(c_field, str):
        raise RuleValidationError(f"{label}.field is required and must be a string", rule_id)
    c_op = raw.get("op")
    if not c_op:
        raise RuleValidationError(f"{label}.op is required", rule_id)
    try:
        op = Operator(c_op)
    except ValueError:
        valid = [o.value for o in Operator]
        raise RuleValidationError(f"{label}.op '{c_op}' is invalid, must be one of {valid}", rule_id)
    c_value = raw.get("value")
    if c_value is None:
        raise RuleValidationError(f"{label}.value is required", rule_id)
    # Validate value type based on operator
    if op == Operator.IN:
        if not isinstance(c_value, list):
            raise RuleValidationError(f"{label}.value must be a list for 'in' operator", rule_id)
    elif op == Operator.RANGE:
        if not isinstance(c_value, list) or len(c_value) != 2:
            raise RuleValidationError(f"{label}.value must be a [min, max] list for 'range' operator", rule_id)
        if not all(isinstance(v, (int, float)) for v in c_value):
            raise RuleValidationError(f"{label}.value must contain numeric values for 'range' operator", rule_id)
        if c_value[0] > c_value[1]:
            raise RuleValidationError(f"{label}.value[0] must be <= value[1] for 'range' operator", rule_id)
    elif op in (Operator.GT, Operator.LT):
        if not isinstance(c_value, (int, float)):
            raise RuleValidationError(f"{label}.value must be numeric for '{op.value}' operator", rule_id)
    else:
        if not isinstance(c_value, (str, int, float, bool)):
            raise RuleValidationError(f"{label}.value must be str, int, float, or bool", rule_id)
    return Condition(field=c_field, op=op, value=c_value)


def _parse_condition_node(raw, label: str, rule_id: str) -> Condition | ConditionGroup:
    """Parse a condition node — either a leaf condition or a group with all/any."""
    if not isinstance(raw, dict):
        raise RuleValidationError(f"{label} must be an object", rule_id)

    has_all = "all" in raw
    has_any = "any" in raw
    has_field = "field" in raw

    if has_all and has_any:
        raise RuleValidationError(f"{label} cannot have both 'all' and 'any'", rule_id)

    if has_all or has_any:
        key = "all" if has_all else "any"
        children_raw = raw[key]
        if not isinstance(children_raw, list) or len(children_raw) == 0:
            raise RuleValidationError(f"{label}.{key} must be a non-empty list", rule_id)
        children = tuple(
            _parse_condition_node(child, f"{label}.{key}[{i}]", rule_id)
            for i, child in enumerate(children_raw)
        )
        if has_all:
            return ConditionGroup(all_of=children)
        return ConditionGroup(any_of=children)

    if has_field:
        return _parse_condition(raw, label, rule_id)

    raise RuleValidationError(f"{label} must be a condition (field/op/value) or a group (all/any)", rule_id)


def _parse_conditions(raw, rule_id: str) -> ConditionGroup:
    """Parse the top-level 'conditions' field.

    Accepts:
      - list of conditions (legacy) → wrapped in ConditionGroup(all_of=...)
      - dict with 'all' or 'any' (new format) → parsed recursively
    """
    if isinstance(raw, list):
        # Legacy flat list → implicit AND
        if len(raw) == 0:
            raise RuleValidationError("'conditions' must be a non-empty list", rule_id)
        children = []
        for i, c in enumerate(raw):
            if not isinstance(c, dict):
                raise RuleValidationError(f"condition[{i}] must be an object", rule_id)
            children.append(_parse_condition(c, f"condition[{i}]", rule_id))
        return ConditionGroup(all_of=tuple(children))

    if isinstance(raw, dict):
        node = _parse_condition_node(raw, "conditions", rule_id)
        if isinstance(node, Condition):
            return ConditionGroup(all_of=(node,))
        return node

    raise RuleValidationError("'conditions' must be a list or an object with 'all'/'any'", rule_id)


def _validate_and_parse(raw: dict, seen_ids: set[str]) -> Rule:
    # id
    rule_id = raw.get("id")
    if not rule_id or not isinstance(rule_id, str):
        raise RuleValidationError("'id' is required and must be a non-empty string", rule_id or "unknown")

    if rule_id in seen_ids:
        raise RuleValidationError(f"duplicate id '{rule_id}'", rule_id)
    seen_ids.add(rule_id)

    # name
    name = raw.get("name")
    if not name or not isinstance(name, str):
        raise RuleValidationError("'name' is required and must be a non-empty string", rule_id)

    # category
    cat_raw = raw.get("category")
    if not cat_raw:
        raise RuleValidationError("'category' is required", rule_id)
    try:
        category = RuleCategory(cat_raw)
    except ValueError:
        valid = [c.value for c in RuleCategory]
        raise RuleValidationError(f"invalid category '{cat_raw}', must be one of {valid}", rule_id)

    # priority
    priority = raw.get("priority")
    if priority is None or not isinstance(priority, int):
        raise RuleValidationError("'priority' is required and must be an integer", rule_id)
    if not (0 <= priority <= 100):
        raise RuleValidationError(f"priority must be 0-100, got {priority}", rule_id)

    # conditions
    conds_raw = raw.get("conditions")
    if not conds_raw:
        raise RuleValidationError("'conditions' is required", rule_id)
    conditions = _parse_conditions(conds_raw, rule_id)

    # output
    out_raw = raw.get("output")
    if not out_raw or not isinstance(out_raw, dict):
        raise RuleValidationError("'output' is required and must be an object", rule_id)

    for req_field in ("theme", "life_area", "trait", "intensity"):
        if not out_raw.get(req_field):
            raise RuleValidationError(f"output.{req_field} is required", rule_id)

    life_area = out_raw["life_area"]
    try:
        LifeArea(life_area)
    except ValueError:
        valid = [la.value for la in LifeArea]
        raise RuleValidationError(f"output.life_area '{life_area}' is invalid, must be one of {valid}", rule_id)

    intensity = out_raw["intensity"]
    try:
        Intensity(intensity)
    except ValueError:
        valid = [it.value for it in Intensity]
        raise RuleValidationError(f"output.intensity '{intensity}' is invalid, must be one of {valid}", rule_id)

    output = RuleOutput(
        theme=out_raw["theme"],
        life_area=life_area,
        trait=out_raw["trait"],
        intensity=intensity,
        shadow=out_raw.get("shadow", ""),
    )

    # tags
    tags_raw = raw.get("tags", [])
    if not isinstance(tags_raw, list):
        raise RuleValidationError("'tags' must be a list of strings", rule_id)
    for i, t in enumerate(tags_raw):
        if not isinstance(t, str):
            raise RuleValidationError(f"tags[{i}] must be a string", rule_id)

    return Rule(
        id=rule_id,
        name=name,
        category=category,
        priority=priority,
        conditions=conditions,
        output=output,
        tags=tags_raw,
    )


def load_rules_from_file(path: str | Path) -> list[Rule]:
    path = Path(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise RuleValidationError("JSON root must be a list of rule objects", "file")

    seen_ids: set[str] = set()
    rules: list[Rule] = []
    for raw in data:
        rules.append(_validate_and_parse(raw, seen_ids))
    return rules


def load_rules_from_dir(dir_path: str | Path) -> list[Rule]:
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    files = sorted(dir_path.glob("*.json"))
    seen_ids: set[str] = set()
    rules: list[Rule] = []
    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise RuleValidationError(f"JSON root in {file.name} must be a list", "file")
        for raw in data:
            rules.append(_validate_and_parse(raw, seen_ids))
    return rules
