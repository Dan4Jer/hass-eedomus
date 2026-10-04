"""Unit test fixtures.

These tests run locally WITHOUT a Home Assistant installation.
The `homeassistant.*` modules are stubbed in sys.modules before the
integration modules are imported, so the pure logic (mapping rules,
value decoding, error handling, options flow submission) can be
tested in isolation.
"""

import sys
import types
from datetime import datetime, timezone
from enum import IntEnum
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


def _install_homeassistant_stubs():
    """Install minimal homeassistant stubs so imports succeed."""

    def module(name):
        if name in sys.modules:
            return sys.modules[name]
        mod = types.ModuleType(name)
        sys.modules[name] = mod
        return mod

    # homeassistant
    ha = module("homeassistant")
    ha.__path__ = []

    # homeassistant.const - Platform enum-like stub
    ha_const = module("homeassistant.const")
    platform_names = [
        "LIGHT",
        "SWITCH",
        "COVER",
        "SENSOR",
        "BINARY_SENSOR",
        "CLIMATE",
        "SELECT",
        "SCENE",
        "FAN",
        "LOCK",
    ]
    ha_const.Platform = types.SimpleNamespace(**{n: n.lower() for n in platform_names})

    # homeassistant.core - callback decorator
    ha_core = module("homeassistant.core")
    ha_core.callback = lambda func: func
    ha_core.HomeAssistant = MagicMock
    ha_core.ServiceCall = MagicMock
    ha_core.ServiceResponse = MagicMock
    ha_core.SupportsResponse = MagicMock

    # homeassistant.helpers
    ha_helpers = module("homeassistant.helpers")
    ha_helpers.__path__ = []

    # homeassistant.helpers.config_validation - passthrough cv stubs
    ha_cv = module("homeassistant.helpers.config_validation")
    ha_cv.icon = lambda value: value
    ha_cv.ensure_list = lambda value: value if isinstance(value, list) else [value]
    ha_cv.string = lambda value: str(value)
    # cv.Invalid must exist: config_manager catches (vol.Invalid, cv.Invalid)
    ha_cv.Invalid = type("Invalid", (Exception,), {})

    # homeassistant.helpers.entity
    ha_entity = module("homeassistant.helpers.entity")
    ha_entity.Entity = MagicMock
    ha_entity.DeviceInfo = dict

    # homeassistant.helpers.update_coordinator
    ha_coord = module("homeassistant.helpers.update_coordinator")

    class _StubCoordinatorEntity:
        """Minimal CoordinatorEntity: keeps the coordinator reference and
        exposes the _handle_coordinator_update hook (a plain MagicMock base
        breaks subclass instantiation - self.coordinator would never be
        set by super().__init__, and EedomusEntity reads it at init).
        """

        def __init__(self, coordinator, context=None):
            self.coordinator = coordinator

        def _handle_coordinator_update(self) -> None:
            pass

    ha_coord.CoordinatorEntity = _StubCoordinatorEntity

    class _StubDataUpdateCoordinator:
        """Minimal base class.

        A MagicMock base breaks subclass instantiation (real coordinator's
        super().__init__ calls plus attribute assignments), so unit tests use
        this plain stub instead.
        """

        def __init__(self, hass=None, *args, **kwargs):
            # Mirror the real DataUpdateCoordinator: expose self.hass
            self.hass = hass

    ha_coord.DataUpdateCoordinator = _StubDataUpdateCoordinator
    ha_coord.UpdateFailed = type("UpdateFailed", (Exception,), {})

    # homeassistant.config_entries
    ha_ce = module("homeassistant.config_entries")
    ha_ce.ConfigEntry = MagicMock
    ha_ce.ConfigFlow = MagicMock
    ha_ce.OptionsFlow = object  # real base class hierarchy is irrelevant here
    ha_ce.STATE_LOADED = "loaded"

    # homeassistant.exceptions
    ha_exc = module("homeassistant.exceptions")
    ha_exc.ConfigEntryNotReady = type("ConfigEntryNotReady", (Exception,), {})

    # HomeAssistantError subclasses used by services.py: the real classes
    # carry translation_domain/translation_key/translation_placeholders for
    # HA-native error localization (verified against HA 2026.9); the stubs
    # accept and drop the same kwargs so the raises stay testable.
    class _StubHomeAssistantError(Exception):
        def __init__(self, *args, **kwargs):
            super().__init__(*args)

    ha_exc.HomeAssistantError = _StubHomeAssistantError
    ha_exc.ServiceValidationError = type(
        "ServiceValidationError", (_StubHomeAssistantError,), {}
    )

    # homeassistant.components (+ http, sensor) - needed by __init__.py chain
    ha_components = module("homeassistant.components")
    ha_components.__path__ = []
    ha_http = module("homeassistant.components.http")
    ha_http.HomeAssistantView = type("HomeAssistantView", (), {})
    ha_sensor = module("homeassistant.components.sensor")
    ha_sensor.SensorEntity = MagicMock

    # homeassistant.components.recorder.models - StatisticMeanType is a real
    # IntEnum consumed by the recorder (the metadata must carry the enum,
    # not a mock): NONE=0, ARITHMETIC=1 (verified against HA 2026.9.4)
    ha_rec_models = module("homeassistant.components.recorder.models")

    class _StatisticMeanType(IntEnum):
        NONE = 0
        ARITHMETIC = 1

    ha_rec_models.StatisticMeanType = _StatisticMeanType

    # homeassistant.components.recorder.statistics - official statistics
    # API used by the history backfill: async_import_statistics is a
    # synchronous @callback (a plain MagicMock matches that contract),
    # statistics_during_period is blocking and goes through the recorder's
    # dedicated database executor (get_instance().async_add_executor_job).
    ha_recorder = module("homeassistant.components.recorder")
    ha_recorder.__path__ = []

    async def _recorder_executor_job(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    ha_recorder.get_instance = lambda hass: SimpleNamespace(
        async_add_executor_job=_recorder_executor_job
    )
    ha_rec_stats = module("homeassistant.components.recorder.statistics")
    ha_rec_stats.async_import_statistics = MagicMock()
    ha_rec_stats.statistics_during_period = MagicMock(return_value={})

    # homeassistant.components.websocket_api - async_register_command is used
    # by ui_service to register the panel commands. In real HA it returns
    # None (no deregistration handle) and is called in the handler form
    # (async_register_command(hass, handler)), where it reads the
    # _ws_command/_ws_schema attributes set by the real decorators. The
    # decorator stubs keep the decorated handlers callable; the
    # websocket_command stub additionally stashes the schema on the
    # handler (mirroring real HA) so tests can pin the declared contract.
    ha_ws = module("homeassistant.components.websocket_api")
    ha_ws.async_register_command = MagicMock(return_value=None)

    def _ws_identity_decorator(func):
        return func

    def _ws_websocket_command(schema):
        def decorate(func):
            func._ws_schema = schema
            func._ws_command = next(
                value
                for key, value in schema.items()
                if getattr(key, "schema", None) == "type"
            )
            return func

        return decorate

    ha_ws.require_admin = _ws_identity_decorator
    ha_ws.async_response = _ws_identity_decorator
    ha_ws.websocket_command = _ws_websocket_command

    # homeassistant.components.frontend - async_remove_panel removes the
    # sidebar panel at integration teardown
    ha_frontend = module("homeassistant.components.frontend")
    ha_frontend.async_remove_panel = MagicMock(return_value=None)

    # homeassistant.components.panel_custom - async_register_panel registers
    # the sidebar panel; in real HA it wraps
    # frontend.async_register_built_in_panel (component_name="custom")
    ha_pc = module("homeassistant.components.panel_custom")
    ha_pc.async_register_panel = AsyncMock(return_value=None)

    # StaticPathConfig (re-exported by homeassistant.components.http from
    # http/server.py): serves the integration's www/ folder
    class _StubStaticPathConfig:
        def __init__(self, url_path, path, cache_headers=True):
            self.url_path = url_path
            self.path = path
            self.cache_headers = cache_headers

    ha_http.StaticPathConfig = _StubStaticPathConfig

    # homeassistant.helpers.storage - Store used by the config manager
    ha_storage = module("homeassistant.helpers.storage")

    class _StubStore:
        """Minimal Store: load/save through a class-level registry."""

        registry: dict = {}

        def __init__(self, hass, version, key):
            self.key = key

        async def async_load(self):
            return _StubStore.registry.get(self.key)

        async def async_save(self, data):
            _StubStore.registry[self.key] = data

    ha_storage.Store = _StubStore

    # homeassistant.helpers.event - trackers used by the config manager
    ha_event = module("homeassistant.helpers.event")
    ha_event.async_track_time_interval = MagicMock(return_value=lambda: None)
    ha_event.async_track_state_change_event = MagicMock(return_value=lambda: None)

    # homeassistant.helpers.aiohttp_client
    ha_aiohttp = module("homeassistant.helpers.aiohttp_client")
    ha_aiohttp.async_get_clientsession = MagicMock

    # homeassistant.helpers.entity_platform
    ha_ep = module("homeassistant.helpers.entity_platform")
    ha_ep.async_get_current_platform = MagicMock
    ha_ep.entity_platform = MagicMock

    # homeassistant.helpers.entity_registry - registry lookup used by the
    # coordinator to resolve real entity_ids (entity_registry.async_get)
    ha_er = module("homeassistant.helpers.entity_registry")
    ha_er.async_get = lambda hass: SimpleNamespace(entities={})

    # homeassistant.util.dt - timezone helpers (as_local attaches the HA
    # timezone to naive datetimes; the stub mimics that with UTC)
    ha_util = module("homeassistant.util")
    ha_util.__path__ = []
    ha_dt = module("homeassistant.util.dt")
    ha_dt.as_local = lambda dt: (
        dt if getattr(dt, "tzinfo", None) else dt.replace(tzinfo=timezone.utc)
    )
    ha_dt.as_utc = lambda dt: (
        dt if getattr(dt, "tzinfo", None) else dt.replace(tzinfo=timezone.utc)
    )
    # UTC constant and utcnow are used by the history backfill's AD-11 clip
    ha_dt.UTC = timezone.utc
    ha_dt.utcnow = lambda: datetime.now(timezone.utc)
    # statistics_during_period returns "start" as a float epoch: the clip
    # converts it back with utc_from_timestamp
    ha_dt.utc_from_timestamp = lambda ts: datetime.fromtimestamp(ts, timezone.utc)


_install_homeassistant_stubs()
