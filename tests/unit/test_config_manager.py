"""Unit tests for the custom mapping persistence (config_manager, P.1.4).

The panel saves the custom mapping OUTSIDE the integration tree (option B,
validated by the user): the config-dir file /eedomus/custom_mapping.yaml is
the save target, the previous version is archived in HA storage (three
kept, oldest purged), and the loader prefers the config-dir file over the
integrated one.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import custom_components.eedomus.config_manager as config_manager_module
from custom_components.eedomus.config_manager import EedomusConfigManager

pytestmark = pytest.mark.unit


class RecordingStore:
    """Functional Store stub recording saved data per storage key."""

    registry: dict = {}

    def __init__(self, hass, version, key):
        self.key = key

    async def async_load(self):
        return RecordingStore.registry.get(self.key)

    async def async_save(self, data):
        RecordingStore.registry[self.key] = data


@pytest.fixture
def manager(tmp_path, monkeypatch):
    """A config manager writing into tmp_path as the HA config dir."""
    monkeypatch.setattr(config_manager_module, "Store", RecordingStore)
    RecordingStore.registry.clear()
    hass = MagicMock()
    hass.config = SimpleNamespace(config_dir=str(tmp_path))

    async def _exec(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    hass.async_add_executor_job = MagicMock(side_effect=_exec)
    return EedomusConfigManager(hass), tmp_path


VALID_MAPPING = {
    "metadata": {"version": "1.0"},
    "custom_usage_id_mappings": {
        "7": {"ha_entity": "sensor", "ha_subtype": "temperature"}
    },
}

INVALID_MAPPING = {
    "custom_usage_id_mappings": {"7": {"ha_entity": 123}},
}


class TestSaveCustomMapping:
    @pytest.mark.asyncio
    async def test_writes_to_config_dir_file(self, manager):
        config_manager, tmp_path = manager

        result = await config_manager.async_save_custom_mapping(VALID_MAPPING)

        assert result["success"] is True
        target = tmp_path / "eedomus" / "custom_mapping.yaml"
        assert target.is_file()
        assert "custom_usage_id_mappings" in target.read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_invalid_mapping_is_refused(self, manager):
        config_manager, tmp_path = manager

        result = await config_manager.async_save_custom_mapping(INVALID_MAPPING)

        assert result["success"] is False
        assert result["error"]
        assert not (tmp_path / "eedomus" / "custom_mapping.yaml").exists()

    @pytest.mark.asyncio
    async def test_archives_replaced_version(self, manager, monkeypatch):
        config_manager, _ = manager
        import custom_components.eedomus.device_mapping as device_mapping_module

        current = {"metadata": {"version": "0.9"}}
        monkeypatch.setattr(
            device_mapping_module,
            "load_custom_yaml_mappings_async",
            _async_return(current),
        )

        await config_manager.async_save_custom_mapping(VALID_MAPPING)

        versions = await config_manager.async_get_mapping_versions()
        assert len(versions) == 1
        assert versions[0]["config"] == current
        assert versions[0]["timestamp"]

    @pytest.mark.asyncio
    async def test_fourth_save_purges_oldest(self, manager):
        config_manager, _ = manager

        for i in range(4):
            await config_manager.async_archive_mapping_version(
                {"metadata": {"version": str(i)}}
            )

        versions = await config_manager.async_get_mapping_versions()
        assert len(versions) == 3
        # Newest first
        assert versions[0]["config"]["metadata"]["version"] == "3"
        assert versions[-1]["config"]["metadata"]["version"] == "1"

    @pytest.mark.asyncio
    async def test_get_custom_mapping_returns_loader_content(
        self, manager, monkeypatch
    ):
        config_manager, _ = manager
        import custom_components.eedomus.device_mapping as device_mapping_module

        monkeypatch.setattr(
            device_mapping_module,
            "load_custom_yaml_mappings_async",
            _async_return(VALID_MAPPING),
        )

        mapping = await config_manager.async_get_custom_mapping()

        assert mapping == VALID_MAPPING


def _async_return(value):
    from unittest.mock import AsyncMock

    return AsyncMock(return_value=value)


class TestCustomMappingPaths:
    def test_config_dir_file_takes_priority(self, tmp_path, monkeypatch):
        import sys

        import custom_components.eedomus.device_mapping as device_mapping_module

        monkeypatch.setattr(
            sys.modules["homeassistant.core"],
            "async_get_hass",
            lambda: SimpleNamespace(config=SimpleNamespace(config_dir=str(tmp_path))),
            raising=False,
        )

        paths = device_mapping_module.get_custom_mapping_paths()

        assert paths[0] == str(Path(tmp_path) / "eedomus" / "custom_mapping.yaml")
        # Integrated file stays as the fallback
        assert paths[1].endswith("config/custom_mapping.yaml")

    def test_without_hass_falls_back_to_integrated_file(self, monkeypatch):
        import custom_components.eedomus.device_mapping as device_mapping_module

        paths = device_mapping_module.get_custom_mapping_paths()

        assert paths == [paths[0]]
        assert paths[0].endswith("config/custom_mapping.yaml")

    def test_loader_prefers_config_dir_file(self, tmp_path, monkeypatch):
        import sys

        import custom_components.eedomus.device_mapping as device_mapping_module

        target = tmp_path / "eedomus"
        target.mkdir()
        (target / "custom_mapping.yaml").write_text(
            "custom_rules: []\nmetadata:\n  version: config-dir\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            sys.modules["homeassistant.core"],
            "async_get_hass",
            lambda: SimpleNamespace(config=SimpleNamespace(config_dir=str(tmp_path))),
            raising=False,
        )

        loaded = device_mapping_module.load_custom_yaml_mappings()

        assert loaded == {"custom_rules": [], "metadata": {"version": "config-dir"}}


class TestMergedLoaderUsesConfigDir:
    def test_merged_config_reflects_config_dir_file(self, tmp_path, monkeypatch):
        """The merge loader (driving the real mapping) must read the
        config-dir custom file, not only the integrated one."""
        import sys

        import custom_components.eedomus.device_mapping as device_mapping_module

        target = tmp_path / "eedomus"
        target.mkdir()
        (target / "custom_mapping.yaml").write_text(
            "custom_usage_id_mappings:\n  '999':\n    ha_entity: sensor\n"
            "    ha_subtype: temperature\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            sys.modules["homeassistant.core"],
            "async_get_hass",
            lambda: SimpleNamespace(
                config=SimpleNamespace(config_dir=str(tmp_path))
            ),
            raising=False,
        )

        merged = device_mapping_module.load_yaml_mappings()

        assert merged["usage_id_mappings"]["999"]["ha_entity"] == "sensor"
        assert merged["usage_id_mappings"]["999"]["ha_subtype"] == "temperature"
