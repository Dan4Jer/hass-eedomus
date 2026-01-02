"""Integration tests for Eedomus entities with focus on Issue #9 (energy sensors)."""

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cover import EedomusCover
from light import EedomusLight
from sensor import EedomusEnergySensor, EedomusSensor
from switch import EedomusSwitch


@pytest.mark.asyncio
async def test_integration_cover_with_energy_sensor():
    """Test integration between cover and energy sensor (Issue #9)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "cover_123": {
            "name": "Living Room Shutter",
            "value": "open",
            "position": 100,
            "usage_id": "48",
        },
        "cover_123_consumption": {
            "name": "Living Room Shutter Consumption",
            "consumption": 15.5,
            "current_power": 50,
            "usage_id": "26",
            "last_reset": "2023-01-01",
        },
    }

    # Create cover entity
    cover_device_info = {
        "periph_id": "cover_123",
        "name": "Living Room Shutter",
        "usage_id": "48",
        "children": [
            {
                "periph_id": "cover_123_consumption",
                "usage_id": "26",
                "name": "Consommation",
            }
        ],
    }

    cover = EedomusCover(mock_coordinator, cover_device_info)

    # Verify cover properties
    assert cover.name == "Living Room Shutter"
    assert cover.is_closed is False

    # Create energy sensor from consumption child
    energy_sensor_device_info = {
        "id": "cover_123_consumption",
        "name": "Living Room Shutter Consumption",
        "usage_id": "26",
    }

    energy_sensor = EedomusEnergySensor(mock_coordinator, energy_sensor_device_info)

    # Verify energy sensor properties
    assert energy_sensor.name == "Living Room Shutter Consumption"
    assert energy_sensor.native_value == 15.5
    assert energy_sensor.extra_state_attributes["current_power"] == 50

    print("✅ Cover + Energy Sensor integration test passed")


@pytest.mark.asyncio
async def test_integration_switch_with_energy_sensor():
    """Test integration between switch and energy sensor (Issue #9)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "switch_123": {
            "name": "Living Room Light Switch",
            "value": "on",
            "value_list": ["on", "off"],
            "usage_id": "37",
        },
        "switch_123_consumption": {
            "name": "Living Room Light Consumption",
            "consumption": 25.5,
            "current_power": 100,
            "usage_id": "26",
            "last_reset": "2023-01-01",
        },
    }

    # Create switch entity
    switch_device_info = {
        "periph_id": "switch_123",
        "name": "Living Room Light Switch",
        "usage_id": "37",
        "children": [
            {
                "periph_id": "switch_123_consumption",
                "usage_id": "26",
                "name": "Consommation",
            }
        ],
    }

    switch = EedomusSwitch(mock_coordinator, switch_device_info)

    # Verify switch properties
    assert switch.name == "Living Room Light Switch"
    assert switch.is_on is True

    # Create energy sensor from consumption child
    energy_sensor_device_info = {
        "id": "switch_123_consumption",
        "name": "Living Room Light Consumption",
        "usage_id": "26",
    }

    energy_sensor = EedomusEnergySensor(mock_coordinator, energy_sensor_device_info)

    # Verify energy sensor properties
    assert energy_sensor.name == "Living Room Light Consumption"
    assert energy_sensor.native_value == 25.5
    assert energy_sensor.extra_state_attributes["current_power"] == 100

    print("✅ Switch + Energy Sensor integration test passed")


