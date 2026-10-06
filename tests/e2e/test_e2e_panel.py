"""E2E tests for the Eedomus Config panel on the live instance (P.1.7).

Covers the panel registration (CAP-1), the websocket commands backing the
four tabs (Périphériques, Règles, Historique, Cohérence), and the save +
auto-apply path (CAP-4). The save test writes the IDENTICAL mapping
content: it exercises the full persist/reload path without changing any
behavior, and archives nothing (skip-if-identical).
"""

import os
import time
from pathlib import Path

import pytest
import requests
import yaml

pytestmark = pytest.mark.e2e

HA_URL = os.environ.get("HA_URL", "http://192.168.1.5:8123")
EXPECTED_PANEL = "eedomus-config"

# The panel is real ES modules (story 102 split): the module list of
# the serving loop is DERIVED from the repo's www/panel/ directory —
# a manual list let supervision.js (4.2) and coherence-helpers.js
# (4.4) drift out silently, the exact regression shape where a 404
# kills the panel while the test stays green. A new module without a
# marker entry fails the test loudly instead of escaping the loop.
PANEL_MODULES_DIR = (
    Path(__file__).resolve().parents[2]
    / "custom_components"
    / "eedomus"
    / "www"
    / "panel"
)

# One distinctive symbol per module (keyed by file name): the file
# must be served AND contain its marker.
PANEL_MODULE_MARKERS = {
    "shared.js": "applySharedMixin",
    "coherence.js": "applyCoherenceMixin",
    "coherence-helpers.js": "COHERENCE_SIGNALS",
    "peripheriques.js": "applyPeripheriquesMixin",
    "regles.js": "applyReglesMixin",
    "historique.js": "applyHistoriqueMixin",
    "supervision.js": "applySupervisionMixin",
}


def _get_peripherals_retrying(ws_call):
    """get_peripherals with a retry: a concurrent entry reload (e.g. the
    OptionsFlow tests) empties coordinator.data for a few seconds."""
    for attempt in range(6):
        result = ws_call("eedomus/get_peripherals")
        if result["total"] > 0:
            return result
        time.sleep(5)
    return result


class TestPanelRegistration:
    def test_panel_in_sidebar(self, ws_call):
        panels = ws_call("get_panels")
        assert EXPECTED_PANEL in panels
        panel = panels[EXPECTED_PANEL]
        assert panel["component_name"] == "custom"
        assert panel["require_admin"] is True

    def test_panel_asset_served(self, ha_headers):
        res = requests.get(
            f"{HA_URL}/local/eedomus/eedomus-panel.js",
            headers=ha_headers,
            timeout=30,
        )
        assert res.status_code == 200
        assert "eedomus-config-panel" in res.text
        # The entry is a real ES module (story 102 split): EVERY tab
        # module must be served by the same static path — a 404 on any
        # one of them (shared.js included) kills the whole panel while
        # the test would otherwise stay green. The loop walks the
        # repo's actual www/panel/ directory; the marker map above
        # keys the serving check per module.
        modules = sorted(path.name for path in PANEL_MODULES_DIR.glob("*.js"))
        assert modules, f"no panel module found in {PANEL_MODULES_DIR}"
        unmarked = [m for m in modules if m not in PANEL_MODULE_MARKERS]
        assert not unmarked, (
            f"panel modules missing a serving marker: {unmarked}"
        )
        for module in modules:
            res_module = requests.get(
                f"{HA_URL}/local/eedomus/panel/{module}",
                headers=ha_headers,
                timeout=30,
            )
            assert res_module.status_code == 200, module
            assert PANEL_MODULE_MARKERS[module] in res_module.text, module


