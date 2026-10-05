"""Unit tests for the CAP-5 backfill queue control commands.

Covers the story's I/O matrix: the derived queue state (statuses,
1-based positions, ignored periphs listed separately), the four
actions (retry now, prioritize, pause/resume, ignore) and their
effect on the queue, the mono-importer lock (busy = nominal
refusal), and the .storage persistence surviving a coordinator
re-instantiation (via the conftest _StubStore registry).

The websocket layer is exercised through the EedomusUIService
handlers, invoked directly with a mock connection (same pattern as
test_ui_service.py). The homeassistant.* modules are conftest stubs.
"""

import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.const import COORDINATOR
from custom_components.eedomus.coordinator import (
    EedomusBackfillError,
    EedomusDataUpdateCoordinator,
)
from custom_components.eedomus.ui_service import EedomusUIService

pytestmark = pytest.mark.unit

ENTRY_ID = "01BACKFILL"
PERIPH_ERROR = "101"
PERIPH_PAUSED = "102"
PERIPH_PENDING = "103"
PERIPH_PRIORITY = "104"
PERIPH_IGNORED = "105"
PERIPH_COMPLETED = "106"

PERIPH_IDS = [
    PERIPH_ERROR,
    PERIPH_PAUSED,
    PERIPH_PENDING,
    PERIPH_PRIORITY,
    PERIPH_IGNORED,
    PERIPH_COMPLETED,
]


@pytest.fixture(autouse=True)
def _clear_stub_store_registry():
    """Isolate the _StubStore class-level registry per test."""
    from homeassistant.helpers.storage import Store

    Store.registry.clear()
    yield
    Store.registry.clear()


def make_coordinator(entry_id=ENTRY_ID, enable_history=True):
    """Build a coordinator with stubbed hass/client and a pending queue."""
    client = MagicMock()
    client.config_entry = SimpleNamespace(options={"history": enable_history}, data={})
    coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=client)
    if entry_id is not None:
        coordinator.config_entry = SimpleNamespace(entry_id=entry_id)
    coordinator.data = {
        periph_id: {"periph_id": periph_id, "name": f"Device {periph_id}"}
        for periph_id in PERIPH_IDS
    }
    coordinator._dynamic_peripherals = {
        periph_id: {"periph_id": periph_id, "ha_entity": "sensor"}
        for periph_id in PERIPH_IDS
    }
    coordinator._history_progress = {
        periph_id: {"last_timestamp": 0, "completed": False}
        for periph_id in PERIPH_IDS
    }
    # The completed periph never re-enters the queue.
    coordinator._history_progress[PERIPH_COMPLETED]["completed"] = True
    coordinator._retry_queue = {}
    coordinator._error_count = {}
    coordinator.client.get_periph_caract = AsyncMock(
        return_value={
            "body": [{"periph_id": periph_id, "value": 42} for periph_id in PERIPH_IDS],
            "_raw_data_size_bytes": 128,
        }
    )
    coordinator._create_error_sensors = AsyncMock()
    coordinator.async_fetch_history_chunk = AsyncMock(return_value=[])
    coordinator.async_import_history_chunk = AsyncMock(return_value=0)
    return coordinator


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


