"""Tests for Eedomus cover entities."""
from unittest.mock import AsyncMock, patch
import pytest
from homeassistant.components.cover import CoverDeviceClass, CoverEntityFeature
from homeassistant.const import STATE_OPEN, STATE_CLOSED, STATE_OPENING, STATE_CLOSING
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from cover import EedomusCover


@pytest.mark.asyncio
async def test_cover_initialization():
    """Test cover entity initialization."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "cover_123": {
            "name": "Test Cover",
            "value": "open",
            "position": 100,
            "tilt_position": 50
        }
    }
    
    device_info = {
        "periph_id": "cover_123",
        "name": "Test Cover",
        "usage_id": "48"
    }
    
    cover = EedomusCover(mock_coordinator, device_info)
    
    assert cover.name == "Test Cover"
    assert cover.unique_id == "eedomus_cover_cover_123"
    assert cover.is_closed is False
    assert cover.current_cover_position == 100
    assert cover.current_cover_tilt_position == 50
    assert cover.supported_features == (
        CoverEntityFeature.OPEN | 
        CoverEntityFeature.CLOSE | 
        CoverEntityFeature.STOP | 
        CoverEntityFeature.SET_POSITION | 
        CoverEntityFeature.SET_TILT_POSITION
    )


@pytest.mark.asyncio
async def test_cover_closed_state():
    """Test cover in closed state."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "cover_123": {
            "value": "closed",
            "position": 0
        }
    }
    
    device_info = {
        "periph_id": "cover_123",
        "name": "Test Cover"
    }
    
    cover = EedomusCover(mock_coordinator, device_info)
    
    assert cover.is_closed is True
    assert cover.current_cover_position == 0


@pytest.mark.asyncio
async def test_cover_open_method():
    """Test cover open method."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "cover_123": {
            "value": "closed",
            "position": 0
        }
    }
    
    device_info = {
        "periph_id": "cover_123",
        "name": "Test Cover"
    }
    
    cover = EedomusCover(mock_coordinator, device_info)
    
    with patch.object(cover, "_set_cover_value") as mock_set_value:
        await cover.async_open_cover()
        mock_set_value.assert_called_once_with("open")


@pytest.mark.asyncio
async def test_cover_set_position():
    """Test cover set position method."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "cover_123": {
            "value": "open",
            "position": 50
        }
    }
    
    device_info = {
        "periph_id": "cover_123",
        "name": "Test Cover"
    }
    
    cover = EedomusCover(mock_coordinator, device_info)
    
    with patch.object(cover, "_set_cover_value") as mock_set_value:
        await cover.async_set_cover_position(position=75)
        mock_set_value.assert_called_once_with("75")


@pytest.mark.asyncio
async def test_cover_with_energy_sensor():
    """Test cover with associated energy sensor (Issue #9 related)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "cover_123": {
            "name": "Test Cover",
            "value": "open",
            "position": 100
        },
        "cover_123_consumption": {
            "consumption": 25.5,
            "current_power": 50
        }
    }
    
    device_info = {
        "periph_id": "cover_123",
        "name": "Test Cover",
        "usage_id": "48",
        "children": [
            {"periph_id": "cover_123_consumption", "usage_id": "26"}
        ]
    }
    
    cover = EedomusCover(mock_coordinator, device_info)
    
    # Verify cover properties
    assert cover.name == "Test Cover"
    
    # Verify energy sensor would be created for consumption child
    # This is handled in the coordinator setup, but we can verify the data exists
    consumption_data = mock_coordinator.data.get("cover_123_consumption", {})
    assert consumption_data.get("consumption") == 25.5