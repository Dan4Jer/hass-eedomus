"""Unit tests: the backfill worker runs as a background task.

The worker is an endless loop. Started with hass.async_create_task it is
tracked, and Home Assistant waits for every tracked task before it
finishes startup: boot stalled until the bootstrap timeout (about five
minutes, "Setup timed out for bootstrap ... _async_backfill_worker").
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from custom_components.eedomus.coordinator import EedomusDataUpdateCoordinator

pytestmark = pytest.mark.unit


def make_coordinator(hass):
    client = MagicMock()
    client.config_entry = SimpleNamespace(options={}, data={})
    return EedomusDataUpdateCoordinator(hass=hass, client=client)


class _HassWithBackground:
    """hass exposing both task APIs, recording which one is used."""

    def __init__(self):
        self.calls = []

    def async_create_background_task(self, target, name, eager_start=True):
        self.calls.append(("background", name))
        return asyncio.get_running_loop().create_task(target)

    def async_create_task(self, target):
        self.calls.append(("tracked", None))
        return asyncio.get_running_loop().create_task(target)


class _HassWithoutBackground:
    """hass predating async_create_background_task."""

    def __init__(self):
        self.calls = []

    def async_create_task(self, target):
        self.calls.append(("tracked", None))
        return asyncio.get_running_loop().create_task(target)


async def _stop(coordinator):
    task = coordinator._backfill_worker_task
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_worker_is_a_background_task():
    """The endless worker must not block the startup phase."""
    hass = _HassWithBackground()
    coordinator = make_coordinator(hass)
    coordinator._ensure_backfill_worker()
    assert hass.calls == [("background", "eedomus_backfill_worker")]
    assert not coordinator._backfill_worker_task.done()
    await _stop(coordinator)


@pytest.mark.asyncio
async def test_worker_start_is_idempotent():
    """A second call while the worker runs creates no second task."""
    hass = _HassWithBackground()
    coordinator = make_coordinator(hass)
    coordinator._ensure_backfill_worker()
    first = coordinator._backfill_worker_task
    coordinator._ensure_backfill_worker()
    assert coordinator._backfill_worker_task is first
    assert len(hass.calls) == 1
    await _stop(coordinator)


@pytest.mark.asyncio
async def test_worker_falls_back_without_background_api():
    """An older hass without the background API still starts the worker."""
    hass = _HassWithoutBackground()
    coordinator = make_coordinator(hass)
    coordinator._ensure_backfill_worker()
    assert hass.calls == [("tracked", None)]
    await _stop(coordinator)
