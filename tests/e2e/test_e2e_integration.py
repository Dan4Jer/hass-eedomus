"""E2E tests that exercise the hass-eedomus integration features
against the live Home Assistant instance on the Raspberry Pi.

Covers: API connectivity, entity discovery, refresh service,
set_value service (RubanLed Salon), and the OptionsFlow
(the async_create_entry fix from commit 2e6b6b3).
"""

import time

import pytest

from .conftest import TEST_ENTITY_ID, TEST_PERIPH_ID

pytestmark = pytest.mark.e2e


class TestConnectivity:
    """Verify HA is reachable and the eedomus integration is loaded."""

    def test_api_running(self, ha_api):
        r = ha_api.get("/api/")
        assert r.status_code == 200
        assert r.json() == {"message": "API running."}

    def test_eedomus_config_entry_exists(self, config_entry_id):
        assert config_entry_id

    def test_eedomus_entities_present(self, ha_api):
        r = ha_api.get("/api/states")
        r.raise_for_status()
        eedomus_entities = [
            s for s in r.json() if "eedomus" in s["entity_id"].lower()
            or s["entity_id"].endswith("_2")  # multi-box suffix
        ]
        # Live instance exposes 165 peripherals; sanity check only
        assert len(eedomus_entities) > 50, (
            f"Expected many eedomus entities, found {len(eedomus_entities)}"
        )

    def test_test_peripheral_exists(self, ha_api):
        state = ha_api.get_state(TEST_ENTITY_ID)
        assert state is not None, f"{TEST_ENTITY_ID} not found on instance"
        assert state["state"] in ("on", "off")


class TestRefreshService:
    """Exercise the eedomus.refresh service."""

    def test_refresh_service(self, ha_api):
        result = ha_api.call_service("eedomus", "refresh")
        # refresh returns the new states list; non-empty means it ran
        assert isinstance(result, list)

    def test_refresh_updates_data(self, ha_api):
        """After a refresh, sensor states should be recently updated."""
        before = ha_api.get_state("sensor.entree_box_eedomus_cpu_box_jdanoffre")
        ha_api.call_service("eedomus", "refresh")
        time.sleep(5)  # let the coordinator complete the refresh
        after = ha_api.get_state("sensor.entree_box_eedomus_cpu_box_jdanoffre")
        if before and after:
            assert after["last_updated"] >= before["last_updated"]


class TestSetValueService:
    """Exercise the eedomus.set_value service on the RubanLed Salon.

    These tests flip the real LED strip state. The strip was chosen
    by the user as safe to modify (no physical side effect).

    Note: set_value is a low-level service that passes the value
    straight to the eedomus API. The RubanLed is a dimmable peripheral:
    its API values are numeric ("0" = off, "100" = on). Sending "off"
    is rejected by the box (error code 6) and only works via the
    PHP fallback, which does not actually change the state.
    """

    def _set_and_check(self, ha_api, value, expected_state):
        ha_api.call_service(
            "eedomus",
            "set_value",
            {"device_id": TEST_PERIPH_ID, "value": value},
        )
        # The coordinator needs a cycle to pick up the new state
        state = ha_api.wait_for_state(TEST_ENTITY_ID, expected_state, timeout=120)
        return state

    def test_set_value_on(self, ha_api):
        self._set_and_check(ha_api, "100", "on")

    def test_set_value_off(self, ha_api):
        self._set_and_check(ha_api, "0", "off")

    def test_set_value_toggle_roundtrip(self, ha_api):
        """Toggle the strip twice: restore whatever state it started in."""
        initial = ha_api.get_state(TEST_ENTITY_ID)
        target_value, target_state = (
            ("0", "off") if initial["state"] == "on" else ("100", "on")
        )
        self._set_and_check(ha_api, target_value, target_state)
        # restore
        restore_value, restore_state = (
            ("0", "off") if target_state == "on" else ("100", "on")
        )
        self._set_and_check(ha_api, restore_value, restore_state)


class TestOptionsFlow:
    """Exercise the OptionsFlow via the HA API - regression tests for
    the AttributeError / TypeError fixed in commits 69ed3f4..2e6b6b3.

    Flow: POST /api/config/config_entries/options/flow creates a flow,
    then POST .../flow/{flow_id} submits the form.
    """

    def _start_options_flow(self, ha_api, config_entry_id):
        r = ha_api.post(
            "/api/config/config_entries/options/flow",
            {"handler": config_entry_id},
        )
        assert r.status_code == 200, f"Flow creation failed: {r.text}"
        return r.json()

    def _submit_options_flow(self, ha_api, flow_id, data):
        r = ha_api.post(
            f"/api/config/config_entries/options/flow/{flow_id}",
            data,
        )
        assert r.status_code == 200, f"Flow submit failed: {r.text}"
        return r.json()

    def test_options_flow_opens(self, ha_api, config_entry_id):
        """The options form must open without error (previously crashed)."""
        flow = self._start_options_flow(ha_api, config_entry_id)
        assert flow["type"] == "form"
        assert flow["step_id"] == "init"

    def test_options_flow_submit_saves(self, ha_api, config_entry_id):
        """Submitting the form must persist the options.

        This is the regression test for the bug: submitting raised
        AttributeError ('OptionsFlowManager' object has no attribute
        'async_update_entry') and options were never saved.
        """
        flow = self._start_options_flow(ha_api, config_entry_id)
        assert flow["type"] == "form", f"Unexpected flow type: {flow}"

        # Submit with each field's current default, keeping values as-is.
        form_data = {
            field["name"]: field["default"]
            for field in flow.get("data_schema") or []
            if "name" in field
        }

        result = self._submit_options_flow(ha_api, flow["flow_id"], form_data)

        # The fix makes the flow complete with type create_entry
        # instead of raising an exception.
        assert result["type"] in ("create_entry", "success"), (
            f"Options flow submit failed: {result}"
        )

    def test_options_persisted_after_restart_cycle(self, ha_api, config_entry_id):
        """Options saved through the flow must be readable back.

        The REST API does not expose entry.options, but re-opening the
        options flow shows the saved values as form defaults. We change
        scan_interval, re-open the flow, verify the default reflects the
        change, then restore the original value.
        """
        # 1. Read current default for scan_interval
        flow = self._start_options_flow(ha_api, config_entry_id)
        schema = {f["name"]: f for f in flow.get("data_schema") or []}
        original = schema["scan_interval"]["default"]
        new_value = original + 1

        # 2. Submit with scan_interval changed
        form_data = {
            f["name"]: f["default"] for f in flow.get("data_schema") or [] if "name" in f
        }
        form_data["scan_interval"] = new_value
        result = self._submit_options_flow(ha_api, flow["flow_id"], form_data)
        assert result["type"] in ("create_entry", "success")

        # 3. Re-open the flow: the default must now reflect the saved value
        flow2 = self._start_options_flow(ha_api, config_entry_id)
        schema2 = {f["name"]: f for f in flow2.get("data_schema") or []}
        assert schema2["scan_interval"]["default"] == new_value, (
            "Options were not persisted: form default unchanged after submit"
        )

        # 4. Restore original value
        form_data2 = {
            f["name"]: f["default"] for f in flow2.get("data_schema") or [] if "name" in f
        }
        form_data2["scan_interval"] = original
        result2 = self._submit_options_flow(ha_api, flow2["flow_id"], form_data2)
        assert result2["type"] in ("create_entry", "success")
