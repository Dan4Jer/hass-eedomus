"""E2E-sim strate: simulated box through the real config flow (CAP-3).

First suite of the simulator strate (marker `e2e_sim`, distinct from
the live-Pi `e2e` strate — AD-16). The harness boots the local API
simulator on the Pi itself, then this suite drives the REAL config
flow over websocket: creation with valid credentials, rejection with
bad credentials, entity coexistence beside the real box, and clean
removal of the simulated entry afterwards.

Never exercised here: the real box's entry (not reloaded, not
removed), the backfill (5.5's scope — the simulated entry is created
with history disabled).
"""

import time

import pytest

from tests.e2e._sim_harness import (
    SIM_API_HOST,
    SIM_SECRET,
    SIM_USER,
    SimulatedBox,
)

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_sim]

SIM_TITLE_MARK = SIM_API_HOST  # entry title contains the api_host


def _flow_user_input(**overrides):
    """A user step payload accepted by the flow's field validators."""
    payload = {
        "api_host": SIM_API_HOST,
        "history_api_host": SIM_API_HOST,
        "api_eedomus": True,
        "enable_api_proxy": False,
        "api_user": SIM_USER,
        "api_secret": SIM_SECRET,
        "scan_interval": 30,
        "history": False,
        "http_request_timeout": 10,
        "max_concurrent_requests": 5,
        "min_request_delay": 0.5,
        "enable_set_value_retry": False,
        "max_retries": 3,
        "enable_webhook": False,
        "api_proxy_disable_security": False,
        "php_fallback_enabled": False,
        "php_fallback_script_name": "",
        "php_fallback_timeout": 5,
    }
    payload.update(overrides)
    return payload


def _sim_entries(ha_api):
    """The simulated entries present on the instance (stale-run guard)."""
    r = ha_api.get("/api/config/config_entries/entry")
    r.raise_for_status()
    return [
        e for e in r.json()
        if e["domain"] == "eedomus" and SIM_TITLE_MARK in e["title"]
    ]


@pytest.fixture(scope="module")
def simulated_box():
    """The simulator process on the Pi, started and stopped by the harness."""
    box = SimulatedBox()
    box.start()
    yield box
    box.stop()


@pytest.fixture(scope="module")
def sim_entry(ha_api, ws_call, simulated_box):
    """The simulated config entry, created through the real flow and
    removed after the suite — even on failure."""
    # Stale-run guard: an entry left by a crashed run blocks the
    # unique_id (eedomus_<api_host>) with already_configured.
    for entry in _sim_entries(ha_api):
        ws_call("config_entries/remove", {"entry_id": entry["entry_id"]})

    result = ws_call(
        "config_entries/flow", {"domain": "eedomus"}
    )
    flow_id = result["flow_id"]
    result = ws_call(
        "config_entries/flow",
        {"flow_id": flow_id, "user_input": _flow_user_input()},
    )
    assert result["type"] == "create_entry", result
    entry_id = result["result"]["entry_id"]
    assert result["data"].get("history_api_host") == SIM_API_HOST

    yield entry_id

    # Best-effort removal: a test may already have removed the entry,
    # and a teardown must never mask the real failure with a websocket
    # error.
    try:
        ws_call("config_entries/remove", {"entry_id": entry_id})
    except AssertionError:
        pass


class TestSimulatedBoxConfigFlow:
    def test_flow_rejects_bad_credentials(self, ws_call, simulated_box):
        """Config flow ko: wrong secret re-shows the form with an error
        and never creates an entry."""
        result = ws_call("config_entries/flow", {"domain": "eedomus"})
        flow_id = result["flow_id"]
        result = ws_call(
            "config_entries/flow",
            {
                "flow_id": flow_id,
                "user_input": _flow_user_input(api_secret="wrong-secret"),
            },
        )
        assert result["type"] == "form", result
        assert result["errors"], "the rejected flow must carry errors"

    def test_flow_creates_entry_with_knob(self, sim_entry):
        """Config flow ok: entry created with the history knob in data."""
        assert sim_entry

    def test_dump_entities_appear_beside_the_real_box(
        self, ha_api, sim_entry
    ):
        """Coexistence: dump entities appear on the instance while the
        real box's entities keep their states."""
        # The real box's state must not move during the simulated setup
        real_before = ha_api.get_state("sensor.cpu_box_jdanoffre_2")

        deadline = time.time() + 120
        found = None
        while time.time() < deadline:
            r = ha_api.get("/api/states")
            r.raise_for_status()
            found = [
                s for s in r.json()
                if "fibaro" in s["entity_id"]
            ]
            if found:
                break
            time.sleep(2)
        assert found, "no dump entity appeared on the instance"

        real_after = ha_api.get_state("sensor.cpu_box_jdanoffre_2")
        assert real_before and real_after
        assert real_before["state"] == real_after["state"]


class TestSimulatedBoxRemoval:
    def test_entry_removed_and_entities_gone(self, ha_api, ws_call, sim_entry):
        """The simulated entry disappears cleanly: removal via the
        config-entries websocket API, dump entities removed."""
        ws_call("config_entries/remove", {"entry_id": sim_entry})

        deadline = time.time() + 60
        while time.time() < deadline:
            entries = _sim_entries(ha_api)
            if not entries:
                break
            time.sleep(2)
        assert not _sim_entries(ha_api), "simulated entry still present"

        deadline = time.time() + 60
        while time.time() < deadline:
            r = ha_api.get("/api/states")
            r.raise_for_status()
            if not [s for s in r.json() if "fibaro" in s["entity_id"]]:
                return
            time.sleep(2)
        pytest.fail("dump entities still present after entry removal")
