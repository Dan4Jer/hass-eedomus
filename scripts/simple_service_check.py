#!/usr/bin/env python3
"""
Simple service check that can be run on the Raspberry Pi.
"""

import sys
import os

# Add custom components to path
sys.path.insert(0, '/config/custom_components')

def main():
    """Main check function."""
    print("🔍 Eedomus Services Simple Check")
    print("=" * 35)
    
    try:
        # Try to import the UIService
        from eedomus.ui_service import EedomusUIService, WS_TYPE_EEDOMUS_VALIDATE
        print("✅ UIService can be imported")
        print(f"✅ WebSocket endpoint defined: {WS_TYPE_EEDOMUS_VALIDATE}")
        
        # Try to import other services
        from eedomus.data_service import EedomusDataService
        from eedomus.schema_service import SchemaService
        from eedomus.config_manager import EedomusConfigManager
        
        print("✅ All service classes are importable")
        print("\n🎉 Services check passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)