class TestGetBackfillState:
    """The queue is derived: statuses, positions, ignored listed apart."""

    def test_state_derives_statuses_positions_and_ignored(self):
        coordinator = make_coordinator()
        retry_after = datetime.now() + timedelta(hours=12)
        coordinator._retry_queue[PERIPH_ERROR] = {
            "error_time": datetime.now().timestamp(),
            "retry_after": retry_after.timestamp(),
            "error_message": "API error",
            "attempts": 2,
        }
        coordinator._backfill_paused = {PERIPH_PAUSED}
        coordinator._backfill_ignored = {PERIPH_IGNORED}
        coordinator._backfill_priority = [PERIPH_PRIORITY]

        state = coordinator.get_backfill_state()

        queue = {row["periph_id"]: row for row in state["queue"]}
        assert set(queue) == {
            PERIPH_ERROR,
            PERIPH_PAUSED,
            PERIPH_PENDING,
            PERIPH_PRIORITY,
        }
        # The prioritized periph jumps to the head of the queue.
        assert state["queue"][0]["periph_id"] == PERIPH_PRIORITY
        assert queue[PERIPH_PRIORITY]["status"] == "priority"
        assert queue[PERIPH_PRIORITY]["position"] == 1
        assert queue[PERIPH_ERROR]["status"] == "error"
        assert queue[PERIPH_ERROR]["error_message"] == "API error"
        assert queue[PERIPH_ERROR]["attempts"] == 2
        # retry_after reaches the panel timezone-aware.
        row_retry_after = queue[PERIPH_ERROR]["retry_after"]
        assert row_retry_after.tzinfo is not None
        assert abs(row_retry_after.timestamp() - retry_after.timestamp()) < 1
        assert queue[PERIPH_PAUSED]["status"] == "paused"
        assert queue[PERIPH_PAUSED]["position"] == 3
        assert queue[PERIPH_PENDING]["status"] == "pending"
        assert queue[PERIPH_PENDING]["position"] == 4
        # Names come from coordinator.data; the row names its box.
        assert queue[PERIPH_PENDING]["name"] == f"Device {PERIPH_PENDING}"
        assert queue[PERIPH_PENDING]["entry_id"] == ENTRY_ID
        # The ignored periph quits the queue and is listed separately.
        assert PERIPH_IGNORED not in queue
        assert state["ignored"] == [
            {
                "periph_id": PERIPH_IGNORED,
                "name": f"Device {PERIPH_IGNORED}",
                "entry_id": ENTRY_ID,
            }
        ]
        # The completed periph is not in the queue nor the ignored list.
        assert PERIPH_COMPLETED not in queue
        assert state["global_paused"] is False
        assert state["engine_active"] is False

    def test_state_engine_active_while_importing(self):
        coordinator = make_coordinator()
        coordinator._backfill_active_periph = PERIPH_PENDING

        state = coordinator.get_backfill_state()

        assert state["engine_active"] is True
        queue = {row["periph_id"]: row for row in state["queue"]}
        assert queue[PERIPH_PENDING]["status"] == "in_progress"

    def test_retry_window_elapsed_degrades_to_pending(self):
        """An error whose retry_after has passed is pending again (the
        natural drain retries it off the retry queue), but the failure
        history stays on the row: the panel needs the reason exactly
        when the periph becomes actionable again.
        """
        coordinator = make_coordinator()
        coordinator._retry_queue[PERIPH_ERROR] = {
            "error_time": datetime.now().timestamp(),
            "retry_after": datetime.now().timestamp() - 3600,
            "error_message": "API error",
            "attempts": 1,
        }

        state = coordinator.get_backfill_state()

        queue = {row["periph_id"]: row for row in state["queue"]}
        assert queue[PERIPH_ERROR]["status"] == "pending"
        assert queue[PERIPH_ERROR]["error_message"] == "API error"
        assert queue[PERIPH_ERROR]["attempts"] == 1
        assert queue[PERIPH_ERROR]["retry_after"].tzinfo is not None


