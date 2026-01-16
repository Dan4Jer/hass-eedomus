#!/usr/bin/env python3
"""
Test script to debug device 1269454 mapping issue.

This script simulates the device structure and tests the mapping logic
to understand why device 1269454 is not being mapped as RGBW.
"""

import sys
import os

# Add the custom_components directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'custom_components'))

# Mock the homeassistant modules to avoid import errors
class MockConfigEntry:
    def __init__(self):
        self.entry_id = "test_entry"
        self.data = {}
        self.options = {}

class MockHomeAssistant:
    def __init__(self):
        self.data = {}

# Create mock modules
sys.modules['homeassistant'] = type(sys)('homeassistant')
sys.modules['homeassistant.config_entries'] = type(sys)('homeassistant.config_entries')
sys.modules['homeassistant.config_entries'].ConfigEntry = MockConfigEntry
sys.modules['homeassistant.core'] = type(sys)('homeassistant.core')
sys.modules['homeassistant.core'].HomeAssistant = MockHomeAssistant
sys.modules['homeassistant.helpers'] = type(sys)('homeassistant.helpers')
sys.modules['homeassistant.helpers.entity'] = type(sys)('homeassistant.helpers.entity')
sys.modules['homeassistant.helpers.update_coordinator'] = type(sys)('homeassistant.helpers.update_coordinator')

# Mock logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Now import the eedomus modules
from eedomus.device_mapping import ADVANCED_MAPPING_RULES, USAGE_ID_MAPPING
from eedomus.entity import map_device_to_ha_entity

def test_device_1269454_mapping():
    """Test the mapping logic for device 1269454 with different scenarios."""
    print("=== Testing Device 1269454 Mapping ===\n")
    
    # Scenario 1: Device with usage_id=1 but only 2 children (typical issue)
    print("Scenario 1: Device 1269454 with usage_id=1 and 2 children")
    
    device_1269454 = {
        "periph_id": "1269454",
        "name": "RGBW Lamp 1269454",
        "usage_id": "1",
        "SUPPORTED_CLASSES": "112,114,133,134,38,39,49,50,51,96",
        "GENERIC": "11",
        "PRODUCT_TYPE_ID": "2304"
    }
    
    # Only 2 children (not enough for RGBW detection)
    child_1 = {
        "periph_id": "1269455",
        "name": "RGBW Channel 1",
        "usage_id": "1",
        "parent_periph_id": "1269454"
    }
    
    child_2 = {
        "periph_id": "1269456", 
        "name": "RGBW Channel 2",
        "usage_id": "1",
        "parent_periph_id": "1269454"
    }
    
    all_devices = {
        "1269454": device_1269454,
        "1269455": child_1,
        "1269456": child_2
    }
    
    print(f"Device data: {device_1269454}")
    print(f"Children: {len([c for c in all_devices.values() if c.get('parent_periph_id') == '1269454'])}")
    
    # Test the mapping
    mapping = map_device_to_ha_entity(device_1269454, all_devices)
    print(f"Mapping result: {mapping}")
    print(f"Expected: light:rgbw, Got: {mapping['ha_entity']}:{mapping['ha_subtype']}")
    
    if mapping['ha_subtype'] == 'rgbw':
        print("✅ SUCCESS: Device correctly mapped as RGBW")
    else:
        print("❌ ISSUE: Device not mapped as RGBW")
        print("   This confirms the issue - device has usage_id=1 but not enough children")
    
    print("\n" + "="*50 + "\n")
    
    # Scenario 2: Device with 4 children (should work)
    print("Scenario 2: Device 1269454 with usage_id=1 and 4 children")
    
    child_3 = {
        "periph_id": "1269457",
        "name": "RGBW Channel 3", 
        "usage_id": "1",
        "parent_periph_id": "1269454"
    }
    
    child_4 = {
        "periph_id": "1269458",
        "name": "RGBW Channel 4",
        "usage_id": "1", 
        "parent_periph_id": "1269454"
    }
    
    all_devices_4_children = all_devices.copy()
    all_devices_4_children["1269457"] = child_3
    all_devices_4_children["1269458"] = child_4
    
    print(f"Children: {len([c for c in all_devices_4_children.values() if c.get('parent_periph_id') == '1269454'])}")
    
    mapping_4 = map_device_to_ha_entity(device_1269454, all_devices_4_children)
    print(f"Mapping result: {mapping_4}")
    
    if mapping_4['ha_subtype'] == 'rgbw':
        print("✅ SUCCESS: Device with 4 children correctly mapped as RGBW")
    else:
        print("❌ UNEXPECTED: Device with 4 children not mapped as RGBW")
    
    print("\n" + "="*50 + "\n")
    
    # Scenario 3: Test the specific device rule
    print("Scenario 3: Testing specific device rule for 1269454")
    
    # Check if the specific rule exists and works
    if "rgbw_lamp_specific_devices" in ADVANCED_MAPPING_RULES:
        specific_rule = ADVANCED_MAPPING_RULES["rgbw_lamp_specific_devices"]
        result = specific_rule["condition"](device_1269454, all_devices)
        print(f"Specific rule condition result: {result}")
        
        if result:
            print("✅ Specific rule would apply to device 1269454")
        else:
            print("❌ Specific rule does not apply")
    else:
        print("❌ Specific rule not found in ADVANCED_MAPPING_RULES")
    
    print("\n" + "="*50)
    print("ANALYSIS COMPLETE")
    print("The issue is likely that device 1269454 has usage_id=1 but fewer than 4 children with usage_id=1")
    print("This prevents the RGBW detection rule from triggering.")
    print("\nSOLUTION OPTIONS:")
    print("1. Add device 1269454 to the specific devices rule (already implemented)")
    print("2. Modify RGBW detection to handle devices with fewer children")
    print("3. Investigate why the device doesn't have 4 children as expected")

if __name__ == "__main__":
    test_device_1269454_mapping()