"""Unit tests for the box metrics buffer and its websocket command.

Covers the story's I/O matrix (CAP-9): the passive cycle capture in
_async_update_data (buffer capped at N cycles, per-cycle API call
delta against the cumulative counters, full and partial paths, a
timed-out cycle records nothing, capture failure never breaks the
refresh), get_box_metrics returning the trimmed cycle series, and
the eedomus/get_box_metrics websocket handler (one section per box
with its entry_id, a raising box skipped without costing the healthy
ones, service_unavailable without a coordinator, _json_safe
serialization).

The homeassistant.* modules are conftest stubs; the websocket layer is
exercised through the EedomusUIService handler invoked directly with
a mock connection (same pattern as test_ui_service.py).
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.const import COORDINATOR
from custom_components.eedomus.coordinator import (
    EedomusDataUpdateCoordinator,
    METRICS_BUFFER_SIZE,
)
from custom_components.eedomus.ui_service import EedomusUIService

pytestmark = pytest.mark.unit

ENTRY_ID = "01METRICS"


def make_coordinator(entry_id=ENTRY_ID):
    """Build a coordinator with stubbed hass/client, ready to cycle."""
    client = MagicMock()
    client.config_entry = SimpleNamespace(options={}, data={})
    coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=client)
    if entry_id is not None:
        coordinator.config_entry = SimpleNamespace(entry_id=entry_id)
    # Never trip the full-refresh heuristic mid-test.
    coordinator._scan_interval = 10**6
    coordinator._full_refresh_needed = False
    coordinator.data = {
        "101": {"periph_id": "101", "name": "Salon"},
        "102": {"periph_id": "102", "name": "Cave"},
    }
    coordinator._all_peripherals = dict(coordinator.data)
    coordinator._dynamic_peripherals = {"101": {"periph_id": "101"}}
    return coordinator


def stub_partial_refresh(coordinator, calls_per_cycle):
    """Mock the partial refresh, bumping the cumulative call counters."""
    ret = {"success": 1, "body": []}

    async def fake_partial():
        coordinator._endpoint_call_counts["get_periph_caract"] += calls_per_cycle
        coordinator._last_api_time = 0.25
        return ret

    coordinator._async_partial_refresh = AsyncMock(side_effect=fake_partial)


def make_service(coordinators):
    """Build a UIService over one or more (entry_id -> coordinator) boxes."""
    hass = MagicMock()
    hass.data = {
        "eedomus": {
            f"entry_{index}": {COORDINATOR: coordinator}
            for index, coordinator in enumerate(coordinators)
        }
    }
    service = EedomusUIService(hass)
    connection = MagicMock()
    return service, connection


class TestCycleCapture:
    """The buffer feeds on _async_update_data, passively (AD-2)."""

    @pytest.mark.asyncio
    async def test_each_cycle_records_durations_counts_and_call_delta(self):
        coordinator = make_coordinator()
        stub_partial_refresh(coordinator, calls_per_cycle=2)

        await coordinator._async_update_data()
        await coordinator._async_update_data()

        assert len(coordinator._metrics_history) == 2
        first, second = coordinator._metrics_history
        # The per-cycle metric is the DELTA of the cumulative counters
        # (never reset), not their running total.
        assert first["api_calls"] == 2
        assert second["api_calls"] == 2
        for cycle in (first, second):
            assert cycle["refresh_time"] >= 0
            assert cycle["api_time"] >= 0
            assert cycle["periphs_total"] == 2
            assert cycle["periphs_dynamic"] == 1
            # Timestamps are ISO strings, JSON-safe as served.
            assert isinstance(cycle["ts"], str)
            assert datetime.fromisoformat(cycle["ts"])

    @pytest.mark.asyncio
    async def test_capture_is_passive_a_failure_never_breaks_the_refresh(self):
        coordinator = make_coordinator()
        stub_partial_refresh(coordinator, calls_per_cycle=1)

        class Boom(list):
            def append(self, item):
                raise RuntimeError("boom")

        coordinator._metrics_history = Boom()

        result = await coordinator._async_update_data()

        # The refresh completed normally; the metrics failure was
        # swallowed (warning only, never an interruption).
        assert result == {"success": 1, "body": []}

    @pytest.mark.asyncio
    async def test_full_refresh_cycle_is_recorded_too(self):
        coordinator = make_coordinator()
        coordinator._full_refresh_needed = True
        stats = {"total_peripherals": 2, "dynamic_peripherals": 1}

        async def fake_full_refresh():
            coordinator._endpoint_call_counts["get_periph_list"] += 1
            return (dict(coordinator.data), stats)

        coordinator._async_full_refresh = AsyncMock(
            side_effect=fake_full_refresh
        )

        await coordinator._async_update_data()

        assert len(coordinator._metrics_history) == 1
        cycle = coordinator._metrics_history[0]
        assert cycle["api_calls"] == 1
        assert cycle["periphs_total"] == 2
        assert cycle["periphs_dynamic"] == 1

    @pytest.mark.asyncio
    async def test_a_timed_out_cycle_records_nothing(self):
        coordinator = make_coordinator()

        async def raise_timeout():
            raise Exception("Request timed out")

        coordinator._async_partial_refresh = AsyncMock(
            side_effect=raise_timeout
        )

        result = await coordinator._async_update_data()

        # Last known good data is served and NO cycle is recorded: a
        # timed-out cycle is not a completed cycle.
        assert result == coordinator.data
        assert len(coordinator._metrics_history) == 0

    def test_missing_or_below_baseline_records_zero_calls(self):
        coordinator = make_coordinator()
        coordinator._endpoint_call_counts["get_periph_caract"] = 12

        # No baseline at all (the guarded read failed): zero, never
        # the unbounded cumulative total.
        coordinator._metrics_cycle_start_calls = None
        coordinator._capture_cycle_metrics(1.0, 0.5)
        assert coordinator._metrics_history[-1]["api_calls"] == 0

        # A cumulative total BELOW the baseline (counters reset under
        # the cycle): zero as well, never a negative.
        coordinator._metrics_cycle_start_calls = 50
        coordinator._capture_cycle_metrics(1.0, 0.5)
        assert coordinator._metrics_history[-1]["api_calls"] == 0

    def test_buffer_is_capped_at_the_last_n_cycles(self):
        coordinator = make_coordinator()
        for index in range(METRICS_BUFFER_SIZE + 5):
            coordinator._capture_cycle_metrics(0.5, 0.1)
            coordinator._metrics_history[-1]["refresh_time"] = float(index)

        assert len(coordinator._metrics_history) == METRICS_BUFFER_SIZE
        # The OLDEST cycles were evicted: the buffer keeps the latest.
        assert coordinator._metrics_history[0]["refresh_time"] == 5.0
        assert coordinator._metrics_history[-1]["refresh_time"] == 34.0


class TestGetBoxMetrics:
    """get_box_metrics renders the series plus the box identity."""

    def test_returns_the_trimmed_payload_the_panel_renders(self):
        coordinator = make_coordinator()
        coordinator._capture_cycle_metrics(1.5, 0.5)
        coordinator._capture_cycle_metrics(2.0, 0.75)

        metrics = coordinator.get_box_metrics()

        assert metrics["entry_id"] == ENTRY_ID
        assert metrics["cycles"] == list(coordinator._metrics_history)
        assert len(metrics["cycles"]) == 2
        # The payload stops at what the panel renders: every card value
        # comes from the cycle records themselves (plus the
        # conditional history-recovery block, story 112).
        assert set(metrics) == {
            "entry_id",
            "name",
            "cycles",
            "active_periphs_last_hour",
            "periphs_by_category",
            "history",
        }
        # History disabled in this harness: the key carries None
        assert metrics["history"] is None

    def test_box_name_resolves_from_the_config_entry_title(self):
        coordinator = make_coordinator()
        coordinator.config_entry = SimpleNamespace(
            entry_id=ENTRY_ID, title="Salon"
        )
        assert coordinator._box_display_name() == "Salon"

    def test_box_name_falls_back_to_api_host_then_host_then_none(self):
        coordinator = make_coordinator()
        coordinator.client.api_host = "192.168.1.10"
        assert coordinator._box_display_name() == "192.168.1.10"
        coordinator.client.api_host = None
        coordinator.client.host = "eedomus.local"
        assert coordinator._box_display_name() == "eedomus.local"
        coordinator.client.host = None
        assert coordinator._box_display_name() is None


class TestGetBoxMetricsHandler:
    """The websocket handler aggregates one section per box (CAP-9)."""

    @pytest.mark.asyncio
    async def test_payload_carries_one_section_per_box_with_entry_id(self):
        first = make_coordinator(entry_id="E1")
        second = make_coordinator(entry_id="E2")
        first._capture_cycle_metrics(1.0, 0.5)
        service, connection = make_service([first, second])

        await service._handle_get_box_metrics(
            service.hass, connection, {"id": 7}
        )

        payload = connection.send_result.call_args[0][1]
        assert [box["entry_id"] for box in payload["boxes"]] == ["E1", "E2"]
        only_buffered = payload["boxes"][0]
        assert len(only_buffered["cycles"]) == 1
        assert only_buffered["cycles"][0]["refresh_time"] == 1.0
        # Trimmed payload: nothing the panel does not render (history
        # rides along, None when the option is off — story 112).
        assert set(only_buffered) == {
            "entry_id",
            "name",
            "cycles",
            "active_periphs_last_hour",
            "periphs_by_category",
            "history",
        }
        # The empty box still gets its section: the panel renders the
        # positive empty state for it, never hides the box.
        assert payload["boxes"][1]["cycles"] == []

    @pytest.mark.asyncio
    async def test_one_raising_box_never_costs_the_healthy_ones(self):
        healthy = make_coordinator(entry_id="E1")
        healthy._capture_cycle_metrics(1.0, 0.5)
        broken = make_coordinator(entry_id="E2")
        broken.get_box_metrics = MagicMock(
            side_effect=RuntimeError("metrics boom")
        )
        service, connection = make_service([healthy, broken])

        await service._handle_get_box_metrics(
            service.hass, connection, {"id": 11}
        )

        # The broken box is skipped with a warning; the healthy box is
        # still served and no error reaches the client.
        payload = connection.send_result.call_args[0][1]
        assert [box["entry_id"] for box in payload["boxes"]] == ["E1"]
        connection.send_error.assert_not_called()

    @pytest.mark.asyncio
    async def test_a_walk_failure_surfaces_as_internal_error(self):
        """A failure of the aggregation walk itself (not one box)
        surfaces as send_error, never as a half-loaded result."""
        service, connection = make_service([])
        service._collect_coordinators = MagicMock(
            side_effect=RuntimeError("walk down")
        )

        await service._handle_get_box_metrics(
            service.hass, connection, {"id": 12}
        )

        connection.send_error.assert_called_once_with(
            12, "internal_error", "Failed to build the box metrics view"
        )
        connection.send_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_coordinator_is_a_nominal_service_unavailable(self):
        service, connection = make_service([])

        await service._handle_get_box_metrics(
            service.hass, connection, {"id": 8}
        )

        connection.send_error.assert_called_once_with(
            8, "service_unavailable", "No eedomus coordinator available"
        )
        connection.send_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_payload_is_json_safe(self):
        coordinator = make_coordinator()
        coordinator.get_box_metrics = lambda: {
            "entry_id": ENTRY_ID,
            "name": None,
            "cycles": [{"ts": datetime(2026, 10, 3, 9, 19)}],
        }
        service, connection = make_service([coordinator])

        await service._handle_get_box_metrics(
            service.hass, connection, {"id": 9}
        )

        payload = connection.send_result.call_args[0][1]
        # _json_safe serialized the embedded datetime as ISO text -
        # the websocket layer never sees a raw datetime.
        assert payload["boxes"][0]["cycles"][0]["ts"] == "2026-10-03T09:19:00"

    @pytest.mark.asyncio
    async def test_a_coordinator_without_the_api_is_skipped_not_fatal(self):
        coordinator = make_coordinator()
        # A coordinator variant without the CAP-9 API is skipped by the
        # multi-box walk instead of failing the aggregation mid-way.
        stripped = MagicMock(spec=[])
        service, connection = make_service([coordinator, stripped])

        await service._handle_get_box_metrics(
            service.hass, connection, {"id": 10}
        )

        payload = connection.send_result.call_args[0][1]
        assert [box["entry_id"] for box in payload["boxes"]] == [ENTRY_ID]


class TestBoxSystemMetrics:
    """Story 111 I/O matrix: the box system periphs sampled per cycle
    (CPU / free space, usage 23 — None when the box has none, never an
    exception on an unparseable state), the activity gauge snapshot and
    the per-category counts, all served by get_box_metrics."""

    def test_cycle_carries_box_system_samples(self):
        coordinator = make_coordinator()
        coordinator.data = {
            "101": {
                "periph_id": "101",
                "name": "CPU Box [demo]",
                "usage_id": "23",
                "last_value": "29.2",
            },
            "102": {
                "periph_id": "102",
                "name": "Espace libre Box [demo]",
                "usage_id": "23",
                "last_value": "2282.452",
            },
        }
        coordinator._capture_cycle_metrics(1.0, 0.5)
        cycle = coordinator._metrics_history[-1]
        assert cycle["cpu"] == 29.2
        assert cycle["free_space_kb"] == 2282.45

    def test_cycle_without_system_periphs_samples_none(self):
        coordinator = make_coordinator()
        coordinator._capture_cycle_metrics(1.0, 0.5)
        cycle = coordinator._metrics_history[-1]
        assert cycle["cpu"] is None
        assert cycle["free_space_kb"] is None

    def test_unparseable_system_value_samples_none(self):
        coordinator = make_coordinator()
        coordinator.data = {
            "101": {
                "periph_id": "101",
                "name": "CPU Box [demo]",
                "usage_id": "23",
                "last_value": "not-a-number",
            }
        }
        coordinator._capture_cycle_metrics(1.0, 0.5)
        cycle = coordinator._metrics_history[-1]
        assert cycle["cpu"] is None

    def test_active_periphs_last_hour_counts_only_recent_changes(self):
        coordinator = make_coordinator()
        now = datetime.now()
        recent = now.strftime("%Y-%m-%d %H:%M:%S")
        old = (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
        coordinator.data = {
            "101": {"periph_id": "101", "last_value_change": recent},
            "102": {"periph_id": "102", "last_value_change": old},
            "103": {"periph_id": "103", "last_value_change": "garbage"},
            "104": {"periph_id": "104"},
        }
        assert coordinator._count_active_periphs_last_hour() == 1

    def test_periphs_by_category_counts_unmapped_too(self):
        coordinator = make_coordinator()
        coordinator.data = {
            "101": {"periph_id": "101", "ha_entity": "sensor"},
            "102": {"periph_id": "102", "ha_entity": "light"},
            "103": {"periph_id": "103"},
        }
        assert coordinator._count_periphs_by_category() == {
            "sensor": 1,
            "light": 1,
            "unmapped": 1,
        }

    def test_get_box_metrics_payload_carries_snapshot_fields(self):
        coordinator = make_coordinator()
        coordinator._capture_cycle_metrics(1.0, 0.5)
        payload = coordinator.get_box_metrics()
        assert isinstance(payload["active_periphs_last_hour"], int)
        assert payload["periphs_by_category"] == {"unmapped": 2}
        assert "cpu" in payload["cycles"][0]
        assert "free_space_kb" in payload["cycles"][0]


class TestHistoryRecoveryIndicators:
    """Story 112: the conditional history-recovery block of the
    box-metrics payload — pure aggregation, no new collection."""

    def _coordinator_with_history(self, **options):
        coordinator = make_coordinator()
        coordinator.client.config_entry = SimpleNamespace(
            options={"history": True, **options}, data={}
        )
        return coordinator

    def test_history_option_off_carries_none(self):
        coordinator = make_coordinator()  # options empty: history off
        assert coordinator._history_recovery_indicators() is None

    def test_indicator_aggregation(self):
        """Completion, points, coverage and queue health aggregate the
        progress map and the derived queue; the ETA follows the worker
        cadence (pending x interval / quota)."""
        coordinator = self._coordinator_with_history(
            history_peripherals_per_scan=5
        )
        coordinator._backfill_eligible_peripherals = {
            "a": {"periph_id": "a"},
            "b": {"periph_id": "b"},
            "c": {"periph_id": "c"},
            "d": {"periph_id": "d"},
        }
        coordinator._backfill_ignored = {"d": True}
        coordinator._backfill_paused = {"c": True}
        coordinator._retry_queue = {
            "b": {"retry_after": 9999999999.0, "error_message": "x"}
        }
        coordinator._history_progress = {
            "a": {
                "completed": True,
                "retrieved_points": 100,
                "total_points": 120,
                "oldest_timestamp": "2025-01-02T00:00:00",
            },
            "b": {
                "completed": False,
                "retrieved_points": 40,
                "total_points": None,
                "oldest_timestamp": "2025-03-01T00:00:00",
            },
            "c": {
                "completed": False,
                "retrieved_points": 10,
                "total_points": None,
                "oldest_timestamp": None,
            },
        }

        indicators = coordinator._history_recovery_indicators()

        assert indicators["eligible"] == 3  # d is ignored
        assert indicators["completed"] == 1
        assert indicators["retrieved_points"] == 150
        # Only estimated totals enter the denominator
        assert indicators["total_points"] == 120
        # The oldest retrieved timestamp across periphs
        assert indicators["oldest_timestamp"] == "2025-01-02T00:00:00"
        # a is completed, c is paused: only b is drainable (in error)
        assert indicators["pending"] == 1
        assert indicators["errors"] == 1
        # ETA = pending x 60 s / quota 5 -> 0.0 h, rounded
        assert indicators["eta_hours"] == 0.0

    def test_no_estimate_and_no_coverage_are_honest(self):
        """total None when nothing carries an estimate, oldest None
        when nothing was retrieved — never a fake number or date."""
        coordinator = self._coordinator_with_history()
        coordinator._backfill_eligible_peripherals = {
            "a": {"periph_id": "a"}
        }
        coordinator._history_progress = {
            "a": {"completed": False, "retrieved_points": 5}
        }
        indicators = coordinator._history_recovery_indicators()
        assert indicators["total_points"] is None
        assert indicators["oldest_timestamp"] is None
        # Quota defaults to 1: one pending periph -> ~0 h ETA
        assert indicators["eta_hours"] == 0.0

    def test_empty_queue_is_the_positive_state(self):
        coordinator = self._coordinator_with_history(
            history_peripherals_per_scan=5
        )
        coordinator._backfill_eligible_peripherals = {
            "a": {"periph_id": "a"}
        }
        coordinator._history_progress = {
            "a": {"completed": True}
        }
        indicators = coordinator._history_recovery_indicators()
        assert indicators["pending"] == 0
        assert indicators["errors"] == 0
        assert indicators["eta_hours"] is None