class TestRetryNow:
    """Retry now: off-schedule immediate retry, purge, mono-importer."""

    @pytest.mark.asyncio
    async def test_retry_now_purges_retry_entry_and_imports(self):
        coordinator = make_coordinator()
        coordinator._retry_queue[PERIPH_ERROR] = {
            "error_time": datetime.now().timestamp(),
            "retry_after": (datetime.now() + timedelta(hours=23)).timestamp(),
            "error_message": "API error",
            "attempts": 3,
        }
        chunk = [{"value": 1, "timestamp": "2026-09-27T08:00:00"}]
        coordinator.async_fetch_history_chunk = AsyncMock(return_value=chunk)
        coordinator.async_import_history_chunk = AsyncMock(return_value=1)

        result = await coordinator.async_backfill_retry_now(PERIPH_ERROR)

        assert result == {
            "success": True,
            "periph_id": PERIPH_ERROR,
            "imported": 1,
            "status": "pending",
        }
        # The retry entry is purged: the next drain retries off-schedule.
        assert PERIPH_ERROR not in coordinator._retry_queue
        coordinator.async_fetch_history_chunk.assert_awaited_once_with(PERIPH_ERROR)
        coordinator.async_import_history_chunk.assert_awaited_once_with(
            PERIPH_ERROR, chunk
        )
        # The active periph is released once the import is done.
        assert coordinator._backfill_active_periph is None

    @pytest.mark.asyncio
    async def test_retry_now_reports_a_refailed_retry(self):
        """Outcome honesty: a re-failed fetch puts the periph back in the
        retry queue, and the result says so (status error + the new
        error_message/retry_after) instead of a bare imported=0.
        """
        coordinator = make_coordinator()

        async def _refailing_fetch(periph_id):
            coordinator._retry_queue[periph_id] = {
                "error_time": datetime.now().timestamp(),
                "retry_after": (datetime.now() + timedelta(hours=24)).timestamp(),
                "error_message": "API error again",
                "attempts": 4,
            }
            return []

        coordinator.async_fetch_history_chunk = AsyncMock(side_effect=_refailing_fetch)
        coordinator.async_import_history_chunk = AsyncMock(return_value=0)

        result = await coordinator.async_backfill_retry_now(PERIPH_ERROR)

        assert result["success"] is True
        assert result["imported"] == 0
        assert result["status"] == "error"
        assert result["error_message"] == "API error again"
        assert result["retry_after"].tzinfo is not None
        # The retry entry was purged before the fetch; the fresh one is
        # whatever the (stubbed) fetch put back for the new failure.
        fresh = coordinator._retry_queue[PERIPH_ERROR]
        assert fresh["error_message"] == "API error again"

    @pytest.mark.asyncio
    async def test_retry_now_completing_the_periph_reports_completed(self):
        coordinator = make_coordinator()
        chunk = [{"value": 1, "timestamp": "2026-09-27T08:00:00"}]

        async def _completing_fetch(periph_id):
            coordinator._history_progress[periph_id]["completed"] = True
            return chunk

        coordinator.async_fetch_history_chunk = AsyncMock(side_effect=_completing_fetch)
        coordinator.async_import_history_chunk = AsyncMock(return_value=1)

        result = await coordinator.async_backfill_retry_now(PERIPH_PENDING)

        assert result["status"] == "completed"
        assert result["imported"] == 1

    @pytest.mark.asyncio
    async def test_retry_now_busy_lock_is_a_nominal_refusal(self):
        """A held mono-importer lock refuses without waiting."""
        coordinator = make_coordinator()
        async with coordinator._backfill_import_lock:
            with pytest.raises(EedomusBackfillError) as excinfo:
                await coordinator.async_backfill_retry_now(PERIPH_PENDING)

        assert excinfo.value.error_type == "error"
        coordinator.async_fetch_history_chunk.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "periph_id, setup",
        [
            ("999", "unknown"),
            (PERIPH_COMPLETED, "completed"),
            (PERIPH_IGNORED, "ignored"),
            (PERIPH_PAUSED, "paused"),
        ],
        ids=["unknown", "completed", "ignored", "paused"],
    )
    async def test_retry_now_refuses_unknown_completed_ignored_paused(
        self, periph_id, setup
    ):
        coordinator = make_coordinator()
        coordinator._backfill_ignored = {PERIPH_IGNORED}
        coordinator._backfill_paused = {PERIPH_PAUSED}

        with pytest.raises(EedomusBackfillError) as excinfo:
            await coordinator.async_backfill_retry_now(periph_id)

        assert excinfo.value.error_type == "invalid_format"
        coordinator.async_fetch_history_chunk.assert_not_awaited()


