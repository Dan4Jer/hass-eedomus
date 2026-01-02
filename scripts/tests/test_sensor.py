"""Tests for Eedomus sensor entities."""

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTemperature

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "custom_components/eedomus")))
from sensor import EedomusSensor


@pytest.mark.asyncio
async def test_temperature_sensor():
    """Test temperature sensor."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "temp_sensor": {
            "name": "Temperature Sensor",
            "value": 22.5,
            "unit": "°C",
            "usage_id": "7",
        }
    }

    device_info = {
        "periph_id": "temp_sensor",
        "name": "Temperature Sensor",
        "usage_id": "7",
    }

    sensor = EedomusSensor(mock_coordinator, device_info)

    assert sensor.name == "Temperature Sensor"
    assert sensor.unique_id == "eedomus_sensor_temp_sensor"
    assert sensor.device_class == SensorDeviceClass.TEMPERATURE
    assert sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS
    assert sensor.native_value == 22.5


@pytest.mark.asyncio
async def test_humidity_sensor():
    """Test humidity sensor."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "humidity_sensor": {
            "name": "Humidity Sensor",
            "value": 45.0,
            "unit": "%",
            "usage_id": "38",
        }
    }

    device_info = {
        "periph_id": "humidity_sensor",
        "name": "Humidity Sensor",
        "usage_id": "38",
    }

    sensor = EedomusSensor(mock_coordinator, device_info)

    assert sensor.device_class == SensorDeviceClass.HUMIDITY
    assert sensor.native_unit_of_measurement == "%"
    assert sensor.native_value == 45.0


@pytest.mark.asyncio
async def test_power_sensor():
    """Test power sensor."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "power_sensor": {
            "name": "Power Sensor",
            "value": 150.5,
            "unit": "W",
            "usage_id": "26",
        }
    }

    device_info = {
        "periph_id": "power_sensor",
        "name": "Power Sensor",
        "usage_id": "26",
    }

    sensor = EedomusSensor(mock_coordinator, device_info)

    assert sensor.device_class == SensorDeviceClass.POWER
    assert sensor.native_unit_of_measurement == UnitOfPower.WATT
    assert sensor.native_value == 150.5


@pytest.mark.asyncio
async def test_energy_sensor():
    """Test energy sensor (Issue #9)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "energy_sensor": {
            "name": "Energy Sensor",
            "value": 12.5,
            "unit": "kWh",
            "usage_id": "26",
        }
    }

    device_info = {
        "periph_id": "energy_sensor",
        "name": "Energy Sensor",
        "usage_id": "26",
    }

    sensor = EedomusSensor(mock_coordinator, device_info)

    assert sensor.device_class == SensorDeviceClass.ENERGY
    assert sensor.native_unit_of_measurement == UnitOfEnergy.KILO_WATT_HOUR
    assert sensor.native_value == 12.5


@pytest.mark.asyncio
async def test_battery_sensor():
    """Test battery sensor."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "battery_sensor": {
            "name": "Battery Level",
            "value": 75,
            "unit": "%",
            "usage_id": "134",
        }
    }

    device_info = {
        "periph_id": "battery_sensor",
        "name": "Battery Level",
        "usage_id": "134",
    }

    sensor = EedomusSensor(mock_coordinator, device_info)

    assert sensor.device_class == SensorDeviceClass.BATTERY
    assert sensor.native_unit_of_measurement == "%"
    assert sensor.native_value == 75


@pytest.mark.asyncio
async def test_sensor_with_missing_data():
    """Test sensor with missing value."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "missing_sensor": {
            "name": "Missing Data Sensor"
            # No value field
        }
    }

    device_info = {"periph_id": "missing_sensor", "name": "Missing Data Sensor"}

    sensor = EedomusSensor(mock_coordinator, device_info)

    assert sensor.native_value is None


@pytest.mark.asyncio
async def test_sensor_update():
    """Test sensor update mechanism."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {"temp_sensor": {"value": 20.0}}

    device_info = {
        "periph_id": "temp_sensor",
        "name": "Temperature Sensor",
        "usage_id": "7",
    }

    sensor = EedomusSensor(mock_coordinator, device_info)

    # Initial value
    assert sensor.native_value == 20.0

    # Simulate update
    mock_coordinator.data["temp_sensor"]["value"] = 22.5

    # Value should update
    assert sensor.native_value == 22.5
