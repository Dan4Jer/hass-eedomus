"""Registration of the Eedomus configuration panel for HA 2026+.

Uses the supported API (verified in the HA 2026.9.3 source):

- the panel JS assets in www/ are served through an http StaticPathConfig;
- the sidebar panel is registered as a custom panel
  (homeassistant.components.panel_custom), which wraps
  frontend.async_register_built_in_panel with component_name="custom" and
  the `_panel_custom` module_url config;
- frontend.async_remove_panel removes it at unload.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PANEL_URL_PATH = "eedomus-config"
PANEL_COMPONENT_NAME = "eedomus-config-panel"
PANEL_SIDEBAR_TITLE = "Eedomus Config"
PANEL_SIDEBAR_ICON = "mdi:cog"
PANEL_ASSETS_URL = "/local/eedomus"
_PANEL_REGISTERED_KEY = "panel_registered"


async def async_setup_panel(hass: HomeAssistant) -> None:
    """Serve the panel assets and register the sidebar panel.

    Domain-level and idempotent: async_register_built_in_panel raises a
    ValueError when overwriting an existing panel, so entry reloads must
    be guarded by the panel_registered flag in hass.data[DOMAIN].
    """
    if hass.data[DOMAIN].get(_PANEL_REGISTERED_KEY):
        return

    www_path = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths(
        [
            # Panel assets change with every release: no cache headers.
            StaticPathConfig(PANEL_ASSETS_URL, str(www_path), False)
        ]
    )
    await async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT_NAME,
        sidebar_title=PANEL_SIDEBAR_TITLE,
        sidebar_icon=PANEL_SIDEBAR_ICON,
        module_url=f"{PANEL_ASSETS_URL}/eedomus-panel.js",
        require_admin=True,
    )
    hass.data[DOMAIN][_PANEL_REGISTERED_KEY] = True
    _LOGGER.info(
        "Eedomus configuration panel registered (sidebar: %s, admin only)",
        PANEL_SIDEBAR_TITLE,
    )


async def async_unload_panel(hass: HomeAssistant) -> None:
    """Remove the sidebar panel when the last entry is unloaded."""
    if not hass.data.get(DOMAIN, {}).get(_PANEL_REGISTERED_KEY):
        return
    async_remove_panel(hass, PANEL_URL_PATH)
    hass.data[DOMAIN][_PANEL_REGISTERED_KEY] = False
    _LOGGER.info("Eedomus configuration panel removed")
