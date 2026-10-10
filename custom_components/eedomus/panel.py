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

import json
from pathlib import Path

from homeassistant.components.frontend import async_remove_panel
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .log import get_logger

_LOGGER = get_logger(__name__)

PANEL_URL_PATH = "eedomus-config"
PANEL_COMPONENT_NAME = "eedomus-config-panel"
PANEL_SIDEBAR_TITLE = "Eedomus Config"
PANEL_SIDEBAR_ICON = "mdi:cog"
PANEL_ASSETS_URL = "/local/eedomus"
_PANEL_REGISTERED_KEY = "panel_registered"


def _panel_module_version() -> str:
    """Manifest version of the integration (cache-busting, AD-17).

    Read from manifest.json next to this file; "dev" when unreadable -
    the URL then still busts once per process, never silently stale.
    """
    try:
        manifest = json.loads(
            (Path(__file__).parent / "manifest.json").read_text(encoding="utf-8")
        )
        return str(manifest.get("version") or "dev")
    except (OSError, ValueError):
        return "dev"


def panel_module_url() -> str:
    """The panel module URL, suffixed with the integration version.

    AD-17 (story 106): the version suffix changes with every release,
    so browsers fetch the new module instead of their cache - no more
    forced reloads after a deploy.
    """
    return f"{PANEL_ASSETS_URL}/eedomus-panel.js?v={_panel_module_version()}"


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
        module_url=panel_module_url(),
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
