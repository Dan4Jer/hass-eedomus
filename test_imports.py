#!/usr/bin/env python3
"""Test script to verify basic imports and syntax"""

import sys
import os

# Add custom_components to path
sys.path.insert(0, 'custom_components')

print("Testing imports...")

try:
    # Test basic imports
    from eedomus.const import DOMAIN, CONF_API_HOST
    print(f"✅ DOMAIN: {DOMAIN}")
    print(f"✅ CONF_API_HOST: {CONF_API_HOST}")
    
    # Test coordinator import
    from eedomus.coordinator import EedomusDataUpdateCoordinator
    print("✅ EedomusDataUpdateCoordinator imported")
    
    # Test entity import
    from eedomus.entity import EedomusEntity
    print("✅ EedomusEntity imported")
    
    # Test services import
    from eedomus.services import async_setup_services
    print("✅ async_setup_services imported")
    
    print("\n✅ All imports successful!")
    
except ImportError as e:
    print(f"❌ ImportError: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
