"""Regression tests for bug 1.10: the dead-window fetch loop.

The eedomus cloud returns the newest 10,000 points of a peripheral
whatever the requested window. Once the walk reaches the present,
every pass returns the SAME full chunk (max timestamp frozen at the
cloud's latest point) and the len < 10000 completion test never fires
— the periph loops forever, burning its quota share of the drain
every pass (observed live on 5 periphs for hours).

The fix: a chunk whose max timestamp no longer advances past the
previous last_timestamp means the walk holds the newest window the
cloud has — the periph is completed.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.coordinator import EedomusDataUpdateCoordinator

pytestmark = pytest.mark.unit

PERIPH = "990010"
CAP = 10000


def make_coordinator():
    """A coordinator whose periph is mid-walk (history enabled)."""
    client = MagicMock()
    client.config_entry = SimpleNamespace(options={"history": True}, data={})
    coordinator = EedomusDataUpdateCoordinator(
        hass=MagicMock(), client=client
    )
    coordinator.config_entry = SimpleNamespace(entry_id="01TEST")
    coordinator.data = {
        PERIPH: {"periph_id": PERIPH, "name": "Device under walk"}
    }
    coordinator._history_progress = {}
    coordinator._retry_queue = {}
    coordinator._error_count = {}
    coordinator.client.get_device_history = AsyncMock(return_value=[])
    coordinator.async_fetch_history_chunk = (
        EedomusDataUpdateCoordinator.async_fetch_history_chunk.__get__(
            coordinator
        )
    )
    return coordinator


def _chunk(count, first_hour, step_hours=1):
    """A chunk of count points, hourly, starting at first_hour."""
    start = datetime(2026, 1, 1) + timedelta(hours=first_hour)
    return [
        {
            "value": str(i % 30),
            "timestamp": (start + timedelta(hours=step_hours * i)).isoformat(),
        }
        for i in range(count)
    ]


def _last_ts(coordinator):
    return coordinator._history_progress[PERIPH]["last_timestamp"]


async def _fetch(coordinator, chunk):
    coordinator.client.get_device_history = AsyncMock(return_value=chunk)
    return await coordinator.async_fetch_history_chunk(PERIPH)


class TestDeadWindowCompletion:
    @pytest.mark.asyncio
    async def test_stale_full_chunk_completes_the_walk(self):
        """A full chunk whose max does not advance past the previous
        last_timestamp completes the periph (the loop stops)."""
        coordinator = make_coordinator()
        # First pass: a FULL chunk keeps the walk alive (a short chunk
        # would complete it through the pre-existing path)
        chunk = await _fetch(coordinator, _chunk(CAP, 0))
        assert chunk
        previous_last = _last_ts(coordinator)
        assert not coordinator._history_progress[PERIPH]["completed"]

        # The cloud replays the SAME newest window (max == previous
        # last): the walk holds the newest data there is
        stale = _chunk(CAP, 0)
        chunk = await _fetch(coordinator, stale)
        assert chunk  # still returned for the idempotent import
        progress = coordinator._history_progress[PERIPH]
        assert progress["completed"] is True

    @pytest.mark.asyncio
    async def test_advancing_full_chunk_continues_the_walk(self):
        """Mid-walk: a full chunk whose max advances is business as
        usual — not completed."""
        coordinator = make_coordinator()
        await _fetch(coordinator, _chunk(CAP, 0))
        previous_last = _last_ts(coordinator)
        assert not coordinator._history_progress[PERIPH]["completed"]

        advancing = _chunk(CAP, 10)  # max well past previous_last
        assert max(
            datetime.fromisoformat(e["timestamp"]).timestamp() for e in advancing
        ) > previous_last
        await _fetch(coordinator, advancing)
        assert (
            coordinator._history_progress[PERIPH]["completed"] is False
        )

    @pytest.mark.asyncio
    async def test_first_pass_full_chunk_is_not_stale(self):
        """last_timestamp = 0: the stale check is skipped — a full
        first chunk must not complete the walk."""
        coordinator = make_coordinator()
        await _fetch(coordinator, _chunk(CAP, 0))
        assert (
            coordinator._history_progress[PERIPH]["completed"] is False
        )

    @pytest.mark.asyncio
    async def test_short_chunk_still_completes(self):
        """The pre-existing completion path (tail shorter than the
        cap) is unchanged."""
        coordinator = make_coordinator()
        await _fetch(coordinator, _chunk(2, 0))
        assert coordinator._history_progress[PERIPH]["completed"] is True
