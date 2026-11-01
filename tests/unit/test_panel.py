"""Unit tests for the Eedomus panel registration (panel.py, P.1.2).

The panel must be registered through the supported HA 2026.9.3 API:
an http StaticPathConfig serving www/ plus a custom panel
(panel_custom.async_register_panel), domain-level and idempotent across
entry reloads, removed when the last entry is deleted.
"""

import json
import re
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
# Deliberately broader than the rewrite regex: double quotes and
# side-effect imports count as imports here, so any import form the
# rewrite misses fails the coverage test below.
_SPECIFIER_SCANNER_RE = re.compile(r"(?:from|import)\s+['\"](\.\.?/[^'\"]+)['\"]")


def all_served_js_files():
    """The entry plus every panel module served through the view."""
    return [WWW_DIR / "eedomus-panel.js", *sorted((WWW_DIR / "panel").glob("*.js"))]


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
        # AD-17 (story 106): the module URL carries the manifest
        # version - every release busts the browser cache natively.
        manifest = json.loads(
            (WWW_DIR.parent / "manifest.json").read_text(encoding="utf-8")
        )
        assert kwargs["module_url"] == (
            f"{PANEL_ASSETS_URL}/eedomus-panel.js?v={manifest['version']}"
        )

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

        hass.http.register_view.assert_not_called()
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


class TestPanelModuleUrlCacheBusting:
    """AD-17 (story 106): the module URL changes with the version."""

    def test_module_url_carries_the_manifest_version(self):
        url = panel_module.panel_module_url()
        assert "?v=" in url
        assert url.startswith(f"{panel_module.PANEL_ASSETS_URL}/eedomus-panel.js")

    def test_a_version_change_changes_the_url(self, monkeypatch, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({"version": "0.99.9"}), encoding="utf-8")
        monkeypatch.setattr(panel_module, "__file__", str(tmp_path / "panel.py"))
        assert panel_module.panel_module_url().endswith("?v=0.99.9")

        manifest.write_text(json.dumps({"version": "0.99.10"}), encoding="utf-8")
        assert panel_module.panel_module_url().endswith("?v=0.99.10")

    def test_unreadable_manifest_falls_back_to_dev(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            panel_module, "__file__", str(tmp_path / "nowhere" / "panel.py")
        )
        assert panel_module.panel_module_url().endswith("?v=dev")


