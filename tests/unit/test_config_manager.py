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
        self._data = RecordingStore.registry.get(key)

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
    async def test_archives_replaced_storage_current(self, manager):
        """Save archives the previous canonical current (AD-13ter)."""
        config_manager, _ = manager
        previous = {"metadata": {"version": "0.9"}}
        RecordingStore.registry["eedomus.mapping"] = {
            "current": previous,
            "file_fingerprint": "metadata:\n  version: '0.9'\n",
        }

        await config_manager.async_save_custom_mapping(VALID_MAPPING)

        versions = await config_manager.async_get_mapping_versions()
        assert len(versions) == 1
        assert versions[0]["config"] == previous

    @pytest.mark.asyncio
    async def test_save_writes_storage_canon_and_mirror(self, manager):
        """Save stores current + fingerprint and rewrites the mirror."""
        config_manager, tmp_path = manager

        result = await config_manager.async_save_custom_mapping(VALID_MAPPING)

        assert result["success"] is True
        stored = RecordingStore.registry["eedomus.mapping"]
        assert stored["current"] == VALID_MAPPING
        assert stored["file_fingerprint"]
        mirror = tmp_path / "eedomus" / "custom_mapping.yaml"
        assert mirror.is_file()
        assert mirror.read_text(encoding="utf-8") == stored["file_fingerprint"]

    @pytest.mark.asyncio
    async def test_get_custom_mapping_reads_the_storage_canon(self, manager):
        config_manager, _ = manager
        RecordingStore.registry["eedomus.mapping"] = {
            "current": VALID_MAPPING,
            "file_fingerprint": "text",
        }

        mapping = await config_manager.async_get_custom_mapping()

        assert mapping == VALID_MAPPING

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
    async def test_get_custom_mapping_falls_back_to_file_before_bootstrap(
        self, manager, monkeypatch
    ):
        """No canon in storage yet: the file is the bootstrap source."""
        config_manager, tmp_path = manager
        import custom_components.eedomus.device_mapping as device_mapping_module

        target = tmp_path / "eedomus"
        target.mkdir()
        (target / "custom_mapping.yaml").write_text(
            "custom_rules: []\n", encoding="utf-8"
        )
        monkeypatch.setattr(
            device_mapping_module,
            "get_custom_mapping_paths",
            lambda: [str(target / "custom_mapping.yaml")],
        )

        mapping = await config_manager.async_get_custom_mapping()

        assert mapping == {"custom_rules": []}


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
        assert paths[1].endswith("config/custom_mapping.yaml.example")

    def test_without_hass_falls_back_to_integrated_file(self, monkeypatch):
        import custom_components.eedomus.device_mapping as device_mapping_module

        paths = device_mapping_module.get_custom_mapping_paths()

        assert paths == [paths[0]]
        assert paths[0].endswith("config/custom_mapping.yaml.example")

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
            lambda: SimpleNamespace(config=SimpleNamespace(config_dir=str(tmp_path))),
            raising=False,
        )

        merged = device_mapping_module.load_yaml_mappings()

        assert merged["usage_id_mappings"]["999"]["ha_entity"] == "sensor"
        assert merged["usage_id_mappings"]["999"]["ha_subtype"] == "temperature"


