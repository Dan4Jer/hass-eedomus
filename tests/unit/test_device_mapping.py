"""Unit tests for device mapping YAML loading and merging (device_mapping.py).

These tests document the ACTUAL merge semantics of merge_yaml_mappings:
- usage_id_mappings: from default; custom overrides arrive via the
  'custom_usage_id_mappings' key of the custom mapping
- advanced_rules: only the default mapping's list is kept (custom
  rules converted by backward-compat are NOT merged into the list)
- name_patterns: custom extends the default via 'custom_name_patterns'
"""

import pytest

from custom_components.eedomus.device_mapping import (
    load_yaml_file,
    merge_yaml_mappings,
)


pytestmark = pytest.mark.unit


class TestLoadYamlFile:
    def test_loads_dict_yaml(self, tmp_path):
        f = tmp_path / "mapping.yaml"
        f.write_text("advanced_rules: []\nusage_id_mappings:\n  10: light\n")
        result = load_yaml_file(str(f))
        # YAML parses the bare numeric key as an int
        assert result == {"advanced_rules": [], "usage_id_mappings": {10: "light"}}

    def test_missing_file_returns_none(self, tmp_path):
        assert load_yaml_file(str(tmp_path / "nope.yaml")) is None

    def test_invalid_yaml_returns_none(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("{unclosed: [")
        assert load_yaml_file(str(f)) is None

    def test_empty_file_returns_none(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        assert load_yaml_file(str(f)) is None


class TestMergeYamlMappings:
    def test_non_dict_inputs_are_coerced(self):
        merged = merge_yaml_mappings("garbage", None)
        assert isinstance(merged, dict)

    def test_custom_usage_id_mappings_override_default(self):
        """Custom overrides arrive via the custom_usage_id_mappings key."""
        default = {"usage_id_mappings": {"10": "light"}}
        custom = {"custom_usage_id_mappings": {"10": "sensor"}}
        merged = merge_yaml_mappings(default, custom)
        assert merged["usage_id_mappings"]["10"] == "sensor"

    def test_plain_custom_usage_id_mappings_ignored(self):
        """A custom 'usage_id_mappings' key alone does not override
        (the merge only reads the custom_* prefixed keys)."""
        default = {"usage_id_mappings": {"10": "light"}}
        custom = {"usage_id_mappings": {"10": "sensor"}}
        merged = merge_yaml_mappings(default, custom)
        assert merged["usage_id_mappings"]["10"] == "light"

    def test_advanced_rules_from_default_only(self):
        """Current behavior: only the default's advanced_rules survive;
        custom rules are not merged into the list."""
        default = {"advanced_rules": [{"name": "d1"}]}
        custom = {"custom_rules": [{"name": "c1"}]}
        merged = merge_yaml_mappings(default, custom)
        names = [r.get("name") for r in merged["advanced_rules"]]
        assert "d1" in names
        assert "c1" not in names

    def test_advanced_rules_always_a_list(self):
        merged = merge_yaml_mappings({}, {})
        assert merged["advanced_rules"] == []

    def test_advanced_rules_dict_indexed_by_name(self):
        """Rules are also exposed as a dict keyed by rule name."""
        default = {"advanced_rules": [{"name": "rgbw", "mapping": {}}]}
        merged = merge_yaml_mappings(default, {})
        assert "rgbw" in merged["advanced_rules_dict"]

    def test_custom_name_patterns_extend_default(self):
        default = {"name_patterns": ["p1"]}
        custom = {"custom_name_patterns": ["p2"]}
        merged = merge_yaml_mappings(default, custom)
        assert merged["name_patterns"] == ["p1", "p2"]

    def test_metadata_from_both_sources(self):
        default = {"metadata": {"version": "1.0"}}
        custom = {"metadata": {"version": "2.0", "author": "me"}}
        merged = merge_yaml_mappings(default, custom)
        assert merged["metadata"]["version"] == "2.0"
        assert merged["metadata"]["author"] == "me"