class TestPanelEntryView:
    """Ticket 118: the served entry versions its whole module graph."""

    @pytest.mark.asyncio
    async def test_view_registered_before_the_static_path(self, monkeypatch):
        """aiohttp resolves in registration order: view first, or the
        static prefix swallows the entry URL and no rewrite happens."""
        hass = make_hass()
        register_panel = AsyncMock()
        monkeypatch.setattr(panel_module, "async_register_panel", register_panel)
        calls: list[str] = []
        hass.http.register_view = MagicMock(side_effect=lambda v: calls.append("view"))
        hass.http.async_register_static_paths = AsyncMock(
            side_effect=lambda cfg: calls.append("static")
        )

        await async_setup_panel(hass)

        assert calls == ["view", "static"]
        (view,) = hass.http.register_view.call_args.args
        assert isinstance(view, panel_module.PanelEntryView)
        assert view.url == f"{PANEL_ASSETS_URL}/eedomus-panel.js"
        assert f"{PANEL_ASSETS_URL}/panel/{{filename}}" in view.extra_urls
        assert view.requires_auth is False

    @pytest.mark.asyncio
    async def test_get_serves_versioned_entry(self):
        """GET on the entry URL returns JavaScript whose first-hop
        specifiers carry the manifest version, no heuristic caching."""
        manifest = json.loads(
            (WWW_DIR.parent / "manifest.json").read_text(encoding="utf-8")
        )
        version = manifest["version"]
        view = panel_module.PanelEntryView()
        hass = make_hass()
        hass.async_add_executor_job = AsyncMock(side_effect=lambda fn, *a: fn(*a))
        request = MagicMock()
        request.app = {"hass": hass}

        response = await view.get(request)

        assert response.status == 200
        assert response.content_type == "text/javascript"
        assert response.headers["Cache-Control"] == "no-cache"
        body = response.text
        # Every module the entry imports is fetched with the version.
        for module in (
            "shared.js",
            "coherence.js",
            "peripheriques.js",
            "regles.js",
            "historique.js",
            "supervision.js",
        ):
            assert f"./panel/{module}?v={version}" in body, module
            assert f"from './panel/{module}';" not in body, module
        # The repo file on disk stays plain (rewrite is serve-time only).
        assert ".js?v=" not in (WWW_DIR / "eedomus-panel.js").read_text(
            encoding="utf-8"
        )

    @pytest.mark.asyncio
    async def test_get_serves_versioned_panel_modules(self):
        """GET on a panel module rewrites ITS imports too - a URL's
        query does not reach a module's own imports (RFC 3986 drops
        the base query), so second-hop files must be served through
        the view, not the static path."""
        manifest = json.loads(
            (WWW_DIR.parent / "manifest.json").read_text(encoding="utf-8")
        )
        version = manifest["version"]
        view = panel_module.PanelEntryView()
        hass = make_hass()
        hass.async_add_executor_job = AsyncMock(side_effect=lambda fn, *a: fn(*a))
        request = MagicMock()
        request.app = {"hass": hass}

        for module in ("coherence.js", "coherence-helpers.js", "peripheriques.js"):
            source = (WWW_DIR / "panel" / module).read_text(encoding="utf-8")
            specifiers = _SPECIFIER_SCANNER_RE.findall(source)
            assert specifiers, f"{module} imports nothing - stale test data?"

            response = await view.get(request, filename=module)

            assert response.status == 200, module
            assert response.content_type == "text/javascript", module
            body = response.text
            for specifier in specifiers:
                assert f"{specifier}?v={version}" in body, (module, specifier)

    @pytest.mark.asyncio
    async def test_get_rejects_non_module_paths(self):
        """Only plain .js files directly inside panel/ are served: no
        traversal, no other extensions, no well-shaped missing names -
        anything else is a 404."""
        view = panel_module.PanelEntryView()
        hass = make_hass()
        hass.async_add_executor_job = AsyncMock(side_effect=lambda fn, *a: fn(*a))
        request = MagicMock()
        request.app = {"hass": hass}

        for bad in ("..", "eedomus-panel.js", "styles.css", "sub/dir.js"):
            response = await view.get(request, filename=bad)
            assert response.status == 404, bad

    @pytest.mark.asyncio
    async def test_get_unreadable_entry_returns_500(self):
        """A broken install fails loudly instead of serving stale JS -
        both a missing file (OSError) and a corrupted one
        (UnicodeDecodeError, a ValueError)."""
        view = panel_module.PanelEntryView()
        request = MagicMock()

        for exc in (OSError("gone"), ValueError("bad bytes")):
            hass = make_hass()

            async def fail_job(fn, *args, _exc=exc):
                raise _exc

            hass.async_add_executor_job = fail_job
            request.app = {"hass": hass}

            response = await view.get(request)

            assert response.status == 500, exc

    def test_repo_entry_file_stays_plain(self):
        """The rewrite is serve-time only: the repo file keeps plain
        specifiers, so the node harness and direct loads are untouched."""
        source = (WWW_DIR / "eedomus-panel.js").read_text(encoding="utf-8")
        assert ".js?v=" not in source
        assert "from './panel/shared.js';" in source

    def test_rewrite_covers_every_import_of_every_served_file(self):
        """Fails loudly if a future import form escapes the rewrite: the
        scanner is deliberately broader (double quotes, side-effect
        imports) than the rewrite regex, and runs over the entry and
        every panel module the view serves."""
        for path in all_served_js_files():
            source = path.read_text(encoding="utf-8")
            rewritten = panel_module._rewrite_panel_imports(source, "9.9.9")
            for specifier in _SPECIFIER_SCANNER_RE.findall(source):
                assert f"{specifier}?v=9.9.9" in rewritten, (path.name, specifier)

    def test_rewrite_handles_multiline_imports_and_leaves_strings(self):
        """Multi-line import blocks are rewritten; non-import text is
        not touched apart from specifier-shaped strings."""
        source = (
            "import {\n  a,\n  b,\n} from './panel/shared.js';\n"
            "const label = 'import from shared';\n"
        )
        rewritten = panel_module._rewrite_panel_imports(source, "1.2.3")
        assert "from './panel/shared.js?v=1.2.3';" in rewritten
        assert "const label = 'import from shared';" in rewritten
