"""UI Service for Eedomus Integration with WebSocket API for frontend communication."""

import math
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

import voluptuous as vol
from homeassistant.core import HomeAssistant

from .const import COORDINATOR, DOMAIN
from .coordinator import EedomusBackfillError
from .log import get_logger
from .mapping_registry import get_mapping_registry
from .panel_translations import get_panel_translations

_LOGGER = get_logger(__name__)

# Define WebSocket command types
WS_TYPE_EEDOMUS_VALIDATE = f"{DOMAIN}/validate_config"
WS_TYPE_EEDOMUS_SUGGESTIONS = f"{DOMAIN}/get_suggestions"
WS_TYPE_EEDOMUS_SCHEMA = f"{DOMAIN}/get_schema"
WS_TYPE_EEDOMUS_PERIPHERALS = f"{DOMAIN}/get_peripherals"
WS_TYPE_EEDOMUS_GET_MAPPING = f"{DOMAIN}/get_mapping"
WS_TYPE_EEDOMUS_SAVE_MAPPING = f"{DOMAIN}/save_mapping"
WS_TYPE_EEDOMUS_GET_VERSIONS = f"{DOMAIN}/get_mapping_versions"
WS_TYPE_EEDOMUS_GET_COHERENCE = f"{DOMAIN}/get_coherence"
WS_TYPE_EEDOMUS_GET_TRANSLATIONS = f"{DOMAIN}/get_translations"
WS_TYPE_EEDOMUS_GET_BACKFILL_STATE = f"{DOMAIN}/get_backfill_state"
WS_TYPE_EEDOMUS_GET_BOX_METRICS = f"{DOMAIN}/get_box_metrics"
WS_TYPE_EEDOMUS_BACKFILL_RETRY_NOW = f"{DOMAIN}/backfill_retry_now"
WS_TYPE_EEDOMUS_BACKFILL_PRIORITIZE = f"{DOMAIN}/backfill_prioritize"
WS_TYPE_EEDOMUS_BACKFILL_RESET_PROGRESS = f"{DOMAIN}/backfill_reset_progress"
WS_TYPE_EEDOMUS_BACKFILL_SET_PAUSED = f"{DOMAIN}/backfill_set_paused"
WS_TYPE_EEDOMUS_BACKFILL_SET_IGNORED = f"{DOMAIN}/backfill_set_ignored"

# Coherence signals (CAP-6): cumulable strings, one chip per signal.
SIGNAL_SANS_ENTITE = "sans_entite"
SIGNAL_DOUTEUX = "douteux"
SIGNAL_REGLE_ACTIVE = "regle_active"
SIGNAL_EN_ERREUR = "en_erreur"

# Placeholder entity states that mean "no living data" (CAP-6 douteux).
NOT_LIVING_STATES = ("unavailable", "unknown")

# Sensor device classes that legitimately carry no unit of measurement:
# a timestamp or a date never has one, so their unitless sensors are not
# a mapping smell (enum is checked alongside - same exemption class).
NO_UNIT_SENSOR_DEVICE_CLASSES = frozenset({"enum", "timestamp", "date"})

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


def _json_safe(value: Any) -> Any:
    """Recursively convert a value into JSON-safe primitives.

    The raw peripheral dicts come straight from coordinator.data and may
    embed datetimes (e.g. history imports); the websocket layer cannot
    serialize them, so dates become ISO strings and exotic objects fall
    back to str().
    """
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        # NaN/Infinity are valid Python but emit invalid JSON tokens,
        # which would break the whole websocket payload.
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


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