class TestPrioritize:
    """Prioritize: head of queue at the next drain, then consumed."""

    @pytest.mark.asyncio
    async def test_prioritized_periph_is_taken_first_and_consumed(self):
        coordinator = make_coordinator()
        # Quota 1: only the head of the queue is drained this cycle.
        coordinator.client.config_entry.options["history_peripherals_per_scan"] = 1
        coordinator._backfill_priority = [PERIPH_PRIORITY]

        await coordinator._async_partial_refresh()

        coordinator.async_fetch_history_chunk.assert_awaited_once_with(
            PERIPH_PRIORITY
        )
        # The priority jump is consumed by the drain that used it.
        assert coordinator._backfill_priority == []

    @pytest.mark.asyncio
    async def test_prioritize_action_appends_to_priority_list(self):
        coordinator = make_coordinator()

        result = await coordinator.async_backfill_prioritize(PERIPH_PENDING)

        assert result == {
            "success": True,
            "periph_id": PERIPH_PENDING,
            "prioritized": True,
        }
        assert PERIPH_PENDING in coordinator._backfill_priority

    @pytest.mark.asyncio
    async def test_prioritize_unknown_periph_refused(self):
        coordinator = make_coordinator()

        with pytest.raises(EedomusBackfillError) as excinfo:
            await coordinator.async_backfill_prioritize("999")

        assert excinfo.value.error_type == "invalid_format"

    @pytest.mark.asyncio
    async def test_prioritize_refuses_completed_and_ignored(self):
        """A priority entry for a completed or ignored periph would never
        drain and linger forever: refused as invalid_format.
        """
        coordinator = make_coordinator()
        coordinator._backfill_ignored = {PERIPH_IGNORED}

        with pytest.raises(EedomusBackfillError) as excinfo:
            await coordinator.async_backfill_prioritize(PERIPH_COMPLETED)
        assert excinfo.value.error_type == "invalid_format"

        with pytest.raises(EedomusBackfillError) as excinfo:
            await coordinator.async_backfill_prioritize(PERIPH_IGNORED)
        assert excinfo.value.error_type == "invalid_format"

        assert coordinator._backfill_priority == []

    @pytest.mark.asyncio
    async def test_paused_periph_stays_prioritizable(self):
        """A pause is temporary: the jump outlives it."""
        coordinator = make_coordinator()
        coordinator._backfill_paused = {PERIPH_PAUSED}

        result = await coordinator.async_backfill_prioritize(PERIPH_PAUSED)

        assert result["prioritized"] is True
        assert PERIPH_PAUSED in coordinator._backfill_priority


class TestPause:
    """Pause: per-periph set persisted, global switch skips the drain."""

    @pytest.mark.asyncio
    async def test_global_pause_stops_drain_without_breaking_resume(self):
        coordinator = make_coordinator()

        await coordinator.async_backfill_set_paused(global_pause=True, paused=True)
        assert coordinator._backfill_global_paused is True

        # Global pause: no history import this cycle, quota untouched.
        await coordinator._async_partial_refresh()
        coordinator.async_fetch_history_chunk.assert_not_awaited()
        assert coordinator._last_history_periphs == 0

        # Resume: the drain is restored intact.
        await coordinator.async_backfill_set_paused(global_pause=True, paused=False)
        assert coordinator._backfill_global_paused is False

        await coordinator._async_partial_refresh()
        assert coordinator.async_fetch_history_chunk.await_count > 0

    @pytest.mark.asyncio
    async def test_paused_periph_is_skipped_by_the_drain(self):
        coordinator = make_coordinator()
        coordinator.client.config_entry.options["history_peripherals_per_scan"] = 10
        coordinator._backfill_paused = {PERIPH_PAUSED}

        await coordinator._async_partial_refresh()

        fetched = [
            call.args[0]
            for call in coordinator.async_fetch_history_chunk.call_args_list
        ]
        assert PERIPH_PAUSED not in fetched
        assert PERIPH_PENDING in fetched

    @pytest.mark.asyncio
    async def test_set_paused_persists_and_returns_nominal(self):
        coordinator = make_coordinator()

        result = await coordinator.async_backfill_set_paused(
            PERIPH_PAUSED, paused=True
        )

        assert result == {
            "success": True,
            "periph_id": PERIPH_PAUSED,
            "paused": True,
        }
        assert coordinator._backfill_paused == {PERIPH_PAUSED}
        # The paused periph stays in the state queue with a paused status.
        state = coordinator.get_backfill_state()
        queue = {row["periph_id"]: row for row in state["queue"]}
        assert queue[PERIPH_PAUSED]["status"] == "paused"

        # Resume drops the pause.
        await coordinator.async_backfill_set_paused(PERIPH_PAUSED, paused=False)
        assert coordinator._backfill_paused == set()

    @pytest.mark.asyncio
    async def test_set_paused_unknown_periph_or_no_target_refused(self):
        coordinator = make_coordinator()

        with pytest.raises(EedomusBackfillError) as excinfo:
            await coordinator.async_backfill_set_paused("999", paused=True)
        assert excinfo.value.error_type == "invalid_format"

        with pytest.raises(EedomusBackfillError) as excinfo:
            await coordinator.async_backfill_set_paused(paused=True)
        assert excinfo.value.error_type == "invalid_format"


