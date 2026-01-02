"""Tests for Eedomus switch entities."""

import os
import sys
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import STATE_OFF, STATE_ON

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from switch import EedomusSwitch


@pytest.mark.asyncio
async def test_switch_initialization():
    """Test switch entity initialization."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "switch_123": {
            "name": "Test Switch",
            "value": "on",
            "value_list": ["on", "off"],
        }
    }

    device_info = {"periph_id": "switch_123", "name": "Test Switch", "usage_id": "37"}

    switch = EedomusSwitch(mock_coordinator, device_info)

    assert switch.name == "Test Switch"
    assert switch.unique_id == "eedomus_switch_switch_123"
    assert switch.is_on is True


@pytest.mark.asyncio
async def test_switch_off_state():
    """Test switch in off state."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {"switch_123": {"value": "off"}}

    device_info = {"periph_id": "switch_123", "name": "Test Switch"}

    switch = EedomusSwitch(mock_coordinator, device_info)

    assert switch.is_on is False


@pytest.mark.asyncio
async def test_switch_turn_on():
    """Test switch turn on method."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "switch_123": {"value": "off", "value_list": ["on", "off"]}
    }

    device_info = {"periph_id": "switch_123", "name": "Test Switch"}

    switch = EedomusSwitch(mock_coordinator, device_info)

    with patch.object(switch, "_set_switch_value") as mock_set_value:
        await switch.async_turn_on()
        mock_set_value.assert_called_once_with("on")


@pytest.mark.asyncio
async def test_switch_turn_off():
    """Test switch turn off method."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {"switch_123": {"value": "on", "value_list": ["on", "off"]}}

    device_info = {"periph_id": "switch_123", "name": "Test Switch"}

    switch = EedomusSwitch(mock_coordinator, device_info)

    with patch.object(switch, "_set_switch_value") as mock_set_value:
        await switch.async_turn_off()
        mock_set_value.assert_called_once_with("off")


@pytest.mark.asyncio
async def test_switch_with_consumption_child():
    """Test switch with consumption child (Issue #9 related)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "switch_123": {
            "name": "Test Switch",
            "value": "on",
            "value_list": ["on", "off"],
        },
        "switch_123_consumption": {
            "consumption": 15.5,
            "current_power": 100,
            "usage_id": "26",
        },
    }

    device_info = {
        "periph_id": "switch_123",
        "name": "Test Switch",
        "usage_id": "37",
        "children": [
            {
                "periph_id": "switch_123_consumption",
                "usage_id": "26",
                "name": "Consommation",
            }
        ],
    }

    switch = EedomusSwitch(mock_coordinator, device_info)

    # Verify switch properties
    assert switch.name == "Test Switch"
    assert switch.is_on is True

    # Verify consumption data exists for energy sensor creation
    consumption_data = mock_coordinator.data.get("switch_123_consumption", {})
    assert consumption_data.get("consumption") == 15.5
    assert consumption_data.get("current_power") == 100


@pytest.mark.asyncio
async def test_switch_consumption_only_device():
    """Test switch that should be remapped as energy sensor."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "consumption_monitor": {
            "name": "Consommation Salon",
            "value": "150",
            "value_list": ["150"],
        }
    }

    device_info = {
        "periph_id": "consumption_monitor",
        "name": "Consommation Salon",
        "usage_id": "2",  # Appareil électrique
        "children": [
            {
                "periph_id": "consumption_monitor_power",
                "usage_id": "26",
                "name": "Puissance",
            }
        ],
    }

    # This should be detected as a consumption monitor and remapped
    # The test verifies the data structure that would trigger remapping
    switch = EedomusSwitch(mock_coordinator, device_info)

    # Verify the device has the right characteristics for remapping
    assert (
        "conso" in device_info["name"].lower()
        or "consommation" in device_info["name"].lower()
    )

    # Check if it has consumption children
    has_consumption_children = any(
        child.get("usage_id") == "26" for child in device_info.get("children", [])
    )
    assert has_consumption_children is True