@require_admin
@websocket_command({vol.Required("type"): WS_TYPE_EEDOMUS_GET_MAPPING})
@async_response
async def _ws_get_mapping(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/get_mapping to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_get_mapping(hass, connection, msg)


@require_admin
@websocket_command(
    {
        vol.Required("type"): WS_TYPE_EEDOMUS_SAVE_MAPPING,
        vol.Required("mapping"): dict,
    }
)
@async_response
async def _ws_save_mapping(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/save_mapping to the UI service (write command)."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_save_mapping(hass, connection, msg)


@require_admin
@websocket_command({vol.Required("type"): WS_TYPE_EEDOMUS_GET_VERSIONS})
@async_response
async def _ws_get_mapping_versions(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/get_mapping_versions to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_get_mapping_versions(hass, connection, msg)


@require_admin
@websocket_command({vol.Required("type"): WS_TYPE_EEDOMUS_GET_COHERENCE})
@async_response
async def _ws_get_coherence(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/get_coherence to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_get_coherence(hass, connection, msg)


@require_admin
@websocket_command(
    {
        vol.Required("type"): WS_TYPE_EEDOMUS_GET_TRANSLATIONS,
        vol.Optional("locale", default=""): vol.Any(str, None),
    }
)
@async_response
async def _ws_get_translations(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/get_translations to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_get_translations(hass, connection, msg)


@require_admin
@websocket_command({vol.Required("type"): WS_TYPE_EEDOMUS_GET_BACKFILL_STATE})
@async_response
async def _ws_get_backfill_state(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/get_backfill_state to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_get_backfill_state(hass, connection, msg)


@require_admin
@websocket_command({vol.Required("type"): WS_TYPE_EEDOMUS_GET_BOX_METRICS})
@async_response
async def _ws_get_box_metrics(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/get_box_metrics to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_get_box_metrics(hass, connection, msg)


@require_admin
@websocket_command(
    {
        vol.Required("type"): WS_TYPE_EEDOMUS_BACKFILL_RETRY_NOW,
        vol.Required("periph_id"): str,
    }
)
@async_response
async def _ws_backfill_retry_now(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/backfill_retry_now to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_backfill_retry_now(hass, connection, msg)


@require_admin
@websocket_command(
    {
        vol.Required("type"): WS_TYPE_EEDOMUS_BACKFILL_PRIORITIZE,
        vol.Required("periph_id"): str,
    }
)
@async_response
async def _ws_backfill_prioritize(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/backfill_prioritize to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_backfill_prioritize(hass, connection, msg)


@require_admin
@websocket_command(
    {
        vol.Required("type"): WS_TYPE_EEDOMUS_BACKFILL_RESET_PROGRESS,
        vol.Required("periph_id"): str,
    }
)
@async_response
async def _ws_backfill_reset_progress(
    hass: HomeAssistant, connection, msg: dict
) -> None:
    """Dispatch eedomus/backfill_reset_progress to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_backfill_reset_progress(hass, connection, msg)


@require_admin
@websocket_command(
    {
        vol.Required("type"): WS_TYPE_EEDOMUS_BACKFILL_SET_PAUSED,
        vol.Optional("periph_id"): str,
        vol.Optional("global"): bool,
        vol.Required("paused"): bool,
    }
)
@async_response
async def _ws_backfill_set_paused(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/backfill_set_paused to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_backfill_set_paused(hass, connection, msg)


@require_admin
@websocket_command(
    {
        vol.Required("type"): WS_TYPE_EEDOMUS_BACKFILL_SET_IGNORED,
        vol.Required("periph_id"): str,
        vol.Required("ignored"): bool,
    }
)
@async_response
async def _ws_backfill_set_ignored(hass: HomeAssistant, connection, msg: dict) -> None:
    """Dispatch eedomus/backfill_set_ignored to the UI service."""
    service = _get_ui_service(hass)
    if service is None:
        connection.send_error(
            msg["id"], "service_unavailable", "Eedomus UI service not initialized"
        )
        return
    await service._handle_backfill_set_ignored(hass, connection, msg)


# The commands in registration order: (command type, module dispatcher).
WS_COMMANDS = (
    (WS_TYPE_EEDOMUS_VALIDATE, _ws_validate_config),
    (WS_TYPE_EEDOMUS_SUGGESTIONS, _ws_get_suggestions),
    (WS_TYPE_EEDOMUS_SCHEMA, _ws_get_schema),
    (WS_TYPE_EEDOMUS_PERIPHERALS, _ws_get_peripherals),
    (WS_TYPE_EEDOMUS_GET_MAPPING, _ws_get_mapping),
    (WS_TYPE_EEDOMUS_SAVE_MAPPING, _ws_save_mapping),
    (WS_TYPE_EEDOMUS_GET_VERSIONS, _ws_get_mapping_versions),
    (WS_TYPE_EEDOMUS_GET_COHERENCE, _ws_get_coherence),
    (WS_TYPE_EEDOMUS_GET_TRANSLATIONS, _ws_get_translations),
    (WS_TYPE_EEDOMUS_GET_BACKFILL_STATE, _ws_get_backfill_state),
    (WS_TYPE_EEDOMUS_GET_BOX_METRICS, _ws_get_box_metrics),
    (WS_TYPE_EEDOMUS_BACKFILL_RETRY_NOW, _ws_backfill_retry_now),
    (WS_TYPE_EEDOMUS_BACKFILL_PRIORITIZE, _ws_backfill_prioritize),
    (WS_TYPE_EEDOMUS_BACKFILL_RESET_PROGRESS, _ws_backfill_reset_progress),
    (WS_TYPE_EEDOMUS_BACKFILL_SET_PAUSED, _ws_backfill_set_paused),
    (WS_TYPE_EEDOMUS_BACKFILL_SET_IGNORED, _ws_backfill_set_ignored),
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


# Human-readable name and description per registered ws command: the
# endpoint list served by get_available_endpoints is DERIVED from
# WS_COMMANDS - a command registered without an entry here fails
# loudly instead of being silently missing from the list.
ENDPOINT_DESCRIPTIONS = {
    WS_TYPE_EEDOMUS_VALIDATE: (
        "Validate Configuration",
        "Validate YAML configuration content",
    ),
    WS_TYPE_EEDOMUS_SUGGESTIONS: (
        "Get Suggestions",
        "Get autocompletion suggestions for fields",
    ),
    WS_TYPE_EEDOMUS_SCHEMA: (
        "Get Schema",
        "Get schema information and documentation",
    ),
    WS_TYPE_EEDOMUS_PERIPHERALS: (
        "Get Peripherals",
        "Get the peripherals of the configured eedomus boxes",
    ),
    WS_TYPE_EEDOMUS_GET_MAPPING: (
        "Get Mapping",
        "Get the custom mapping document",
    ),
    WS_TYPE_EEDOMUS_SAVE_MAPPING: (
        "Save Mapping",
        "Persist the custom mapping document",
    ),
    WS_TYPE_EEDOMUS_GET_VERSIONS: (
        "Get Mapping Versions",
        "Get the mapping configuration history",
    ),
    WS_TYPE_EEDOMUS_GET_COHERENCE: (
        "Get Coherence",
        "Get the mapping coherence view of the peripherals",
    ),
    WS_TYPE_EEDOMUS_GET_TRANSLATIONS: (
        "Get Translations",
        "Get the panel translation catalog for a locale",
    ),
    WS_TYPE_EEDOMUS_GET_BACKFILL_STATE: (
        "Get Backfill State",
        "Get the history backfill queue state of the eedomus boxes",
    ),
    WS_TYPE_EEDOMUS_GET_BOX_METRICS: (
        "Get Box Metrics",
        "Get the refresh metrics of the eedomus boxes",
    ),
    WS_TYPE_EEDOMUS_BACKFILL_RETRY_NOW: (
        "Backfill Retry Now",
        "Retry the history import of a peripheral immediately",
    ),
    WS_TYPE_EEDOMUS_BACKFILL_PRIORITIZE: (
        "Backfill Prioritize",
        "Move a peripheral to the head of the backfill queue",
    ),
    WS_TYPE_EEDOMUS_BACKFILL_RESET_PROGRESS: (
        "Reset Backfill Progress",
        "Clear one peripheral's persisted history progress marker "
        "(the imported statistics are kept)",
    ),
    WS_TYPE_EEDOMUS_BACKFILL_SET_PAUSED: (
        "Backfill Set Paused",
        "Pause or resume one peripheral or the whole backfill engine",
    ),
    WS_TYPE_EEDOMUS_BACKFILL_SET_IGNORED: (
        "Backfill Set Ignored",
        "Ignore or re-activate a peripheral in the backfill queue",
    ),
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

    async def _handle_get_peripherals(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the get peripherals WebSocket command (Peripherals tab)."""
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
        """Load the canonical custom mapping (not the merged config).

        Story 103: the badge reads through config_manager - the same
        path get_mapping/save_mapping use - so the two can never
        diverge. The device_mapping reader stays as the bootstrap
        fallback when no ConfigManager is running (proxy-only mode).
        The merged config is deliberately not used: it mixes the
        default mapping into usage_id_mappings, which would flag every
        peripheral as "modified"; the badge must only reflect
        user-defined overrides.
        """
        try:
            config_manager = self._get_config_manager()
            if config_manager is not None:
                return await config_manager.async_get_custom_mapping() or {}

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
        self,
        hass: HomeAssistant,
        coordinator,
        custom_config: Dict[str, Any],
        with_raw: bool = False,
    ) -> List[Dict[str, Any]]:
        """Project one coordinator's data into panel rows.

        with_raw carries each raw coordinator dict on its row under the
        private "_raw" key: the raw section rides the same single walk
        as the base fields instead of a re-indexed second pass, so the
        two can never disagree. The get_peripherals path leaves it off,
        keeping that contract frozen.
        """
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
            row: Dict[str, Any] = {
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
            if with_raw:
                row["_raw"] = periph
            rows.append(row)
        return rows

    @staticmethod
    def _resolve_entity_id(coordinator, periph_id) -> Optional[str]:
        """Resolve the HA entity_id of a peripheral via the registry."""
        try:
            return coordinator._resolve_main_entity_id(str(periph_id))
        except Exception as e:
            _LOGGER.debug("Entity resolution failed for %s: %s", periph_id, e)
            return None

    async def _handle_get_coherence(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the coherence WebSocket command (Coherence tab, CAP-6)."""
        try:
            custom_config = await self._load_custom_mapping(hass)
            peripherals = self._collect_coherence(hass, custom_config)
            connection.send_result(
                msg.get("id"),
                {"peripherals": peripherals, "total": len(peripherals)},
            )
        except Exception as e:
            # The client gets a stable, branchable code and message; the
            # internal detail (paths, upstream messages) stays in the log.
            _LOGGER.error("Coherence error: %s", e, exc_info=True)
            connection.send_error(
                msg.get("id"),
                "internal_error",
                "Failed to build the coherence view",
            )

    def _collect_coherence(
        self, hass: HomeAssistant, custom_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Project coordinator.data into fused coherence rows (CAP-6).

        Same multi-box walk as _collect_peripherals. The registry only
        covers mapped peripherals, so the join is driven by the
        coordinator rows (never by the registry): every peripheral gets a
        line, mapped or not.
        """
        registry = self._registry_by_periph_id()
        rows: List[Dict[str, Any]] = []
        for value in hass.data.get(DOMAIN, {}).values():
            if not isinstance(value, dict) or COORDINATOR not in value:
                continue
            coordinator = value[COORDINATOR]
            # The raw dict rides the shared projection (with_raw): the
            # same single walk builds the base row and carries its raw
            # counterpart, so the raw section cannot miss.
            for base in self._project_coordinator(
                hass, coordinator, custom_config, with_raw=True
            ):
                raw = base.pop("_raw", {})
                rows.append(self._coherence_row(hass, coordinator, base, registry, raw))
        return rows

    @staticmethod
    def _registry_by_periph_id() -> Dict[str, Dict[str, Any]]:
        """Index the mapping registry by periph_id (last wins).

        Devices re-register on every integration reload (the registry
        is pruned per entry at setup, then repopulated by the refresh),
        so the latest entry reflects the current mapping - the first
        one would be stale.
        """
        registry: Dict[str, Dict[str, Any]] = {}
        for entry in get_mapping_registry():
            if not isinstance(entry, dict) or entry.get("periph_id") is None:
                continue
            registry[str(entry["periph_id"])] = entry
        return registry

    def _coherence_row(
        self,
        hass: HomeAssistant,
        coordinator,
        base: Dict[str, Any],
        registry: Dict[str, Dict[str, Any]],
        raw: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extend a peripherals row with registry, live state, raw, signals.

        The signals are cumulable strings so the frontend can render one
        chip per signal (EXPERIENCE.md coherence-chip).
        """
        periph_id = base["periph_id"]
        mapping = registry.get(periph_id) or {}
        entity_id = base["entity_id"]
        state = hass.states.get(entity_id) if entity_id else None

        # The retry queue is a coordinator internal (no public accessor):
        # guarded with getattr so a coordinator variant without it still
        # projects a line instead of raising.
        retry_queue = getattr(coordinator, "_retry_queue", None)
        retry_info = (
            retry_queue.get(periph_id) if isinstance(retry_queue, dict) else None
        )

        signals: List[str] = []
        if entity_id is None:
            # No HA entity: nothing else can be checked on this line.
            signals.append(SIGNAL_SANS_ENTITE)
        elif state is None or state.state in NOT_LIVING_STATES:
            # Resolved but absent from hass.states, or resting on a
            # placeholder state: no living data, doubtful mapping.
            signals.append(SIGNAL_DOUTEUX)
        elif (
            base["platform"] == "sensor"
            and base["device_class"]
            and base["device_class"] not in NO_UNIT_SENSOR_DEVICE_CLASSES
            and not base["unit"]
        ):
            # A living sensor expected to carry a unit but lacking one
            # is a mapping smell (CAP-6); enum, timestamp and date
            # sensors legitimately have none, and an empty-string unit
            # is as unitless as a missing one.
            signals.append(SIGNAL_DOUTEUX)
        if base["modified_by_rule"]:
            signals.append(SIGNAL_REGLE_ACTIVE)
        # A queue entry outlives its retry window: the coordinator never
        # purges on success, so flag (and expose details) only while the
        # retry is still pending. A missing/invalid retry_after keeps the
        # flag on — never hide an unknown error state.
        retry_active = False
        if retry_info is not None:
            retry_after_epoch = retry_info.get("retry_after")
            retry_active = (
                not isinstance(retry_after_epoch, (int, float))
                or datetime.now().timestamp() < retry_after_epoch
            )
        active_info = retry_info if retry_active else None
        if retry_active:
            signals.append(SIGNAL_EN_ERREUR)

        # The queue stores epoch floats (coordinator); a datetime variant
        # would serialize the same way - both render as ISO. Converted as
        # UTC-aware so the payload carries one time convention (matches
        # state.last_updated).
        retry_after = active_info.get("retry_after") if active_info else None
        if isinstance(retry_after, (int, float)):
            retry_after = datetime.fromtimestamp(retry_after, tz=timezone.utc)

        # CAP-5 (story 1.4): the periph detail of the Coherence tab
        # carries the same progress indicator as the Supervision queue -
        # guarded with getattr so a coordinator variant without the
        # progress dict still projects a line.
        progress_map = getattr(coordinator, "_history_progress", None)
        progress = (
            progress_map.get(periph_id) if isinstance(progress_map, dict) else None
        ) or {}
        oldest = progress.get("oldest_timestamp")
        if isinstance(oldest, (int, float)):
            oldest = datetime.fromtimestamp(oldest, tz=timezone.utc)

        base.update(
            {
                "ha_entity": mapping.get("ha_entity"),
                "ha_subtype": mapping.get("ha_subtype"),
                "parent_periph_id": mapping.get("parent_periph_id"),
                "justification": mapping.get("justification"),
                "state": state.state if state else None,
                "last_update": _json_safe(state.last_updated) if state else None,
                "raw": _json_safe(raw),
                "signals": signals,
                "error_message": (
                    active_info.get("error_message") if active_info else None
                ),
                "attempts": active_info.get("attempts") if active_info else None,
                "retry_after": _json_safe(retry_after),
                "retrieved_points": progress.get("retrieved_points", 0),
                "total_points": progress.get("total_points"),
                "estimated": progress.get("estimated", False),
                "oldest_timestamp": _json_safe(oldest),
                "retention_start": progress.get("retention_start"),
            }
        )
        return base

    async def _handle_get_mapping(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the get mapping WebSocket command (Rules tab)."""
        try:
            config_manager = self._get_config_manager()
            if not config_manager:
                connection.send_error(
                    msg.get("id"),
                    "service_unavailable",
                    "ConfigManager not available",
                )
                return

            mapping = await config_manager.async_get_custom_mapping()
            connection.send_result(msg.get("id"), {"mapping": mapping})

        except Exception as e:
            _LOGGER.error(f"Get mapping error: {e}")
            connection.send_error(msg.get("id"), "error", str(e))

    async def _handle_save_mapping(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the save mapping WebSocket command (CAP-4).

        Save via the config manager (config-dir file + version archive),
        then auto-apply: every eedomus entry is reloaded so the new
        mapping takes effect without a restart or a manual reload.
        """
        try:
            config_manager = self._get_config_manager()
            if not config_manager:
                connection.send_error(
                    msg.get("id"),
                    "service_unavailable",
                    "ConfigManager not available",
                )
                return

            config = msg.get("mapping")
            if not isinstance(config, dict):
                connection.send_error(
                    msg.get("id"), "invalid_format", "mapping must be a dict"
                )
                return

            result = await config_manager.async_save_custom_mapping(config)
            if not result.get("success"):
                connection.send_error(
                    msg.get("id"), "validation_error", result.get("error", "invalid")
                )
                return

            # Auto-apply: reload every eedomus config entry so the merged
            # mapping is rebuilt from the saved file and entities pick up
            # their new device_class / unit.
            entries = hass.config_entries.async_entries(DOMAIN)
            for entry in entries:
                await hass.config_entries.async_reload(entry.entry_id)

            connection.send_result(
                msg.get("id"),
                {
                    "saved": True,
                    "path": result.get("path"),
                    "reloaded_entries": len(entries),
                },
            )

        except Exception as e:
            _LOGGER.error(f"Save mapping error: {e}")
            connection.send_error(msg.get("id"), "error", str(e))

    async def _handle_get_mapping_versions(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the get mapping versions command (Historique tab, CAP-5).

        Returns the archived versions (newest first, three kept) and the
        current canonical mapping: the panel shows the current state as
        the active card and the archives as restorable versions.
        """
        try:
            config_manager = self._get_config_manager()
            if not config_manager:
                connection.send_error(
                    msg.get("id"),
                    "service_unavailable",
                    "ConfigManager not available",
                )
                return

            versions = await config_manager.async_get_mapping_versions()
            current = await config_manager.async_get_custom_mapping()
            connection.send_result(
                msg.get("id"),
                {"versions": versions, "current": current},
            )

        except Exception as e:
            _LOGGER.error(f"Get mapping versions error: {e}")
            connection.send_error(msg.get("id"), "error", str(e))

    async def _handle_get_translations(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the get translations command (panel i18n catalog, CAP-3).

        Serves the flat panel.* catalog for the requested locale, with
        English as the source of truth and the fallback for any unknown
        locale or missing key. An explicit null locale is coerced to the
        English catalog (vol.Any(str, None) admits it through the
        schema); a non-string locale stays a schema error.
        """
        try:
            requested = msg.get("locale") or ""
            locale, translations = get_panel_translations(requested)
            connection.send_result(
                msg.get("id"),
                {"locale": locale, "translations": translations},
            )
        except Exception as e:
            # The client gets a stable, branchable code and message; the
            # internal detail (paths, upstream messages) stays in the log.
            _LOGGER.error("Get translations error: %s", e, exc_info=True)
            connection.send_error(
                msg.get("id"),
                "internal_error",
                "Failed to build the translations catalog",
            )

    def _collect_coordinators(self, hass: HomeAssistant) -> list:
        """Collect the config entry coordinators (multi-box walk).

        Same walk as _collect_peripherals: hass.data[DOMAIN] mixes
        domain-level services and per-entry dicts holding COORDINATOR.
        """
        coordinators = []
        for value in hass.data.get(DOMAIN, {}).values():
            if isinstance(value, dict) and COORDINATOR in value:
                coordinators.append(value[COORDINATOR])
        return coordinators

    def _aggregate_backfill_state(self, hass: HomeAssistant) -> Dict[str, Any]:
        """Merge every coordinator's backfill state into one view.

        One box = one config entry = one coordinator: the queues are
        concatenated (positions stay per box), and the global flags are
        OR-ed. A coordinator variant without the CAP-5 API is skipped.
        """
        queue: List[Dict[str, Any]] = []
        ignored: List[Dict[str, Any]] = []
        global_paused = False
        engine_active = False
        for coordinator in self._collect_coordinators(hass):
            get_state = getattr(coordinator, "get_backfill_state", None)
            if get_state is None:
                continue
            state = get_state()
            queue.extend(state.get("queue") or [])
            ignored.extend(state.get("ignored") or [])
            global_paused = global_paused or bool(state.get("global_paused"))
            engine_active = engine_active or bool(state.get("engine_active"))
        return {
            "queue": queue,
            "ignored": ignored,
            "global_paused": global_paused,
            "engine_active": engine_active,
        }

    def _coordinator_for_periph(self, hass: HomeAssistant, periph_id):
        """Find the coordinator owning a peripheral (multi-box)."""
        for coordinator in self._collect_coordinators(hass):
            if periph_id in (coordinator.data or {}):
                return coordinator
        return None

    def _send_backfill_error(self, connection, msg: dict, error: Exception) -> None:
        """Send a refused action with its stable websocket code.

        EedomusBackfillError carries a branchable code and a
        client-safe message. Any other exception gets a generic message:
        the internal detail (paths, upstream messages) stays in the
        server-side log only.
        """
        if isinstance(error, EedomusBackfillError):
            connection.send_error(msg.get("id"), error.error_type, str(error))
            return
        _LOGGER.error("Backfill command error: %s", error, exc_info=True)
        connection.send_error(
            msg.get("id"),
            "error",
            "Unexpected error while steering the backfill queue",
        )

    async def _handle_get_backfill_state(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the get backfill state command (Supervision tab, CAP-5).

        The state is derived by the coordinator (queue x statuses x
        positions); the panel renders it, the engine stays untouched.
        """
        try:
            if not self._collect_coordinators(hass):
                connection.send_error(
                    msg.get("id"),
                    "service_unavailable",
                    "No eedomus coordinator available",
                )
                return
            state = self._aggregate_backfill_state(hass)
            connection.send_result(msg.get("id"), _json_safe(state))
        except Exception as e:
            self._send_backfill_error(connection, msg, e)

    async def _handle_get_box_metrics(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the get box metrics command (Supervision tab, CAP-9).

        One section per box (multi-box walk of _collect_coordinators):
        each coordinator contributes its buffered refresh cycles,
        entry_id included. A coordinator whose get_box_metrics raises
        is skipped with a warning - one broken box never costs the
        healthy boxes their metrics. No coordinator at all is a nominal
        service_unavailable refusal. The panel never subscribes - one
        call per tab visit.
        """
        try:
            boxes: List[Dict[str, Any]] = []
            for coordinator in self._collect_coordinators(hass):
                get_metrics = getattr(coordinator, "get_box_metrics", None)
                if get_metrics is None:
                    continue
                try:
                    boxes.append(get_metrics())
                except Exception as e:
                    _LOGGER.warning(
                        "Skipping the box metrics of one coordinator: %s",
                        e,
                        exc_info=True,
                    )
            if not boxes:
                connection.send_error(
                    msg.get("id"),
                    "service_unavailable",
                    "No eedomus coordinator available",
                )
                return
            connection.send_result(msg.get("id"), _json_safe({"boxes": boxes}))
        except Exception as e:
            _LOGGER.error("Box metrics error: %s", e, exc_info=True)
            connection.send_error(
                msg.get("id"),
                "internal_error",
                "Failed to build the box metrics view",
            )

    async def _handle_backfill_retry_now(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the backfill retry now command (CAP-5).

        AD-7: the action goes through the coordinator only - the ui_service
        never calls the eedomus API. A busy mono-importer lock is a
        nominal refusal, never a wait.
        """
        try:
            periph_id = msg.get("periph_id")
            coordinator = self._coordinator_for_periph(hass, periph_id)
            if coordinator is None:
                connection.send_error(
                    msg.get("id"),
                    "invalid_format",
                    f"Unknown peripheral {periph_id}",
                )
                return
            result = await coordinator.async_backfill_retry_now(periph_id)
            # Every action response carries the aggregated state so the
            # panel re-renders the queue in one round trip.
            state = self._aggregate_backfill_state(hass)
            connection.send_result(
                msg.get("id"), _json_safe({**result, "state": state})
            )
        except Exception as e:
            self._send_backfill_error(connection, msg, e)

    async def _handle_backfill_prioritize(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the backfill prioritize command (CAP-5)."""
        try:
            periph_id = msg.get("periph_id")
            coordinator = self._coordinator_for_periph(hass, periph_id)
            if coordinator is None:
                connection.send_error(
                    msg.get("id"),
                    "invalid_format",
                    f"Unknown peripheral {periph_id}",
                )
                return
            result = await coordinator.async_backfill_prioritize(periph_id)
            state = self._aggregate_backfill_state(hass)
            connection.send_result(
                msg.get("id"), _json_safe({**result, "state": state})
            )
        except Exception as e:
            self._send_backfill_error(connection, msg, e)

    async def _handle_backfill_reset_progress(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the backfill reset progress command (CAP-5, 5th action).

        AD-7: through the coordinator only. The reset clears the
        persisted progress marker - the imported statistics are never
        deleted (CAP-3 idempotence); the response carries the fresh
        aggregated state for the panel re-render.
        """
        try:
            periph_id = msg.get("periph_id")
            coordinator = self._coordinator_for_periph(hass, periph_id)
            if coordinator is None:
                connection.send_error(
                    msg.get("id"),
                    "invalid_format",
                    f"Unknown peripheral {periph_id}",
                )
                return
            result = await coordinator.async_backfill_reset_progress(periph_id)
            state = self._aggregate_backfill_state(hass)
            connection.send_result(
                msg.get("id"), _json_safe({**result, "state": state})
            )
        except Exception as e:
            self._send_backfill_error(connection, msg, e)

    async def _handle_backfill_set_paused(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the backfill set paused command (CAP-5).

        Exactly one target: periph_id or global. The response carries the
        nominal result and the aggregated state so the panel can re-render
        the queue in one round trip.
        """
        try:
            periph_id = msg.get("periph_id")
            global_target = msg.get("global")
            paused = msg.get("paused")
            # The global switch is targeted by a truthy global flag: a
            # falsy global without periph_id is a no-target payload, and
            # a truthy global next to a periph_id is incoherent.
            use_global = bool(global_target)
            if use_global == (periph_id is not None):
                connection.send_error(
                    msg.get("id"),
                    "invalid_format",
                    "Provide exactly one of periph_id or global",
                )
                return
            if use_global:
                coordinators = self._collect_coordinators(hass)
                if not coordinators:
                    connection.send_error(
                        msg.get("id"),
                        "service_unavailable",
                        "No eedomus coordinator available",
                    )
                    return
                for coordinator in coordinators:
                    # One box = one coordinator: the global switch is
                    # per config entry, applied to each here. A
                    # coordinator variant without the API is skipped
                    # instead of failing the fan-out mid-way.
                    set_paused = getattr(coordinator, "async_backfill_set_paused", None)
                    if set_paused is None:
                        continue
                    await set_paused(global_pause=True, paused=paused)
            else:
                coordinator = self._coordinator_for_periph(hass, periph_id)
                if coordinator is None:
                    connection.send_error(
                        msg.get("id"),
                        "invalid_format",
                        f"Unknown peripheral {periph_id}",
                    )
                    return
                await coordinator.async_backfill_set_paused(
                    periph_id=periph_id, paused=paused
                )
            state = self._aggregate_backfill_state(hass)
            connection.send_result(
                msg.get("id"),
                _json_safe(
                    {
                        "success": True,
                        "periph_id": periph_id,
                        "global": bool(global_target),
                        "paused": bool(paused),
                        "state": state,
                    }
                ),
            )
        except Exception as e:
            self._send_backfill_error(connection, msg, e)

    async def _handle_backfill_set_ignored(
        self,
        hass: HomeAssistant,
        connection,
        msg: dict,
    ) -> None:
        """Handle the backfill set ignored command (CAP-5).

        Ignoring persists in .storage and survives a restart; the action
        is reversible (ignored=False re-activates the peripheral without
        losing its history progress).
        """
        try:
            periph_id = msg.get("periph_id")
            coordinator = self._coordinator_for_periph(hass, periph_id)
            if coordinator is None:
                connection.send_error(
                    msg.get("id"),
                    "invalid_format",
                    f"Unknown peripheral {periph_id}",
                )
                return
            result = await coordinator.async_backfill_set_ignored(
                periph_id, msg.get("ignored")
            )
            state = self._aggregate_backfill_state(hass)
            connection.send_result(
                msg.get("id"), _json_safe({**result, "state": state})
            )
        except Exception as e:
            self._send_backfill_error(connection, msg, e)

    @staticmethod
    def _matching_rule_name(
        usage_id, usage_id_mappings: dict, custom_rules: list
    ) -> Optional[str]:
        """Name of the custom rule or mapping currently applied to a usage_id.

        Powers the accessible "modified by rule {name}, {date}" badge.
        """
        if usage_id is None or usage_id == "":
            return None
        key = str(usage_id)
        if key in usage_id_mappings:
            return f"custom mapping {key}"
        for rule in custom_rules:
            if not isinstance(rule, dict):
                continue
            condition = rule.get("condition")
            rule_usage_id = (
                condition.get("usage_id") if isinstance(condition, dict) else None
            )
            if rule_usage_id is not None and str(rule_usage_id) == key:
                return rule.get("name") or f"rule {key}"
        return None

    def _get_schema_service(self):
        """Get SchemaService instance."""
        if DOMAIN in self.hass.data and "schema_service" in self.hass.data[DOMAIN]:
            return self.hass.data[DOMAIN]["schema_service"]
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

            # Test ConfigManager
            config_manager = self._get_config_manager()
            if not config_manager:
                return False

            return True
        except Exception as e:
            _LOGGER.error(f"WebSocket test failed: {e}")
            return False

    async def get_available_endpoints(self) -> List[Dict[str, str]]:
        """Get the list of available WebSocket endpoints.

        Derived from WS_COMMANDS - the registration order is the list
        order, and a command registered without an ENDPOINT_DESCRIPTIONS
        entry fails loudly (KeyError) instead of vanishing silently.
        """
        return [
            {
                "name": ENDPOINT_DESCRIPTIONS[command_type][0],
                "endpoint": command_type,
                "description": ENDPOINT_DESCRIPTIONS[command_type][1],
            }
            for command_type, _handler in WS_COMMANDS
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
