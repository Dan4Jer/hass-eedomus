"""Unit tests for partial refresh timing decomposition (coordinator.py).

Regression tests for the PARTIAL REFRESH log improvement: the log line
must expose API / History / Processing times separately, with history
metrics (peripherals, states) measured around the fetch+import calls.
"""

import logging
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.coordinator import EedomusDataUpdateCoordinator

pytestmark = pytest.mark.unit

PERIPH_ID = "123456"


def make_coordinator(enable_history=True):
    """Build a coordinator with stubbed hass/client (HA is stubbed in conftest)."""
    client = MagicMock()
    client.config_entry = SimpleNamespace(options={"history": enable_history}, data={})
    coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=client)
    coordinator.data = {PERIPH_ID: {"periph_id": PERIPH_ID, "value": 1}}
    coordinator._dynamic_peripherals = {
        PERIPH_ID: {"periph_id": PERIPH_ID, "ha_entity": "light"}
    }
    # AD-3: the queue reads the eligible set (numeric sensors), not
    # the dynamic set (the periph above is a light: real-time only).
    coordinator._backfill_eligible_peripherals = {
        PERIPH_ID: {
            "periph_id": PERIPH_ID,
            "ha_entity": "sensor",
            "value_type": "float",
        }
    }
    coordinator._history_progress = {}
    coordinator.client.get_periph_caract = AsyncMock(
        return_value={
            "body": [{"periph_id": PERIPH_ID, "value": 42}],
            "_raw_data_size_bytes": 128,
        }
    )
    return coordinator


@pytest.mark.asyncio
async def test_cycle_reports_zero_history_and_the_drain_pass_fetches():
    """AD-2 (story 1.4): the cycle reports zero history metrics - the
    background drain pass owns the fetch+import."""
    coordinator = make_coordinator(enable_history=True)
    chunk = [{"value": 1}, {"value": 2}, {"value": 3}]
    coordinator.async_fetch_history_chunk = AsyncMock(return_value=chunk)
    # async_import_history_chunk returns the number of statistics imported
    coordinator.async_import_history_chunk = AsyncMock(return_value=len(chunk))

    await coordinator._async_partial_refresh()
    assert coordinator._last_history_periphs == 0
    assert coordinator._last_history_states == 0
    coordinator.async_fetch_history_chunk.assert_not_awaited()

    await coordinator._backfill_drain_pass()
    coordinator.async_fetch_history_chunk.assert_awaited_once_with(PERIPH_ID)
    coordinator.async_import_history_chunk.assert_awaited_once_with(PERIPH_ID, chunk)


@pytest.mark.asyncio
async def test_drain_pass_no_history_when_disabled():
    """With history disabled, the drain pass is a no-op."""
    coordinator = make_coordinator(enable_history=False)
    coordinator.async_fetch_history_chunk = AsyncMock()
    coordinator.async_import_history_chunk = AsyncMock()

    await coordinator._backfill_drain_pass()

    coordinator.async_fetch_history_chunk.assert_not_awaited()
    coordinator.async_import_history_chunk.assert_not_awaited()
    assert coordinator._last_history_periphs == 0
    assert coordinator._last_history_states == 0
    assert coordinator._last_history_time == 0.0


@pytest.mark.asyncio
async def test_partial_refresh_log_decomposition(caplog):
    """The PARTIAL REFRESH log exposes API / History / Processing separately."""
    coordinator = make_coordinator(enable_history=False)
    coordinator.async_fetch_history_chunk = AsyncMock()
    coordinator.async_import_history_chunk = AsyncMock()
    coordinator._full_refresh_needed = False
    coordinator._last_update_start_time = datetime.now()

    caplog.set_level(logging.INFO, logger="custom_components.eedomus.coordinator")
    result = await coordinator._async_update_data()

    partial_logs = [
        record for record in caplog.records if "PARTIAL REFRESH" in record.message
    ]
    assert partial_logs, "PARTIAL REFRESH log line missing"
    message = partial_logs[0].getMessage()
    assert "API: " in message
    assert "History: " in message
    assert "[0 periphs, 0 states]" in message
    assert "Processing: " in message
    assert "Endpoints: " in message
    assert result is coordinator.data


