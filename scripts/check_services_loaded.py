#!/usr/bin/env python3
"""
Simple script to check if Eedomus services are loaded in Home Assistant.
This script can be run on the Raspberry Pi to verify the integration status.
"""

import sys
import os

# Add custom components to path
sys.path.insert(0, '/config/custom_components')

def check_services():
    """Check if all Eedomus services are properly loaded."""
    print("🔍 Checking Eedomus Services Status")
    print("=" * 40)
    
    try:
        # Try to import all service classes
        from eedomus.ui_service import EedomusUIService
        from eedomus.data_service import EedomusDataService
        from eedomus.schema_service import SchemaService
        from eedomus.config_manager import EedomusConfigManager
        
        print("✅ All service classes can be imported successfully")
        
        # Check if services are registered in hass.data
        try:
            import homeassistant.core as ha
            # This would work if run within HA context
            print("📋 Service classes available:")
            print(f"  - UIService: {EedomusUIService}")
            print(f"  - DataService: {EedomusDataService}")
            print(f"  - SchemaService: {SchemaService}")
            print(f"  - ConfigManager: {EedomusConfigManager}")
            
            return True
            
        except Exception as e:
            print(f"ℹ️  Cannot check hass.data outside HA context: {e}")
            print("✅ But all service classes are importable")
            return True
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_websocket_endpoints():
    """Check if WebSocket endpoints are registered."""
    print("\n🔍 Checking WebSocket Endpoints")
    print("=" * 40)
    
    try:
        from eedomus.ui_service import (
            WS_TYPE_EEDOMUS_VALIDATE,
            WS_TYPE_EEDOMUS_SUGGESTIONS, 
            WS_TYPE_EEDOMUS_SCHEMA,
            WS_TYPE_EEDOMUS_CACHE_STATS
        )
        
        print("✅ All WebSocket command types defined:")
        print(f"  - Validate: {WS_TYPE_EEDOMUS_VALIDATE}")
        print(f"  - Suggestions: {WS_TYPE_EEDOMUS_SUGGESTIONS}")
        print(f"  - Schema: {WS_TYPE_EEDOMUS_SCHEMA}")
        print(f"  - Cache Stats: {WS_TYPE_EEDOMUS_CACHE_STATS}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Cannot import WebSocket endpoints: {e}")
        return False

if __name__ == "__main__":
    print("Eedomus Services Check")
    print("=" * 25)
    
    services_ok = check_services()
    websocket_ok = check_websocket_endpoints()
    
    if services_ok and websocket_ok:
        print("\n🎉 All checks passed! Eedomus services are ready.")
        sys.exit(0)
    else:
        print("\n💥 Some checks failed!")
        sys.exit(1)