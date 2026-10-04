"""E2E tests for the Eedomus Config panel on the live instance (P.1.7).

Covers the panel registration (CAP-1), the websocket commands backing the
four tabs (Périphériques, Règles, Historique, Cohérence), and the save +
auto-apply path (CAP-4). The save test writes the IDENTICAL mapping
content: it exercises the full persist/reload path without changing any
behavior, and archives nothing (skip-if-identical).
"""

import os
import time

import pytest
import requests
import yaml

pytestmark = pytest.mark.e2e

HA_URL = os.environ.get("HA_URL", "http://192.168.1.5:8123")
EXPECTED_PANEL = "eedomus-config"


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