@pytest.mark.asyncio
async def test_partial_refresh_log_reports_zero_history_counts(caplog):
    """With history enabled, the refresh log reports zero history - the
    drain lives in the background worker (AD-2, story 1.4)."""
    coordinator = make_coordinator(enable_history=True)
    coordinator.async_fetch_history_chunk = AsyncMock()
    coordinator.async_import_history_chunk = AsyncMock()
    coordinator._full_refresh_needed = False
    coordinator._last_update_start_time = datetime.now()

    caplog.set_level(logging.INFO, logger="custom_components.eedomus.coordinator")
    await coordinator._async_update_data()

    partial_logs = [
        record for record in caplog.records if "PARTIAL REFRESH" in record.message
    ]
    assert partial_logs
    message = partial_logs[0].getMessage()
    assert "[0 periphs, 0 states]" in message


@pytest.mark.asyncio
async def test_partial_refresh_history_quota_limits_per_scan():
    """AD-2 cadence: at most history_peripherals_per_scan imports per cycle.

    Pending peripherals beyond the quota are not fetched in the same
    cycle; they drain on later scans. An empty chunk still consumes its
    quota slot (a no-data fetch is not free).
    """
    periph_ids = ["111", "222", "333"]
    client = MagicMock()
    client.config_entry = SimpleNamespace(
        options={"history": True, "history_peripherals_per_scan": 2},
        data={},
    )
    coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=client)
    coordinator.data = {p: {"periph_id": p, "value": 1} for p in periph_ids}
    coordinator._dynamic_peripherals = {p: {"periph_id": p} for p in periph_ids}
    coordinator._backfill_eligible_peripherals = {
        p: {"periph_id": p, "ha_entity": "sensor", "value_type": "float"}
        for p in periph_ids
    }
    coordinator._history_progress = {}
    coordinator.client.get_periph_caract = AsyncMock(
        return_value={
            "body": [{"periph_id": p, "value": 42} for p in periph_ids],
            "_raw_data_size_bytes": 128,
        }
    )
    # 111 returns an empty chunk: it consumes its quota slot but stays
    # pending, so it is retried on a later scan
    coordinator.async_fetch_history_chunk = AsyncMock(
        side_effect=lambda periph_id: []
        if periph_id == "111"
        else [{"value": 1}]
    )
    coordinator.async_import_history_chunk = AsyncMock(return_value=1)

    await coordinator._backfill_drain_pass()

    fetched_first = [
        call.args[0] for call in coordinator.async_fetch_history_chunk.call_args_list
    ]
    assert len(fetched_first) == 2, "quota of 2 must cap the first pass"
    assert "333" not in fetched_first, "the third periph is beyond the quota"

    # 222 is complete: the next cycle retries the empty 111 and drains
    # 333 (quota 2, two pending).
    coordinator._history_progress["222"] = {"completed": True}

    await coordinator._backfill_drain_pass()

    all_calls = coordinator.async_fetch_history_chunk.call_args_list
    fetched_second = [call.args[0] for call in all_calls][len(fetched_first) :]
    assert set(fetched_second) == {"111", "333"}


@pytest.mark.asyncio
async def test_partial_refresh_busy_lock_skips_history_segment():
    """CAP-5 mono-importer lock, drain side: a busy lock (retry_now in
    flight) skips the history segment this cycle instead of blocking the
    real-time refresh - and the quota is left intact.
    """
    periph_ids = ["111", "222"]
    client = MagicMock()
    client.config_entry = SimpleNamespace(
        options={"history": True, "history_peripherals_per_scan": 2},
        data={},
    )
    coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=client)
    coordinator.data = {p: {"periph_id": p, "value": 1} for p in periph_ids}
    coordinator._dynamic_peripherals = {p: {"periph_id": p} for p in periph_ids}
    coordinator._backfill_eligible_peripherals = {
        p: {"periph_id": p, "ha_entity": "sensor", "value_type": "float"}
        for p in periph_ids
    }
    coordinator._history_progress = {}
    coordinator.client.get_periph_caract = AsyncMock(
        return_value={
            "body": [{"periph_id": p, "value": 42} for p in periph_ids],
            "_raw_data_size_bytes": 128,
        }
    )
    coordinator.async_fetch_history_chunk = AsyncMock(return_value=[{"value": 1}])
    coordinator.async_import_history_chunk = AsyncMock(return_value=1)

    async with coordinator._backfill_import_lock:
        await coordinator._backfill_drain_pass()

    # Busy lock: no history import this cycle, quota untouched.
    coordinator.async_fetch_history_chunk.assert_not_awaited()
    assert coordinator._last_history_periphs == 0

    # Lock released: the next cycle drains with its full quota.
    await coordinator._backfill_drain_pass()
    assert coordinator.async_fetch_history_chunk.await_count == 2


