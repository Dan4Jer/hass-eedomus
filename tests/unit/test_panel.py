"""Unit tests for the Eedomus panel registration (panel.py, P.1.2).

The panel must be registered through the supported HA 2026.9.3 API:
an http StaticPathConfig serving www/ plus a custom panel
(panel_custom.async_register_panel), domain-level and idempotent across
entry reloads, removed when the last entry is deleted.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import custom_components.eedomus.panel as panel_module
from custom_components.eedomus.const import DOMAIN
from custom_components.eedomus.panel import (
    PANEL_ASSETS_URL,
    PANEL_COMPONENT_NAME,
    PANEL_SIDEBAR_TITLE,
    PANEL_URL_PATH,
    async_setup_panel,
    async_unload_panel,
)

pytestmark = pytest.mark.unit

WWW_DIR = Path(panel_module.__file__).parent / "www"


def make_hass(registered=False):
    """Build a fake hass with a real DOMAIN dict and an async http app."""
    hass = MagicMock()
    hass.data = {DOMAIN: {"panel_registered": registered}}
    hass.http.async_register_static_paths = AsyncMock()
    return hass


class TestSetupPanel:
    @pytest.mark.asyncio
    async def test_registers_static_path_and_panel(self, monkeypatch):
        """StaticPathConfig serves www/; the panel is admin-only custom."""
        hass = make_hass()
        register_panel = AsyncMock()
        monkeypatch.setattr(panel_module, "async_register_panel", register_panel)

        await async_setup_panel(hass)

        hass.http.async_register_static_paths.assert_awaited_once()
        (static_paths,) = hass.http.async_register_static_paths.await_args.args
        assert len(static_paths) == 1
        static_path = static_paths[0]
        assert static_path.url_path == PANEL_ASSETS_URL
        assert static_path.path == str(WWW_DIR)
        assert static_path.cache_headers is False

        register_panel.assert_awaited_once()
        kwargs = register_panel.await_args.kwargs
        assert kwargs["frontend_url_path"] == PANEL_URL_PATH
        assert kwargs["webcomponent_name"] == PANEL_COMPONENT_NAME
        assert kwargs["sidebar_title"] == PANEL_SIDEBAR_TITLE
        assert kwargs["require_admin"] is True
        assert kwargs["module_url"] == f"{PANEL_ASSETS_URL}/eedomus-panel.js"

        assert hass.data[DOMAIN]["panel_registered"] is True

    @pytest.mark.asyncio
    async def test_static_path_serves_real_www_assets(self):
        """The served path must be the integration's real www/ folder.

        The panel is real ES modules since the story 102 split: the
        entry plus every ./panel/*.js module it imports lives under
        the same static path."""
        assert (WWW_DIR / "eedomus-panel.js").is_file()
        for module in (
            "shared.js",
            "coherence.js",
            "coherence-helpers.js",
            "peripheriques.js",
            "regles.js",
            "historique.js",
            "supervision.js",
        ):
            assert (WWW_DIR / "panel" / module).is_file(), module

    @pytest.mark.asyncio
    async def test_idempotent_across_reloads(self, monkeypatch):
        """A second setup (entry reload) must not re-register anything."""
        hass = make_hass(registered=True)
        register_panel = AsyncMock()
        monkeypatch.setattr(panel_module, "async_register_panel", register_panel)

        await async_setup_panel(hass)

        hass.http.async_register_static_paths.assert_not_awaited()
        register_panel.assert_not_awaited()
        assert hass.data[DOMAIN]["panel_registered"] is True

    @pytest.mark.asyncio
    async def test_webcomponent_matches_the_registered_js_element(self):
        """The webcomponent name must match customElements.define in the JS."""
        panel_js = (WWW_DIR / "eedomus-panel.js").read_text(encoding="utf-8")
        assert f"customElements.define('{PANEL_COMPONENT_NAME}'" in panel_js


class TestUnloadPanel:
    @pytest.mark.asyncio
    async def test_removes_registered_panel(self, monkeypatch):
        """async_remove_panel must be called with the panel url path."""
        hass = make_hass(registered=True)
        remove_panel = MagicMock()
        monkeypatch.setattr(panel_module, "async_remove_panel", remove_panel)

        await async_unload_panel(hass)

        remove_panel.assert_called_once_with(hass, PANEL_URL_PATH)
        assert hass.data[DOMAIN]["panel_registered"] is False

    @pytest.mark.asyncio
    async def test_noop_when_not_registered(self, monkeypatch):
        """No error and no frontend call when the panel was never set up."""
        hass = make_hass(registered=False)
        hass.data[DOMAIN] = {}
        remove_panel = MagicMock()
        monkeypatch.setattr(panel_module, "async_remove_panel", remove_panel)

        await async_unload_panel(hass)

        remove_panel.assert_not_called()
