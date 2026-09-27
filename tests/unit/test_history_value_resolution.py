"""Unit tests for history value resolution via value_list (coordinator.py).

Regression tests for the "Skipping invalid data point: could not convert
string to float: 'Confort'" warnings: the history API returns value labels
for list-type peripherals, and the numeric value must be resolved from the
peripheral's value_list (data[periph_id]["values"], from periph.value_list).
"""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.coordinator import EedomusDataUpdateCoordinator

pytestmark = pytest.mark.unit

PERIPH_ID = "72762"

VALUES = [
    {"value": "0", "description": "Arrêt", "icon": "off.png"},
    {"value": "100", "description": "Confort", "icon": "on.png"},
]


def make_coordinator():
    """Build a coordinator whose peripheral has a value_list."""
    coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=MagicMock())
    coordinator.data = {
        PERIPH_ID: {
            "periph_id": PERIPH_ID,
            "name": "Thermostat Salon",
            "values": VALUES,
        }
    }
    return coordinator


class TestResolveHistoryValue:
    def test_numeric_value_passes_through(self):
        coordinator = make_coordinator()
        assert coordinator._resolve_history_value(PERIPH_ID, "21.5") == 21.5
        assert coordinator._resolve_history_value(PERIPH_ID, 20) == 20.0

    def test_label_resolved_from_values_list(self):
        coordinator = make_coordinator()
        assert coordinator._resolve_history_value(PERIPH_ID, "Confort") == 100.0
        assert coordinator._resolve_history_value(PERIPH_ID, "Arrêt") == 0.0

    def test_unknown_label_returns_none(self):
        coordinator = make_coordinator()
        assert coordinator._resolve_history_value(PERIPH_ID, "Hors-Gel") is None

    def test_no_values_list_returns_none_for_label(self):
        coordinator = make_coordinator()
        coordinator.data[PERIPH_ID]["values"] = []
        assert coordinator._resolve_history_value(PERIPH_ID, "Confort") is None

    def test_unknown_periph_returns_none_for_label(self):
        coordinator = make_coordinator()
        assert coordinator._resolve_history_value("999999", "Confort") is None

    def test_non_numeric_mapped_value_returns_none(self):
        coordinator = make_coordinator()
        coordinator.data[PERIPH_ID]["values"] = [
            {"value": "abc", "description": "Confort"}
        ]
        assert coordinator._resolve_history_value(PERIPH_ID, "Confort") is None


@pytest.mark.asyncio
async def test_statistics_import_resolves_labels():
    """Labels are converted to their numeric value in the statistics import."""
    coordinator = make_coordinator()
    coordinator.hass.services.async_call = AsyncMock()
    chunk = [
        {"value": "Confort", "timestamp": "2026-09-27T09:00:00"},
        {"value": "20.5", "timestamp": "2026-09-27T09:30:00"},
    ]

    await coordinator._import_via_statistics(
        f"sensor.eedomus_{PERIPH_ID}", chunk, "Thermostat Salon", PERIPH_ID
    )

    coordinator.hass.services.async_call.assert_awaited_once()
    call = coordinator.hass.services.async_call.await_args
    statistics = call.kwargs["service_data"]["statistics"]
    assert len(statistics) == 2
    assert statistics[0]["mean"] == 100.0
    assert statistics[0]["state"] == 100.0
    assert statistics[1]["mean"] == 20.5


@pytest.mark.asyncio
async def test_statistics_import_skips_unresolvable_label(caplog):
    """A label with no value_list entry is skipped with one warning per point."""
    coordinator = make_coordinator()
    coordinator.hass.services.async_call = AsyncMock()
    chunk = [
        {"value": "Hors-Gel", "timestamp": "2026-09-27T09:00:00"},
        {"value": "Arrêt", "timestamp": "2026-09-27T09:30:00"},
    ]
    caplog.set_level(logging.WARNING, logger="custom_components.eedomus.coordinator")

    await coordinator._import_via_statistics(
        f"sensor.eedomus_{PERIPH_ID}", chunk, "Thermostat Salon", PERIPH_ID
    )

    skip_warnings = [
        record
        for record in caplog.records
        if "Skipping invalid data point" in record.message
    ]
    assert len(skip_warnings) == 1
    assert "Hors-Gel" in skip_warnings[0].getMessage()
    # The valid point is still imported
    call = coordinator.hass.services.async_call.await_args
    statistics = call.kwargs["service_data"]["statistics"]
    assert len(statistics) == 1
    assert statistics[0]["mean"] == 0.0


@pytest.mark.asyncio
async def test_async_set_fallback_resolves_labels():
    """The async_set fallback converts labels to numeric states too."""
    coordinator = make_coordinator()
    coordinator.hass.services.async_call = AsyncMock(
        side_effect=Exception("service not found")
    )
    coordinator.hass.states.async_set = MagicMock()
    chunk = [
        {"value": "Confort", "timestamp": "2026-09-27T09:00:00"},
        {"value": "20.5", "timestamp": "2026-09-27T09:30:00"},
    ]

    await coordinator._fallback_import_history_chunk(PERIPH_ID, chunk)

    states_set = coordinator.hass.states.async_set.call_args_list
    assert len(states_set) == 2
    # Integer list values stay readable ("100", not "100.0")
    assert states_set[0].args[1] == "100"
    assert states_set[1].args[1] == "20.5"
