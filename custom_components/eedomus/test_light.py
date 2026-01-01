"""Tests for Eedomus light entities."""
from unittest.mock import AsyncMock, patch
import pytest
from homeassistant.components.light import ColorMode, ATTR_BRIGHTNESS, ATTR_RGBW
from homeassistant.const import STATE_ON, STATE_OFF
from .light import EedomusLight


@pytest.mark.asyncio
async def test_light_initialization():
    """Test light entity initialization."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "light_123": {
            "name": "Test Light",
            "value": "on",
            "brightness": 255,
            "color": "255,255,255,255"
        }
    }
    
    device_info = {
        "periph_id": "light_123",
        "name": "Test Light",
        "usage_id": "1",
        "color_mode": "rgbw"
    }
    
    light = EedomusLight(mock_coordinator, device_info)
    
    assert light.name == "Test Light"
    assert light.unique_id == "eedomus_light_light_123"
    assert light.is_on is True
    assert light.color_mode == ColorMode.RGBW
    assert light.brightness == 255


@pytest.mark.asyncio
async def test_light_off_state():
    """Test light in off state."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "light_123": {
            "value": "off",
            "brightness": 0
        }
    }
    
    device_info = {
        "periph_id": "light_123",
        "name": "Test Light",
        "color_mode": "brightness"
    }
    
    light = EedomusLight(mock_coordinator, device_info)
    
    assert light.is_on is False
    assert light.brightness == 0


@pytest.mark.asyncio
async def test_light_turn_on():
    """Test light turn on method."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "light_123": {
            "value": "off",
            "brightness": 0,
            "value_list": ["on", "off"]
        }
    }
    
    device_info = {
        "periph_id": "light_123",
        "name": "Test Light"
    }
    
    light = EedomusLight(mock_coordinator, device_info)
    
    with patch.object(light, "_set_light_value") as mock_set_value:
        await light.async_turn_on()
        mock_set_value.assert_called_once_with("on")


@pytest.mark.asyncio
async def test_light_turn_off():
    """Test light turn off method."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "light_123": {
            "value": "on",
            "value_list": ["on", "off"]
        }
    }
    
    device_info = {
        "periph_id": "light_123",
        "name": "Test Light"
    }
    
    light = EedomusLight(mock_coordinator, device_info)
    
    with patch.object(light, "_set_light_value") as mock_set_value:
        await light.async_turn_off()
        mock_set_value.assert_called_once_with("off")


@pytest.mark.asyncio
async def test_light_with_consumption_child():
    """Test light with consumption child (Issue #9 related)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "light_123": {
            "name": "Test Light",
            "value": "on",
            "brightness": 255,
            "value_list": ["on", "off"]
        },
        "light_123_consumption": {
            "consumption": 20.5,
            "current_power": 80,
            "usage_id": "26",
            "name": "Consommation"
        }
    }
    
    device_info = {
        "periph_id": "light_123",
        "name": "Test Light",
        "usage_id": "1",
        "color_mode": "brightness",
        "children": [
            {"periph_id": "light_123_consumption", "usage_id": "26"}
        ]
    }
    
    light = EedomusLight(mock_coordinator, device_info)
    
    # Verify light properties
    assert light.name == "Test Light"
    assert light.is_on is True
    
    # Verify consumption data exists for energy sensor creation
    consumption_data = mock_coordinator.data.get("light_123_consumption", {})
    assert consumption_data.get("consumption") == 20.5
    assert consumption_data.get("current_power") == 80


@pytest.mark.asyncio
async def test_light_rgbw_color():
    """Test RGBW light color handling."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "light_rgbw": {
            "name": "RGBW Light",
            "value": "on",
            "color": "255,128,64,200",  # R,G,B,W
            "value_list": ["on", "off"]
        }
    }
    
    device_info = {
        "periph_id": "light_rgbw",
        "name": "RGBW Light",
        "usage_id": "1",
        "color_mode": "rgbw"
    }
    
    light = EedomusLight(mock_coordinator, device_info)
    
    assert light.color_mode == ColorMode.RGBW
    # Verify color parsing
    color_parts = light._parse_color("255,128,64,200")
    assert color_parts == [255, 128, 64, 200]


@pytest.mark.asyncio
async def test_light_brightness_only():
    """Test brightness-only light."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "light_dimmer": {
            "name": "Dimmer Light",
            "value": "on",
            "brightness": 128,
            "value_list": ["on", "off"]
        }
    }
    
    device_info = {
        "periph_id": "light_dimmer",
        "name": "Dimmer Light",
        "usage_id": "1",
        "color_mode": "brightness"
    }
    
    light = EedomusLight(mock_coordinator, device_info)
    
    assert light.color_mode == ColorMode.BRIGHTNESS
    assert light.brightness == 128
    assert light.supported_color_modes == {ColorMode.BRIGHTNESS}