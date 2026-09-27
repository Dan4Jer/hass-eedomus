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
    coordinator._history_progress = {}
    coordinator.client.get_periph_caract = AsyncMock(
        return_value={
            "body": [{"periph_id": PERIPH_ID, "value": 42}],
            "_raw_data_size_bytes": 128,
        }
    )
    coordinator._create_error_sensors = AsyncMock()
    return coordinator


@pytest.mark.asyncio
async def test_partial_refresh_history_metrics_accumulate():
    """History fetch/import are timed and counted per imported peripheral."""
    coordinator = make_coordinator(enable_history=True)
    chunk = [{"value": 1}, {"value": 2}, {"value": 3}]
    coordinator.async_fetch_history_chunk = AsyncMock(return_value=chunk)
    coordinator.async_import_history_chunk = AsyncMock()

    await coordinator._async_partial_refresh()

    coordinator.async_fetch_history_chunk.assert_awaited_once_with(PERIPH_ID)
    coordinator.async_import_history_chunk.assert_awaited_once_with(PERIPH_ID, chunk)
    assert coordinator._last_history_periphs == 1
    assert coordinator._last_history_states == 3
    assert coordinator._last_history_time >= 0.0
    assert (
        coordinator._last_history_fetch_time + coordinator._last_history_import_time
    ) <= coordinator._last_history_time + 0.001


@pytest.mark.asyncio
async def test_partial_refresh_no_history_when_disabled():
    """With history disabled, no fetch/import call is made and metrics stay zero."""
    coordinator = make_coordinator(enable_history=False)
    coordinator.async_fetch_history_chunk = AsyncMock()
    coordinator.async_import_history_chunk = AsyncMock()

    await coordinator._async_partial_refresh()

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
async def test_partial_refresh_log_reports_history_counts(caplog):
    """With history enabled, the log line reports the imported peripherals/states."""
    coordinator = make_coordinator(enable_history=True)
    chunk = [{"value": 1}, {"value": 2}]
    coordinator.async_fetch_history_chunk = AsyncMock(return_value=chunk)
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
    assert "[1 periphs, 2 states]" in message
