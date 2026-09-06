"""Unit tests for Eedomus UI Service and Panel components.

Tests for:
- ui_service.py: WebSocket command registration, validation, cleanup
- panel.py: Panel registration, duplicate prevention
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

# Add the custom component to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "custom_components/eedomus")))


# ============================================================================
# UI SERVICE TESTS
# ============================================================================

class TestEedomusUIService:
    """Tests for EedomusUIService class."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance."""
        hass = MagicMock()
        hass.config.config_dir = "/tmp"
        return hass

    @pytest.fixture
    def ui_service(self, mock_hass):
        """Create an EedomusUIService instance."""
        from ui_service import EedomusUIService
        return EedomusUIService(mock_hass)

    def test_ui_service_initialization(self, ui_service, mock_hass):
        """Test UIService initializes correctly."""
        assert ui_service.hass == mock_hass
        assert ui_service._registered_commands == []
        assert ui_service._initialized is False

    @patch('ui_service._LOGGER')
    @patch('homeassistant.components.websocket_api.async_register_command', new_callable=AsyncMock)
    async def test_async_init_success(self, mock_register, mock_logger, ui_service, mock_hass):
        """Test successful UIService initialization with WebSocket API."""
        # Configure mock to return unregister functions
        mock_register.side_effect = [
            AsyncMock(),  # validate_config
            AsyncMock(),  # get_suggestions
            AsyncMock(),  # get_schema
            AsyncMock(),  # get_cache_stats
        ]
        
        await ui_service.async_init()
        
        # Verify initialization
        assert ui_service._initialized is True
        assert len(ui_service._registered_commands) == 4
        assert mock_logger.info.call_count == 1
        
        # Verify WebSocket commands were registered
        expected_commands = [
            "eedomus/validate_config",
            "eedomus/get_suggestions", 
            "eedomus/get_schema",
            "eedomus/get_cache_stats"
        ]
        for i, cmd in enumerate(expected_commands):
            mock_register.assert_any_call_with(mock_hass, cmd, ANY)

    @patch('ui_service._LOGGER')
    async def test_async_init_websocket_unavailable(self, mock_logger, ui_service, mock_hass):
        """Test UIService initialization when WebSocket API is not available."""
        # Simulate ImportError for WebSocket API
        with patch.dict('sys.modules', {'homeassistant.components.websocket_api': None}):
            with patch('builtins.__import__', side_effect=ImportError("No module")):
                await ui_service.async_init()
        
        # Should still initialize in limited mode
        assert ui_service._initialized is True
        assert len(ui_service._registered_commands) == 0
        mock_logger.warning.assert_called_once()

    @patch('ui_service._LOGGER')
    async def test_async_init_exception(self, mock_logger, ui_service, mock_hass):
        """Test UIService initialization handles exceptions gracefully."""
        with patch('homeassistant.components.websocket_api.async_register_command', 
                  side_effect=Exception("WebSocket error")):
            await ui_service.async_init()
        
        # Should not raise, but log error and continue in limited mode
        assert ui_service._initialized is False
        mock_logger.error.assert_called_once()

    @patch('ui_service._LOGGER')
    async def test_async_shutdown_empty(self, mock_logger, ui_service):
        """Test shutdown with no registered commands."""
        ui_service._registered_commands = []
        await ui_service.async_shutdown()
        
        assert ui_service._registered_commands == []
        assert ui_service._initialized is False
        mock_logger.debug.assert_called_once()

    @patch('ui_service._LOGGER')
    async def test_async_shutdown_with_commands(self, mock_logger, ui_service):
        """Test shutdown properly unregisters all commands."""
        # Create mock unregister functions
        mock_unregister_1 = AsyncMock()
        mock_unregister_2 = AsyncMock()
        mock_unregister_3 = AsyncMock()
        
        ui_service._registered_commands = [
            mock_unregister_1,
            mock_unregister_2, 
            mock_unregister_3
        ]
        ui_service._initialized = True
        
        await ui_service.async_shutdown()
        
        # Verify all commands were called
        mock_unregister_1.assert_called_once()
        mock_unregister_2.assert_called_once()
        mock_unregister_3.assert_called_once()
        
        assert ui_service._registered_commands == []
        assert ui_service._initialized is False

    @patch('ui_service._LOGGER')
    async def test_async_shutdown_none_unregister_func(self, mock_logger, ui_service):
        """Test shutdown handles None unregister functions gracefully."""
        # This tests the fix for: "Failed to unregister WebSocket command: 'NoneType' object is not callable"
        ui_service._registered_commands = [
            None,  # This was causing the error
            AsyncMock(),
            None,
        ]
        ui_service._initialized = True
        
        await ui_service.async_shutdown()
        
        # Should not raise, just skip None entries
        assert ui_service._registered_commands == []
        assert ui_service._initialized is False
        # Should not have error logs for None entries
        error_calls = [call for call in mock_logger.error.call_args_list 
                      if "Failed to unregister" in str(call)]
        assert len(error_calls) == 0

    @patch('ui_service._LOGGER')
    async def test_async_shutdown_non_callable_unregister_func(self, mock_logger, ui_service):
        """Test shutdown handles non-callable unregister functions."""
        # This tests additional edge cases
        ui_service._registered_commands = [
            "not_callable",  # String instead of function
            AsyncMock(),
            123,  # Integer
        ]
        ui_service._initialized = True
        
        await ui_service.async_shutdown()
        
        # Should not raise
        assert ui_service._registered_commands == []
        assert ui_service._initialized is False

    async def test_handle_validate_config_basic(self, ui_service, mock_hass):
        """Test basic config validation handler."""
        mock_connection = AsyncMock()
        mock_msg = {'yaml_content': 'test: value'}
        
        # Mock the WebSocket command to avoid actual registration
        ui_service._registered_commands = []
        
        result = await ui_service._handle_validate_config(
            mock_hass, mock_connection, mock_msg
        )
        
        # Should return a dict with result
        assert isinstance(result, dict)

    async def test_handle_get_suggestions_basic(self, ui_service, mock_hass):
        """Test basic suggestions handler."""
        mock_connection = AsyncMock()
        mock_msg = {'entity_type': 'light', 'usage_id': '1'}
        
        result = await ui_service._handle_get_suggestions(
            mock_hass, mock_connection, mock_msg
        )
        
        assert isinstance(result, dict)

    async def test_handle_get_schema_basic(self, ui_service, mock_hass):
        """Test basic schema handler."""
        mock_connection = AsyncMock()
        mock_msg = {}
        
        result = await ui_service._handle_get_schema(
            mock_hass, mock_connection, mock_msg
        )
        
        assert isinstance(result, dict)

    async def test_handle_get_cache_stats_basic(self, ui_service, mock_hass):
        """Test basic cache stats handler."""
        mock_connection = AsyncMock()
        mock_msg = {}
        
        result = await ui_service._handle_get_cache_stats(
            mock_hass, mock_connection, mock_msg
        )
        
        assert isinstance(result, dict)


