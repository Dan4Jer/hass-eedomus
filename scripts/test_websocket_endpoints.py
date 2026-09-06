#!/usr/bin/env python3
"""
Test script to verify Eedomus WebSocket endpoints functionality on Raspberry Pi.
This script runs directly on the HA system to test the WebSocket API.
"""

import asyncio
import json
import sys
from datetime import datetime

async def test_websocket_endpoints():
    """Test WebSocket endpoints by importing and using the UIService."""
    print("🧪 Testing Eedomus WebSocket Endpoints on Raspberry Pi")
    print("=" * 55)
    
    try:
        # Import Home Assistant modules
        from homeassistant.core import HomeAssistant
        from homeassistant.bootstrap import async_setup_component
        
        # Create a minimal HomeAssistant instance for testing
        print("🔧 Setting up test environment...")
        
        # Import our UIService
        from custom_components.eedomus.ui_service import EedomusUIService
        from custom_components.eedomus.schema_service import SchemaService
        from custom_components.eedomus.data_service import EedomusDataService
        from custom_components.eedomus.config_manager import EedomusConfigManager
        from custom_components.eedomus.const import DOMAIN
        
        # Create mock services
        class MockHass:
            def __init__(self):
                self.data = {DOMAIN: {}}
                
        # Initialize services
        mock_hass = MockHass()
        
        # Initialize SchemaService
        schema_service = SchemaService()
        mock_hass.data[DOMAIN]['schema_service'] = schema_service
        
        # Initialize DataService  
        data_service = EedomusDataService(mock_hass)
        await data_service.async_init()
        mock_hass.data[DOMAIN]['data_service'] = data_service
        
        # Initialize ConfigManager
        config_manager = EedomusConfigManager(mock_hass)
        await config_manager.async_init()
        mock_hass.data[DOMAIN]['config_manager'] = config_manager
        
        # Initialize UIService
        print("🔧 Initializing UIService...")
        ui_service = EedomusUIService(mock_hass)
        await ui_service.async_init()
        
        print("✅ UIService initialized successfully!")
        
        # Test 1: Validate configuration
        print("\n📋 Test 1: Configuration Validation")
        test_yaml = """
custom_devices:
  - device_id: "123"
    device_type: "light"
    name: "Test Light"
    state: "on"
"""
        result = await ui_service.validate_config_via_websocket(test_yaml)
        print(f"Validation result: {json.dumps(result, indent=2)}")
        
        # Test 2: Get suggestions
        print("\n💡 Test 2: Get Suggestions")
        suggestions_result = await ui_service.get_suggestions_via_websocket('device_type', 'li')
        print(f"Suggestions for 'device_type' with query 'li': {suggestions_result}")
        
        # Test 3: WebSocket connection test
        print("\n🔌 Test 3: WebSocket Connection Test")
        connection_ok = await ui_service.test_websocket_connection()
        print(f"WebSocket connection test: {'✅ PASS' if connection_ok else '❌ FAIL'}")
        
        # Test 4: Available endpoints
        print("\n📡 Test 4: Available WebSocket Endpoints")
        endpoints = await ui_service.get_available_endpoints()
        for endpoint in endpoints:
            print(f"  - {endpoint['name']}: {endpoint['endpoint']}")
        
        # Cleanup
        await ui_service.async_shutdown()
        await data_service.async_shutdown()
        await config_manager.async_shutdown()
        
        print("\n🎉 All WebSocket endpoint tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_invalid_yaml():
    """Test validation with invalid YAML."""
    print("\n🧪 Testing Invalid YAML Handling")
    print("=" * 42)
    
    try:
        from custom_components.eedomus.ui_service import EedomusUIService
        from custom_components.eedomus.schema_service import SchemaService
        from custom_components.eedomus.const import DOMAIN
        
        class MockHass:
            def __init__(self):
                self.data = {DOMAIN: {'schema_service': SchemaService()}}
        
        ui_service = EedomusUIService(MockHass())
        await ui_service.async_init()
        
        # Test invalid YAML
        invalid_yaml = "invalid: yaml: content: [unclosed: bracket:"
        result = await ui_service.validate_config_via_websocket(invalid_yaml)
        print(f"Invalid YAML result: {json.dumps(result, indent=2)}")
        
        await ui_service.async_shutdown()
        print("✅ Invalid YAML test completed!")
        
    except Exception as e:
        print(f"❌ Invalid YAML test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run tests
    success = asyncio.run(test_websocket_endpoints())
    asyncio.run(test_invalid_yaml())
    
    if success:
        print("\n🎉 All WebSocket endpoint tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)