class TestIgnore:
    """Ignore: quits the queue, progress kept, persisted, reversible."""

    @pytest.mark.asyncio
    async def test_ignore_removes_from_queue_and_reactivates(self):
        coordinator = make_coordinator()

        result = await coordinator.async_backfill_set_ignored(
            PERIPH_PENDING, ignored=True
        )

        assert result == {
            "success": True,
            "periph_id": PERIPH_PENDING,
            "ignored": True,
        }
        # Out of the queue, listed separately, progress NOT erased.
        state = coordinator.get_backfill_state()
        queue_ids = {row["periph_id"] for row in state["queue"]}
        assert PERIPH_PENDING not in queue_ids
        assert state["ignored"] == [
            {
                "periph_id": PERIPH_PENDING,
                "name": f"Device {PERIPH_PENDING}",
                "entry_id": ENTRY_ID,
            }
        ]
        assert coordinator._history_progress[PERIPH_PENDING]["completed"] is False

        # Reactivation puts the periph back in the queue, progress intact.
        await coordinator.async_backfill_set_ignored(PERIPH_PENDING, ignored=False)
        state = coordinator.get_backfill_state()
        queue_ids = {row["periph_id"] for row in state["queue"]}
        assert PERIPH_PENDING in queue_ids
        assert state["ignored"] == []

    @pytest.mark.asyncio
    async def test_ignore_voids_a_pending_priority_jump(self):
        coordinator = make_coordinator()
        await coordinator.async_backfill_prioritize(PERIPH_PENDING)

        await coordinator.async_backfill_set_ignored(PERIPH_PENDING, ignored=True)

        assert coordinator._backfill_priority == []

    @pytest.mark.asyncio
    async def test_set_ignored_unknown_periph_refused(self):
        coordinator = make_coordinator()

        with pytest.raises(EedomusBackfillError) as excinfo:
            await coordinator.async_backfill_set_ignored("999", ignored=True)

        assert excinfo.value.error_type == "invalid_format"