# ============================================================================
# PANEL TESTS
# ============================================================================

class TestEedomusPanel:
    """Tests for Eedomus panel registration."""

    @pytest.fixture
    def mock_hass(self):
        """Create a mock HomeAssistant instance."""
        hass = MagicMock()
        return hass

    @patch('panel._LOGGER')
    @patch('panel._PANEL_REGISTERED', False)
    async def test_async_setup_panel_success(self, mock_logger, mock_hass):
        """Test successful panel setup."""
        from panel import async_setup_panel, _PANEL_REGISTERED
        
        # Reset global for test
        import panel as panel_module
        panel_module._PANEL_REGISTERED = False
        
        with patch('homeassistant.components.frontend.async_register_built_in_panel') as mock_register:
            result = await async_setup_panel(mock_hass)
        
        assert result is True
        assert panel_module._PANEL_REGISTERED is True
        mock_logger.info.assert_called_once()
        mock_register.assert_called_once_with(
            mock_hass,
            "eedomus-config",
            "eedomus-config-panel",
            "mdi:cog",
            require_admin=True
        )

    @patch('panel._LOGGER')
    @patch('panel._PANEL_REGISTERED', False)
    async def test_async_setup_panel_duplicate(self, mock_logger, mock_hass):
        """Test panel setup skips duplicate registration."""
        from panel import async_setup_panel
        import panel as panel_module
        
        # First registration
        panel_module._PANEL_REGISTERED = False
        with patch('homeassistant.components.frontend.async_register_built_in_panel'):
            await async_setup_panel(mock_hass)
        
        assert panel_module._PANEL_REGISTERED is True
        
        # Second call should skip
        with patch('homeassistant.components.frontend.async_register_built_in_panel') as mock_register:
            result = await async_setup_panel(mock_hass)
        
        assert result is True
        # Should not register again
        mock_register.assert_not_called()
        mock_logger.debug.assert_called_once()

    @patch('panel._LOGGER')
    @patch('panel._PANEL_REGISTERED', False)
    async def test_async_setup_panel_frontend_unavailable(self, mock_logger, mock_hass):
        """Test panel setup when frontend component is not available."""
        from panel import async_setup_panel
        import panel as panel_module
        panel_module._PANEL_REGISTERED = False
        
        # Simulate ImportError
        with patch.dict('sys.modules', {'homeassistant.components.frontend': None}):
            with patch('builtins.__import__', side_effect=ImportError("No module")):
                result = await async_setup_panel(mock_hass)
        
        assert result is False
        mock_logger.warning.assert_called_once()

    @patch('panel._LOGGER')
    @patch('panel._PANEL_REGISTERED', False)
    async def test_async_setup_panel_exception(self, mock_logger, mock_hass):
        """Test panel setup handles exceptions."""
        from panel import async_setup_panel
        import panel as panel_module
        panel_module._PANEL_REGISTERED = False
        
        with patch('homeassistant.components.frontend.async_register_built_in_panel',
                  side_effect=Exception("Registration error")):
            result = await async_setup_panel(mock_hass)
        
        assert result is False
        mock_logger.error.assert_called_once()

    async def test_async_unload_panel(self):
        """Test panel unload."""
        from panel import async_unload_panel
        
        result = await async_unload_panel(MagicMock())
        
        assert result is True


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestUIServicePanelIntegration:
    """Integration tests for UIService and Panel."""

    async def test_pipeline_init_and_cleanup(self):
        """Test complete initialization and cleanup pipeline."""
        from ui_service import EedomusUIService
        
        mock_hass = MagicMock()
        service = EedomusUIService(mock_hass)
        
        # Initialization
        with patch('homeassistant.components.websocket_api.async_register_command',
                  side_effect=[AsyncMock()] * 4):
            await service.async_init()
        
        assert service._initialized is True
        assert len(service._registered_commands) == 4
        
        # Cleanup
        await service.async_shutdown()
        
        assert service._initialized is False
        assert len(service._registered_commands) == 0

    async def test_multiple_panels_only_registers_once(self):
        """Test that multiple panel setup calls only register once."""
        from panel import async_setup_panel
        import panel as panel_module
        
        mock_hass = MagicMock()
        
        # Reset global
        panel_module._PANEL_REGISTERED = False
        
        with patch('homeassistant.components.frontend.async_register_built_in_panel') as mock_register:
            # First call
            await async_setup_panel(mock_hass)
            # Second call
            await async_setup_panel(mock_hass)
            # Third call
            await async_setup_panel(mock_hass)
        
        # Should only register once
        assert mock_register.call_count == 1


