"""Registration of the Eedomus configuration panel for HA 2026+.

Uses the supported API (verified in the HA 2026.9.3 source):

- every panel JS file (www/eedomus-panel.js and each www/panel/*.js)
  is served through a HomeAssistantView that suffixes every relative
  import specifier with the integration version (ticket 118): a URL's
  query does NOT reach a module's own imports (RFC 3986 drops the base
  query when the reference has a path), so each served file is
  rewritten - every URL in the module graph then carries
  ?v=<manifest version>, and a deploy busts the whole graph;
- the remaining www/ assets fall back to an http StaticPathConfig;
- the sidebar panel is registered as a custom panel
  (homeassistant.components.panel_custom), which wraps
  frontend.async_register_built_in_panel with component_name="custom" and
  the `_panel_custom` module_url config;
- frontend.async_remove_panel removes it at unload.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from aiohttp import web
from homeassistant.components.frontend import async_remove_panel
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
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

_PANEL_ENTRY_FILE = Path(__file__).parent / "www" / "eedomus-panel.js"
_PANEL_MODULES_DIR = Path(__file__).parent / "www" / "panel"
_IMPORT_SPECIFIER_RE = re.compile(r"from '(\./[^']+\.js)'")


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


def _rewrite_panel_imports(source: str, version: str) -> str:
    """Suffix every relative import specifier with the version (118).

    Only static single-quoted `from '...'` specifiers: no served file
    uses dynamic import, double quotes, or `export ... from`, and the
    unit tests pin that (a broader scanner would fail loudly). Repo
    files keep their plain specifiers - the rewrite happens at serve
    time only.
    """
    return _IMPORT_SPECIFIER_RE.sub(
        lambda match: f"from '{match.group(1)}?v={version}'", source
    )


def _load_versioned_js(file_path: Path) -> str:
    """Read a panel JS file from disk and version its imports (blocking).

    Request-time read so a code-mode reload or a deploy serves the
    current file; runs through an executor job to keep the disk I/O off
    the event loop, like HA's own static-resource builder.
    """
    version = _panel_module_version()
    source = file_path.read_text(encoding="utf-8")
    return _rewrite_panel_imports(source, version)


class PanelEntryView(HomeAssistantView):
    """Serve the panel JS files with versioned import specifiers (118).

    Registered before the static path: aiohttp resolves routes in
    registration order, so these exact-match URLs win over the
    /local/eedomus static prefix. A URL's query does not reach a
    module's own imports (RFC 3986 drops the base query), so the entry
    AND every panel module are served through this view, each with its
    specifiers rewritten - no file in the graph is left on an
    unversioned, heuristically-cached URL.
    """

    requires_auth = False
    url = f"{PANEL_ASSETS_URL}/eedomus-panel.js"
    extra_urls = [f"{PANEL_ASSETS_URL}/panel/{{filename}}"]
    name = "eedomus:panel-entry"

    async def get(
        self, request: web.Request, filename: str | None = None
    ) -> web.Response:
        """Serve the entry (no filename) or a panel module, versioned."""
        if filename is None:
            file_path = _PANEL_ENTRY_FILE
        else:
            file_path = (_PANEL_MODULES_DIR / filename).resolve()
            if (
                file_path.parent != _PANEL_MODULES_DIR.resolve()
                or file_path.suffix != ".js"
            ):
                return web.Response(text="Not found", status=404)
        hass = request.app["hass"]
        try:
            source = await hass.async_add_executor_job(_load_versioned_js, file_path)
        except FileNotFoundError:
            return web.Response(text="Not found", status=404)
        except (OSError, ValueError):
            _LOGGER.error("Panel asset not readable: %s", file_path)
            return web.Response(text="Panel asset unavailable", status=500)
        # Panel URLs are fixed paths: no heuristic browser caching.
        return web.Response(
            text=source,
            content_type="text/javascript",
            headers={"Cache-Control": "no-cache"},
        )


async def async_setup_panel(hass: HomeAssistant) -> None:
    """Serve the panel assets and register the sidebar panel.

    Domain-level and idempotent: async_register_built_in_panel raises a
    ValueError when overwriting an existing panel, so entry reloads must
    be guarded by the panel_registered flag in hass.data[DOMAIN].
    """
    if hass.data[DOMAIN].get(_PANEL_REGISTERED_KEY):
        return

    www_path = Path(__file__).parent / "www"
    # Registration order matters: aiohttp resolves in registration order,
    # so the exact-match JS view routes must land before the static prefix.
    hass.http.register_view(PanelEntryView())
    await hass.http.async_register_static_paths(
        [
            # Fallback for non-JS assets: every panel JS file is served
            # versioned through the view above, not from here.
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
