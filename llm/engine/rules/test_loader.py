"""
Tests for the rule loader — 30 tests covering happy path and all validation error cases.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from llm.engine.rules.loader import (
    RuleValidationError,
    load_rules_from_dir,
    load_rules_from_file,
)
from llm.engine.rules.schema import Operator, RuleCategory


SAMPLE_RULES_PATH = Path(__file__).parent / "sample_rules.json"


def _write_json(tmp_path: Path, filename: str, data: object) -> Path:
    p = tmp_path / filename
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _minimal_rule(**overrides) -> dict:
    base = {
        "id": "test_rule_1",
        "name": "Test Rule",
        "category": "natal_moon",
        "priority": 50,
        "conditions": [{"field": "moon_sign", "op": "eq", "value": "Aries"}],
        "output": {
            "theme": "test_theme",
            "life_area": "self",
            "trait": "test trait",
            "intensity": "medium",
            "shadow": "",
        },
        "tags": ["test"],
    }
    base.update(overrides)
    return base


# ── Happy path ──────────────────────────────────────────────────────


class TestLoadRulesHappyPath:
    def test_load_sample_rules_file(self):
        rules = load_rules_from_file(SAMPLE_RULES_PATH)
        assert len(rules) == 50

    def test_all_rules_have_ids(self):
        rules = load_rules_from_file(SAMPLE_RULES_PATH)
        ids = [r.id for r in rules]
        assert len(ids) == len(set(ids)), "All rule IDs must be unique"

    def test_rule_category_parsed(self):
        rules = load_rules_from_file(SAMPLE_RULES_PATH)
        moon_rules = [r for r in rules if r.category == RuleCategory.NATAL_MOON]
        assert len(moon_rules) == 12

    def test_nakshatra_rules_count(self):
        rules = load_rules_from_file(SAMPLE_RULES_PATH)
        nak_rules = [r for r in rules if r.category == RuleCategory.NAKSHATRA]
        assert len(nak_rules) == 27

    def test_priority_range(self):
        rules = load_rules_from_file(SAMPLE_RULES_PATH)
        for r in rules:
            assert 0 <= r.priority <= 100, f"Rule {r.id} priority out of range"

    def test_conditions_are_non_empty(self):
        rules = load_rules_from_file(SAMPLE_RULES_PATH)
        for r in rules:
            assert len(r.conditions) >= 1

    def test_operator_is_eq(self):
        rules = load_rules_from_file(SAMPLE_RULES_PATH)
        for r in rules:
            for c in r.conditions:
                assert c.op == Operator.EQ

    def test_output_fields_present(self):
        rules = load_rules_from_file(SAMPLE_RULES_PATH)
        for r in rules:
            assert r.output.theme
            assert r.output.life_area
            assert r.output.trait
            assert r.output.intensity

    def test_tags_are_lists_of_strings(self):
        rules = load_rules_from_file(SAMPLE_RULES_PATH)
        for r in rules:
            assert isinstance(r.tags, list)
            for t in r.tags:
                assert isinstance(t, str)

    def test_load_single_rule_file(self, tmp_path):
        rule = _minimal_rule()
        path = _write_json(tmp_path, "rules.json", [rule])
        rules = load_rules_from_file(path)
        assert len(rules) == 1
        assert rules[0].id == "test_rule_1"
        assert rules[0].name == "Test Rule"

    def test_load_from_dir(self, tmp_path):
        _write_json(tmp_path, "a.json", [_minimal_rule(id="r1")])
        _write_json(tmp_path, "b.json", [_minimal_rule(id="r2")])
        rules = load_rules_from_dir(tmp_path)
        assert len(rules) == 2
        assert rules[0].id == "r1"
        assert rules[1].id == "r2"

    def test_load_from_dir_alphabetical_order(self, tmp_path):
        _write_json(tmp_path, "z_last.json", [_minimal_rule(id="z")])
        _write_json(tmp_path, "a_first.json", [_minimal_rule(id="a")])
        rules = load_rules_from_dir(tmp_path)
        assert rules[0].id == "a"
        assert rules[1].id == "z"

    def test_shadow_defaults_to_empty(self, tmp_path):
        rule = _minimal_rule()
        del rule["output"]["shadow"]
        path = _write_json(tmp_path, "rules.json", [rule])
        rules = load_rules_from_file(path)
        assert rules[0].output.shadow == ""

    def test_tags_default_to_empty(self, tmp_path):
        rule = _minimal_rule()
        del rule["tags"]
        path = _write_json(tmp_path, "rules.json", [rule])
        rules = load_rules_from_file(path)
        assert rules[0].tags == []


# ── Validation error cases ──────────────────────────────────────────


class TestLoaderValidationErrors:
    def test_missing_id(self, tmp_path):
        rule = _minimal_rule()
        del rule["id"]
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="id"):
            load_rules_from_file(path)

    def test_empty_id(self, tmp_path):
        rule = _minimal_rule(id="")
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="id"):
            load_rules_from_file(path)

    def test_duplicate_id_same_file(self, tmp_path):
        path = _write_json(tmp_path, "rules.json", [_minimal_rule(id="dup"), _minimal_rule(id="dup")])
        with pytest.raises(RuleValidationError, match="duplicate"):
            load_rules_from_file(path)

    def test_duplicate_id_across_files(self, tmp_path):
        _write_json(tmp_path, "a.json", [_minimal_rule(id="dup")])
        _write_json(tmp_path, "b.json", [_minimal_rule(id="dup")])
        with pytest.raises(RuleValidationError, match="duplicate"):
            load_rules_from_dir(tmp_path)

    def test_missing_name(self, tmp_path):
        rule = _minimal_rule()
        del rule["name"]
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="name"):
            load_rules_from_file(path)

    def test_invalid_category(self, tmp_path):
        rule = _minimal_rule(category="invalid_cat")
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="category"):
            load_rules_from_file(path)

    def test_missing_priority(self, tmp_path):
        rule = _minimal_rule()
        del rule["priority"]
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="priority"):
            load_rules_from_file(path)

    def test_priority_out_of_range(self, tmp_path):
        rule = _minimal_rule(priority=101)
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="priority"):
            load_rules_from_file(path)

    def test_priority_negative(self, tmp_path):
        rule = _minimal_rule(priority=-1)
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="priority"):
            load_rules_from_file(path)

    def test_empty_conditions(self, tmp_path):
        rule = _minimal_rule(conditions=[])
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="conditions"):
            load_rules_from_file(path)

    def test_condition_missing_field(self, tmp_path):
        rule = _minimal_rule(conditions=[{"op": "eq", "value": "Aries"}])
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="field"):
            load_rules_from_file(path)

    def test_condition_invalid_operator(self, tmp_path):
        rule = _minimal_rule(conditions=[{"field": "moon_sign", "op": "ne", "value": "Aries"}])
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="op"):
            load_rules_from_file(path)

    def test_condition_missing_value(self, tmp_path):
        rule = _minimal_rule(conditions=[{"field": "moon_sign", "op": "eq"}])
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="value"):
            load_rules_from_file(path)

    def test_missing_output(self, tmp_path):
        rule = _minimal_rule()
        del rule["output"]
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="output"):
            load_rules_from_file(path)

    def test_output_missing_theme(self, tmp_path):
        rule = _minimal_rule()
        del rule["output"]["theme"]
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="theme"):
            load_rules_from_file(path)

    def test_output_invalid_life_area(self, tmp_path):
        rule = _minimal_rule()
        rule["output"]["life_area"] = "invalid_area"
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="life_area"):
            load_rules_from_file(path)

    def test_output_invalid_intensity(self, tmp_path):
        rule = _minimal_rule()
        rule["output"]["intensity"] = "extreme"
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="intensity"):
            load_rules_from_file(path)

    def test_json_root_not_list(self, tmp_path):
        path = _write_json(tmp_path, "rules.json", {"not": "a list"})
        with pytest.raises(RuleValidationError, match="list"):
            load_rules_from_file(path)

    def test_tags_not_list(self, tmp_path):
        rule = _minimal_rule(tags="not_a_list")
        path = _write_json(tmp_path, "rules.json", [rule])
        with pytest.raises(RuleValidationError, match="tags"):
            load_rules_from_file(path)

    def test_dir_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_rules_from_dir("/nonexistent/path/xyz")