class TestPersistence:
    """Ignored/paused/global pause survive a coordinator re-instantiation."""

    @pytest.mark.asyncio
    async def test_control_state_survives_reinstantiation(self):
        first = make_coordinator(entry_id=ENTRY_ID)
        await first.async_backfill_set_ignored(PERIPH_IGNORED, ignored=True)
        await first.async_backfill_set_paused(PERIPH_PAUSED, paused=True)
        await first.async_backfill_set_paused(global_pause=True, paused=True)

        # Re-instantiation: a fresh coordinator on the same config entry
        # reloads the control state from the store.
        second = make_coordinator(entry_id=ENTRY_ID)
        await second._load_backfill_persistence()

        assert second._backfill_ignored == {PERIPH_IGNORED}
        assert second._backfill_paused == {PERIPH_PAUSED}
        assert second._backfill_global_paused is True

    @pytest.mark.asyncio
    async def test_first_refresh_reloads_the_control_state(self):
        """The restart-survival wiring: async_config_entry_first_refresh
        (not just a direct _load_backfill_persistence call) repopulates
        the control state from the store.
        """
        from homeassistant.helpers.storage import Store

        Store.registry[f"eedomus.backfill_{ENTRY_ID}"] = {
            "ignored": [PERIPH_IGNORED],
            "paused": [PERIPH_PAUSED],
            "global_paused": True,
            "config_schema_version": 1,
        }
        coordinator = make_coordinator(entry_id=ENTRY_ID)
        # Heavy refresh internals stubbed: the test pins the wiring, not
        # the refresh itself.
        coordinator._load_yaml_config_async = AsyncMock(return_value={})
        coordinator._load_history_progress = AsyncMock()
        coordinator._async_full_data_retreive = AsyncMock(return_value=([], [], []))

        await coordinator.async_config_entry_first_refresh()

        assert coordinator._backfill_ignored == {PERIPH_IGNORED}
        assert coordinator._backfill_paused == {PERIPH_PAUSED}
        assert coordinator._backfill_global_paused is True

    @pytest.mark.asyncio
    async def test_future_schema_version_starts_empty(self, caplog):
        """A store written by a newer integration is not loaded
        unvalidated: the control state starts empty, with a warning.
        """
        import logging

        from homeassistant.helpers.storage import Store

        Store.registry[f"eedomus.backfill_{ENTRY_ID}"] = {
            "ignored": [PERIPH_IGNORED],
            "paused": [PERIPH_PAUSED],
            "global_paused": True,
            "config_schema_version": 99,
        }
        coordinator = make_coordinator(entry_id=ENTRY_ID)
        caplog.set_level(
            logging.WARNING, logger="custom_components.eedomus.coordinator"
        )

        await coordinator._load_backfill_persistence()

        assert coordinator._backfill_ignored == set()
        assert coordinator._backfill_paused == set()
        assert coordinator._backfill_global_paused is False
        assert "newer than" in caplog.text

    @pytest.mark.asyncio
    async def test_empty_store_starts_with_empty_sets(self):
        coordinator = make_coordinator(entry_id=ENTRY_ID)

        await coordinator._load_backfill_persistence()

        assert coordinator._backfill_ignored == set()
        assert coordinator._backfill_paused == set()
        assert coordinator._backfill_global_paused is False

    @pytest.mark.asyncio
    async def test_store_without_version_is_stamped_not_migrated(self):
        from homeassistant.helpers.storage import Store

        Store.registry[f"eedomus.backfill_{ENTRY_ID}"] = {
            "ignored": [PERIPH_IGNORED],
            "paused": [],
            "global_paused": True,
        }

        coordinator = make_coordinator(entry_id=ENTRY_ID)
        await coordinator._load_backfill_persistence()

        assert coordinator._backfill_ignored == {PERIPH_IGNORED}
        assert coordinator._backfill_global_paused is True
        stored = Store.registry[f"eedomus.backfill_{ENTRY_ID}"]
        assert stored["config_schema_version"] == 1

    @pytest.mark.asyncio
    async def test_no_entry_id_disables_persistence_silently(self):
        # No config_entry at all (entry_id=None leaves the attribute
        # unset): the store is skipped, not an error.
        coordinator = make_coordinator(entry_id=None)

        await coordinator.async_backfill_set_ignored(PERIPH_IGNORED, ignored=True)

        assert coordinator._backfill_ignored == {PERIPH_IGNORED}