class TestWebsocketCommands:
    def test_get_peripherals_lists_the_box(self, ws_call):
        result = _get_peripherals_retrying(ws_call)
        assert result["total"] > 100
        row = result["peripherals"][0]
        for key in ("periph_id", "name", "usage_id", "entity_id", "modified"):
            assert key in row

    def test_get_coherence_lists_every_peripheral(self, ws_call):
        """Cohérence tab (CAP-6): one fused row per peripheral, signals included."""
        # Same empty-coordinator window as get_peripherals: gate on it first.
        _get_peripherals_retrying(ws_call)
        result = ws_call("eedomus/get_coherence")
        assert result["total"] > 0
        row = result["peripherals"][0]
        for key in ("periph_id", "name", "entity_id", "signals"):
            assert key in row
        # CAP-6 promises a line for every peripheral, mapped or not:
        # the coherence row set must equal the peripherals row set.
        periphs = ws_call("eedomus/get_peripherals")
        coherence_ids = {p["periph_id"] for p in result["peripherals"]}
        periph_ids = {p["periph_id"] for p in periphs["peripherals"]}
        assert coherence_ids == periph_ids

    def test_get_mapping_returns_the_canon(self, ws_call):
        result = ws_call("eedomus/get_mapping")
        assert "metadata" in result["mapping"]

    def test_get_mapping_versions_shape(self, ws_call):
        result = ws_call("eedomus/get_mapping_versions")
        assert "current" in result
        assert isinstance(result["versions"], list)
        for version in result["versions"]:
            assert "timestamp" in version
            assert "config" in version

    def test_validate_config_accepts_the_current_mapping(self, ws_call):
        mapping = ws_call("eedomus/get_mapping")["mapping"]
        yaml_content = yaml.safe_dump(mapping, sort_keys=False, allow_unicode=True)
        result = ws_call("eedomus/validate_config", {"yaml_content": yaml_content})
        assert result["valid"] is True
        assert result["validated_config"] is not None

    def test_get_backfill_state_lists_the_live_queue(self, ws_call):
        """Supervision tab (CAP-5, story 4.1/4.3): the live queue shape.

        Read-only: none of the four actions is exercised on the real
        instance (non-destructive); the queue must be non-empty —
        157 peripherals were pending at epic time.
        """
        result = ws_call("eedomus/get_backfill_state")
        assert isinstance(result["queue"], list)
        assert len(result["queue"]) > 0
        row = result["queue"][0]
        for key in ("periph_id", "name", "status", "position", "entry_id"):
            assert key in row, key
        assert row["status"] in (
            "priority", "in_progress", "error", "paused", "pending",
        )
        assert isinstance(result["ignored"], list)
        assert isinstance(result["global_paused"], bool)
        assert isinstance(result["engine_active"], bool)

    def test_get_box_metrics_serves_the_live_buffer(self, ws_call):
        """Supervision tab (CAP-9, story 4.2): one section per box with
        its refresh-cycle buffer, non-empty once the box has refreshed."""
        result = ws_call("eedomus/get_box_metrics")
        assert isinstance(result["boxes"], list)
        assert len(result["boxes"]) >= 1
        box = result["boxes"][0]
        for key in ("entry_id", "name", "cycles"):
            assert key in box, key
        assert len(box["cycles"]) > 0
        cycle = box["cycles"][-1]
        for key in (
            "ts", "refresh_time", "api_time", "api_calls",
            "periphs_total", "periphs_dynamic",
        ):
            assert key in cycle, key


class TestSaveAutoApply:
    def test_identical_save_applies_and_changes_nothing(self, ws_call):
        """CAP-4 round-trip: persist + auto-apply (entry reload) with the
        identical content - no behavior change, nothing archived."""
        before = ws_call("eedomus/get_mapping")["mapping"]
        versions_before = len(ws_call("eedomus/get_mapping_versions")["versions"])

        result = ws_call("eedomus/save_mapping", {"mapping": before})

        assert result["saved"] is True
        assert result["reloaded_entries"] >= 1
        # The mapping survived the reload untouched
        after = ws_call("eedomus/get_mapping")["mapping"]
        assert after == before
        versions_after = len(ws_call("eedomus/get_mapping_versions")["versions"])
        assert versions_after == versions_before
