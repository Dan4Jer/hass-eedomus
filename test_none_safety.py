#!/usr/bin/env python3
"""
Test script to verify that the NoneType safety corrections work properly.
This script simulates the conditions that cause TypeError and verifies that
the code handles them gracefully.
"""

import sys
import os

# Add the custom components to the path
sys.path.insert(0, '/Users/danjer/mistral/hass-eedomus/custom_components')

from unittest.mock import Mock, MagicMock
from eedomus.entity import EedomusEntity
from eedomus.light import EedomusLight
from eedomus.cover import EedomusCover
from eedomus.sensor import EedomusSensor

def test_entity_with_none_data():
    """Test that entities handle None coordinator data gracefully."""
    print("Testing entity with None coordinator data...")
    
    # Create a mock coordinator with None data
    mock_coordinator = Mock()
    mock_coordinator.data = None
    mock_coordinator.client = Mock()
    
    try:
        entity = EedomusEntity(mock_coordinator, "test_periph_id")
        print(f"✓ Entity created successfully with name: {entity._attr_name}")
        print(f"✓ Entity available: {entity.available}")
        return True
    except Exception as e:
        print(f"✗ Entity creation failed: {e}")
        return False

def test_light_with_none_data():
    """Test that lights handle None coordinator data gracefully."""
    print("\nTesting light with None coordinator data...")
    
    # Create a mock coordinator with None data
    mock_coordinator = Mock()
    mock_coordinator.data = None
    mock_coordinator.client = Mock()
    
    try:
        light = EedomusLight(mock_coordinator, "test_light_id")
        print(f"✓ Light created successfully with name: {light._attr_name}")
        print(f"✓ Light available: {light.available}")
        
        # Test is_on property
        is_on = light.is_on
        print(f"✓ Light is_on: {is_on}")
        
        return True
    except Exception as e:
        print(f"✗ Light creation failed: {e}")
        return False

def test_cover_with_none_data():
    """Test that covers handle None coordinator data gracefully."""
    print("\nTesting cover with None coordinator data...")
    
    # Create a mock coordinator with None data
    mock_coordinator = Mock()
    mock_coordinator.data = None
    mock_coordinator.client = Mock()
    
    try:
        cover = EedomusCover(mock_coordinator, "test_cover_id")
        print(f"✓ Cover created successfully with name: {cover._attr_name}")
        print(f"✓ Cover available: {cover.available}")
        
        # Test is_closed property
        is_closed = cover.is_closed
        print(f"✓ Cover is_closed: {is_closed}")
        
        # Test current_cover_position property
        position = cover.current_cover_position
        print(f"✓ Cover position: {position}")
        
        return True
    except Exception as e:
        print(f"✗ Cover creation failed: {e}")
        return False

def test_sensor_with_none_data():
    """Test that sensors handle None coordinator data gracefully."""
    print("\nTesting sensor with None coordinator data...")
    
    # Create a mock coordinator with None data
    mock_coordinator = Mock()
    mock_coordinator.data = None
    mock_coordinator.client = Mock()
    
    try:
        sensor = EedomusSensor(mock_coordinator, "test_sensor_id")
        print(f"✓ Sensor created successfully with name: {sensor._attr_name}")
        print(f"✓ Sensor available: {sensor.available}")
        
        # Test native_value property
        value = sensor.native_value
        print(f"✓ Sensor native_value: {value}")
        
        return True
    except Exception as e:
        print(f"✗ Sensor creation failed: {e}")
        return False

def test_entity_with_missing_periph_data():
    """Test that entities handle missing peripheral data gracefully."""
    print("\nTesting entity with missing peripheral data...")
    
    # Create a mock coordinator with data but missing our peripheral
    mock_coordinator = Mock()
    mock_coordinator.data = {"other_periph_id": {"name": "Other Device"}}
    mock_coordinator.client = Mock()
    
    try:
        entity = EedomusEntity(mock_coordinator, "missing_periph_id")
        print(f"✓ Entity created successfully with name: {entity._attr_name}")
        print(f"✓ Entity available: {entity.available}")
        return True
    except Exception as e:
        print(f"✗ Entity creation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Running NoneType safety tests...")
    print("=" * 50)
    
    tests = [
        test_entity_with_none_data,
        test_light_with_none_data,
        test_cover_with_none_data,
        test_sensor_with_none_data,
        test_entity_with_missing_periph_data,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! NoneType safety corrections are working.")
        return 0
    else:
        print("✗ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())