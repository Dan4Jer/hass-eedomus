"""Unit tests for the panel WebSocket service (ui_service.py).

Covers the P.1.1 fix: the websocket handlers must actually respond on the
client connection (send_result / send_error) instead of returning dicts,
and registration must not assume async_register_command returns a
deregistration handle (it returns None in HA 2026).

The P.1.3 tests cover eedomus/get_peripherals: coordinator.data projected
into JSON-safe rows with the current mapping (live HA state) and the
accessible "modified" badge (custom rule name + date).

The CAP-6 tests cover eedomus/get_coherence: the fused per-peripheral view
(registry x live state x raw data x coherence signals) that feeds the
Cohérence tab, while the eedomus/get_peripherals response shape stays
frozen.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol

import custom_components.eedomus.device_mapping as device_mapping_module
import custom_components.eedomus.mapping_registry as mapping_registry_module
import custom_components.eedomus.panel_translations as panel_translations_module
import custom_components.eedomus.ui_service as ui_service_module
from custom_components.eedomus.const import COORDINATOR
from custom_components.eedomus.ui_service import (
    SIGNAL_DOUTEUX,
    SIGNAL_EN_ERREUR,
    SIGNAL_REGLE_ACTIVE,
    SIGNAL_SANS_ENTITE,
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

        assert register.call_count == 9
        # Handler form: (hass, handler) on the module-level dispatchers -
        # HA calls websocket handlers as plain (hass, connection, msg)
        # functions, so bound methods cannot be dispatched directly
        assert all(call.args[0] is service.hass for call in register.call_args_list)
        handlers = [call.args[1] for call in register.call_args_list]
        assert handlers == [
            ui_service_module._ws_validate_config,
            ui_service_module._ws_get_suggestions,
            ui_service_module._ws_get_schema,
            ui_service_module._ws_get_peripherals,
            ui_service_module._ws_get_mapping,
            ui_service_module._ws_save_mapping,
            ui_service_module._ws_get_mapping_versions,
            ui_service_module._ws_get_coherence,
            ui_service_module._ws_get_translations,
        ]
        assert service._registered_commands == [
            WS_TYPE_EEDOMUS_VALIDATE,
            WS_TYPE_EEDOMUS_SUGGESTIONS,
            WS_TYPE_EEDOMUS_SCHEMA,
            ui_service_module.WS_TYPE_EEDOMUS_PERIPHERALS,
            ui_service_module.WS_TYPE_EEDOMUS_GET_MAPPING,
            ui_service_module.WS_TYPE_EEDOMUS_SAVE_MAPPING,
            ui_service_module.WS_TYPE_EEDOMUS_GET_VERSIONS,
            ui_service_module.WS_TYPE_EEDOMUS_GET_COHERENCE,
            ui_service_module.WS_TYPE_EEDOMUS_GET_TRANSLATIONS,
        ]
        assert service.is_initialized() is True

    def test_get_translations_handler_declares_its_ws_contract(self):
        """The dispatcher must carry its command type and a locale
        schema that admits an explicit null (served as the English
        catalog) while a malformed non-string value stays a schema
        error - standard HA message validation."""
        handler = ui_service_module._ws_get_translations
        assert handler._ws_command == (
            ui_service_module.WS_TYPE_EEDOMUS_GET_TRANSLATIONS
        )
        schema = handler._ws_schema
        locale_marker = next(
            key for key in schema if getattr(key, "schema", None) == "locale"
        )
        assert isinstance(locale_marker, vol.Optional)
        # voluptuous wraps a non-callable default in a factory.
        default = locale_marker.default
        assert (default() if callable(default) else default) == ""
        validator = schema[locale_marker]
        assert validator(None) is None
        assert validator("fr") == "fr"
        # A malformed non-string value stays a schema error.
        with pytest.raises(vol.Invalid):
            validator(123)


class TestGetAvailableEndpoints:
    """get_available_endpoints is DERIVED from WS_COMMANDS: a command
    registered in WS_COMMANDS must appear in the list (in registration
    order), and a command without an ENDPOINT_DESCRIPTIONS entry fails
    loudly (KeyError) instead of silently missing from the list."""

    @pytest.mark.asyncio
    async def test_endpoint_list_derives_from_ws_commands(self):
        service, _ = make_service()

        endpoints = await service.get_available_endpoints()

        assert [e["endpoint"] for e in endpoints] == [
            command_type for command_type, _handler in ui_service_module.WS_COMMANDS
        ]
        for endpoint in endpoints:
            assert set(endpoint) == {"name", "endpoint", "description"}
            assert endpoint["name"]
            assert endpoint["description"]

    def test_every_ws_command_has_an_endpoint_description(self):
        """The strict lookup behind the derivation stays green: a new
        WS command registered without a description entry would crash
        get_available_endpoints - this pin names the missing entry
        before it ships."""
        described = set(ui_service_module.ENDPOINT_DESCRIPTIONS)
        registered = {
            command_type for command_type, _handler in ui_service_module.WS_COMMANDS
        }
        assert described == registered

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
        assert register.call_count == 18

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
            },
            {
                "condition": {"usage_id": "42", "state": "any"},
                "actions": [{"type": "override", "attributes": {}}],
            },
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
            "444": {
                "periph_id": "444",
                "name": "Prise Salon",
                "usage_id": "42",
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
        assert result["total"] == 4
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
        assert rows["222"]["modified_by_rule"] == "custom mapping 24"
        # usage_id 42 -> named rule with no name falls back to "rule {key}"
        assert rows["444"]["modified"] is True
        assert rows["444"]["modified_by_rule"] == "rule 42"
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


class TestProjectCoordinatorWithRaw:
    """Sweep: the raw section rides the shared projection (with_raw).

    Pins the refactor's edge contract: _raw exists only in the with_raw
    path, is the exact coordinator entry, a non-dict coordinator value
    yields no row (the projection's dict skip still guards the attach),
    and the get_peripherals row shape stays frozen without _raw.
    """

    def make_coordinator(self):
        coordinator = MagicMock()
        coordinator.data = {
            "111": {
                "periph_id": "111",
                "name": "Température Salon",
                "usage_id": "7",
            },
            "999": "not-a-dict",
        }
        coordinator._resolve_main_entity_id = MagicMock(return_value=None)
        return coordinator

    def make_hass(self, coordinator):
        hass = MagicMock()
        hass.data = {"eedomus": {"entry_1": {COORDINATOR: coordinator}}}
        hass.states.get = MagicMock(return_value=None)
        return hass

    def project(self, with_raw=False):
        coordinator = self.make_coordinator()
        hass = self.make_hass(coordinator)
        service = EedomusUIService(hass)
        rows = service._project_coordinator(hass, coordinator, {}, with_raw=with_raw)
        return coordinator, rows

    def test_raw_rides_only_the_with_raw_path(self):
        _, plain = self.project()
        _, with_raw = self.project(with_raw=True)

        assert [row["periph_id"] for row in plain] == ["111"]
        assert [row["periph_id"] for row in with_raw] == ["111"]
        assert all("_raw" not in row for row in plain)
        assert all("_raw" in row for row in with_raw)

    def test_raw_is_the_exact_coordinator_entry(self):
        coordinator, rows = self.project(with_raw=True)

        assert rows[0]["_raw"] is coordinator.data["111"]

    def test_non_dict_value_yields_no_row(self):
        _, plain = self.project()
        _, with_raw = self.project(with_raw=True)

        assert [row["periph_id"] for row in plain] == ["111"]
        assert [row["periph_id"] for row in with_raw] == ["111"]

    @pytest.mark.asyncio
    async def test_get_peripherals_rows_never_carry_raw(self, monkeypatch):
        coordinator = self.make_coordinator()
        hass = self.make_hass(coordinator)
        service = EedomusUIService(hass)
        connection = MagicMock()
        monkeypatch.setattr(
            device_mapping_module,
            "load_custom_yaml_mappings_async",
            AsyncMock(return_value={}),
        )

        await service._handle_get_peripherals(hass, connection, {"id": 5})

        rows = connection.send_result.call_args.args[1]["peripherals"]
        assert [row["periph_id"] for row in rows] == ["111"]
        assert all("_raw" not in row for row in rows)


class TestGetCoherenceHandler:
    """CAP-6: the Cohérence tab reads a fused view of every peripheral
    through eedomus/get_coherence — registry fields joined by periph_id,
    living state, raw coordinator data and the derived signals — while
    the eedomus/get_peripherals contract stays frozen."""

    # The 10 keys of the frozen eedomus/get_peripherals row contract.
    PERIPHERALS_ROW_KEYS = frozenset(
        {
            "periph_id",
            "name",
            "usage_id",
            "entity_id",
            "platform",
            "device_class",
            "unit",
            "modified",
            "modified_by_rule",
            "modified_date",
        }
    )
    COHERENCE_EXTRA_KEYS = frozenset(
        {
            "ha_entity",
            "ha_subtype",
            "parent_periph_id",
            "justification",
            "state",
            "last_update",
            "raw",
            "signals",
            "error_message",
            "attempts",
            "retry_after",
        }
    )

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
                # Datetimes can leak into coordinator.data (history
                # imports): the raw section must serialize them.
                "last_seen": datetime(2026, 10, 1, 12, 0),
            },
            "222": {
                "periph_id": "222",
                "name": "Humidité Salle de bain",
                "usage_id": "24",
            },
            "333": {"periph_id": "333", "name": "RubanLED Salon", "usage_id": "133"},
            "444": {"periph_id": "444", "name": "Capteur CO2", "usage_id": "150"},
            "555": {"periph_id": "555", "name": "Énergie", "usage_id": "200"},
            "777": {"periph_id": "777", "name": "Sonnette", "usage_id": "7"},
        }
        # 555 is inside its retry window (active error); 777 is past it
        # (stale: the coordinator never purges, so it must NOT flag).
        coordinator._retry_queue = {
            "555": {
                "error_time": time.time() - 60,
                "retry_after": time.time() + 3600,
                "error_message": "API rate limit",
                "attempts": 1,
            },
            "777": {
                "error_time": time.time() - 90000,
                "retry_after": time.time() - 3600,
                "error_message": "API rate limit",
                "attempts": 2,
            },
        }
        coordinator._resolve_main_entity_id = MagicMock(
            side_effect=lambda pid: {
                "111": "sensor.temperature_salon",
                "222": "sensor.humidite_salle_de_bain",
                "444": "sensor.co2",
                "555": "sensor.energie",
            }.get(pid)
        )
        return coordinator

    def make_hass(self, coordinator):
        hass = MagicMock()
        hass.data = {"eedomus": {"entry_1": {COORDINATOR: coordinator}}}
        hass.states.get = MagicMock(
            side_effect=lambda entity_id: {
                "sensor.temperature_salon": SimpleNamespace(
                    state="21.5",
                    last_updated=datetime(2026, 10, 2, 8, 30),
                    attributes={
                        "device_class": "temperature",
                        "unit_of_measurement": "°C",
                    },
                ),
                "sensor.co2": SimpleNamespace(
                    state="812",
                    last_updated=datetime(2026, 10, 2, 8, 30),
                    # Living sensor without unit: doubtful mapping.
                    attributes={"device_class": "carbon_dioxide"},
                ),
                "sensor.energie": SimpleNamespace(
                    state="1.4",
                    last_updated=datetime(2026, 10, 2, 8, 30),
                    attributes={
                        "device_class": "power",
                        "unit_of_measurement": "kW",
                    },
                ),
            }.get(entity_id)
        )
        return hass

    def patch_registry(self, monkeypatch):
        """Populate the global mapping registry (only mapped periphs)."""
        monkeypatch.setattr(
            mapping_registry_module,
            "_MAPPING_REGISTRY",
            [
                {
                    "periph_id": "111",
                    "periph_name": "Température Salon",
                    "parent_periph_id": "999",
                    "ha_entity": "sensor",
                    "ha_subtype": "temperature",
                    "justification": "usage_id 7 = température",
                },
                {
                    "periph_id": "555",
                    "periph_name": "Énergie",
                    "parent_periph_id": None,
                    "ha_entity": "sensor",
                    "ha_subtype": "power",
                    "justification": "compteur électrique",
                },
            ],
        )

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

    async def fetch_rows(self, monkeypatch, coordinator=None):
        """Run eedomus/get_coherence and return the response payload."""
        if coordinator is None:
            coordinator = self.make_coordinator()
        hass = self.make_hass(coordinator)
        service = EedomusUIService(hass)
        connection = MagicMock()
        self.patch_registry(monkeypatch)
        self.patch_custom_mapping(monkeypatch)

        await service._handle_get_coherence(hass, connection, {"id": 11})

        connection.send_result.assert_called_once()
        return connection.send_result.call_args.args[1]

    @pytest.mark.asyncio
    async def test_full_join_locks_row_contract(self, monkeypatch):
        """A mapped, healthy, rule-driven peripheral carries all sections."""
        result = await self.fetch_rows(monkeypatch)

        assert result["total"] == 6
        rows = {row["periph_id"]: row for row in result["peripherals"]}
        assert rows["111"] == {
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
            "ha_entity": "sensor",
            "ha_subtype": "temperature",
            "parent_periph_id": "999",
            "justification": "usage_id 7 = température",
            "state": "21.5",
            "last_update": "2026-10-02T08:30:00",
            "raw": {
                "periph_id": "111",
                "name": "Température Salon",
                "usage_id": "7",
                "last_seen": "2026-10-01T12:00:00",
            },
            "signals": [SIGNAL_REGLE_ACTIVE],
            "error_message": None,
            "attempts": None,
            "retry_after": None,
        }

    @pytest.mark.asyncio
    async def test_periph_without_entity_is_never_lost(self, monkeypatch):
        """An unresolved peripheral still gets a line, flagged sans_entite."""
        result = await self.fetch_rows(monkeypatch)

        rows = {row["periph_id"]: row for row in result["peripherals"]}
        assert "333" in rows
        assert rows["333"]["entity_id"] is None
        assert SIGNAL_SANS_ENTITE in rows["333"]["signals"]

    @pytest.mark.asyncio
    async def test_periph_outside_registry_gets_null_registry_fields(self, monkeypatch):
        """The registry only covers mapped periphs: the join must not raise."""
        result = await self.fetch_rows(monkeypatch)

        rows = {row["periph_id"]: row for row in result["peripherals"]}
        assert "444" in rows
        assert rows["444"]["ha_entity"] is None
        assert rows["444"]["ha_subtype"] is None
        assert rows["444"]["parent_periph_id"] is None
        assert rows["444"]["justification"] is None

    @pytest.mark.asyncio
    async def test_signals_derivation_covers_the_four_signals(self, monkeypatch):
        """sans_entite / douteux / regle_active / en_erreur, cumulable."""
        result = await self.fetch_rows(monkeypatch)

        rows = {row["periph_id"]: row for row in result["peripherals"]}
        # Living sensor with unit, custom rule on usage 7.
        assert rows["111"]["signals"] == [SIGNAL_REGLE_ACTIVE]
        # Entity resolved but no living state + custom mapping on usage 24.
        assert rows["222"]["signals"] == [SIGNAL_DOUTEUX, SIGNAL_REGLE_ACTIVE]
        # Entity resolution failed.
        assert rows["333"]["signals"] == [SIGNAL_SANS_ENTITE]
        # Living sensor without unit_of_measurement.
        assert rows["444"]["signals"] == [SIGNAL_DOUTEUX]
        # In the coordinator retry queue.
        assert rows["555"]["signals"] == [SIGNAL_EN_ERREUR]
        # Stale retry entry (window long past): the coordinator never
        # purges, but the signal must clear with the window.
        assert rows["777"]["signals"] == [
            SIGNAL_SANS_ENTITE,
            SIGNAL_REGLE_ACTIVE,
        ]
        assert rows["777"]["error_message"] is None
        assert rows["777"]["attempts"] is None
        assert rows["777"]["retry_after"] is None

    @pytest.mark.asyncio
    async def test_unavailable_and_unknown_states_are_douteux(self, monkeypatch):
        """A resolved entity resting on a placeholder state carries no
        living data: douteux, exactly like an absent state."""
        coordinator = MagicMock()
        coordinator.data = {
            "888": {"periph_id": "888", "name": "Prise indisponible", "usage_id": "10"},
            "889": {"periph_id": "889", "name": "Capteur inconnu", "usage_id": "11"},
        }
        coordinator._retry_queue = {}
        coordinator._resolve_main_entity_id = MagicMock(
            side_effect=lambda pid: {
                "888": "switch.prise_indisponible",
                "889": "sensor.capteur_inconnu",
            }.get(pid)
        )
        hass = MagicMock()
        hass.data = {"eedomus": {"entry_1": {COORDINATOR: coordinator}}}
        hass.states.get = MagicMock(
            side_effect=lambda entity_id: {
                "switch.prise_indisponible": SimpleNamespace(
                    state="unavailable",
                    last_updated=datetime(2026, 10, 2, 8, 30),
                    attributes={"device_class": "outlet"},
                ),
                "sensor.capteur_inconnu": SimpleNamespace(
                    state="unknown",
                    last_updated=datetime(2026, 10, 2, 8, 30),
                    attributes={"device_class": "power"},
                ),
            }.get(entity_id)
        )
        service = EedomusUIService(hass)
        connection = MagicMock()
        self.patch_registry(monkeypatch)
        self.patch_custom_mapping(monkeypatch, config={})

        await service._handle_get_coherence(hass, connection, {"id": 11})

        rows = {
            row["periph_id"]: row
            for row in connection.send_result.call_args.args[1]["peripherals"]
        }
        assert rows["888"]["signals"] == [SIGNAL_DOUTEUX]
        assert rows["889"]["signals"] == [SIGNAL_DOUTEUX]

    @pytest.mark.asyncio
    async def test_enum_sensor_without_unit_is_not_flagged(self, monkeypatch):
        """Enum sensors legitimately have no unit: never douteux."""
        coordinator = MagicMock()
        coordinator.data = {
            "890": {"periph_id": "890", "name": "Mode chauffage", "usage_id": "12"},
        }
        coordinator._retry_queue = {}
        coordinator._resolve_main_entity_id = MagicMock(
            return_value="sensor.mode_chauffage"
        )
        hass = MagicMock()
        hass.data = {"eedomus": {"entry_1": {COORDINATOR: coordinator}}}
        hass.states.get = MagicMock(
            return_value=SimpleNamespace(
                state="auto",
                last_updated=datetime(2026, 10, 2, 8, 30),
                attributes={"device_class": "enum"},
            )
        )
        service = EedomusUIService(hass)
        connection = MagicMock()
        self.patch_registry(monkeypatch)
        self.patch_custom_mapping(monkeypatch, config={})

        await service._handle_get_coherence(hass, connection, {"id": 11})

        rows = connection.send_result.call_args.args[1]["peripherals"]
        assert rows[0]["signals"] == []

    @pytest.mark.asyncio
    async def test_error_message_is_exposed_with_en_erreur(self, monkeypatch):
        result = await self.fetch_rows(monkeypatch)

        rows = {row["periph_id"]: row for row in result["peripherals"]}
        assert rows["555"]["error_message"] == "API rate limit"
        assert rows["555"]["attempts"] == 1
        # The epoch is dynamic (active window): assert the UTC convention
        # and that the value is in the future, not an exact timestamp.
        retry_after = rows["555"]["retry_after"]
        parsed = datetime.fromisoformat(retry_after)
        assert parsed.tzinfo is not None
        assert parsed.timestamp() > datetime.now(timezone.utc).timestamp()
        assert rows["111"]["error_message"] is None
        assert rows["111"]["attempts"] is None
        assert rows["111"]["retry_after"] is None

    @pytest.mark.asyncio
    async def test_registry_join_is_last_wins(self, monkeypatch):
        """On reload, devices re-register into the never-cleared global
        registry: the latest (post-change) entry must win the join."""
        monkeypatch.setattr(
            mapping_registry_module,
            "_MAPPING_REGISTRY",
            [
                {
                    "periph_id": "111",
                    "periph_name": "Température Salon (avant rechargement)",
                    "parent_periph_id": None,
                    "ha_entity": "sensor",
                    "ha_subtype": "temperature",
                    "justification": "mapping avant rechargement",
                },
                {
                    "periph_id": "111",
                    "periph_name": "Température Salon",
                    "parent_periph_id": "999",
                    "ha_entity": "sensor",
                    "ha_subtype": "temperature",
                    "justification": "usage_id 7 = température",
                },
            ],
        )
        coordinator = self.make_coordinator()
        hass = self.make_hass(coordinator)
        service = EedomusUIService(hass)
        connection = MagicMock()
        self.patch_custom_mapping(monkeypatch)

        await service._handle_get_coherence(hass, connection, {"id": 11})

        row = {
            r["periph_id"]: r
            for r in connection.send_result.call_args.args[1]["peripherals"]
        }["111"]
        assert row["parent_periph_id"] == "999"
        assert row["justification"] == "usage_id 7 = température"

    @pytest.mark.asyncio
    async def test_non_finite_floats_in_raw_become_strings(self, monkeypatch):
        """NaN/Infinity would emit invalid JSON tokens and break the whole
        websocket payload: they must be serialized as strings."""
        coordinator = self.make_coordinator()
        coordinator.data["111"]["value"] = float("nan")
        coordinator.data["111"]["peak"] = float("inf")

        result = await self.fetch_rows(monkeypatch, coordinator)

        row = {r["periph_id"]: r for r in result["peripherals"]}["111"]
        assert row["raw"]["value"] == "nan"
        assert row["raw"]["peak"] == "inf"
        json.dumps(result)

    @pytest.mark.asyncio
    async def test_payload_is_json_serializable(self, monkeypatch):
        """Datetimes in the raw dict are serialized, not smuggled through."""
        result = await self.fetch_rows(monkeypatch)

        rows = {row["periph_id"]: row for row in result["peripherals"]}
        assert rows["111"]["raw"]["last_seen"] == "2026-10-01T12:00:00"
        json.dumps(result)

    @pytest.mark.asyncio
    async def test_multi_box_collects_every_coordinator(self, monkeypatch):
        """One line per peripheral of each coordinator (multi-box)."""
        coordinator_1 = self.make_coordinator()
        coordinator_2 = self.make_coordinator()
        coordinator_2.data = {
            "900": {"periph_id": "900", "name": "Box 2 capteur", "usage_id": "7"},
        }
        coordinator_2._retry_queue = {}
        coordinator_2._resolve_main_entity_id = MagicMock(return_value=None)
        hass = MagicMock()
        hass.data = {
            "eedomus": {
                "entry_1": {COORDINATOR: coordinator_1},
                "entry_2": {COORDINATOR: coordinator_2},
            }
        }
        hass.states.get = MagicMock(return_value=None)
        service = EedomusUIService(hass)
        connection = MagicMock()
        self.patch_registry(monkeypatch)
        self.patch_custom_mapping(monkeypatch)

        await service._handle_get_coherence(hass, connection, {"id": 11})

        result = connection.send_result.call_args.args[1]
        rows = {row["periph_id"]: row for row in result["peripherals"]}
        assert "900" in rows
        # The second coordinator's walk must not disturb the box-1 rows.
        assert rows["111"]["ha_subtype"] == "temperature"
        assert SIGNAL_REGLE_ACTIVE in rows["111"]["signals"]
        assert result["total"] == 7

    @pytest.mark.asyncio
    async def test_get_peripherals_contract_stays_frozen(self, monkeypatch):
        """get_peripherals rows must not gain any coherence field."""
        coordinator = self.make_coordinator()
        hass = self.make_hass(coordinator)
        service = EedomusUIService(hass)
        connection = MagicMock()
        self.patch_registry(monkeypatch)
        self.patch_custom_mapping(monkeypatch)

        await service._handle_get_peripherals(hass, connection, {"id": 5})
        peripherals = connection.send_result.call_args.args[1]
        assert peripherals["total"] == 6
        for row in peripherals["peripherals"]:
            assert set(row) == self.PERIPHERALS_ROW_KEYS

        await service._handle_get_coherence(hass, connection, {"id": 11})
        coherence = connection.send_result.call_args.args[1]
        for row in coherence["peripherals"]:
            assert set(row) == self.PERIPHERALS_ROW_KEYS | self.COHERENCE_EXTRA_KEYS

    @pytest.mark.asyncio
    async def test_custom_mapping_load_failure_keeps_rows(self, monkeypatch):
        """A broken custom mapping degrades the badge, never the join."""
        coordinator = self.make_coordinator()
        hass = self.make_hass(coordinator)
        service = EedomusUIService(hass)
        connection = MagicMock()
        self.patch_registry(monkeypatch)
        self.patch_custom_mapping(monkeypatch, side_effect=Exception("no file"))

        await service._handle_get_coherence(hass, connection, {"id": 11})

        result = connection.send_result.call_args.args[1]
        assert result["total"] == 6
        rows = {row["periph_id"]: row for row in result["peripherals"]}
        assert SIGNAL_REGLE_ACTIVE not in rows["111"]["signals"]

    @pytest.mark.asyncio
    async def test_no_coordinator_entries_returns_empty_list(self, monkeypatch):
        service, connection = make_service({})
        self.patch_registry(monkeypatch)
        self.patch_custom_mapping(monkeypatch)

        await service._handle_get_coherence(service.hass, connection, {"id": 11})

        result = connection.send_result.call_args.args[1]
        assert result == {"peripherals": [], "total": 0}

    @pytest.mark.asyncio
    async def test_exception_sends_error(self):
        """A mid-row failure (state machine error) surfaces as send_error,
        never as a half-loaded result."""
        coordinator = self.make_coordinator()
        hass = self.make_hass(coordinator)
        hass.states.get = MagicMock(side_effect=RuntimeError("state machine down"))
        service = EedomusUIService(hass)
        connection = MagicMock()

        await service._handle_get_coherence(hass, connection, {"id": 11})

        connection.send_error.assert_called_once_with(
            11, "internal_error", "Failed to build the coherence view"
        )
        connection.send_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_removed_mapping_no_longer_feeds_the_line(self, monkeypatch):
        """Registry lifecycle (sweep): after the entry's registration wave
        is pruned - what a reload does before re-registering the current
        mappings - a deleted mapping must not resurrect as identity
        fields on the coherence row."""
        coordinator = self.make_coordinator()
        hass = self.make_hass(coordinator)
        service = EedomusUIService(hass)
        connection = MagicMock()
        self.patch_custom_mapping(monkeypatch)
        monkeypatch.setattr(mapping_registry_module, "_MAPPING_REGISTRY", [])

        mapping_registry_module.register_device_mapping(
            {
                "ha_entity": "sensor",
                "ha_subtype": "power",
                "justification": "compteur électrique",
            },
            "Énergie",
            "555",
            None,
            entry_id="entry_1",
        )
        await service._handle_get_coherence(hass, connection, {"id": 11})
        rows = {
            row["periph_id"]: row
            for row in connection.send_result.call_args.args[1]["peripherals"]
        }
        assert rows["555"]["ha_entity"] == "sensor"
        assert rows["555"]["ha_subtype"] == "power"
        assert rows["555"]["justification"] == "compteur électrique"

        # A prune without entry_id is a no-op (legacy registrations).
        mapping_registry_module.prune_mapping_registry(None)
        await service._handle_get_coherence(hass, connection, {"id": 12})
        rows = {
            row["periph_id"]: row
            for row in connection.send_result.call_args.args[1]["peripherals"]
        }
        assert rows["555"]["ha_entity"] == "sensor"

        # The entry reloads without the rule: the wave is pruned, the
        # peripheral is no longer mapped, nothing re-registers.
        mapping_registry_module.prune_mapping_registry("entry_1")
        await service._handle_get_coherence(hass, connection, {"id": 13})
        rows = {
            row["periph_id"]: row
            for row in connection.send_result.call_args.args[1]["peripherals"]
        }
        assert rows["555"]["ha_entity"] is None
        assert rows["555"]["ha_subtype"] is None
        assert rows["555"]["parent_periph_id"] is None
        assert rows["555"]["justification"] is None

        # Another entry's registrations survive this entry's lifecycle.
        mapping_registry_module.register_device_mapping(
            {"ha_entity": "light", "ha_subtype": "switch"},
            "RubanLED",
            "333",
            None,
            entry_id="entry_2",
        )
        mapping_registry_module.prune_mapping_registry("entry_1")
        entries = [
            m["periph_id"]
            for m in mapping_registry_module.get_mapping_registry()
        ]
        assert entries == ["333"]

    @pytest.mark.asyncio
    async def test_douteux_exempts_unitless_timestamp_and_date_sensors(
        self, monkeypatch
    ):
        """A timestamp or date sensor legitimately carries no unit: the
        douteux heuristic must not flag them (CAP-6 sweep fix)."""
        coordinator = MagicMock()
        coordinator.data = {
            "888": {"periph_id": "888", "name": "Dernier allumage", "usage_id": "60"},
            "889": {
                "periph_id": "889",
                "name": "Date de mise à jour",
                "usage_id": "61",
            },
        }
        coordinator._retry_queue = {}
        coordinator._resolve_main_entity_id = MagicMock(
            side_effect=lambda pid: {
                "888": "sensor.dernier_allumage",
                "889": "sensor.date_mise_a_jour",
            }.get(pid)
        )
        hass = MagicMock()
        hass.data = {"eedomus": {"entry_1": {COORDINATOR: coordinator}}}
        hass.states.get = MagicMock(
            side_effect=lambda entity_id: {
                "sensor.dernier_allumage": SimpleNamespace(
                    state="2026-10-02T08:30",
                    last_updated=datetime(2026, 10, 2, 8, 30),
                    attributes={"device_class": "timestamp"},
                ),
                "sensor.date_mise_a_jour": SimpleNamespace(
                    state="2026-10-01",
                    last_updated=datetime(2026, 10, 2, 8, 30),
                    attributes={"device_class": "date"},
                ),
            }.get(entity_id)
        )
        service = EedomusUIService(hass)
        connection = MagicMock()
        monkeypatch.setattr(mapping_registry_module, "_MAPPING_REGISTRY", [])
        self.patch_custom_mapping(monkeypatch)

        await service._handle_get_coherence(hass, connection, {"id": 11})

        rows = {
            row["periph_id"]: row
            for row in connection.send_result.call_args.args[1]["peripherals"]
        }
        assert SIGNAL_DOUTEUX not in rows["888"]["signals"]
        assert SIGNAL_DOUTEUX not in rows["889"]["signals"]

    @pytest.mark.asyncio
    async def test_douteux_flags_empty_string_unit(self, monkeypatch):
        """An empty-string unit is as unitless as a missing one: a living
        sensor expected to carry a unit stays doubtful (CAP-6 sweep
        fix - the old `is None` check let unit == \"\" through)."""
        coordinator = MagicMock()
        coordinator.data = {
            "890": {"periph_id": "890", "name": "Puissance vide", "usage_id": "62"},
        }
        coordinator._retry_queue = {}
        coordinator._resolve_main_entity_id = MagicMock(
            side_effect=lambda pid: {"890": "sensor.puissance_vide"}.get(pid)
        )
        hass = MagicMock()
        hass.data = {"eedomus": {"entry_1": {COORDINATOR: coordinator}}}
        hass.states.get = MagicMock(
            side_effect=lambda entity_id: {
                "sensor.puissance_vide": SimpleNamespace(
                    state="1.4",
                    last_updated=datetime(2026, 10, 2, 8, 30),
                    attributes={"device_class": "power", "unit_of_measurement": ""},
                ),
            }.get(entity_id)
        )
        service = EedomusUIService(hass)
        connection = MagicMock()
        monkeypatch.setattr(mapping_registry_module, "_MAPPING_REGISTRY", [])
        self.patch_custom_mapping(monkeypatch)

        await service._handle_get_coherence(hass, connection, {"id": 11})

        rows = {
            row["periph_id"]: row
            for row in connection.send_result.call_args.args[1]["peripherals"]
        }
        assert SIGNAL_DOUTEUX in rows["890"]["signals"]


class TestGetCoherenceDispatcher:
    """The module dispatcher resolves the service from hass.data at call
    time - a copy-paste error in its body would otherwise go unexercised
    by the handler-level tests."""

    @pytest.mark.asyncio
    async def test_dispatches_to_the_service_handler(self):
        service = MagicMock()
        service._handle_get_coherence = AsyncMock()
        hass = MagicMock()
        hass.data = {"eedomus": {"ui_service": service}}
        connection = MagicMock()

        await ui_service_module._ws_get_coherence(hass, connection, {"id": 21})

        service._handle_get_coherence.assert_awaited_once_with(
            hass, connection, {"id": 21}
        )
        connection.send_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_service_sends_service_unavailable(self):
        hass = MagicMock()
        hass.data = {"eedomus": {}}
        connection = MagicMock()

        await ui_service_module._ws_get_coherence(hass, connection, {"id": 21})

        connection.send_error.assert_called_once_with(
            21, "service_unavailable", "Eedomus UI service not initialized"
        )


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


class TestGetMappingVersionsHandler:
    """P.1.6: the Historique tab reads the archived versions and the
    current canonical mapping through eedomus/get_mapping_versions."""

    @pytest.mark.asyncio
    async def test_returns_versions_and_current(self):
        manager = MagicMock()
        manager.async_get_mapping_versions = AsyncMock(
            return_value=[
                {
                    "timestamp": "2026-09-28T09:19:00",
                    "config": {"custom_rules": []},
                    "reason": "ingestion",
                }
            ]
        )
        manager.async_get_custom_mapping = AsyncMock(
            return_value={"custom_usage_id_mappings": {}}
        )
        hass = MagicMock()
        hass.data = {"eedomus": {"config_manager": manager}}
        service = EedomusUIService(hass)
        connection = MagicMock()

        await service._handle_get_mapping_versions(hass, connection, {"id": 8})

        connection.send_result.assert_called_once_with(
            8,
            {
                "versions": [
                    {
                        "timestamp": "2026-09-28T09:19:00",
                        "config": {"custom_rules": []},
                        "reason": "ingestion",
                    }
                ],
                "current": {"custom_usage_id_mappings": {}},
            },
        )

    @pytest.mark.asyncio
    async def test_without_manager_sends_error(self):
        service, connection = make_service({})

        await service._handle_get_mapping_versions(service.hass, connection, {"id": 8})

        connection.send_error.assert_called_once_with(
            8, "service_unavailable", "ConfigManager not available"
        )


class TestCoherenceSignalContract:
    """The signal strings are a cross-language contract: the backend
    constants and the panel's COHERENCE_SIGNALS keys must match exactly,
    or chips silently degrade to the neutral fallback (nothing fails).

    The contract is bidirectional: a backend signal missing from the
    panel degrades its chip, and a panel key without a backend signal
    is a dead chip that can never render from real data. The regex is
    scoped to the COHERENCE_SIGNALS block itself (top-level keys at
    two-space indentation) - a same-shaped object anywhere else in
    the coherence module must not satisfy the contract by accident.

    The block lives in the coherence ES module since the story 102
    split (the entry imports it); the file read follows the move."""

    PANEL_JS = (
        Path(__file__).resolve().parents[2]
        / "custom_components"
        / "eedomus"
        / "www"
        / "panel"
        / "coherence.js"
    ).read_text(encoding="utf-8")

    @classmethod
    def panel_signal_keys(cls):
        import re

        start = cls.PANEL_JS.index("const COHERENCE_SIGNALS = {")
        end = cls.PANEL_JS.index("\n};", start)
        block = cls.PANEL_JS[start:end]
        keys = set(re.findall(r"^  (\w+): \{", block, re.MULTILINE))
        assert keys, "COHERENCE_SIGNALS block not found in the panel"
        return keys

    def test_backend_signals_exist_in_the_panel(self):
        panel_keys = self.panel_signal_keys()
        for signal in (
            ui_service_module.SIGNAL_SANS_ENTITE,
            ui_service_module.SIGNAL_DOUTEUX,
            ui_service_module.SIGNAL_REGLE_ACTIVE,
            ui_service_module.SIGNAL_EN_ERREUR,
        ):
            assert signal in panel_keys, (
                f"signal {signal!r} missing from the panel's "
                "COHERENCE_SIGNALS: the chip would degrade to the "
                "neutral fallback with no test failure"
            )

    def test_panel_keys_all_come_from_the_backend(self):
        """Dead chip key detection: a COHERENCE_SIGNALS entry that no
        backend code can ever emit renders nothing but dead markup."""
        backend_signals = {
            ui_service_module.SIGNAL_SANS_ENTITE,
            ui_service_module.SIGNAL_DOUTEUX,
            ui_service_module.SIGNAL_REGLE_ACTIVE,
            ui_service_module.SIGNAL_EN_ERREUR,
        }
        assert self.panel_signal_keys() <= backend_signals, (
            "the panel declares COHERENCE_SIGNALS keys the backend "
            "never emits (dead chips)"
        )


class TestGetTranslationsHandler:
    """CAP-3: the panel reads its localized strings through
    eedomus/get_translations — a flat key -> text catalog for the
    requested locale, English as the source of truth and the fallback
    for anything unknown."""

    @pytest.mark.asyncio
    async def test_fr_locale_serves_the_complete_fr_catalog(self):
        service, connection = make_service()

        await service._handle_get_translations(
            service.hass, connection, {"id": 12, "locale": "fr"}
        )

        connection.send_result.assert_called_once_with(
            12,
            {
                "locale": "fr",
                "translations": panel_translations_module.PANEL_TRANSLATIONS["fr"],
            },
        )
        connection.send_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_locale_serves_the_en_catalog(self):
        """A locale without a translation must never error, never be empty."""
        service, connection = make_service()

        await service._handle_get_translations(
            service.hass, connection, {"id": 12, "locale": "de"}
        )

        connection.send_result.assert_called_once_with(
            12,
            {
                "locale": "en",
                "translations": panel_translations_module.PANEL_TRANSLATIONS["en"],
            },
        )

    @pytest.mark.asyncio
    async def test_missing_locale_serves_the_en_catalog(self):
        service, connection = make_service()

        await service._handle_get_translations(service.hass, connection, {"id": 12})

        result = connection.send_result.call_args.args[1]
        assert result["locale"] == "en"
        assert result["translations"] == (
            panel_translations_module.PANEL_TRANSLATIONS["en"]
        )

    @pytest.mark.asyncio
    async def test_locale_variant_resolves_to_its_base(self):
        """hass.locale may carry a region suffix (fr-FR): the base
        language is what selects the catalog."""
        service, connection = make_service()

        await service._handle_get_translations(
            service.hass, connection, {"id": 12, "locale": "fr-FR"}
        )

        result = connection.send_result.call_args.args[1]
        assert result["locale"] == "fr"
        assert result["translations"] == (
            panel_translations_module.PANEL_TRANSLATIONS["fr"]
        )

    @pytest.mark.asyncio
    async def test_missing_fr_key_falls_back_to_the_en_text(self, monkeypatch):
        """Transitory partial catalog: a missing key serves the English
        source text, never an empty string."""
        monkeypatch.setattr(
            panel_translations_module,
            "PANEL_TRANSLATIONS",
            {
                "en": {
                    "panel.common.retry": "Retry",
                    "panel.common.save": "Save",
                },
                "fr": {"panel.common.retry": "Réessayer"},
            },
        )
        service, connection = make_service()

        await service._handle_get_translations(
            service.hass, connection, {"id": 12, "locale": "fr"}
        )

        result = connection.send_result.call_args.args[1]
        assert result["locale"] == "fr"
        assert result["translations"] == {
            "panel.common.retry": "Réessayer",
            "panel.common.save": "Save",
        }

    @pytest.mark.asyncio
    async def test_served_catalog_is_a_copy_not_the_module_dict(self):
        """A mutated response must never leak into the module catalog."""
        service, connection = make_service()

        await service._handle_get_translations(
            service.hass, connection, {"id": 12, "locale": "en"}
        )

        served = connection.send_result.call_args.args[1]["translations"]
        served["panel.common.retry"] = "mutated"
        assert (
            panel_translations_module.PANEL_TRANSLATIONS["en"]["panel.common.retry"]
            == "Retry"
        )

    @pytest.mark.asyncio
    async def test_exception_sends_error(self, monkeypatch):
        """A catalog build failure sends the stable client error, not
        the raw exception - the internal detail stays in the log."""

        def raise_boom(locale):
            raise RuntimeError("boom")

        monkeypatch.setattr(ui_service_module, "get_panel_translations", raise_boom)
        service, connection = make_service()

        await service._handle_get_translations(
            service.hass, connection, {"id": 12, "locale": "fr"}
        )

        connection.send_error.assert_called_once_with(
            12, "internal_error", "Failed to build the translations catalog"
        )
        connection.send_result.assert_not_called()


class TestPanelTranslationsCatalog:
    """Catalog invariants: the en/fr key trees are identical (a missing
    key in either language silently degrades the panel — the identity
    test also guards the 3.4 backend-i18n trees), every key is a
    panel.* key, and the committed fixtures (panel-keys.json generated
    from the i18n inventory, panel-catalog.json snapshotting the
    catalog) stay pinned to the Python source of truth."""

    def test_en_and_fr_key_trees_are_identical(self):
        en = set(panel_translations_module.PANEL_TRANSLATIONS["en"])
        fr = set(panel_translations_module.PANEL_TRANSLATIONS["fr"])
        assert en == fr

    def test_every_key_is_a_panel_key(self):
        for catalog in panel_translations_module.PANEL_TRANSLATIONS.values():
            assert catalog
            assert all(
                key.startswith("panel.") and " " not in key for key in catalog
            ), "keys must be flat panel.* identifiers"

    def test_every_value_is_a_non_empty_string(self):
        for catalog in panel_translations_module.PANEL_TRANSLATIONS.values():
            for key, value in catalog.items():
                assert isinstance(value, str) and value, key

    def test_placeholders_match_between_en_and_fr(self):
        """Every {token} of the EN source must exist in the FR text and
        vice versa: the panel interpolates client-side, so a mismatched
        placeholder would leak into the rendered string."""
        import re

        token = re.compile(r"\{(\w+)\}")
        en = panel_translations_module.PANEL_TRANSLATIONS["en"]
        fr = panel_translations_module.PANEL_TRANSLATIONS["fr"]
        for key, en_text in en.items():
            assert sorted(token.findall(en_text)) == sorted(token.findall(fr[key])), key

    def test_locale_normalization_resolves_space_case_and_underscore(self):
        """A leading space with uppercase and an underscore variant
        must resolve to the FR catalog, not silently fall back to EN."""
        fr = panel_translations_module.PANEL_TRANSLATIONS["fr"]
        for variant in (" FR", "fr_FR"):
            locale, catalog = panel_translations_module.get_panel_translations(variant)
            assert locale == "fr"
            assert catalog == fr

    def test_panel_keys_fixture_equals_the_catalog(self):
        """Fixture ≡ catalog parity: the committed key list
        (tests/fixtures/panel-keys.json, generated ONCE from the i18n
        inventory's Key column by expanding its '/' shorthand — a
        suffix replaces the last segment of the base key) must equal
        the catalog's key set. The inventory remains the GENERATION
        source only; this pin guards the fixture the tests actually
        read, so an archived _bmad-output never breaks the suite."""
        fixture_path = (
            Path(__file__).resolve().parents[1] / "fixtures" / "panel-keys.json"
        )
        keys = set(json.loads(fixture_path.read_text(encoding="utf-8")))

        assert keys == set(
            panel_translations_module.PANEL_TRANSLATIONS["en"]
        ), "the catalog and the panel key fixture have diverged"

    def test_catalog_fixture_equals_the_python_catalog(self):
        """Drift-check of the catalog fixture: the committed
        panel-catalog.json must be exactly PANEL_TRANSLATIONS (both
        locale trees, keys and values) — the JS harness reads the
        fixture, the ws command serves the Python source; the two may
        never disagree."""
        fixture_path = (
            Path(__file__).resolve().parents[1] / "fixtures" / "panel-catalog.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

        assert fixture == panel_translations_module.PANEL_TRANSLATIONS, (
            "tests/fixtures/panel-catalog.json has drifted from "
            "panel_translations.py - regenerate it"
        )


class TestGetTranslationsDispatcher:
    """The module dispatcher resolves the service from hass.data at call
    time - a copy-paste error in its body would otherwise go unexercised
    by the handler-level tests."""

    @pytest.mark.asyncio
    async def test_dispatches_to_the_service_handler(self):
        service = MagicMock()
        service._handle_get_translations = AsyncMock()
        hass = MagicMock()
        hass.data = {"eedomus": {"ui_service": service}}
        connection = MagicMock()

        await ui_service_module._ws_get_translations(
            hass, connection, {"id": 21, "locale": "fr"}
        )

        service._handle_get_translations.assert_awaited_once_with(
            hass, connection, {"id": 21, "locale": "fr"}
        )
        connection.send_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_service_sends_service_unavailable(self):
        hass = MagicMock()
        hass.data = {"eedomus": {}}
        connection = MagicMock()

        await ui_service_module._ws_get_translations(
            hass, connection, {"id": 21, "locale": "fr"}
        )

        connection.send_error.assert_called_once_with(
            21, "service_unavailable", "Eedomus UI service not initialized"
        )
