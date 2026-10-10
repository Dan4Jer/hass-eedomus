"""E2E-sim strate: simulated box through the real config flow (CAP-3).

First suite of the simulator strate (marker `e2e_sim`, distinct from
the live-Pi `e2e` strate — AD-16). The harness boots the local API
simulator on the Pi itself, then this suite drives the REAL config
flow through HA's REST flow API: creation with valid credentials,
rejection with bad credentials, entity coexistence beside the real
box, and clean removal of the simulated entry afterwards.

Never exercised here: the real box's entry (not reloaded, not
removed), the backfill (5.5's scope — the simulated entry is created
with history disabled).
"""

import time

import pytest

from tests.e2e._sim_harness import (
    SIM_API_HOST,
    SIM_TITLE_MARK,
    SimulatedBox,
    build_user_input,
    create_sim_entry,
    discard_flow,
    remove_entry,
    sim_entries,
)

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_sim]


@pytest.fixture(scope="module")
def simulated_box():
    """The simulator process on the Pi, started and stopped by the harness."""
    box = SimulatedBox()
    box.start()
    yield box
    box.stop()


@pytest.fixture(scope="module")
def sim_entry(ha_api, simulated_box):
    """The simulated config entry, created through the real flow and
    removed after the suite — even on failure."""
    # Stale-run guard: an entry left by a crashed run blocks the
    # unique_id (eedomus_<api_host>) with already_configured.
    for entry in sim_entries(ha_api):
        remove_entry(ha_api, entry["entry_id"])

    entry_id, _ = create_sim_entry(ha_api)

    yield entry_id

    # Best-effort removal: a test may already have removed the entry.
    remove_entry(ha_api, entry_id)


class TestSimulatedBoxConfigFlow:
    def test_flow_rejects_bad_credentials(self, ha_api, simulated_box):
        """Config flow ko: wrong secret re-shows the form with an error
        and never creates an entry."""
        r = ha_api.post("/api/config/config_entries/flow", {"handler": "eedomus"})
        r.raise_for_status()
        flow_id = r.json()["flow_id"]
        r = ha_api.post(
            f"/api/config/config_entries/flow/{flow_id}",
            build_user_input(api_secret="wrong-secret"),
        )
        r.raise_for_status()
        result = r.json()
        assert result["type"] == "form", result
        assert result["errors"], "the rejected flow must carry errors"
        # Never leaves a pending flow behind
        discard_flow(ha_api, result["flow_id"])

    def test_flow_creates_entry_with_knob(self, sim_entry):
        """Config flow ok: entry created through the real flow."""
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
            found = [s for s in r.json() if "fibaro" in s["entity_id"]]
            if found:
                break
            time.sleep(2)
        assert found, "no dump entity appeared on the instance"

        real_after = ha_api.get_state("sensor.cpu_box_jdanoffre_2")
        assert real_before and real_after
        assert real_before["state"] == real_after["state"]


class TestSimulatedBoxRemoval:
    def test_entry_removed_and_entities_gone(self, ha_api, sim_entry):
        """The simulated entry disappears cleanly via the config-entries
        REST API, and its dump entities are removed."""
        assert remove_entry(ha_api, sim_entry)

        deadline = time.time() + 60
        while time.time() < deadline:
            if not sim_entries(ha_api):
                break
            time.sleep(2)
        assert not sim_entries(ha_api), "simulated entry still present"

        deadline = time.time() + 60
        while time.time() < deadline:
            r = ha_api.get("/api/states")
            r.raise_for_status()
            if not [s for s in r.json() if "fibaro" in s["entity_id"]]:
                return
            time.sleep(2)
        pytest.fail("dump entities still present after entry removal")