class TestWebsocketHandlers:
    """The 5 commands through the EedomusUIService handlers."""

    @pytest.mark.asyncio
    async def test_get_backfill_state_aggregates_multi_box(self):
        box1 = make_coordinator()
        box1._backfill_ignored = {PERIPH_IGNORED}
        box2 = make_coordinator()
        box2._backfill_global_paused = True
        service, connection = make_service([box1, box2])

        await service._handle_get_backfill_state(service.hass, connection, {"id": 1})

        result = connection.send_result.call_args.args[1]
        queue_ids = {row["periph_id"] for row in result["queue"]}
        # box1 ignores 105, box2 does not: the flat list carries every
        # pending row of both boxes (105 comes from box2).
        assert queue_ids == set(PERIPH_IDS) - {PERIPH_COMPLETED}
        assert len(result["queue"]) == 9
        # Every row names its box (multi-box: same entry id here).
        assert all(row["entry_id"] == ENTRY_ID for row in result["queue"])
        assert result["global_paused"] is True
        assert result["engine_active"] is False
        json.dumps(result)

    @pytest.mark.asyncio
    async def test_get_backfill_state_no_coordinator_service_unavailable(self):
        service, connection = make_service([])

        await service._handle_get_backfill_state(service.hass, connection, {"id": 1})

        connection.send_result.assert_not_called()
        connection.send_error.assert_called_once()
        assert connection.send_error.call_args.args[1] == "service_unavailable"

    @pytest.mark.asyncio
    async def test_get_backfill_state_payload_is_json_serializable(self):
        coordinator = make_coordinator()
        retry_after = datetime.now() + timedelta(hours=12)
        coordinator._retry_queue[PERIPH_ERROR] = {
            "error_time": datetime.now().timestamp(),
            "retry_after": retry_after.timestamp(),
            "error_message": "API error",
            "attempts": 2,
        }
        service, connection = make_service([coordinator])

        await service._handle_get_backfill_state(service.hass, connection, {"id": 1})

        result = connection.send_result.call_args.args[1]
        # Datetimes are serialized as ISO strings by _json_safe.
        json.dumps(result)
        queue = {row["periph_id"]: row for row in result["queue"]}
        assert isinstance(queue[PERIPH_ERROR]["retry_after"], str)

    @pytest.mark.asyncio
    async def test_retry_now_routes_to_the_owner_coordinator(self):
        box1 = make_coordinator()
        box2 = make_coordinator()
        box1.async_backfill_retry_now = AsyncMock(
            return_value={
                "success": True,
                "periph_id": PERIPH_ERROR,
                "imported": 1,
                "status": "pending",
            }
        )
        box2.async_backfill_retry_now = AsyncMock()
        service, connection = make_service([box1, box2])
        # box1 owns the periph (both share ids here, box1 wins the walk).
        await service._handle_backfill_retry_now(
            service.hass, connection, {"id": 1, "periph_id": PERIPH_ERROR}
        )

        box1.async_backfill_retry_now.assert_awaited_once_with(PERIPH_ERROR)
        box2.async_backfill_retry_now.assert_not_awaited()
        result = connection.send_result.call_args.args[1]
        assert result["success"] is True
        # The action response carries the aggregated state.
        assert len(result["state"]["queue"]) > 0
        json.dumps(result)

    @pytest.mark.asyncio
    async def test_action_unknown_periph_sends_invalid_format(self):
        coordinator = make_coordinator()
        service, connection = make_service([coordinator])

        await service._handle_backfill_retry_now(
            service.hass, connection, {"id": 1, "periph_id": "999"}
        )

        connection.send_result.assert_not_called()
        assert connection.send_error.call_args.args[1] == "invalid_format"

    @pytest.mark.asyncio
    async def test_busy_lock_sends_error_code(self):
        coordinator = make_coordinator()
        coordinator.async_backfill_retry_now = AsyncMock(
            side_effect=EedomusBackfillError(
                "error", "A history import is already in progress"
            )
        )
        service, connection = make_service([coordinator])

        await service._handle_backfill_retry_now(
            service.hass, connection, {"id": 1, "periph_id": PERIPH_PENDING}
        )

        connection.send_result.assert_not_called()
        assert connection.send_error.call_args.args[1] == "error"

    @pytest.mark.asyncio
    async def test_set_paused_requires_exactly_one_target(self):
        coordinator = make_coordinator()
        coordinator.async_backfill_set_paused = AsyncMock()
        service, connection = make_service([coordinator])

        # Neither target.
        await service._handle_backfill_set_paused(
            service.hass, connection, {"id": 1, "paused": True}
        )
        assert connection.send_error.call_args.args[1] == "invalid_format"

        # A falsy global is not a target: without periph_id the payload
        # has no target at all.
        await service._handle_backfill_set_paused(
            service.hass, connection, {"id": 2, "global": False, "paused": True}
        )
        assert connection.send_error.call_args.args[1] == "invalid_format"

        # Both targets.
        await service._handle_backfill_set_paused(
            service.hass,
            connection,
            {"id": 3, "periph_id": PERIPH_PAUSED, "global": True, "paused": True},
        )
        assert connection.send_error.call_args.args[1] == "invalid_format"
        coordinator.async_backfill_set_paused.assert_not_awaited()
        connection.send_result.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_paused_global_skips_coordinators_without_the_api(self):
        """The fan-out survives a coordinator variant without the CAP-5
        API instead of failing mid-way after partially pausing boxes.
        """
        coordinator = make_coordinator()
        legacy_box = make_coordinator()
        legacy_box.async_backfill_set_paused = None
        service, connection = make_service([coordinator, legacy_box])

        await service._handle_backfill_set_paused(
            service.hass, connection, {"id": 1, "global": True, "paused": True}
        )

        result = connection.send_result.call_args.args[1]
        assert result["success"] is True
        assert coordinator._backfill_global_paused is True
        assert legacy_box._backfill_global_paused is False

    @pytest.mark.asyncio
    async def test_set_paused_periph_returns_state(self):
        coordinator = make_coordinator()
        service, connection = make_service([coordinator])

        await service._handle_backfill_set_paused(
            service.hass,
            connection,
            {"id": 1, "periph_id": PERIPH_PAUSED, "paused": True},
        )

        result = connection.send_result.call_args.args[1]
        assert result["success"] is True
        assert result["periph_id"] == PERIPH_PAUSED
        assert result["paused"] is True
        # The state rides the response so the panel re-renders the queue.
        queue = {row["periph_id"]: row for row in result["state"]["queue"]}
        assert queue[PERIPH_PAUSED]["status"] == "paused"
        json.dumps(result)

    @pytest.mark.asyncio
    async def test_set_paused_global_flips_the_aggregate_flag(self):
        coordinator = make_coordinator()
        service, connection = make_service([coordinator])

        await service._handle_backfill_set_paused(
            service.hass, connection, {"id": 1, "global": True, "paused": True}
        )

        result = connection.send_result.call_args.args[1]
        assert result["global"] is True
        assert result["state"]["global_paused"] is True

    @pytest.mark.asyncio
    async def test_set_ignored_returns_nominal_result_and_state(self):
        coordinator = make_coordinator()
        service, connection = make_service([coordinator])

        await service._handle_backfill_set_ignored(
            service.hass,
            connection,
            {"id": 1, "periph_id": PERIPH_IGNORED, "ignored": True},
        )

        result = connection.send_result.call_args.args[1]
        assert result["success"] is True
        assert result["periph_id"] == PERIPH_IGNORED
        assert result["ignored"] is True
        # The action response carries the aggregated state: the ignored
        # periph already shows in its ignored list.
        assert {row["periph_id"] for row in result["state"]["ignored"]} == {
            PERIPH_IGNORED
        }
        json.dumps(result)

    @pytest.mark.asyncio
    async def test_prioritize_handler_returns_nominal_result_and_state(self):
        coordinator = make_coordinator()
        service, connection = make_service([coordinator])

        await service._handle_backfill_prioritize(
            service.hass, connection, {"id": 1, "periph_id": PERIPH_PENDING}
        )

        result = connection.send_result.call_args.args[1]
        assert result["prioritized"] is True
        assert len(result["state"]["queue"]) > 0
        json.dumps(result)

    def test_set_paused_dispatcher_declares_its_ws_contract(self):
        """The dispatcher carries its command type and its schema: an
        exactly-one-target rule is enforced in the handler (both
        optional keys are legitimate alone), and paused stays required.
        """
        import custom_components.eedomus.ui_service as ui_service_module

        handler = ui_service_module._ws_backfill_set_paused
        assert handler._ws_command == (
            ui_service_module.WS_TYPE_EEDOMUS_BACKFILL_SET_PAUSED
        )
        schema = handler._ws_schema
        keys = {getattr(key, "schema", None) for key in schema}
        assert {"periph_id", "global", "paused"} <= keys