class TestIngestCustomMapping:
    """AD-13bis: the editable file is compared to the storage canon at
    load time and ingested as a new version when it differs and validates."""

    def make_ingest_manager(self, tmp_path, monkeypatch, file_text=None):
        """A config manager whose custom mapping paths point at tmp_path."""
        import custom_components.eedomus.config_manager as config_manager_module
        import custom_components.eedomus.device_mapping as device_mapping_module

        monkeypatch.setattr(config_manager_module, "Store", RecordingStore)
        RecordingStore.registry.clear()
        hass = MagicMock()
        hass.config = SimpleNamespace(config_dir=str(tmp_path))

        async def _exec(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        hass.async_add_executor_job = MagicMock(side_effect=_exec)

        config_dir_file = tmp_path / "eedomus" / "custom_mapping.yaml"
        monkeypatch.setattr(
            device_mapping_module,
            "get_custom_mapping_paths",
            lambda: [str(config_dir_file)],
        )
        if file_text is not None:
            config_dir_file.parent.mkdir(parents=True, exist_ok=True)
            config_dir_file.write_text(file_text, encoding="utf-8")
        return EedomusConfigManager(hass), config_dir_file

    @pytest.mark.asyncio
    async def test_bootstrap_file_becomes_initial_canon(self, tmp_path, monkeypatch):
        file_text = "custom_rules: []\nmetadata:\n  version: 1.0\n"
        manager, mirror = self.make_ingest_manager(
            tmp_path, monkeypatch, file_text=file_text
        )

        await manager._async_ingest_custom_mapping()

        stored = RecordingStore.registry["eedomus.mapping"]
        assert stored["current"] == {"custom_rules": [], "metadata": {"version": 1.0}}
        assert stored["file_fingerprint"]
        # The mirror is rewritten to the canonical dump: text == fingerprint
        assert mirror.read_text(encoding="utf-8") == stored["file_fingerprint"]

    @pytest.mark.asyncio
    async def test_identical_fingerprint_is_a_noop(self, tmp_path, monkeypatch):
        canon = {"custom_rules": []}
        import yaml as yaml_module

        fingerprint = yaml_module.safe_dump(canon, sort_keys=False, allow_unicode=True)
        manager, mirror = self.make_ingest_manager(
            tmp_path, monkeypatch, file_text=fingerprint
        )
        RecordingStore.registry["eedomus.mapping"] = {
            "current": canon,
            "file_fingerprint": fingerprint,
        }

        await manager._async_ingest_custom_mapping()

        stored = RecordingStore.registry["eedomus.mapping"]
        assert stored["current"] == canon
        versions = RecordingStore.registry.get("eedomus.mapping_versions")
        assert versions in (None, {"versions": []})

    @pytest.mark.asyncio
    async def test_manual_edit_becomes_new_version(self, tmp_path, monkeypatch):
        old = {"custom_rules": []}
        RecordingStore.registry_placeholder = None
        manager, mirror = self.make_ingest_manager(
            tmp_path, monkeypatch, file_text="custom_rules: []\n"
        )
        RecordingStore.registry["eedomus.mapping"] = {
            "current": old,
            "file_fingerprint": "custom_rules: []\n",
        }
        # The user edits the file (adds a rule, hand-written text)
        mirror.write_text(
            "custom_usage_id_mappings:\n  '7':\n    ha_entity: sensor\n"
            "    ha_subtype: temperature\n",
            encoding="utf-8",
        )

        await manager._async_ingest_custom_mapping()

        stored = RecordingStore.registry["eedomus.mapping"]
        assert stored["current"] == {
            "custom_usage_id_mappings": {
                "7": {"ha_entity": "sensor", "ha_subtype": "temperature"}
            }
        }
        assert stored["file_fingerprint"].startswith("custom_usage_id_mappings")
        versions = RecordingStore.registry["eedomus.mapping_versions"]["versions"]
        assert versions[0]["config"] == old

    @pytest.mark.asyncio
    async def test_schema_invalid_edit_keeps_canon_and_mirrors_it(
        self, tmp_path, monkeypatch
    ):
        canon = {"custom_rules": []}
        manager, mirror = self.make_ingest_manager(
            tmp_path, monkeypatch, file_text="custom_rules: []\n"
        )
        RecordingStore.registry["eedomus.mapping"] = {
            "current": canon,
            "file_fingerprint": "custom_rules: []\n",
        }
        # Invalid against the schema (ha_entity must be a string)
        mirror.write_text(
            "custom_usage_id_mappings:\n  '7':\n    ha_entity: 123\n",
            encoding="utf-8",
        )

        await manager._async_ingest_custom_mapping()

        stored = RecordingStore.registry["eedomus.mapping"]
        assert stored["current"] == canon
        # The mirror is regenerated from the canon
        assert mirror.read_text(encoding="utf-8") == "custom_rules: []\n"
        assert "eedomus.mapping_versions" not in RecordingStore.registry

    @pytest.mark.asyncio
    async def test_unparseable_file_keeps_canon(self, tmp_path, monkeypatch):
        canon = {"custom_rules": []}
        manager, mirror = self.make_ingest_manager(
            tmp_path, monkeypatch, file_text="custom_rules: []\n"
        )
        RecordingStore.registry["eedomus.mapping"] = {
            "current": canon,
            "file_fingerprint": "custom_rules: []\n",
        }
        mirror.write_text("custom_rules: [unclosed\n", encoding="utf-8")

        await manager._async_ingest_custom_mapping()

        stored = RecordingStore.registry["eedomus.mapping"]
        assert stored["current"] == canon
        assert mirror.read_text(encoding="utf-8") == "custom_rules: []\n"

    @pytest.mark.asyncio
    async def test_missing_file_is_regenerated_from_canon(self, tmp_path, monkeypatch):
        canon = {"custom_rules": []}
        manager, mirror = self.make_ingest_manager(tmp_path, monkeypatch)
        RecordingStore.registry["eedomus.mapping"] = {
            "current": canon,
            "file_fingerprint": "custom_rules: []\n",
        }

        await manager._async_ingest_custom_mapping()

        stored = RecordingStore.registry["eedomus.mapping"]
        assert stored["current"] == canon
        assert mirror.read_text(encoding="utf-8") == "custom_rules: []\n"


class TestSchemaMigrations:
    """AD-14bis: config_schema_version stamping and the migration chain."""

    def make_ingest_manager(self, tmp_path, monkeypatch):
        import custom_components.eedomus.config_manager as config_manager_module

        monkeypatch.setattr(config_manager_module, "Store", RecordingStore)
        RecordingStore.registry.clear()
        hass = MagicMock()
        hass.config = SimpleNamespace(config_dir=str(tmp_path))

        async def _exec(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        hass.async_add_executor_job = MagicMock(side_effect=_exec)
        return config_manager_module, EedomusConfigManager(hass)

    @pytest.mark.asyncio
    async def test_absent_version_is_stamped_not_migrated(self, tmp_path, monkeypatch):
        """A pre-AD-14 document is the birth version: stamped, untouched."""
        module, manager = self.make_ingest_manager(tmp_path, monkeypatch)
        canon = {"custom_rules": []}
        RecordingStore.registry["eedomus.mapping"] = {
            "current": canon,
            "file_fingerprint": "custom_rules: []\n",
        }

        await module._async_migrate_mapping_document(manager.hass)

        stored = RecordingStore.registry["eedomus.mapping"]
        assert stored["current"] == canon
        assert stored["config_schema_version"] == 1
        assert "eedomus.mapping_versions" not in RecordingStore.registry

    @pytest.mark.asyncio
    async def test_migration_chain_runs_and_archives_as_version(
        self, tmp_path, monkeypatch
    ):
        """A pending migration archives the old canon with reason=migration."""
        module, manager = self.make_ingest_manager(tmp_path, monkeypatch)
        monkeypatch.setattr(module, "MAPPING_CONFIG_SCHEMA_VERSION", 2)
        monkeypatch.setattr(
            module,
            "_MAPPING_MIGRATIONS",
            {2: lambda config: {**config, "custom_name_patterns": []}},
        )
        old = {"custom_rules": []}
        RecordingStore.registry["eedomus.mapping"] = {
            "current": old,
            "file_fingerprint": "custom_rules: []\n",
            "config_schema_version": 1,
        }

        await module._async_migrate_mapping_document(manager.hass)

        stored = RecordingStore.registry["eedomus.mapping"]
        assert stored["config_schema_version"] == 2
        assert stored["current"]["custom_name_patterns"] == []
        assert stored["current"]["custom_rules"] == []
        versions = RecordingStore.registry["eedomus.mapping_versions"]["versions"]
        assert versions[0]["config"] == old
        assert versions[0]["reason"] == "migration"
        mirror = tmp_path / "eedomus" / "custom_mapping.yaml"
        assert mirror.read_text(encoding="utf-8") == stored["file_fingerprint"]

    @pytest.mark.asyncio
    async def test_failed_migration_keeps_the_canon(self, tmp_path, monkeypatch):
        module, manager = self.make_ingest_manager(tmp_path, monkeypatch)
        monkeypatch.setattr(module, "MAPPING_CONFIG_SCHEMA_VERSION", 2)

        def _boom(config):
            raise ValueError("unsupported structure")

        monkeypatch.setattr(module, "_MAPPING_MIGRATIONS", {2: _boom})
        canon = {"custom_rules": []}
        RecordingStore.registry["eedomus.mapping"] = {
            "current": canon,
            "file_fingerprint": "custom_rules: []\n",
            "config_schema_version": 1,
        }

        await module._async_migrate_mapping_document(manager.hass)

        stored = RecordingStore.registry["eedomus.mapping"]
        assert stored["current"] == canon
        assert stored["config_schema_version"] == 1
        assert "eedomus.mapping_versions" not in RecordingStore.registry

    @pytest.mark.asyncio
    async def test_current_version_runs_nothing(self, tmp_path, monkeypatch):
        module, manager = self.make_ingest_manager(tmp_path, monkeypatch)
        RecordingStore.registry["eedomus.mapping"] = {
            "current": {"custom_rules": []},
            "file_fingerprint": "text",
            "config_schema_version": 1,
        }

        await module._async_migrate_mapping_document(manager.hass)

        assert RecordingStore.registry["eedomus.mapping"]["file_fingerprint"] == "text"
        assert "eedomus.mapping_versions" not in RecordingStore.registry

    def test_integrated_seed_is_an_example_with_header(self):
        import custom_components.eedomus.device_mapping as device_mapping_module

        seed = (
            Path(device_mapping_module.__file__).parent
            / "config"
            / ("custom_mapping.yaml.example")
        )
        assert seed.is_file()
        head = seed.read_text(encoding="utf-8")[:400]
        assert "NE PAS EDITER" in head
        # The pre-AD-14 integrated file must no longer exist as an edit target
        assert not (seed.parent / "custom_mapping.yaml").exists()


class TestIngestionPreservesSchemaVersion:
    """Retro A1 (regression): the ingestion writes must keep the
    config_schema_version stamp, or the next boot would re-stamp to the
    current version and silently skip pending migrations."""

    @pytest.mark.asyncio
    async def test_manual_edit_keeps_the_stamped_version(self, tmp_path, monkeypatch):
        import custom_components.eedomus.config_manager as config_manager_module

        monkeypatch.setattr(config_manager_module, "Store", RecordingStore)
        RecordingStore.registry.clear()
        hass = MagicMock()
        hass.config = SimpleNamespace(config_dir=str(tmp_path))

        async def _exec(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        hass.async_add_executor_job = MagicMock(side_effect=_exec)
        manager = EedomusConfigManager(hass)

        canon = {"custom_rules": []}
        RecordingStore.registry["eedomus.mapping"] = {
            "current": canon,
            "file_fingerprint": "custom_rules: []\n",
            "config_schema_version": 1,
        }
        mirror = tmp_path / "eedomus" / "custom_mapping.yaml"
        mirror.parent.mkdir(parents=True)
        mirror.write_text(
            "custom_usage_id_mappings:\n  '7':\n    ha_entity: sensor\n",
            encoding="utf-8",
        )
        import custom_components.eedomus.device_mapping as device_mapping_module

        monkeypatch.setattr(
            device_mapping_module,
            "get_custom_mapping_paths",
            lambda: [str(mirror)],
        )

        await config_manager_module.async_ingest_custom_mapping(hass)

        stored = RecordingStore.registry["eedomus.mapping"]
        assert stored["config_schema_version"] == 1
        assert (
            stored["current"]["custom_usage_id_mappings"]["7"]["ha_entity"] == "sensor"
        )

    @pytest.mark.asyncio
    async def test_bootstrap_stamps_the_version(self, tmp_path, monkeypatch):
        import custom_components.eedomus.config_manager as config_manager_module

        monkeypatch.setattr(config_manager_module, "Store", RecordingStore)
        RecordingStore.registry.clear()
        hass = MagicMock()
        hass.config = SimpleNamespace(config_dir=str(tmp_path))

        async def _exec(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        hass.async_add_executor_job = MagicMock(side_effect=_exec)

        mirror = tmp_path / "eedomus" / "custom_mapping.yaml"
        mirror.parent.mkdir(parents=True)
        mirror.write_text("custom_rules: []\n", encoding="utf-8")
        import custom_components.eedomus.device_mapping as device_mapping_module

        monkeypatch.setattr(
            device_mapping_module,
            "get_custom_mapping_paths",
            lambda: [str(mirror)],
        )

        await config_manager_module.async_ingest_custom_mapping(hass)

        stored = RecordingStore.registry["eedomus.mapping"]
        assert stored["config_schema_version"] == 1
        assert stored["current"] == {"custom_rules": []}


@pytest.mark.asyncio
async def test_both_canonical_readers_return_the_same_storage_dict(
    manager, monkeypatch
):
    """Story 103: the badge path (config_manager.async_get_custom_mapping)
    and the bootstrap reader (device_mapping.async_get_canonical_custom_
    mapping) read the same eedomus.mapping storage and must return the
    same dict - the two paths can never diverge silently."""
    canon = {
        "custom_usage_id_mappings": {
            "7": {"ha_entity": "sensor", "ha_subtype": "temperature"}
        }
    }
    # Seed both store registries: the config manager reads through the
    # manager's patched Store, the device_mapping reader through the
    # conftest's homeassistant.helpers.storage.Store stub.
    RecordingStore.registry["eedomus.mapping"] = {"current": canon}
    from homeassistant.helpers.storage import Store

    Store.registry["eedomus.mapping"] = {"current": canon}

    config_manager, _ = manager

    from custom_components.eedomus.device_mapping import (
        async_get_canonical_custom_mapping,
    )

    via_config_manager = await config_manager.async_get_custom_mapping()
    via_device_mapping = await async_get_canonical_custom_mapping(
        config_manager.hass
    )

    assert via_config_manager == canon
    assert via_device_mapping == canon
    assert via_config_manager == via_device_mapping