@pytest.mark.asyncio
async def test_integration_light_with_energy_sensor():
    """Test integration between light and energy sensor (Issue #9)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "light_123": {
            "name": "Living Room Light",
            "value": "on",
            "brightness": 255,
            "color": "255,255,255,255",
            "usage_id": "1",
        },
        "light_123_consumption": {
            "name": "Living Room Light Consumption",
            "consumption": 20.5,
            "current_power": 80,
            "usage_id": "26",
            "last_reset": "2023-01-01",
        },
    }

    # Create light entity
    light_device_info = {
        "periph_id": "light_123",
        "name": "Living Room Light",
        "usage_id": "1",
        "color_mode": "rgbw",
        "children": [
            {
                "periph_id": "light_123_consumption",
                "usage_id": "26",
                "name": "Consommation",
            }
        ],
    }

    light = EedomusLight(mock_coordinator, light_device_info)

    # Verify light properties
    assert light.name == "Living Room Light"
    assert light.is_on is True
    assert light.brightness == 255

    # Create energy sensor from consumption child
    energy_sensor_device_info = {
        "id": "light_123_consumption",
        "name": "Living Room Light Consumption",
        "usage_id": "26",
    }

    energy_sensor = EedomusEnergySensor(mock_coordinator, energy_sensor_device_info)

    # Verify energy sensor properties
    assert energy_sensor.name == "Living Room Light Consumption"
    assert energy_sensor.native_value == 20.5
    assert energy_sensor.extra_state_attributes["current_power"] == 80

    print("✅ Light + Energy Sensor integration test passed")


@pytest.mark.asyncio
async def test_multiple_devices_with_energy_sensors():
    """Test multiple devices each with their own energy sensor (Issue #9)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        # Switch with consumption
        "switch_1": {
            "name": "Device 1 Switch",
            "value": "on",
            "usage_id": "37",
        },
        "switch_1_consumption": {
            "consumption": 10.5,
            "current_power": 50,
            "usage_id": "26",
        },
        # Light with consumption
        "light_1": {
            "name": "Device 2 Light",
            "value": "on",
            "brightness": 200,
            "usage_id": "1",
        },
        "light_1_consumption": {
            "consumption": 15.0,
            "current_power": 75,
            "usage_id": "26",
        },
        # Cover with consumption
        "cover_1": {
            "name": "Device 3 Cover",
            "value": "open",
            "position": 100,
            "usage_id": "48",
        },
        "cover_1_consumption": {
            "consumption": 5.5,
            "current_power": 25,
            "usage_id": "26",
        },
    }

    # Create energy sensors for all devices
    energy_sensors = []

    for device_type, device_id in [("switch", "1"), ("light", "1"), ("cover", "1")]:
        energy_sensor_device_info = {
            "id": f"{device_type}_{device_id}_consumption",
            "name": f"{device_type.capitalize()} {device_id} Consumption",
            "usage_id": "26",
        }

        sensor = EedomusEnergySensor(mock_coordinator, energy_sensor_device_info)
        energy_sensors.append(sensor)

    # Verify all energy sensors have correct data
    assert energy_sensors[0].native_value == 10.5  # Switch consumption
    assert energy_sensors[1].native_value == 15.0  # Light consumption
    assert energy_sensors[2].native_value == 5.5  # Cover consumption

    print("✅ Multiple devices with energy sensors test passed")


@pytest.mark.asyncio
async def test_energy_sensor_data_update():
    """Test energy sensor data updates over time (Issue #9)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "device_consumption": {
            "consumption": 10.0,
            "current_power": 50,
            "last_reset": "2023-01-01",
        }
    }

    device_info = {
        "id": "device_consumption",
        "name": "Device Consumption",
        "usage_id": "26",
    }

    sensor = EedomusEnergySensor(mock_coordinator, device_info)

    # Initial values
    assert sensor.native_value == 10.0
    assert sensor.extra_state_attributes["current_power"] == 50

    # Simulate data updates over time
    mock_coordinator.data["device_consumption"]["consumption"] = 12.5
    mock_coordinator.data["device_consumption"]["current_power"] = 60

    # Verify updated values
    assert sensor.native_value == 12.5
    assert sensor.extra_state_attributes["current_power"] == 60

    # Another update
    mock_coordinator.data["device_consumption"]["consumption"] = 15.0
    mock_coordinator.data["device_consumption"]["current_power"] = 75

    # Verify final values
    assert sensor.native_value == 15.0
    assert sensor.extra_state_attributes["current_power"] == 75

    print("✅ Energy sensor data update test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
