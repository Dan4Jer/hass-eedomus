"""E2E-sim strate: multi-box aggregation + destructive actions (CAP-4).

The surfaces the live-Pi strate can never test (one real box,
destructive actions forbidden on it): multi-box aggregation of the
backfill state and box metrics, global-pause fan-out, and the four
destructive backfill actions — executed end-to-end against the
simulated box through the real websocket commands.

The simulated entry is created WITH history enabled: its drain runs
through the production path to the simulator's synthetic
periph.history (CAP-2's success, story 5.2's endpoint).

The real box is never steered: the only shared action is the global
pause, resumed in teardown; the real box's periphs are never targeted
(dump ids are strings, the real box's ids are numeric).
"""

import time

import pytest

from tests.e2e._sim_harness import (
    SimulatedBox,
    create_sim_entry,
    remove_entry,
    sim_entries,
)

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_sim]

WORKER_PASS_SECONDS = 60


@pytest.fixture(scope="module")
def simulated_box():
    """The simulator process on the Pi, started and stopped by the harness."""
    box = SimulatedBox()
    box.start()
    yield box
    box.stop()


@pytest.fixture(scope="module")
def sim_entry_history(ha_api, ws_call, simulated_box):
    """The simulated entry with history ENABLED — its drain exercises
    the production path to the simulator. Removed after the suite,
    with the global pause resumed first (however the suite ends)."""
    for entry in sim_entries(ha_api):
        remove_entry(ha_api, entry["entry_id"])

    entry_id, _ = create_sim_entry(ha_api, history=True)

    yield entry_id

    try:
        ws_call("eedomus/backfill_set_paused", {"global": True, "paused": False})
    except AssertionError:
        pass
    remove_entry(ha_api, entry_id)


def _queue_rows(ws_call):
    state = ws_call("eedomus/get_backfill_state")
    return state["queue"], state


def _sim_rows(ws_call, entry_id):
    queue, _ = _queue_rows(ws_call)
    return [r for r in queue if r.get("entry_id") == entry_id]


