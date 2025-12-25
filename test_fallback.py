"""Tests for the fallback functionality in eedomus_client."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientSession, ClientError
from homeassistant.config_entries import ConfigEntry
from hass-eedomus.eedomus_client import EedomusClient
from hass-eedomus.const import (
    CONF_FALLBACK_ENABLED, CONF_FALLBACK_SCRIPT_URL, 
    CONF_FALLBACK_TIMEOUT, CONF_FALLBACK_LOG_ENABLED
)


@pytest.mark.asyncio
async def test_fallback_not_configured():
    """Test that fallback returns error when not configured."""
    # Setup
    session = AsyncMock(spec=ClientSession)
    config_entry = ConfigEntry(
        version=1,
        domain="eedomus",
        title="test",
        data={
            "api_host": "192.168.1.100",
            "api_user": "test_user",
            "api_secret": "test_secret"
        },
        options={
            CONF_FALLBACK_ENABLED: False,
            CONF_FALLBACK_SCRIPT_URL: "",
            CONF_FALLBACK_TIMEOUT: 5,
            CONF_FALLBACK_LOG_ENABLED: False
        }
    )
    
    client = EedomusClient(session, config_entry)
    
    # Test
    result = await client.fallback_set_value("123", "invalid_value")
    
    # Assert
    assert result["success"] == 0
    assert "Fallback not configured" in result["error"]


@pytest.mark.asyncio
async def test_fallback_script_success():
    """Test successful fallback script call and value transformation."""
    # Setup
    session = AsyncMock(spec=ClientSession)
    
    # Mock response from fallback script
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.read.return_value = b"100"  # Script returns "100"
    
    session.get.return_value.__aenter__.return_value = mock_response
    
    config_entry = ConfigEntry(
        version=1,
        domain="eedomus",
        title="test",
        data={
            "api_host": "192.168.1.100",
            "api_user": "test_user",
            "api_secret": "test_secret"
        },
        options={
            CONF_FALLBACK_ENABLED: True,
            CONF_FALLBACK_SCRIPT_URL: "http://192.168.1.100/fallback.php",
            CONF_FALLBACK_TIMEOUT: 5,
            CONF_FALLBACK_LOG_ENABLED: False
        }
    )
    
    client = EedomusClient(session, config_entry)
    
    # Mock the successful set_periph_value call
    with patch.object(client, 'set_periph_value', new_callable=AsyncMock) as mock_set_value:
        mock_set_value.return_value = {"success": 1, "message": "Value set successfully"}
        
        # Test
        result = await client.fallback_set_value("123", "haut")
        
        # Assert
        assert result["success"] == 1
        assert "Value set successfully" in result["message"]
        
        # Verify set_periph_value was called with the transformed value
        mock_set_value.assert_called_once_with("123", "100")


@pytest.mark.asyncio
async def test_fallback_script_error():
    """Test fallback script returns error."""
    # Setup
    session = AsyncMock(spec=ClientSession)
    
    # Mock error response from fallback script
    mock_response = AsyncMock()
    mock_response.status = 400
    mock_response.read.return_value = b"Invalid value: test"
    
    session.get.return_value.__aenter__.return_value = mock_response
    
    config_entry = ConfigEntry(
        version=1,
        domain="eedomus",
        title="test",
        data={
            "api_host": "192.168.1.100",
            "api_user": "test_user",
            "api_secret": "test_secret"
        },
        options={
            CONF_FALLBACK_ENABLED: True,
            CONF_FALLBACK_SCRIPT_URL: "http://192.168.1.100/fallback.php",
            CONF_FALLBACK_TIMEOUT: 5,
            CONF_FALLBACK_LOG_ENABLED: False
        }
    )
    
    client = EedomusClient(session, config_entry)
    
    # Test
    result = await client.fallback_set_value("123", "invalid_value")
    
    # Assert
    assert result["success"] == 0
    assert "Fallback script error: HTTP 400" in result["error"]
    assert "Invalid value: test" in result["details"]


@pytest.mark.asyncio
async def test_fallback_script_timeout():
    """Test fallback script timeout."""
    # Setup
    session = AsyncMock(spec=ClientSession)
    
    # Mock timeout
    session.get.side_effect = TimeoutError("Request timed out")
    
    config_entry = ConfigEntry(
        version=1,
        domain="eedomus",
        title="test",
        data={
            "api_host": "192.168.1.100",
            "api_user": "test_user",
            "api_secret": "test_secret"
        },
        options={
            CONF_FALLBACK_ENABLED: True,
            CONF_FALLBACK_SCRIPT_URL: "http://192.168.1.100/fallback.php",
            CONF_FALLBACK_TIMEOUT: 1,  # Short timeout for test
            CONF_FALLBACK_LOG_ENABLED: False
        }
    )
    
    client = EedomusClient(session, config_entry)
    
    # Test
    result = await client.fallback_set_value("123", "test_value")
    
    # Assert
    assert result["success"] == 0
    assert "Fallback script timeout" in result["error"]


@pytest.mark.asyncio
async def test_fallback_script_client_error():
    """Test fallback script client error."""
    # Setup
    session = AsyncMock(spec=ClientSession)
    
    # Mock client error
    session.get.side_effect = ClientError("Connection failed")
    
    config_entry = ConfigEntry(
        version=1,
        domain="eedomus",
        title="test",
        data={
            "api_host": "192.168.1.100",
            "api_user": "test_user",
            "api_secret": "test_secret"
        },
        options={
            CONF_FALLBACK_ENABLED: True,
            CONF_FALLBACK_SCRIPT_URL: "http://192.168.1.100/fallback.php",
            CONF_FALLBACK_TIMEOUT: 5,
            CONF_FALLBACK_LOG_ENABLED: False
        }
    )
    
    client = EedomusClient(session, config_entry)
    
    # Test
    result = await client.fallback_set_value("123", "test_value")
    
    # Assert
    assert result["success"] == 0
    assert "Fallback script client error" in result["error"]
    assert "Connection failed" in result["error"]


@pytest.mark.asyncio
async def test_set_periph_value_with_fallback():
    """Test set_periph_value uses fallback when API fails."""
    # Setup
    session = AsyncMock(spec=ClientSession)
    
    # Mock initial API failure
    mock_api_response = {
        "success": 0,
        "error": "Invalid parameter value",
        "error_code": "4"
    }
    
    # Mock fallback script success
    mock_fallback_response = AsyncMock()
    mock_fallback_response.status = 200
    mock_fallback_response.read.return_value = b"100"
    
    config_entry = ConfigEntry(
        version=1,
        domain="eedomus",
        title="test",
        data={
            "api_host": "192.168.1.100",
            "api_user": "test_user",
            "api_secret": "test_secret"
        },
        options={
            CONF_FALLBACK_ENABLED: True,
            CONF_FALLBACK_SCRIPT_URL: "http://192.168.1.100/fallback.php",
            CONF_FALLBACK_TIMEOUT: 5,
            CONF_FALLBACK_LOG_ENABLED: False
        }
    )
    
    client = EedomusClient(session, config_entry)
    
    # Mock fetch_data to return failure, then mock set_periph_value for fallback
    with patch.object(client, 'fetch_data', new_callable=AsyncMock) as mock_fetch:
        with patch.object(client, 'set_periph_value', new_callable=AsyncMock) as mock_set_value:
            # First call fails
            mock_fetch.return_value = mock_api_response
            # Second call (fallback) succeeds
            mock_set_value.return_value = {"success": 1, "message": "Value set successfully"}
            
            # Mock session.get for fallback script
            session.get.return_value.__aenter__.return_value = mock_fallback_response
            
            # Test
            result = await client.set_periph_value("123", "invalid_value")
            
            # Assert
            assert result["success"] == 1
            assert "Value set successfully" in result["message"]
            
            # Verify fallback was called
            mock_set_value.assert_called_with("123", "100")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
