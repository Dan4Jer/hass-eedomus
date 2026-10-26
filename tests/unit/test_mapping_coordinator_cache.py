"""Unit tests: the device mapping is read from the coordinator's cache.

map_device_to_ha_entity used to read the module-level DEVICE_MAPPINGS, a
global loaded once at import time and never refreshed. It could miss the
user's custom mapping (saved in HA storage and merged by the coordinator
at setup): a custom usage_id mapping showed in the panel but was not
applied, the peripheral stayed mapped by the default fallback.
"""

from types import SimpleNamespace

import pytest

from custom_components.eedomus.device_mapping import merge_yaml_mappings
from custom_components.eedomus.entity import map_device_to_ha_entity

pytestmark = pytest.mark.unit

DEFAULT = {
    "usage_id_mappings": {
        "1": {"ha_entity": "light", "ha_subtype": "dimmable", "justification": "d"},
    },
    "advanced_rules": [],
    "name_patterns": [],
}


class FakeCoordinator:
    """Coordinator stand-in exposing the async-loaded mapping cache."""

    config_entry = SimpleNamespace(entry_id="01TEST")

    def __init__(self, merged=None, loaded=True):
        self._merged = merged
        self._loaded = loaded

    def get_yaml_config_sync(self):
        if not self._loaded:
            raise Exception("YAML configuration not loaded")
        return self._merged


def _device(periph_id="2585976", usage_id="49", name="Prog Chauffage"):
    return {
        "periph_id": periph_id,
        "name": name,
        "usage_id": usage_id,
        "value_type": "list",
        "parent_periph_id": "",
    }


def _map(device, coordinator):
    return map_device_to_ha_entity(
        device, {device["periph_id"]: device}, coordinator=coordinator
    )


def test_custom_usage_id_mapping_from_cache_is_applied():
    """A custom usage_id mapping in the coordinator cache wins."""
    custom = {
        "custom_usage_id_mappings": {
            "49": {"ha_entity": "switch", "ha_subtype": "", "justification": "Rules"}
        }
    }
    merged = merge_yaml_mappings(DEFAULT, custom)
    result = _map(_device(), FakeCoordinator(merged))
    assert result["ha_entity"] == "switch"
    assert result["justification"] == "Rules"


def test_default_usage_id_mapping_still_applies():
    """An unrelated usage_id keeps the default mapping."""
    custom = {
        "custom_usage_id_mappings": {"49": {"ha_entity": "switch", "ha_subtype": ""}}
    }
    merged = merge_yaml_mappings(DEFAULT, custom)
    result = _map(_device("7", "1", "Lampe"), FakeCoordinator(merged))
    assert (result["ha_entity"], result["ha_subtype"]) == ("light", "dimmable")


def test_cache_not_loaded_falls_back_to_module_mapping():
    """Before the coordinator cache exists, mapping must not raise."""
    result = _map(_device("7", "1", "Lampe"), FakeCoordinator(loaded=False))
    assert result["ha_entity"]


def test_no_coordinator_falls_back_to_module_mapping():
    """Callers without a coordinator keep the import-time mapping."""
    result = map_device_to_ha_entity(_device("7", "1", "Lampe"), {})
    assert result["ha_entity"]


def test_custom_name_pattern_from_cache_is_applied():
    """Name patterns are read from the cache too."""
    merged = {
        "usage_id_mappings": {},
        "advanced_rules": [],
        "advanced_rules_dict": {},
        "name_patterns": [
            {"pattern": "prog ", "ha_entity": "switch", "ha_subtype": "program"}
        ],
    }
    result = _map(_device(usage_id="9999"), FakeCoordinator(merged))
    assert (result["ha_entity"], result["ha_subtype"]) == ("switch", "program")


def test_state_conditional_custom_rule_does_not_crash():
    """A documented custom_rules entry (condition dict + actions) is skipped.

    The documented shape has no mapping and a dict condition; the engine
    used to call that dict as a function (TypeError) once rules reached it.
    """
    custom = {
        "custom_rules": [
            {
                "name": "my rule",
                "condition": {"usage_id": "49", "state": "on"},
                "actions": [{"type": "override", "ha_entity": "switch"}],
            }
        ],
        "custom_usage_id_mappings": {"49": {"ha_entity": "switch", "ha_subtype": ""}},
    }
    merged = merge_yaml_mappings(DEFAULT, custom)
    assert "my rule" in merged["advanced_rules_dict"]
    result = _map(_device(), FakeCoordinator(merged))
    assert result["ha_entity"] == "switch"
