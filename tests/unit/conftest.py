"""Unit test fixtures.

These tests run locally WITHOUT a Home Assistant installation.
The `homeassistant.*` modules are stubbed in sys.modules before the
integration modules are imported, so the pure logic (mapping rules,
value decoding, error handling, options flow submission) can be
tested in isolation.
"""

import sys
import types
from unittest.mock import MagicMock


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
        "LIGHT", "SWITCH", "COVER", "SENSOR", "BINARY_SENSOR",
        "CLIMATE", "SELECT", "SCENE", "FAN", "LOCK",
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

    # homeassistant.helpers.entity
    ha_entity = module("homeassistant.helpers.entity")
    ha_entity.Entity = MagicMock
    ha_entity.DeviceInfo = dict

    # homeassistant.helpers.update_coordinator
    ha_coord = module("homeassistant.helpers.update_coordinator")
    ha_coord.CoordinatorEntity = MagicMock

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

    # homeassistant.components (+ http, sensor) - needed by __init__.py chain
    ha_components = module("homeassistant.components")
    ha_components.__path__ = []
    ha_http = module("homeassistant.components.http")
    ha_http.HomeAssistantView = type("HomeAssistantView", (), {})
    ha_sensor = module("homeassistant.components.sensor")
    ha_sensor.SensorEntity = MagicMock

    # homeassistant.helpers.aiohttp_client
    ha_aiohttp = module("homeassistant.helpers.aiohttp_client")
    ha_aiohttp.async_get_clientsession = MagicMock

    # homeassistant.helpers.entity_platform
    ha_ep = module("homeassistant.helpers.entity_platform")
    ha_ep.async_get_current_platform = MagicMock
    ha_ep.entity_platform = MagicMock


_install_homeassistant_stubs()
