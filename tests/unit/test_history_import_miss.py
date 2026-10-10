"""Regression tests for bug 1.11: silent chunk loss without a registry match.

An eligible sensor whose entity never resolves in the registry has no
importable statistics target. Historically every fetched chunk was
skipped with a warning while the fetch kept advancing the progress —
the points were lost silently (271 chunks observed live before the
AD-3 eligibility fix removed the legacy climate/select entries).

The hardening: 3 consecutive resolution misses remove the periph from
the queue (progress popped, persisted); a resolved target resets the
streak.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.coordinator import EedomusDataUpdateCoordinator

pytestmark = pytest.mark.unit

PERIPH = "990011"


def make_coordinator():
    """A coordinator with one pending, eligible periph.

    The conftest entity-registry stub has no entities, so
    _resolve_main_entity_id naturally returns None.
    """
    client = MagicMock()
    client.config_entry = SimpleNamespace(options={"history": True}, data={})
    coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=client)
    coordinator.config_entry = SimpleNamespace(entry_id="01TEST")
    coordinator.data = {PERIPH: {"periph_id": PERIPH, "name": "Sensor"}}
    coordinator._history_progress = {PERIPH: {"last_timestamp": 10, "completed": False}}
    coordinator._backfill_eligible_peripherals = {
        PERIPH: {"periph_id": PERIPH, "ha_entity": "sensor"}
    }
    coordinator._retry_queue = {}
    coordinator._error_count = {}
    coordinator._save_history_progress = AsyncMock()
    return coordinator


CHUNK = [{"value": "20", "timestamp": "2026-10-01T08:00:00"}]


class TestImportMissCounter:
    @pytest.mark.asyncio
    async def test_three_misses_remove_the_periph_from_the_queue(self):
        """A periph with no importable target leaves the queue after
        3 consecutive resolution misses — no silent chunk burning."""
        coordinator = make_coordinator()
        coordinator._resolve_main_entity_id = lambda *a, **k: None

        for _ in range(2):
            imported = await coordinator.async_import_history_chunk(PERIPH, CHUNK)
            assert imported == 0
            assert PERIPH in coordinator._history_progress

        imported = await coordinator.async_import_history_chunk(PERIPH, CHUNK)
        assert imported == 0
        assert PERIPH not in coordinator._history_progress
        coordinator._save_history_progress.assert_awaited()

    @pytest.mark.asyncio
    async def test_transient_miss_then_resolution_keeps_the_periph(self):
        """A resolved target resets the streak: transient misses are
        tolerated and the periph stays in the queue."""
        coordinator = make_coordinator()
        resolve_calls = []

        def _resolve(periph_id, allow_suffixed=True):
            # Two misses, then the entity appears
            resolve_calls.append(periph_id)
            return None if len(resolve_calls) <= 2 else "sensor.resolved"

        coordinator._resolve_main_entity_id = _resolve

        assert await coordinator.async_import_history_chunk(PERIPH, CHUNK) == 0
        assert await coordinator.async_import_history_chunk(PERIPH, CHUNK) == 0
        assert PERIPH in coordinator._history_progress

        # Third call resolves: the import proceeds (fails later on the
        # stub recorder path, but the periph is NOT removed)
        await coordinator.async_import_history_chunk(PERIPH, CHUNK)
        assert PERIPH in coordinator._history_progress
        assert PERIPH not in coordinator._import_miss_count

    @pytest.mark.asyncio
    async def test_resolution_resets_an_earlier_streak(self):
        """A successful resolution clears the counter — a later miss
        starts a fresh streak."""
        coordinator = make_coordinator()
        coordinator._resolve_main_entity_id = lambda *a, **k: None

        # Two misses
        await coordinator.async_import_history_chunk(PERIPH, CHUNK)
        await coordinator.async_import_history_chunk(PERIPH, CHUNK)
        assert coordinator._import_miss_count[PERIPH] == 2

        # Resolution succeeds (then the stubbed import path fails
        # harmlessly — the counter is already reset)
        coordinator._resolve_main_entity_id = lambda *a, **k: "sensor.ok"
        await coordinator.async_import_history_chunk(PERIPH, CHUNK)
        assert PERIPH not in coordinator._import_miss_count
        assert PERIPH in coordinator._history_progress