def _wait_for(predicate, timeout, interval=5):
    """Deterministic bounded wait (no wall-clock assertion)."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = predicate()
        if last:
            return last
        time.sleep(interval)
    return last


class TestMultiBoxAggregation:
    def test_backfill_state_holds_both_boxes(
        self, ws_call, sim_entry_history
    ):
        """Multi-box queue: the aggregated state carries the simulated
        box's rows (entry_id-distinguished) beside the real box's."""
        rows = _wait_for(
            lambda: _sim_rows(ws_call, sim_entry_history) or None,
            timeout=180,
        )
        assert rows, "no simulated row in the aggregated backfill state"

        queue, state = _queue_rows(ws_call)
        entry_ids = {r.get("entry_id") for r in queue}
        assert sim_entry_history in entry_ids
        # The real box's rows are never mixed up with the simulated
        # ones: a distinct entry_id per row.
        assert len(entry_ids) >= 2, "expected rows of at least two boxes"

    def test_box_metrics_render_two_sections(
        self, ws_call, sim_entry_history
    ):
        """The Supervision payload sections per box: two loaded entries
        produce two sections with distinct entry_ids."""
        result = ws_call("eedomus/get_box_metrics")
        boxes = result["boxes"]
        assert len(boxes) == 2, f"expected two box sections, got {boxes}"
        entry_ids = {b["entry_id"] for b in boxes}
        assert sim_entry_history in entry_ids
        assert len(entry_ids) == 2


class TestProductionPathImport:
    def test_worker_drains_the_simulated_history(
        self, ws_call, sim_entry_history
    ):
        """CAP-2 success: the drain fetches the synthetic history from
        the simulator through the production path (the 5.3 knob routes
        periph.history to the simulator) and imports it."""
        def progressed():
            rows = _sim_rows(ws_call, sim_entry_history)
            done = [r for r in rows if (r.get("retrieved_points") or 0) > 0]
            return done or None

        rows = _wait_for(progressed, timeout=3 * WORKER_PASS_SECONDS + 60)
        assert rows, "no simulated periph progressed (fetch+import)"
        row = rows[0]
        # The synthetic anchor is years deep: a progressed row has a
        # real oldest timestamp, not a fresh one.
        assert row.get("oldest_timestamp"), row


class TestGlobalPauseFanOut:
    def test_global_pause_reaches_both_engines_and_resumes(
        self, ws_call, sim_entry_history
    ):
        """The global switch fans out to every coordinator (one box =
        one entry): the aggregated state flips, and resumes."""
        result = ws_call(
            "eedomus/backfill_set_paused", {"global": True, "paused": True}
        )
        assert result["success"] is True
        assert result["paused"] is True
        state = result["state"]
        assert state["global_paused"] is True

        result = ws_call(
            "eedomus/backfill_set_paused", {"global": True, "paused": False}
        )
        assert result["paused"] is False
        assert result["state"]["global_paused"] is False


class TestDestructiveBackfillActions:
    def test_four_actions_run_end_to_end(self, ws_call, sim_entry_history):
        """retry_now (production import), prioritize, per-periph
        pause/resume, ignore + reactivation — on a simulated periph,
        through the real websocket commands."""
        # A pending simulated row to act on
        rows = _wait_for(
            lambda: [
                r for r in _sim_rows(ws_call, sim_entry_history)
                if r["status"] == "pending"
            ] or None,
            timeout=180,
        )
        assert rows, "no pending simulated periph to act on"
        periph_id = rows[0]["periph_id"]

        # 1. Global pause frees the mono-importer lock (off-schedule
        #    retry is never blocked by the drain), then retry_now
        #    fetches a chunk through the simulator and imports it.
        ws_call(
            "eedomus/backfill_set_paused", {"global": True, "paused": True}
        )
        try:
            result = ws_call(
                "eedomus/backfill_retry_now", {"periph_id": periph_id}
            )
            assert result["success"] is True, result
            assert "imported" in result

            # 2. Per-periph pause, then resume (before prioritizing: the
            #    priority marker is an overlay that masks the paused
            #    status in the row's derivation)
            result = ws_call(
                "eedomus/backfill_set_paused",
                {"periph_id": periph_id, "paused": True},
            )
            assert result["success"] is True, result
            row = next(
                r for r in result["state"]["queue"]
                if r["periph_id"] == periph_id
            )
            assert row["status"] == "paused", row
            result = ws_call(
                "eedomus/backfill_set_paused",
                {"periph_id": periph_id, "paused": False},
            )
            assert result["success"] is True, result

            # 3. Prioritize jumps the queue
            result = ws_call(
                "eedomus/backfill_prioritize", {"periph_id": periph_id}
            )
            assert result["success"] is True, result
            queue_rows = [
                r for r in result["state"]["queue"]
                if r.get("entry_id") == sim_entry_history
            ]
            positions = [r["position"] for r in queue_rows]
            assert positions == sorted(
                positions
            ), "the simulated queue lost its ordering"

            # 4. Ignore (the destructive two-gesture's executed action),
            #    then reactivation — reversible by design.
            result = ws_call(
                "eedomus/backfill_set_ignored",
                {"periph_id": periph_id, "ignored": True},
            )
            assert result["success"] is True, result
            state = result["state"]
            assert periph_id in {
                i.get("periph_id") for i in state["ignored"]
            }, "ignored periph not listed"
            assert not [
                r for r in state["queue"] if r["periph_id"] == periph_id
            ], "ignored periph still in the queue"
            result = ws_call(
                "eedomus/backfill_set_ignored",
                {"periph_id": periph_id, "ignored": False},
            )
            assert result["success"] is True, result
            assert [
                r for r in result["state"]["queue"]
                if r["periph_id"] == periph_id
            ], "reactivated periph not back in the queue"
        finally:
            # The global engine never stays paused, whatever happened
            ws_call(
                "eedomus/backfill_set_paused",
                {"global": True, "paused": False},
            )
