#!/usr/bin/env python3
"""
Test WebSocket endpoints via Home Assistant API.
This script uses the HA Python API to test WebSocket communication.
"""

import asyncio
import sys
import os

# Add custom components to path
sys.path.insert(0, '/config/custom_components')

async def test_websocket_via_api():
    """Test WebSocket endpoints using HA API."""
    print("🧪 Testing Eedomus WebSocket Endpoints via HA API")
    print("=" * 50)
    
    try:
        # Import Home Assistant core
        import homeassistant.core as ha
        from homeassistant.core import HomeAssistant
        
        # Get the current HomeAssistant instance
        hass = ha.HomeAssistant('/config')
        
        # Check if Eedomus integration is loaded
        if 'eedomus' not in hass.data:
            print("❌ Eedomus integration not loaded")
            return False
            
        print("✅ Eedomus integration is loaded")
        
        # Check if UIService is available
        if 'ui_service' not in hass.data['eedomus']:
            print("❌ UIService not available")
            return False
            
        ui_service = hass.data['eedomus']['ui_service']
        print("✅ UIService is available")
        
        # Test WebSocket connection
        print("\n🔌 Testing WebSocket connection...")
        connection_ok = await ui_service.test_websocket_connection()
        print(f"WebSocket connection: {'✅ PASS' if connection_ok else '❌ FAIL'}")
        
        if not connection_ok:
            print("❌ WebSocket connection failed")
            return False
            
        # Test validation endpoint
        print("\n📋 Testing validation endpoint...")
        test_yaml = """
custom_devices:
  - device_id: "123"
    device_type: "light"
    name: "Test Light"
"""
        validation_result = await ui_service.validate_config_via_websocket(test_yaml)
        print(f"Validation result: {validation_result}")
        
        if not validation_result.get('success', False):
            print("❌ Validation failed")
            return False
            
        # Test suggestions endpoint
        print("\n💡 Testing suggestions endpoint...")
        suggestions_result = await ui_service.get_suggestions_via_websocket('device_type', 'li')
        print(f"Suggestions result: {suggestions_result}")
        
        if not suggestions_result.get('success', False):
            print("❌ Suggestions failed")
            return False
            
        # Test available endpoints
        print("\n📡 Available WebSocket endpoints:")
        endpoints = await ui_service.get_available_endpoints()
        for endpoint in endpoints:
            print(f"  - {endpoint['name']}: {endpoint['endpoint']}")
        
        print("\n🎉 All WebSocket endpoint tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_websocket_via_api())
    sys.exit(0 if success else 1)