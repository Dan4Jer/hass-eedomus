"""Unit tests for the history progress sensors (history_sensor.py).

Regression tests for the listener errors "TypeError: '>' not supported
between instances of 'NoneType' and 'int'" and "TypeError: unsupported
operand type(s) for +: 'int' and 'NoneType'": a progress entry created
by async_fetch_history_chunk can carry total_points=None
(_estimate_total_points returns None when creation_date/POLLING are
unavailable). The sensors must tolerate the None key instead of raising
on every coordinator update.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from custom_components.eedomus.coordinator import EedomusDataUpdateCoordinator
from custom_components.eedomus.history_sensor import (
    EedomusHistoryProgressSensor,
    EedomusHistoryStatsSensor,
)

pytestmark = pytest.mark.unit

PERIPH_ID = "72762"


def make_coordinator(progress):
    """Build a coordinator around an explicit progress map."""
    coordinator = EedomusDataUpdateCoordinator(
        hass=MagicMock(), client=MagicMock()
    )
    coordinator.config_entry = SimpleNamespace(entry_id="01TEST")
    coordinator.data = {
        PERIPH_ID: {"periph_id": PERIPH_ID, "name": "Thermostat Salon"}
    }
    coordinator._history_progress = progress
    return coordinator


def make_progress_sensor(coordinator):
    return EedomusHistoryProgressSensor(
        coordinator, PERIPH_ID, "Thermostat Salon", MagicMock()
    )


def test_progress_sensor_tolerates_none_total_points():
    """A None total_points (estimate unavailable) reports 0, not TypeError."""
    coordinator = make_coordinator(
        {PERIPH_ID: {"total_points": None, "retrieved_points": 60000}}
    )
    sensor = make_progress_sensor(coordinator)
    assert sensor.native_value == 0


def test_progress_sensor_percentage_with_estimated_total():
    """The percentage math is unchanged when the estimate is present."""
    coordinator = make_coordinator(
        {PERIPH_ID: {"total_points": 120000, "retrieved_points": 60000}}
    )
    sensor = make_progress_sensor(coordinator)
    assert sensor.native_value == 50


def test_progress_sensor_missing_entry_reports_zero():
    """No progress entry at all: the sensor reports 0, not TypeError."""
    coordinator = make_coordinator({})
    sensor = make_progress_sensor(coordinator)
    assert sensor.native_value == 0


def test_stats_sensor_sum_tolerates_none_totals():
    """The aggregate sums skip None totals instead of raising."""
    coordinator = make_coordinator(
        {
            "111": {"total_points": None, "retrieved_points": 10000},
            "222": {"total_points": 100000, "retrieved_points": 50000},
        }
    )
    sensor = EedomusHistoryStatsSensor(coordinator, MagicMock())
    # 60000 retrieved points at 100 bytes each -> MB, rounded to 2 decimals
    assert sensor.native_value == pytest.approx(5.72, abs=0.01)
