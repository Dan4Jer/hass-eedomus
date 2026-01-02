"""Tests for Eedomus energy sensors."""

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergy
from sensor import EedomusEnergySensor


@pytest.mark.asyncio
async def test_energy_sensor_initialization():
    """Test energy sensor initialization."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "device_123": {
            "consumption": 42.5,
            "current_power": 150,
            "last_reset": "2023-01-01",
        }
    }

    device_info = {"id": "device_123", "name": "Test Energy Sensor", "usage_id": "26"}

    sensor = EedomusEnergySensor(mock_coordinator, device_info)

    assert sensor.name == "Test Energy Sensor"
    assert sensor.unique_id == "eedomus_energy_device_123"
    assert sensor.device_class == SensorDeviceClass.ENERGY
    assert sensor.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR
    assert sensor.native_value == 42.5

    # Test extra attributes
    attrs = sensor.extra_state_attributes
    assert attrs["current_power"] == 150
    assert attrs["last_reset"] == "2023-01-01"


@pytest.mark.asyncio
async def test_energy_sensor_with_missing_data():
    """Test energy sensor with missing consumption data."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {"device_123": {}}

    device_info = {"id": "device_123", "name": "Test Energy Sensor"}

    sensor = EedomusEnergySensor(mock_coordinator, device_info)

    assert sensor.native_value is None
    assert sensor.extra_state_attributes == {}


@pytest.mark.asyncio
async def test_energy_sensor_update():
    """Test energy sensor update mechanism."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {"device_123": {"consumption": 42.5}}

    device_info = {"id": "device_123", "name": "Test Energy Sensor"}

    sensor = EedomusEnergySensor(mock_coordinator, device_info)

    # Simulate data update
    mock_coordinator.data["device_123"]["consumption"] = 45.0

    assert sensor.native_value == 45.0