# ============================================================================
# EDGE CASE TESTS (for the specific errors mentioned in logs)
# ============================================================================

class TestErrorScenarios:
    """Tests for specific error scenarios found in logs."""

    async def test_unregister_none_type_object_not_callable(self):
        """Test: 'Failed to unregister WebSocket command: 'NoneType' object is not callable'
        
        This was a real error in the logs. The fix ensures None is checked before calling.
        """
        from ui_service import EedomusUIService
        
        mock_hass = MagicMock()
        service = EedomusUIService(mock_hass)
        
        # Simulate the error condition: registered_commands contains None
        service._registered_commands = [None, None, None]
        service._initialized = True
        
        # This should NOT raise an error
        await service.async_shutdown()
        
        # All should be cleared
        assert service._registered_commands == []

    async def test_panel_overwriting_error(self):
        """Test: 'Error setting up Eedomus panel: Overwriting panel eedomus-config owned by eedomus-config'
        
        This was a real error in the logs. The fix uses _PANEL_REGISTERED flag to prevent duplicates.
        """
        from panel import async_setup_panel
        import panel as panel_module
        
        mock_hass = MagicMock()
        
        # Reset global
        panel_module._PANEL_REGISTERED = False
        
        with patch('homeassistant.components.frontend.async_register_built_in_panel') as mock_register:
            # First registration
            result1 = await async_setup_panel(mock_hass)
            assert result1 is True
            
            # Second registration should skip and NOT cause "Overwriting panel" error
            with patch('panel._LOGGER') as mock_logger:
                result2 = await async_setup_panel(mock_hass)
                assert result2 is True
                # Should log that it's skipping
                mock_logger.debug.assert_called_with(
                    "Eedomus panel already registered, skipping duplicate registration"
                )
                # Should NOT register again
                assert mock_register.call_count == 1


if __name__ == "__main__":
    # Run tests directly if executed
    import asyncio
    
    async def run_tests():
        # Create test instances
        mock_hass = MagicMock()
        
        # Test UIService
        from ui_service import EedomusUIService
        ui_service = EedomusUIService(mock_hass)
        
        print("Testing UIService initialization...")
        with patch('homeassistant.components.websocket_api.async_register_command',
                  side_effect=[AsyncMock()] * 4):
            await ui_service.async_init()
        assert ui_service._initialized is True
        print("✅ UIService initialization test passed")
        
        print("Testing UIService shutdown with None commands...")
        ui_service._registered_commands = [None, AsyncMock(), None]
        await ui_service.async_shutdown()
        assert ui_service._registered_commands == []
        print("✅ UIService shutdown test passed")
        
        # Test Panel
        from panel import async_setup_panel
        import panel as panel_module
        panel_module._PANEL_REGISTERED = False
        
        print("Testing panel registration...")
        with patch('homeassistant.components.frontend.async_register_built_in_panel'):
            result = await async_setup_panel(mock_hass)
        assert result is True
        print("✅ Panel registration test passed")
        
        print("Testing duplicate panel prevention...")
        result = await async_setup_panel(mock_hass)
        assert result is True
        print("✅ Duplicate panel prevention test passed")
        
        print("\n🎉 All basic tests passed!")
    
    asyncio.run(run_tests())
