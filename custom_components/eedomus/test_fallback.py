"""Tests for the fallback functionality in eedomus_client."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientSession, ClientError
from homeassistant.config_entries import ConfigEntry
from hass-eedomus.eedomus_client import EedomusClient
from hass-eedomus.const import (
    CONF_PHP_FALLBACK_ENABLED, CONF_PHP_FALLBACK_SCRIPT_NAME, 
    CONF_PHP_FALLBACK_TIMEOUT, 
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
            CONF_PHP_FALLBACK_ENABLED: False,
            CONF_PHP_FALLBACK_SCRIPT_NAME: "eedomus_fallback",
            CONF_PHP_FALLBACK_TIMEOUT: 5,
            : False
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
    
    # Mock response from fallback script (JSON response from eedomus API)
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"success":1,"body":{"result":"ok"}}'  # Script returns JSON
    
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
            CONF_PHP_FALLBACK_ENABLED: True,
            CONF_PHP_FALLBACK_SCRIPT_NAME: "http://192.168.1.100/fallback.php",
            CONF_PHP_FALLBACK_TIMEOUT: 5,
            : False
        }
    )
    
    client = EedomusClient(session, config_entry)
    
    # Test
    result = await client.fallback_set_value("123", "50")
    
    # Assert
    assert result["success"] == 1
    assert result["body"]["result"] == "ok"


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
            CONF_PHP_FALLBACK_ENABLED: True,
            CONF_PHP_FALLBACK_SCRIPT_NAME: "http://192.168.1.100/fallback.php",
            CONF_PHP_FALLBACK_TIMEOUT: 5,
            : False
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
            CONF_PHP_FALLBACK_ENABLED: True,
            CONF_PHP_FALLBACK_SCRIPT_NAME: "http://192.168.1.100/fallback.php",
            CONF_PHP_FALLBACK_TIMEOUT: 1,  # Short timeout for test
            : False
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
            CONF_PHP_FALLBACK_ENABLED: True,
            CONF_PHP_FALLBACK_SCRIPT_NAME: "http://192.168.1.100/fallback.php",
            CONF_PHP_FALLBACK_TIMEOUT: 5,
            : False
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
async def test_fallback_script_parameters():
    """Test that fallback script receives correct parameters."""
    # Setup
    session = AsyncMock(spec=ClientSession)
    
    # Mock response from fallback script
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"success":1,"body":{"result":"ok"}}'
    
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
            CONF_PHP_FALLBACK_ENABLED: True,
            CONF_PHP_FALLBACK_SCRIPT_NAME: "http://192.168.1.100/fallback.php",
            CONF_PHP_FALLBACK_TIMEOUT: 5,
            : True
        }
    )
    
    client = EedomusClient(session, config_entry)
    
    # Test
    await client.fallback_set_value("123", "50")
    
    # Verify that session.get was called with correct parameters
    session.get.assert_called_once()
    call_args = session.get.call_args
    
    # Extract the URL and params from the call
    url = call_args[0][0]
    params = call_args[1].get('params', {})
    
    # Assert that the URL is correct
    assert url == "http://192.168.1.100/fallback.php"
    
    # Assert that all required parameters are present
    assert 'value' in params
    assert 'device_id' in params
    assert 'api_host' in params
    assert 'api_user' in params
    assert 'api_secret' in params
    assert 'log' in params
    
    # Assert that the parameter values are correct
    assert params['value'] == "50"
    assert params['device_id'] == "123"
    assert params['api_host'] == "192.168.1.100"
    assert params['api_user'] == "test_user"
    assert params['api_secret'] == "test_secret"
    assert params['log'] == "true"


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
    
    # Mock fallback script success (JSON response from eedomus API)
    mock_fallback_response = AsyncMock()
    mock_fallback_response.status = 200
    mock_fallback_response.read.return_value = b'{"success":1,"body":{"result":"ok"}}'
    
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
            CONF_PHP_FALLBACK_ENABLED: True,
            CONF_PHP_FALLBACK_SCRIPT_NAME: "http://192.168.1.100/fallback.php",
            CONF_PHP_FALLBACK_TIMEOUT: 5,
            : False
        }
    )
    
    client = EedomusClient(session, config_entry)
    
    # Mock fetch_data to return failure
    with patch.object(client, 'fetch_data', new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_api_response
        
        # Mock session.get for fallback script
        session.get.return_value.__aenter__.return_value = mock_fallback_response
        
        # Test
        result = await client.set_periph_value("123", "invalid_value")
        
        # Assert
        assert result["success"] == 1
        assert result["body"]["result"] == "ok"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
