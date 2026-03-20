"""
JSON rule loader with strict validation.

Fails fast: every malformed rule raises RuleValidationError with the rule id.
"""
from __future__ import annotations

import json
from pathlib import Path

from llm.engine.rules.schema import (
    Condition,
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
    if not conds_raw or not isinstance(conds_raw, list) or len(conds_raw) == 0:
        raise RuleValidationError("'conditions' must be a non-empty list", rule_id)

    conditions: list[Condition] = []
    for i, c in enumerate(conds_raw):
        if not isinstance(c, dict):
            raise RuleValidationError(f"condition[{i}] must be an object", rule_id)
        c_field = c.get("field")
        if not c_field or not isinstance(c_field, str):
            raise RuleValidationError(f"condition[{i}].field is required and must be a string", rule_id)
        c_op = c.get("op")
        if not c_op:
            raise RuleValidationError(f"condition[{i}].op is required", rule_id)
        try:
            op = Operator(c_op)
        except ValueError:
            raise RuleValidationError(f"condition[{i}].op '{c_op}' is invalid", rule_id)
        c_value = c.get("value")
        if c_value is None:
            raise RuleValidationError(f"condition[{i}].value is required", rule_id)
        if not isinstance(c_value, (str, int, bool)):
            raise RuleValidationError(f"condition[{i}].value must be str, int, or bool", rule_id)
        conditions.append(Condition(field=c_field, op=op, value=c_value))

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
