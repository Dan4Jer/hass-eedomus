"""Unit tests for the panel WebSocket service (ui_service.py).

Covers the P.1.1 fix: the websocket handlers must actually respond on the
client connection (send_result / send_error) instead of returning dicts,
and registration must not assume async_register_command returns a
deregistration handle (it returns None in HA 2026).

The P.1.3 tests cover eedomus/get_peripherals: coordinator.data projected
into JSON-safe rows with the current mapping (live HA state) and the
accessible "modified" badge (custom rule name + date).
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import custom_components.eedomus.device_mapping as device_mapping_module
import custom_components.eedomus.ui_service as ui_service_module
from custom_components.eedomus.const import COORDINATOR
from custom_components.eedomus.ui_service import (
    WS_TYPE_EEDOMUS_CACHE_STATS,
    WS_TYPE_EEDOMUS_SCHEMA,
    WS_TYPE_EEDOMUS_SUGGESTIONS,
    WS_TYPE_EEDOMUS_VALIDATE,
    EedomusUIService,
)

pytestmark = pytest.mark.unit


def make_service(domain_data=None):
    """Build a UIService with a fake hass and a mock connection."""
    hass = MagicMock()
    hass.data = {"eedomus": domain_data if domain_data is not None else {}}
    service = EedomusUIService(hass)
    connection = MagicMock()
    return service, connection


class TestAsyncInit:
    @pytest.mark.asyncio
    async def test_registers_all_four_commands_once(self, monkeypatch):
        """async_register_command is called once per command, no handle kept.

        Registration uses the handler form: the command type and schema are
        read from the handler's _ws_command/_ws_schema attributes (set by the
        @websocket_command decorators), so only the handler is passed.
        """
        service, _ = make_service()
        register = MagicMock(return_value=None)
        monkeypatch.setattr(ui_service_module, "async_register_command", register)

        await service.async_init()

        assert register.call_count == 7
        # Handler form: (hass, handler) on the module-level dispatchers -
        # HA calls websocket handlers as plain (hass, connection, msg)
        # functions, so bound methods cannot be dispatched directly
        assert all(call.args[0] is service.hass for call in register.call_args_list)
        handlers = [call.args[1] for call in register.call_args_list]
        assert handlers == [
            ui_service_module._ws_validate_config,
            ui_service_module._ws_get_suggestions,
            ui_service_module._ws_get_schema,
            ui_service_module._ws_get_cache_stats,
            ui_service_module._ws_get_peripherals,
            ui_service_module._ws_get_mapping,
            ui_service_module._ws_save_mapping,
        ]
        assert service._registered_commands == [
            WS_TYPE_EEDOMUS_VALIDATE,
            WS_TYPE_EEDOMUS_SUGGESTIONS,
            WS_TYPE_EEDOMUS_SCHEMA,
            WS_TYPE_EEDOMUS_CACHE_STATS,
            ui_service_module.WS_TYPE_EEDOMUS_PERIPHERALS,
            ui_service_module.WS_TYPE_EEDOMUS_GET_MAPPING,
            ui_service_module.WS_TYPE_EEDOMUS_SAVE_MAPPING,
        ]
        assert service.is_initialized() is True

    @pytest.mark.asyncio
    async def test_registration_failure_leaves_service_uninitialized(self, monkeypatch):
        """A registration error must not crash setup (limited mode)."""
        service, _ = make_service()
        register = MagicMock(side_effect=RuntimeError("already registered"))
        monkeypatch.setattr(ui_service_module, "async_register_command", register)

        await service.async_init()

        assert service.is_initialized() is False

    @pytest.mark.asyncio
    async def test_no_websocket_api_runs_in_limited_mode(self, monkeypatch):
        """Without websocket_api the service reports initialized, registers nothing."""
        service, _ = make_service()
        monkeypatch.setattr(ui_service_module, "async_register_command", None)

        await service.async_init()

        assert service.is_initialized() is True
        assert service._registered_commands == []

    @pytest.mark.asyncio
    async def test_retried_init_does_not_duplicate_registered_commands(
        self, monkeypatch
    ):
        """A retry resets the tracked command list instead of appending."""
        service, _ = make_service()
        register = MagicMock(return_value=None)
        monkeypatch.setattr(ui_service_module, "async_register_command", register)

        await service.async_init()
        first = list(service._registered_commands)
        await service.async_init()

        assert service._registered_commands == first
        assert register.call_count == 14

    @pytest.mark.asyncio
    async def test_shutdown_resets_state_without_unregistering(self):
        """async_shutdown only resets local state - commands stay registered."""
        service, _ = make_service()
        service._registered_commands = [WS_TYPE_EEDOMUS_VALIDATE]
        service._initialized = True

        await service.async_shutdown()

        assert service._registered_commands == []
        assert service.is_initialized() is False


class TestValidateConfigHandler:
    @pytest.mark.asyncio
    async def test_success_sends_result(self):
        schema_service = MagicMock()
        schema_service.validate_yaml_content = MagicMock(
            return_value=(True, {"custom_devices": []})
        )
        service, connection = make_service({"schema_service": schema_service})

        await service._handle_validate_config(
            service.hass,
            connection,
            {"id": 7, "yaml_content": "custom_devices: []"},
        )

        connection.send_result.assert_called_once_with(
            7, {"valid": True, "validated_config": {"custom_devices": []}}
        )
        connection.send_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_content_sends_error_with_type(self):
        schema_service = MagicMock()
        schema_service.validate_yaml_content = MagicMock(
            return_value=(False, {"error": "bad yaml", "type": "yaml_error"})
        )
        service, connection = make_service({"schema_service": schema_service})

        await service._handle_validate_config(
            service.hass, connection, {"id": 7, "yaml_content": "!!!"}
        )

        connection.send_error.assert_called_once_with(7, "yaml_error", "bad yaml")
        connection.send_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_schema_service_sends_error(self):
        service, connection = make_service({})

        await service._handle_validate_config(
            service.hass, connection, {"id": 3, "yaml_content": ""}
        )

        connection.send_error.assert_called_once_with(
            3, "service_unavailable", "SchemaService not available"
        )

    @pytest.mark.asyncio
    async def test_exception_sends_error(self):
        schema_service = MagicMock()
        schema_service.validate_yaml_content = MagicMock(
            side_effect=RuntimeError("boom")
        )
        service, connection = make_service({"schema_service": schema_service})

        await service._handle_validate_config(
            service.hass, connection, {"id": 7, "yaml_content": ""}
        )

        connection.send_error.assert_called_once_with(7, "error", "boom")


class TestGetSuggestionsHandler:
    @pytest.mark.asyncio
    async def test_success_sends_result(self):
        schema_service = MagicMock()
        schema_service.get_dynamic_suggestions = AsyncMock(
            return_value=[{"value": "light", "label": "light"}]
        )
        service, connection = make_service({"schema_service": schema_service})

        await service._handle_get_suggestions(
            service.hass,
            connection,
            {"id": 9, "field_type": "device_type", "query": "li", "context": {}},
        )

        connection.send_result.assert_called_once_with(
            9,
            {
                "suggestions": [{"value": "light", "label": "light"}],
                "field_type": "device_type",
                "query": "li",
            },
        )
        schema_service.get_dynamic_suggestions.assert_awaited_once_with(
            "device_type", "li", {}
        )

    @pytest.mark.asyncio
    async def test_missing_schema_service_sends_error(self):
        service, connection = make_service({})

        await service._handle_get_suggestions(
            service.hass, connection, {"id": 9, "field_type": "device_type"}
        )

        connection.send_error.assert_called_once_with(
            9, "service_unavailable", "SchemaService not available"
        )


class TestGetSchemaHandler:
    @pytest.mark.asyncio
    async def test_full_schema_sends_result(self):
        schema_service = MagicMock()
        schema_service.get_schema_version = MagicMock(return_value="1.1.0")
        schema_service.generate_schema_documentation = MagicMock(
            return_value={"sections": {}}
        )
        service, connection = make_service({"schema_service": schema_service})

        await service._handle_get_schema(service.hass, connection, {"id": 4})

        connection.send_result.assert_called_once_with(
            4, {"schema_version": "1.1.0", "documentation": {"sections": {}}}
        )

    @pytest.mark.asyncio
    async def test_section_found_sends_result(self):
        schema_service = MagicMock()
        schema_service._get_section_schema = MagicMock(return_value="SECTION_SCHEMA")
        service, connection = make_service({"schema_service": schema_service})

        await service._handle_get_schema(
            service.hass, connection, {"id": 4, "section": "custom_devices"}
        )

        connection.send_result.assert_called_once_with(
            4, {"section": "custom_devices", "schema": "SECTION_SCHEMA"}
        )

    @pytest.mark.asyncio
    async def test_unknown_section_sends_error(self):
        schema_service = MagicMock()
        schema_service._get_section_schema = MagicMock(return_value=None)
        service, connection = make_service({"schema_service": schema_service})

        await service._handle_get_schema(
            service.hass, connection, {"id": 4, "section": "nope"}
        )

        connection.send_error.assert_called_once_with(
            4, "not_found", "Section 'nope' not found"
        )


class TestGetCacheStatsHandler:
    @pytest.mark.asyncio
    async def test_success_sends_result(self):
        data_service = MagicMock()
        data_service.get_cache_stats = MagicMock(
            return_value={"refresh_count": 3, "devices": 10}
        )
        service, connection = make_service({"data_service": data_service})

        await service._handle_get_cache_stats(service.hass, connection, {"id": 2})

        connection.send_result.assert_called_once()
        call_args = connection.send_result.call_args
        assert call_args.args[0] == 2
        payload = call_args.args[1]
        assert payload["cache_stats"] == {"refresh_count": 3, "devices": 10}
        assert "timestamp" in payload

    @pytest.mark.asyncio
    async def test_missing_data_service_sends_error(self):
        service, connection = make_service({})

        await service._handle_get_cache_stats(service.hass, connection, {"id": 2})

        connection.send_error.assert_called_once_with(
            2, "service_unavailable", "DataService not available"
        )


class TestDirectCallHelpers:
    """The *_via_websocket helpers reuse the handlers via a capture connection."""

    @pytest.mark.asyncio
    async def test_validate_config_via_websocket_success(self):
        schema_service = MagicMock()
        schema_service.validate_yaml_content = MagicMock(return_value=(True, {"x": 1}))
        service, _ = make_service({"schema_service": schema_service})

        result = await service.validate_config_via_websocket("x: 1")

        assert result == {
            "type": "result",
            "success": True,
            "result": {"valid": True, "validated_config": {"x": 1}},
        }

    @pytest.mark.asyncio
    async def test_validate_config_via_websocket_error_shape(self):
        service, _ = make_service({})

        result = await service.validate_config_via_websocket("x: 1")

        assert result["success"] is False
        assert result["error"] == "SchemaService not available"
        assert result["error_type"] == "service_unavailable"

    @pytest.mark.asyncio
    async def test_get_suggestions_via_websocket_success(self):
        schema_service = MagicMock()
        schema_service.get_dynamic_suggestions = AsyncMock(
            return_value=[{"value": "light", "label": "light"}]
        )
        service, _ = make_service({"schema_service": schema_service})

        result = await service.get_suggestions_via_websocket("device_type", "li")

        assert result["success"] is True
        assert result["result"]["suggestions"] == [{"value": "light", "label": "light"}]


class TestGetPeripheralsHandler:
    """P.1.3: the Périphériques tab reads coordinator.data through the
    eedomus/get_peripherals command, with the modified badge driven by the
    raw custom mapping (never the merged config, which mixes in the
    default mapping and would flag every peripheral)."""

    CUSTOM_CONFIG = {
        "custom_usage_id_mappings": {"24": {"ha_entity": "sensor.humidite"}},
        "custom_rules": [
            {
                "name": "Unité température salon",
                "condition": {"usage_id": "7", "state": "any"},
                "actions": [{"type": "override", "attributes": {}}],
            }
        ],
        "metadata": {"last_modified": "2026-09-26 21:04"},
    }

    def make_coordinator(self):
        coordinator = MagicMock()
        coordinator.data = {
            "111": {
                "periph_id": "111",
                "name": "Température Salon",
                "usage_id": "7",
            },
            "222": {
                "periph_id": "222",
                "name": "Humidité Salle de bain",
                "usage_id": "24",
            },
            "333": {
                "periph_id": "333",
                "name": "RubanLED Salon",
                "usage_id": "133",
            },
        }
        coordinator._resolve_main_entity_id = MagicMock(
            side_effect=lambda pid: {
                "111": "sensor.temperature_salon",
                "222": "sensor.humidite_salle_de_bain",
            }.get(pid)
        )
        return coordinator

    def make_hass(self, coordinator):
        hass = MagicMock()
        hass.data = {"eedomus": {"entry_1": {COORDINATOR: coordinator}}}
        hass.states.get = MagicMock(
            side_effect=lambda entity_id: {
                "sensor.temperature_salon": SimpleNamespace(
                    attributes={
                        "device_class": "temperature",
                        "unit_of_measurement": "°C",
                    }
                ),
                "sensor.humidite_salle_de_bain": SimpleNamespace(
                    attributes={"device_class": "humidity", "unit_of_measurement": "%"}
                ),
            }.get(entity_id)
        )
        return hass

    def patch_custom_mapping(self, monkeypatch, config=None, side_effect=None):
        """Patch the raw custom mapping loader used by the handler."""
        loader = AsyncMock(
            return_value=self.CUSTOM_CONFIG if config is None else config
        )
        if side_effect is not None:
            loader.side_effect = side_effect
        monkeypatch.setattr(
            device_mapping_module, "load_custom_yaml_mappings_async", loader
        )
        return loader

    @pytest.mark.asyncio
    async def test_projects_rows_with_current_mapping(self, monkeypatch):
        coordinator = self.make_coordinator()
        hass = self.make_hass(coordinator)
        service = EedomusUIService(hass)
        connection = MagicMock()
        self.patch_custom_mapping(monkeypatch)

        await service._handle_get_peripherals(hass, connection, {"id": 5})

        result = connection.send_result.call_args.args[1]
        assert result["total"] == 3
        row = result["peripherals"][0]
        assert row == {
            "periph_id": "111",
            "name": "Température Salon",
            "usage_id": "7",
            "entity_id": "sensor.temperature_salon",
            "platform": "sensor",
            "device_class": "temperature",
            "unit": "°C",
            "modified": True,
            "modified_by_rule": "Unité température salon",
            "modified_date": "2026-09-26 21:04",
        }

    @pytest.mark.asyncio
    async def test_badge_distinguishes_rule_and_plain_mapping(self, monkeypatch):
        coordinator = self.make_coordinator()
        hass = self.make_hass(coordinator)
        service = EedomusUIService(hass)
        connection = MagicMock()
        self.patch_custom_mapping(monkeypatch)

        await service._handle_get_peripherals(hass, connection, {"id": 5})

        rows = {
            row["periph_id"]: row
            for row in connection.send_result.call_args.args[1]["peripherals"]
        }
        # usage_id 24 -> direct usage_id mapping (no named rule)
        assert rows["222"]["modified"] is True
        assert rows["222"]["modified_by_rule"] == "mapping personnalisé 24"
        # usage_id 133 -> untouched
        assert rows["333"]["modified"] is False
        assert rows["333"]["modified_by_rule"] is None
        assert rows["333"]["modified_date"] is None

    @pytest.mark.asyncio
    async def test_default_mapping_entries_are_not_modified(self, monkeypatch):
        """The badge must not light up from the default mapping."""
        coordinator = self.make_coordinator()
        hass = self.make_hass(coordinator)
        service = EedomusUIService(hass)
        connection = MagicMock()
        # Only the custom file content drives the badge: an empty custom
        # mapping means no peripheral is touched, whatever the default
        # mapping contains.
        self.patch_custom_mapping(monkeypatch, config={})

        await service._handle_get_peripherals(hass, connection, {"id": 5})

        rows = connection.send_result.call_args.args[1]["peripherals"]
        assert all(row["modified"] is False for row in rows)
        assert all(row["modified_by_rule"] is None for row in rows)

    @pytest.mark.asyncio
    async def test_payload_is_json_serializable(self, monkeypatch):
        coordinator = self.make_coordinator()
        hass = self.make_hass(coordinator)
        service = EedomusUIService(hass)
        connection = MagicMock()
        self.patch_custom_mapping(monkeypatch)

        await service._handle_get_peripherals(hass, connection, {"id": 5})

        json.dumps(connection.send_result.call_args.args[1])

    @pytest.mark.asyncio
    async def test_unresolved_entity_yields_empty_mapping(self, monkeypatch):
        coordinator = self.make_coordinator()
        coordinator._resolve_main_entity_id.return_value = None
        coordinator._resolve_main_entity_id.side_effect = None
        hass = self.make_hass(coordinator)
        service = EedomusUIService(hass)
        connection = MagicMock()
        self.patch_custom_mapping(monkeypatch)

        await service._handle_get_peripherals(hass, connection, {"id": 5})

        rows = {
            row["periph_id"]: row
            for row in connection.send_result.call_args.args[1]["peripherals"]
        }
        assert rows["111"]["entity_id"] is None
        assert rows["111"]["platform"] is None
        assert rows["111"]["device_class"] is None
        assert rows["111"]["unit"] is None

    @pytest.mark.asyncio
    async def test_custom_mapping_load_failure_degrades_to_unmodified(
        self, monkeypatch
    ):
        coordinator = self.make_coordinator()
        hass = self.make_hass(coordinator)
        service = EedomusUIService(hass)
        connection = MagicMock()
        self.patch_custom_mapping(monkeypatch, side_effect=Exception("file not found"))

        await service._handle_get_peripherals(hass, connection, {"id": 5})

        rows = connection.send_result.call_args.args[1]["peripherals"]
        assert all(row["modified"] is False for row in rows)

    @pytest.mark.asyncio
    async def test_no_coordinator_entries_returns_empty_list(self, monkeypatch):
        service, connection = make_service({})
        connection.send_result = MagicMock()
        self.patch_custom_mapping(monkeypatch)

        await service._handle_get_peripherals(service.hass, connection, {"id": 5})

        result = connection.send_result.call_args.args[1]
        assert result == {"peripherals": [], "total": 0}

    @pytest.mark.asyncio
    async def test_exception_sends_error(self):
        hass = MagicMock()
        hass.data = {"eedomus": {"entry_1": {COORDINATOR: "not-a-coordinator"}}}
        service = EedomusUIService(hass)
        connection = MagicMock()

        await service._handle_get_peripherals(hass, connection, {"id": 5})

        connection.send_error.assert_called_once()
        connection.send_result.assert_not_called()


class TestMappingHandlers:
    """P.1.4: the Regles tab reads the custom mapping through
    eedomus/get_mapping and persists + auto-applies through
    eedomus/save_mapping (every eedomus entry is reloaded)."""

    def make_manager(self):
        manager = MagicMock()
        manager.async_get_custom_mapping = AsyncMock(
            return_value={"custom_rules": [], "custom_usage_id_mappings": {}}
        )
        manager.async_save_custom_mapping = AsyncMock(
            return_value={
                "success": True,
                "error": None,
                "path": "/config/eedomus/custom_mapping.yaml",
            }
        )
        return manager

    def make_save_hass(self, manager):
        hass = MagicMock()
        hass.data = {"eedomus": {"config_manager": manager}}
        entry = MagicMock()
        entry.entry_id = "entry_1"
        hass.config_entries.async_entries = MagicMock(return_value=[entry])
        hass.config_entries.async_reload = AsyncMock()
        return hass

    @pytest.mark.asyncio
    async def test_get_mapping_returns_raw_custom_mapping(self):
        manager = self.make_manager()
        hass = MagicMock()
        hass.data = {"eedomus": {"config_manager": manager}}
        service = EedomusUIService(hass)
        connection = MagicMock()

        await service._handle_get_mapping(hass, connection, {"id": 6})

        connection.send_result.assert_called_once_with(
            6,
            {"mapping": {"custom_rules": [], "custom_usage_id_mappings": {}}},
        )

    @pytest.mark.asyncio
    async def test_get_mapping_without_manager_sends_error(self):
        service, connection = make_service({})

        await service._handle_get_mapping(service.hass, connection, {"id": 6})

        connection.send_error.assert_called_once_with(
            6, "service_unavailable", "ConfigManager not available"
        )

    @pytest.mark.asyncio
    async def test_save_persists_then_reloads_every_entry(self):
        manager = self.make_manager()
        hass = self.make_save_hass(manager)
        service = EedomusUIService(hass)
        connection = MagicMock()
        mapping = {"custom_usage_id_mappings": {"7": {"ha_entity": "sensor"}}}

        await service._handle_save_mapping(
            hass, connection, {"id": 7, "mapping": mapping}
        )

        manager.async_save_custom_mapping.assert_awaited_once_with(mapping)
        hass.config_entries.async_reload.assert_awaited_once_with("entry_1")
        result = connection.send_result.call_args.args[1]
        assert result == {
            "saved": True,
            "path": "/config/eedomus/custom_mapping.yaml",
            "reloaded_entries": 1,
        }

    @pytest.mark.asyncio
    async def test_save_does_not_reload_on_validation_error(self):
        manager = self.make_manager()
        manager.async_save_custom_mapping = AsyncMock(
            return_value={"success": False, "error": "not a valid option", "path": None}
        )
        hass = self.make_save_hass(manager)
        service = EedomusUIService(hass)
        connection = MagicMock()

        await service._handle_save_mapping(
            hass,
            connection,
            {"id": 7, "mapping": {"custom_usage_id_mappings": {"x": {}}}},
        )

        connection.send_error.assert_called_once_with(
            7, "validation_error", "not a valid option"
        )
        hass.config_entries.async_reload.assert_not_awaited()
        connection.send_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_without_manager_sends_error(self):
        service, connection = make_service({})

        await service._handle_save_mapping(
            service.hass, connection, {"id": 7, "mapping": {}}
        )

        connection.send_error.assert_called_once_with(
            7, "service_unavailable", "ConfigManager not available"
        )
