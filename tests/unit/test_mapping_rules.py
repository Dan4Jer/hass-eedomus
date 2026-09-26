"""Unit tests for the advanced mapping rules (mapping_rules.py).

Pure logic tests: condition evaluation for device mapping
(usage_id, children counts, parent relations, name matching).
"""

import pytest

from custom_components.eedomus.mapping_rules import (
    evaluate_advanced_rules,
    evaluate_conditions,
)


pytestmark = pytest.mark.unit


class TestUsageIdCondition:
    def test_usage_id_matches(self):
        device = {"periph_id": "1", "name": "Dev", "usage_id": "10"}
        assert evaluate_conditions([{"usage_id": "10"}], device, {}, "1", "r")

    def test_usage_id_mismatch(self):
        device = {"periph_id": "1", "name": "Dev", "usage_id": "11"}
        assert not evaluate_conditions([{"usage_id": "10"}], device, {}, "1", "r")


class TestMinChildrenCondition:
    def _device(self, periph_id="parent"):
        return {"periph_id": periph_id, "name": "Parent", "usage_id": "1"}

    def test_min_children_met(self):
        devices = {
            "c1": {"parent_periph_id": "parent"},
            "c2": {"parent_periph_id": "parent"},
        }
        assert evaluate_conditions(
            [{"min_children": 2}], self._device(), devices, "parent", "r"
        )

    def test_min_children_not_met(self):
        devices = {"c1": {"parent_periph_id": "parent"}}
        assert not evaluate_conditions(
            [{"min_children": 2}], self._device(), devices, "parent", "r"
        )

    def test_min_children_no_devices(self):
        assert not evaluate_conditions(
            [{"min_children": 1}], self._device(), {}, "parent", "r"
        )

    def test_min_children_uses_precomputed_relations(self):
        """When parent_child_relations are provided they win over all_devices.

        Note: all_devices must be non-empty for the condition to be
        evaluated at all; the relations then provide the child count.
        all_devices lists 1 child, relations say 3 → min_children=3 passes.
        """
        relations = {"parent": ["c1", "c2", "c3"]}
        devices = {"c1": {"parent_periph_id": "parent"}}
        assert evaluate_conditions(
            [{"min_children": 3}], self._device(), devices, "parent", "r",
            parent_child_relations=relations,
        )


class TestChildUsageIdCondition:
    def test_child_with_usage_id_exists(self):
        device = {"periph_id": "p", "name": "P"}
        devices = {"c1": {"parent_periph_id": "p", "usage_id": "42"}}
        assert evaluate_conditions(
            [{"child_usage_id": "42"}], device, devices, "p", "r"
        )

    def test_child_with_wrong_usage_id(self):
        device = {"periph_id": "p", "name": "P"}
        devices = {"c1": {"parent_periph_id": "p", "usage_id": "43"}}
        assert not evaluate_conditions(
            [{"child_usage_id": "42"}], device, devices, "p", "r"
        )


class TestParentConditions:
    def test_has_parent(self):
        device = {"periph_id": "c", "name": "C", "parent_periph_id": "p"}
        assert evaluate_conditions([{"has_parent": True}], device, {}, "c", "r")

    def test_has_parent_missing(self):
        device = {"periph_id": "c", "name": "C"}
        assert not evaluate_conditions([{"has_parent": True}], device, {}, "c", "r")

    def test_parent_usage_id_matches(self):
        device = {"periph_id": "c", "name": "C", "parent_periph_id": "p"}
        devices = {"p": {"usage_id": "7"}}
        assert evaluate_conditions(
            [{"parent_usage_id": "7"}], device, devices, "c", "r"
        )

    def test_parent_has_min_children(self):
        device = {"periph_id": "c", "name": "C", "parent_periph_id": "p"}
        devices = {
            "s1": {"parent_periph_id": "p"},
            "s2": {"parent_periph_id": "p"},
        }
        assert evaluate_conditions(
            [{"parent_has_min_children": 2}], device, devices, "c", "r"
        )


class TestHasChildrenWithNames:
    def test_all_required_names_present(self):
        device = {"periph_id": "p", "name": "P"}
        devices = {
            "c1": {"parent_periph_id": "p", "name": "RGBW Rouge"},
            "c2": {"parent_periph_id": "p", "name": "RGBW Bleu"},
        }
        assert evaluate_conditions(
            [{"has_children_with_names": ["rouge", "bleu"]}],
            device, devices, "p", "r",
        )

    def test_missing_required_name(self):
        device = {"periph_id": "p", "name": "P"}
        devices = {"c1": {"parent_periph_id": "p", "name": "RGBW Rouge"}}
        assert not evaluate_conditions(
            [{"has_children_with_names": ["rouge", "bleu"]}],
            device, devices, "p", "r",
        )

    def test_single_name_as_string(self):
        device = {"periph_id": "p", "name": "P"}
        devices = {"c1": {"parent_periph_id": "p", "name": "Rouge"}}
        assert evaluate_conditions(
            [{"has_children_with_names": "rouge"}], device, devices, "p", "r"
        )


class TestUnknownCondition:
    def test_unknown_key_fails_condition(self):
        device = {"periph_id": "1", "name": "Dev"}
        assert not evaluate_conditions([{"nope": 1}], device, {}, "1", "r")


class TestEvaluateAdvancedRules:
    def test_first_matching_rule_returns_mapping(self):
        device = {"periph_id": "1", "name": "Dev", "usage_id": "10"}
        rules = {
            "rule_a": {
                "conditions": [{"usage_id": "99"}],
                "mapping": {"wrong": True},
            },
            "rule_b": {
                "conditions": [{"usage_id": "10"}],
                "mapping": {"type": "light", "subtype": "dimmable"},
            },
        }
        result = evaluate_advanced_rules(device, {}, rules)
        assert result == {"type": "light", "subtype": "dimmable"}

    def test_no_matching_rule_returns_none(self):
        device = {"periph_id": "1", "name": "Dev", "usage_id": "10"}
        rules = {
            "rule_a": {
                "conditions": [{"usage_id": "99"}],
                "mapping": {"wrong": True},
            },
        }
        assert evaluate_advanced_rules(device, {}, rules) is None

    def test_callable_condition(self):
        device = {"periph_id": "1", "name": "Dev"}
        rules = {
            "rule": {
                "condition": lambda dev, all_devs: True,
                "mapping": {"ok": 1},
            },
        }
        assert evaluate_advanced_rules(device, {}, rules) == {"ok": 1}