@pytest.mark.asyncio
async def test_partial_refresh_global_pause_skips_history_segment():
    """CAP-5 global pause: no history import runs and the quota is not
    consumed; resuming restores the drain with the quota intact.
    """
    periph_ids = ["111", "222"]
    client = MagicMock()
    client.config_entry = SimpleNamespace(
        options={"history": True, "history_peripherals_per_scan": 1},
        data={},
    )
    coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=client)
    coordinator.data = {p: {"periph_id": p, "value": 1} for p in periph_ids}
    coordinator._dynamic_peripherals = {p: {"periph_id": p} for p in periph_ids}
    coordinator._backfill_eligible_peripherals = {
        p: {"periph_id": p, "ha_entity": "sensor", "value_type": "float"}
        for p in periph_ids
    }
    coordinator._history_progress = {}
    coordinator.client.get_periph_caract = AsyncMock(
        return_value={
            "body": [{"periph_id": p, "value": 42} for p in periph_ids],
            "_raw_data_size_bytes": 128,
        }
    )
    coordinator.async_fetch_history_chunk = AsyncMock(return_value=[])
    coordinator.async_import_history_chunk = AsyncMock(return_value=0)

    coordinator._backfill_global_paused = True
    await coordinator._backfill_drain_pass()

    # Global pause: the history segment is skipped entirely, quota intact.
    coordinator.async_fetch_history_chunk.assert_not_awaited()
    assert coordinator._last_history_periphs == 0

    # Resume: the drain picks up with its full quota.
    coordinator._backfill_global_paused = False
    await coordinator._backfill_drain_pass()

    fetched = [
        call.args[0] for call in coordinator.async_fetch_history_chunk.call_args_list
    ]
    assert len(fetched) == 1, "quota of 1 applies again after the resume"


@pytest.mark.asyncio
async def test_partial_refresh_priority_jumps_the_natural_order():
    """CAP-5 priority: the prioritized periph is taken first at the next
    drain, before the natural order, and the jump is consumed.
    """
    periph_ids = ["111", "222"]
    client = MagicMock()
    client.config_entry = SimpleNamespace(
        options={"history": True, "history_peripherals_per_scan": 1},
        data={},
    )
    coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=client)
    coordinator.data = {p: {"periph_id": p, "value": 1} for p in periph_ids}
    coordinator._dynamic_peripherals = {p: {"periph_id": p} for p in periph_ids}
    coordinator._backfill_eligible_peripherals = {
        p: {"periph_id": p, "ha_entity": "sensor", "value_type": "float"}
        for p in periph_ids
    }
    coordinator._history_progress = {}
    coordinator.client.get_periph_caract = AsyncMock(
        return_value={
            "body": [{"periph_id": p, "value": 42} for p in periph_ids],
            "_raw_data_size_bytes": 128,
        }
    )
    coordinator.async_fetch_history_chunk = AsyncMock(return_value=[{"value": 1}])
    coordinator.async_import_history_chunk = AsyncMock(return_value=1)

    coordinator._backfill_priority = ["222"]
    await coordinator._backfill_drain_pass()

    # Quota 1: the prioritized periph (natural second) got the slot.
    coordinator.async_fetch_history_chunk.assert_awaited_once_with("222")
    assert coordinator._backfill_priority == [], "the jump is consumed by the drain"

    # Next drain: the natural order drains the remaining periph.
    await coordinator._backfill_drain_pass()
    coordinator.async_fetch_history_chunk.assert_any_await("111")


@pytest.mark.asyncio
async def test_cycle_writes_no_sensor_eedomus_state():
    """Story 1.3: a backfill cycle never writes a sensor.eedomus_*
    helper state — the error/completion information lives in the
    CAP-5 view (eedomus/get_backfill_state), never in the state
    machine."""
    coordinator = make_coordinator(enable_history=True)
    coordinator.hass.states.async_set = MagicMock()
    chunk = [{"value": 1, "timestamp": "2026-09-27T08:15:00"}]
    coordinator.async_fetch_history_chunk = AsyncMock(return_value=chunk)
    coordinator.async_import_history_chunk = AsyncMock(return_value=1)
    coordinator._retry_queue["999"] = {
        "error_time": datetime.now().timestamp(),
        "retry_after": datetime.now().timestamp() + 3600,
        "error_message": "API error",
        "attempts": 2,
    }

    await coordinator._backfill_drain_pass()

    for call in coordinator.hass.states.async_set.call_args_list:
        entity_id = call.args[0]
        assert not entity_id.startswith("sensor.eedomus_"), entity_id
