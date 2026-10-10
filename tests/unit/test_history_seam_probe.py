"""Regression tests for story 1.9: the seam probe.

A completed peripheral is never re-fetched by the drain; the seam
probe covers what the one-shot walk cannot: cloud points arrived
after the walk (and the seam hours they may unlock — late entity
registration, a disabled entity, cloud lag at walk time). The probe
keeps ONLY points strictly newer than the frontier — the real cloud
API returns the newest 10,000 points whatever the window (bug 1.10),
so an unfiltered probe would re-import the newest window every pass.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.coordinator import EedomusDataUpdateCoordinator

pytestmark = pytest.mark.unit

PERIPH = "990012"


def _entry(iso, value="20"):
    """A history entry with an ISO naive-local timestamp."""
    return {"value": value, "timestamp": iso}


def _ts(iso):
    """The epoch the coordinator derives from a naive ISO timestamp —
    the same interpretation the probe uses (naive = local time)."""
    return int(datetime.fromisoformat(iso).timestamp())


def make_coordinator(completed=True, last_timestamp=_ts("2026-10-01T09:00:00")):
    """A coordinator with one completed, eligible periph."""
    client = MagicMock()
    client.config_entry = SimpleNamespace(
        options={"history": True, "history_peripherals_per_scan": 1},
        data={},
    )
    coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=client)
    coordinator.config_entry = SimpleNamespace(entry_id="01TEST")
    coordinator.data = {PERIPH: {"periph_id": PERIPH, "name": "Sensor"}}
    coordinator._backfill_eligible_peripherals = {
        PERIPH: {"periph_id": PERIPH, "ha_entity": "sensor"}
    }
    coordinator._history_progress = {
        PERIPH: {
            "last_timestamp": last_timestamp,
            "completed": completed,
            "retrieved_points": 10,
        }
    }
    coordinator._retry_queue = {}
    coordinator._error_count = {}
    coordinator.client.get_device_history = AsyncMock(return_value=[])
    coordinator.async_import_history_chunk = AsyncMock(return_value=0)
    return coordinator


class TestSeamProbe:
    @pytest.mark.asyncio
    async def test_new_points_are_imported_and_frontier_advances(self):
        """Points strictly newer than the frontier are imported, the
        frontier advances, and the periph STAYS completed."""
        coordinator = make_coordinator()
        frontier = _ts("2026-10-01T09:00:00")
        chunk = [
            _entry("2026-10-01T08:00:00"),  # older: filtered out
            _entry("2026-10-01T09:00:00"),  # the frontier: filtered out
            _entry("2026-10-01T10:00:00"),  # new
            _entry("2026-10-01T11:00:00"),  # new
        ]
        coordinator.client.get_device_history = AsyncMock(return_value=chunk)

        await coordinator._seam_probe_one()

        coordinator.async_import_history_chunk.assert_awaited_once()
        imported = coordinator.async_import_history_chunk.call_args.args
        assert imported[0] == PERIPH
        # Only the strictly-newer points reach the import
        assert [e["timestamp"] for e in imported[1]] == [
            "2026-10-01T10:00:00",
            "2026-10-01T11:00:00",
        ]
        progress = coordinator._history_progress[PERIPH]
        assert progress["completed"] is True  # never re-queued
        assert progress["last_timestamp"] == _ts("2026-10-01T11:00:00")
        assert progress["retrieved_points"] == 12  # 10 + 2 new

    @pytest.mark.asyncio
    async def test_dead_window_is_a_no_op(self):
        """A chunk with nothing newer than the frontier imports
        nothing and changes no state."""
        coordinator = make_coordinator()
        coordinator.client.get_device_history = AsyncMock(
            return_value=[
                _entry("2026-10-01T08:00:00"),
                _entry("2026-10-01T09:00:00"),
            ]
        )

        await coordinator._seam_probe_one()

        coordinator.async_import_history_chunk.assert_not_awaited()
        progress = coordinator._history_progress[PERIPH]
        assert progress["last_timestamp"] == _ts("2026-10-01T09:00:00")
        assert progress["retrieved_points"] == 10

    @pytest.mark.asyncio
    async def test_probe_failure_never_poisons_the_periph(self):
        """A client error is logged and skipped: no retry queue, no
        state change."""
        coordinator = make_coordinator()
        coordinator.client.get_device_history = AsyncMock(
            side_effect=RuntimeError("cloud down")
        )

        await coordinator._seam_probe_one()

        assert PERIPH not in coordinator._retry_queue
        assert coordinator._history_progress[PERIPH]["last_timestamp"] == _ts(
            "2026-10-01T09:00:00"
        )

    @pytest.mark.asyncio
    async def test_pending_periphs_are_never_probed(self):
        """No completed periph, no probe — a pending periph is the
        drain's business, never the probe's."""
        coordinator = make_coordinator(completed=False)
        await coordinator._seam_probe_one()
        coordinator.client.get_device_history.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_drain_priority_over_the_probe(self):
        """A non-empty queue drains; the probe does not run."""
        coordinator = make_coordinator()
        coordinator._backfill_eligible_peripherals["990013"] = {
            "periph_id": "990013",
            "ha_entity": "sensor",
        }
        coordinator._history_progress["990013"] = {
            "last_timestamp": 0,
            "completed": False,
        }
        coordinator.client.get_periph_caract = AsyncMock(return_value={})

        async def _fetch(periph_id):
            return [{"value": "1", "timestamp": "2026-10-01T08:00:00"}]

        coordinator.async_fetch_history_chunk = AsyncMock(side_effect=_fetch)

        await coordinator._backfill_drain_pass()

        # The pending periph was drained, the probe never ran
        coordinator.async_fetch_history_chunk.assert_awaited()
        coordinator.async_import_history_chunk.assert_awaited_once_with(
            "990013",
            [{"value": "1", "timestamp": "2026-10-01T08:00:00"}],
        )

    @pytest.mark.asyncio
    async def test_empty_queue_triggers_the_probe(self):
        """Queue empty: the pass ends with one probe of the completed
        periph."""
        coordinator = make_coordinator()
        coordinator.client.get_device_history = AsyncMock(return_value=[])

        await coordinator._backfill_drain_pass()

        coordinator.client.get_device_history.assert_awaited_once_with(
            PERIPH, start_timestamp=_ts("2026-10-01T09:00:00")
        )
