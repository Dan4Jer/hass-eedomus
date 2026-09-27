"""Unit tests for the panel WebSocket service (ui_service.py).

Covers the P.1.1 fix: the websocket handlers must actually respond on the
client connection (send_result / send_error) instead of returning dicts,
and registration must not assume async_register_command returns a
deregistration handle (it returns None in HA 2026).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

import custom_components.eedomus.ui_service as ui_service_module
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

        assert register.call_count == 4
        # Handler form: (hass, handler) - the command type and schema come
        # from the handler's _ws_command/_ws_schema attributes
        assert all(call.args[0] is service.hass for call in register.call_args_list)
        handlers = [call.args[1] for call in register.call_args_list]
        assert handlers == [
            service._handle_validate_config,
            service._handle_get_suggestions,
            service._handle_get_schema,
            service._handle_get_cache_stats,
        ]
        assert service._registered_commands == [
            WS_TYPE_EEDOMUS_VALIDATE,
            WS_TYPE_EEDOMUS_SUGGESTIONS,
            WS_TYPE_EEDOMUS_SCHEMA,
            WS_TYPE_EEDOMUS_CACHE_STATS,
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
        assert register.call_count == 8

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
