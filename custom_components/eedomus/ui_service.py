"""UI Service for Eedomus Integration with WebSocket API for frontend communication."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import voluptuous as vol

from homeassistant.core import HomeAssistant

from .const import COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Define WebSocket command types
WS_TYPE_EEDOMUS_VALIDATE = f"{DOMAIN}/validate_config"
WS_TYPE_EEDOMUS_SUGGESTIONS = f"{DOMAIN}/get_suggestions"
WS_TYPE_EEDOMUS_SCHEMA = f"{DOMAIN}/get_schema"
WS_TYPE_EEDOMUS_CACHE_STATS = f"{DOMAIN}/get_cache_stats"
WS_TYPE_EEDOMUS_PERIPHERALS = f"{DOMAIN}/get_peripherals"

# The handlers are decorated at class-definition time, so the websocket_api
# imports must happen at module level. When the component is unavailable the
# module still imports (limited mode) with identity decorator fallbacks and
# no way to register commands.
try:
    from homeassistant.components.websocket_api import (
        async_register_command,
        async_response,
        require_admin,
        websocket_command,
    )
except ImportError:  # pragma: no cover
    async_register_command = None

    def async_response(func):
        """Identity fallback - no task scheduling without websocket_api."""
        return func

    def require_admin(func):
        """Identity fallback - no admin check without websocket_api."""
        return func

    def websocket_command(schema):
        """Identity fallback - no schema validation without websocket_api."""

        def decorate(func):
            return func

        return decorate


def _get_ui_service(hass: HomeAssistant) -> Optional["EedomusUIService"]:
    """Fetch the domain-level UI service instance from hass.data."""
    return hass.data.get(DOMAIN, {}).get("ui_service")


# Module-level dispatch functions: HA calls websocket handlers as plain
# functions (hass, connection, msg) - bound methods would receive a spurious
# extra `self` argument and crash at dispatch. Each dispatcher looks the
# service up in hass.data at call time, so a reload that replaces the
# instance needs no re-registration.
@require_admin
@websocket_command(
    {
        vol.Required("type"): WS_TYPE_EEDOMUS_VALIDATE,
        vol.Optional("yaml_content", default=""): str,
    }
)
@async_response
async def _ws_validate_config(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/validate_config to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_validate_config(hass, connection, msg)


@require_admin
@websocket_command(
    {
        vol.Required("type"): WS_TYPE_EEDOMUS_SUGGESTIONS,
        vol.Optional("field_type", default=""): str,
        vol.Optional("query", default=""): str,
    }
)
@async_response
async def _ws_get_suggestions(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/get_suggestions to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_get_suggestions(hass, connection, msg)


@require_admin
@websocket_command({vol.Required("type"): WS_TYPE_EEDOMUS_SCHEMA})
@async_response
async def _ws_get_schema(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/get_schema to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_get_schema(hass, connection, msg)


@require_admin
@websocket_command({vol.Required("type"): WS_TYPE_EEDOMUS_CACHE_STATS})
@async_response
async def _ws_get_cache_stats(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/get_cache_stats to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_get_cache_stats(hass, connection, msg)


@require_admin
@websocket_command({vol.Required("type"): WS_TYPE_EEDOMUS_PERIPHERALS})
@async_response
async def _ws_get_peripherals(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/get_peripherals to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_get_peripherals(hass, connection, msg)


# The commands in registration order: (command type, module dispatcher).
WS_COMMANDS = (
    (WS_TYPE_EEDOMUS_VALIDATE, _ws_validate_config),
    (WS_TYPE_EEDOMUS_SUGGESTIONS, _ws_get_suggestions),
    (WS_TYPE_EEDOMUS_SCHEMA, _ws_get_schema),
    (WS_TYPE_EEDOMUS_CACHE_STATS, _ws_get_cache_stats),
    (WS_TYPE_EEDOMUS_PERIPHERALS, _ws_get_peripherals),
)


class _LocalConnection:
    """Fake websocket connection capturing responses.

    Lets the direct-call helpers (validate_config_via_websocket, ...) reuse
    the websocket handlers even though there is no real client connection.
    """

    def __init__(self) -> None:
        self.success: Optional[Dict[str, Any]] = None
        self.error: Optional[Dict[str, Any]] = None

    def send_result(self, msg_id: Any, result: Any) -> None:
        self.success = {"type": "result", "success": True, "result": result}

    def send_error(self, msg_id: Any, code: str, message: str) -> None:
        self.error = {
            "type": "result",
            "success": False,
            "error": message,
            "error_type": code,
        }


class EedomusUIService:
    """UI service with WebSocket API for frontend communication."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the UI service."""
        self.hass = hass
        self._registered_commands: List[str] = []
        self._initialized = False

    async def async_init(self) -> None:
        """Initialize the UI service and register WebSocket commands."""
        if async_register_command is None:
            _LOGGER.warning(
                "WebSocket API not available - UIService will run in limited mode"
            )
            self._initialized = True
            return
        try:
            # Registration uses the handler form on the module-level
            # dispatchers: async_register_command reads the _ws_command/
            # _ws_schema attributes set by @websocket_command. HA calls
            # websocket handlers as plain (hass, connection, msg) functions,
            # which is why the dispatchers live at module level instead of
            # the bound methods. The dispatchers resolve the service from
            # hass.data at call time, so a reload swapping the instance
            # needs no re-registration. async_register_command returns
            # None: the tracked command types are kept here, reset so a
            # retried init never records duplicate entries.
            self._registered_commands = []
            for command_type, handler in WS_COMMANDS:
                async_register_command(self.hass, handler)
                self._registered_commands.append(command_type)

            self._initialized = True
            _LOGGER.info(
                "Eedomus UIService initialized successfully"
                " - WebSocket commands registered"
            )

        except Exception as e:
            _LOGGER.error(f"Failed to initialize UIService: {e}")
            # Don't raise - allow the integration to continue in limited mode
            self._initialized = False

    async def async_shutdown(self) -> None:
        """Reset local state.

        The websocket commands are registered at the domain level and are
        NOT unregistered here: async_register_command returns no handle in
        HA 2026 and re-registering on reload would fail anyway. The handlers
        tolerate missing services, so stale commands are harmless.
        """
        self._registered_commands = []
        self._initialized = False
        _LOGGER.debug("Eedomus UIService shutdown complete")

    async def _handle_validate_config(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle validate configuration WebSocket command."""
        try:
            yaml_content = msg.get("yaml_content", "")

            # Get SchemaService
            schema_service = self._get_schema_service()
            if not schema_service:
                connection.send_error(
                    msg.get("id"),
                    "service_unavailable",
                    "SchemaService not available",
                )
                return

            # Validate YAML content
            is_valid, result = schema_service.validate_yaml_content(yaml_content)

            if is_valid:
                connection.send_result(
                    msg.get("id"),
                    {
                        "valid": True,
                        "validated_config": result,
                    },
                )
            else:
                connection.send_error(
                    msg.get("id"),
                    result.get("type", "validation_error"),
                    result.get("error", "Validation failed"),
                )

        except Exception as e:
            _LOGGER.error(f"Validation error: {e}")
            connection.send_error(msg.get("id"), "error", str(e))

    async def _handle_get_suggestions(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle get suggestions WebSocket command."""
        try:
            field_type = msg.get("field_type", "")
            query = msg.get("query", "")
            context = msg.get("context", {})

            # Get SchemaService for suggestions
            schema_service = self._get_schema_service()
            if not schema_service:
                connection.send_error(
                    msg.get("id"),
                    "service_unavailable",
                    "SchemaService not available",
                )
                return

            # Get suggestions
            suggestions = await schema_service.get_dynamic_suggestions(
                field_type, query, context
            )

            connection.send_result(
                msg.get("id"),
                {
                    "suggestions": suggestions,
                    "field_type": field_type,
                    "query": query,
                },
            )

        except Exception as e:
            _LOGGER.error(f"Suggestions error: {e}")
            connection.send_error(msg.get("id"), "error", str(e))

    async def _handle_get_schema(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle get schema WebSocket command."""
        try:
            section = msg.get("section", "")

            # Get SchemaService
            schema_service = self._get_schema_service()
            if not schema_service:
                connection.send_error(
                    msg.get("id"),
                    "service_unavailable",
                    "SchemaService not available",
                )
                return

            if section:
                # Get specific section schema
                section_schema = schema_service._get_section_schema(section)
                if section_schema:
                    connection.send_result(
                        msg.get("id"),
                        {
                            "section": section,
                            "schema": str(section_schema),
                        },
                    )
                else:
                    connection.send_error(
                        msg.get("id"),
                        "not_found",
                        f"Section '{section}' not found",
                    )
            else:
                # Get full schema documentation
                documentation = schema_service.generate_schema_documentation()
                connection.send_result(
                    msg.get("id"),
                    {
                        "schema_version": schema_service.get_schema_version(),
                        "documentation": documentation,
                    },
                )

        except Exception as e:
            _LOGGER.error(f"Schema error: {e}")
            connection.send_error(msg.get("id"), "error", str(e))

    async def _handle_get_cache_stats(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle get cache statistics WebSocket command."""
        try:
            # Get DataService
            data_service = self._get_data_service()
            if not data_service:
                connection.send_error(
                    msg.get("id"),
                    "service_unavailable",
                    "DataService not available",
                )
                return

            # Get cache statistics
            stats = data_service.get_cache_stats()

            connection.send_result(
                msg.get("id"),
                {
                    "cache_stats": stats,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        except Exception as e:
            _LOGGER.error(f"Cache stats error: {e}")
            connection.send_error(msg.get("id"), "error", str(e))

    async def _handle_get_peripherals(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the get peripherals WebSocket command (Périphériques tab)."""
        try:
            custom_config = await self._load_custom_mapping(hass)
            peripherals = self._collect_peripherals(hass, custom_config)
            connection.send_result(
                msg.get("id"),
                {"peripherals": peripherals, "total": len(peripherals)},
            )
        except Exception as e:
            _LOGGER.error(f"Peripherals error: {e}")
            connection.send_error(msg.get("id"), "error", str(e))

    async def _load_custom_mapping(self, hass: HomeAssistant) -> Dict[str, Any]:
        """Load the raw custom_mapping.yaml content (not the merged config).

        The merged config mixes the default mapping into usage_id_mappings,
        which would flag every peripheral as "modified": the badge must only
        reflect user-defined overrides.
        """
        try:
            from .device_mapping import load_custom_yaml_mappings_async

            return await load_custom_yaml_mappings_async(hass) or {}
        except Exception as e:
            _LOGGER.debug("Custom mapping unavailable for peripherals: %s", e)
            return {}

    def _collect_peripherals(
        self, hass: HomeAssistant, custom_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Project coordinator.data into a JSON-safe list for the panel.

        One entry per config entry coordinator (multi-box): hass.data[DOMAIN]
        mixes domain-level services and per-entry dicts holding COORDINATOR.
        The current mapping (entity_id, device_class, unit) is read from the
        live HA state of the registered entity, and the "modified" badge from
        the custom mapping overrides (custom rules / usage_id mappings).
        """
        peripherals: List[Dict[str, Any]] = []
        for value in hass.data.get(DOMAIN, {}).values():
            if not isinstance(value, dict) or COORDINATOR not in value:
                continue
            peripherals.extend(
                self._project_coordinator(hass, value[COORDINATOR], custom_config)
            )
        return peripherals

    def _project_coordinator(
        self, hass: HomeAssistant, coordinator, custom_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Project one coordinator's data into panel rows."""
        usage_id_mappings = custom_config.get("custom_usage_id_mappings")
        if not isinstance(usage_id_mappings, dict):
            usage_id_mappings = {}
        custom_rules = custom_config.get("custom_rules")
        if not isinstance(custom_rules, list):
            custom_rules = []
        metadata = custom_config.get("metadata")
        modified_date = (
            metadata.get("last_modified") if isinstance(metadata, dict) else None
        )

        rows: List[Dict[str, Any]] = []
        for periph_id, periph in (coordinator.data or {}).items():
            if not isinstance(periph, dict):
                continue
            usage_id = periph.get("usage_id")
            rule_name = self._matching_rule_name(
                usage_id, usage_id_mappings, custom_rules
            )
            entity_id = self._resolve_entity_id(coordinator, periph_id)
            state = hass.states.get(entity_id) if entity_id else None
            attributes = state.attributes if state else {}
            rows.append(
                {
                    "periph_id": str(periph_id),
                    "name": periph.get("name") or "",
                    "usage_id": str(usage_id) if usage_id is not None else "",
                    "entity_id": entity_id,
                    "platform": entity_id.split(".")[0] if entity_id else None,
                    "device_class": attributes.get("device_class"),
                    "unit": attributes.get("unit_of_measurement"),
                    "modified": rule_name is not None,
                    "modified_by_rule": rule_name,
                    "modified_date": modified_date if rule_name else None,
                }
            )
        return rows

    @staticmethod
    def _resolve_entity_id(coordinator, periph_id) -> Optional[str]:
        """Resolve the HA entity_id of a peripheral via the registry."""
        try:
            return coordinator._resolve_main_entity_id(str(periph_id))
        except Exception as e:
            _LOGGER.debug("Entity resolution failed for %s: %s", periph_id, e)
            return None

    @staticmethod
    def _matching_rule_name(
        usage_id, usage_id_mappings: dict, custom_rules: list
    ) -> Optional[str]:
        """Name of the custom rule or mapping currently applied to a usage_id.

        Powers the accessible "modifié par la règle {nom}, {date}" badge.
        """
        if usage_id is None or usage_id == "":
            return None
        key = str(usage_id)
        if key in usage_id_mappings:
            return f"mapping personnalisé {key}"
        for rule in custom_rules:
            if not isinstance(rule, dict):
                continue
            condition = rule.get("condition")
            rule_usage_id = (
                condition.get("usage_id") if isinstance(condition, dict) else None
            )
            if rule_usage_id is not None and str(rule_usage_id) == key:
                return rule.get("name") or f"règle {key}"
        return None

    def _get_schema_service(self):
        """Get SchemaService instance."""
        if DOMAIN in self.hass.data and "schema_service" in self.hass.data[DOMAIN]:
            return self.hass.data[DOMAIN]["schema_service"]
        return None

    def _get_data_service(self):
        """Get DataService instance."""
        if DOMAIN in self.hass.data and "data_service" in self.hass.data[DOMAIN]:
            return self.hass.data[DOMAIN]["data_service"]
        return None

    def _get_config_manager(self):
        """Get ConfigManager instance."""
        if DOMAIN in self.hass.data and "config_manager" in self.hass.data[DOMAIN]:
            return self.hass.data[DOMAIN]["config_manager"]
        return None

    def _create_success_response(self, result: Dict) -> dict:
        """Create a success response."""
        return {
            "type": "result",
            "success": True,
            "result": result,
        }

    def _create_error_response(self, error: str, error_type: str = "error") -> dict:
        """Create an error response."""
        return {
            "type": "result",
            "success": False,
            "error": error,
            "error_type": error_type,
        }

    async def get_validation_endpoint(self) -> str:
        """Get the WebSocket endpoint for configuration validation."""
        return WS_TYPE_EEDOMUS_VALIDATE

    async def get_suggestions_endpoint(self) -> str:
        """Get the WebSocket endpoint for suggestions."""
        return WS_TYPE_EEDOMUS_SUGGESTIONS

    async def get_schema_endpoint(self) -> str:
        """Get the WebSocket endpoint for schema information."""
        return WS_TYPE_EEDOMUS_SCHEMA

    async def get_cache_stats_endpoint(self) -> str:
        """Get the WebSocket endpoint for cache statistics."""
        return WS_TYPE_EEDOMUS_CACHE_STATS

    async def validate_config_via_websocket(self, yaml_content: str) -> Dict:
        """Validate configuration and return the response payload directly."""
        connection = _LocalConnection()
        try:
            await self._handle_validate_config(
                self.hass,
                connection,
                {"id": 1, "yaml_content": yaml_content},
            )
        except Exception as e:
            _LOGGER.error(f"WebSocket validation error: {e}")
            return self._create_error_response(str(e))

        if connection.error is not None:
            return connection.error
        return connection.success or self._create_error_response("No response")

    async def get_suggestions_via_websocket(
        self, field_type: str, query: str = "", context: Dict = None
    ) -> Dict:
        """Get suggestions and return the response payload directly."""
        connection = _LocalConnection()
        try:
            await self._handle_get_suggestions(
                self.hass,
                connection,
                {
                    "id": 1,
                    "field_type": field_type,
                    "query": query,
                    "context": context or {},
                },
            )
        except Exception as e:
            _LOGGER.error(f"WebSocket suggestions error: {e}")
            return self._create_error_response(str(e))

        if connection.error is not None:
            return connection.error
        return connection.success or self._create_error_response("No response")

    async def test_websocket_connection(self) -> bool:
        """Test WebSocket connection and service availability."""
        try:
            # Test SchemaService
            schema_service = self._get_schema_service()
            if not schema_service:
                return False

            # Test DataService
            data_service = self._get_data_service()
            if not data_service:
                return False

            # Test ConfigManager
            config_manager = self._get_config_manager()
            if not config_manager:
                return False

            return True
        except Exception as e:
            _LOGGER.error(f"WebSocket test failed: {e}")
            return False

    async def get_available_endpoints(self) -> List[Dict[str, str]]:
        """Get list of available WebSocket endpoints."""
        return [
            {
                "name": "Validate Configuration",
                "endpoint": WS_TYPE_EEDOMUS_VALIDATE,
                "description": "Validate YAML configuration content",
            },
            {
                "name": "Get Suggestions",
                "endpoint": WS_TYPE_EEDOMUS_SUGGESTIONS,
                "description": "Get autocompletion suggestions for fields",
            },
            {
                "name": "Get Schema",
                "endpoint": WS_TYPE_EEDOMUS_SCHEMA,
                "description": "Get schema information and documentation",
            },
            {
                "name": "Get Cache Stats",
                "endpoint": WS_TYPE_EEDOMUS_CACHE_STATS,
                "description": "Get data cache statistics",
            },
        ]

    def is_initialized(self) -> bool:
        """Check if UIService is properly initialized."""
        return self._initialized


# Utility functions for WebSocket API
async def get_eedomus_ui_service(hass: HomeAssistant) -> Optional[EedomusUIService]:
    """Get Eedomus UIService instance."""
    if DOMAIN in hass.data and "ui_service" in hass.data[DOMAIN]:
        return hass.data[DOMAIN]["ui_service"]
    return None


async def validate_config(hass: HomeAssistant, yaml_content: str) -> Dict:
    """Validate configuration using UIService."""
    ui_service = await get_eedomus_ui_service(hass)
    if ui_service:
        return await ui_service.validate_config_via_websocket(yaml_content)
    return {"success": False, "error": "UIService not available"}


async def get_suggestions(
    hass: HomeAssistant, field_type: str, query: str = "", context: Dict = None
) -> Dict:
    """Get suggestions using UIService."""
    ui_service = await get_eedomus_ui_service(hass)
    if ui_service:
        return await ui_service.get_suggestions_via_websocket(
            field_type, query, context
        )
    return {"success": False, "error": "UIService not available"}
