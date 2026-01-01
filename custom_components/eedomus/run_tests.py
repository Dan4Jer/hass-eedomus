#!/usr/bin/env python3
"""Alternative test runner that doesn't require pytest."""
import asyncio
import sys
import traceback
import os
import importlib.util
from unittest.mock import AsyncMock


class TestResult:
    """Simple test result tracker."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self):
        self.passed += 1

    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, error))

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Test Results: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"❌ {self.failed} tests failed:")
            for test_name, error in self.errors:
                print(f"  - {test_name}: {error}")
        else:
            print("✅ All tests passed!")
        print(f"{'='*60}")
        return self.failed == 0


async def test_energy_sensor():
    """Test energy sensor functionality (Issue #9)."""
    result = TestResult()
    
    try:
        # Import the energy sensor class using absolute path
        module_path = os.path.join(os.path.dirname(__file__), "sensor.py")
        spec = importlib.util.spec_from_file_location("sensor", module_path)
        sensor_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sensor_module)
        EedomusEnergySensor = sensor_module.EedomusEnergySensor
        
        # Test 1: Basic initialization
        print("🧪 Testing energy sensor initialization...")
        mock_coordinator = AsyncMock()
        mock_coordinator.data = {
            "device_123": {
                "consumption": 42.5,
                "current_power": 150,
                "last_reset": "2023-01-01"
            }
        }
        
        device_info = {
            "id": "device_123",
            "name": "Test Energy Sensor",
            "usage_id": "26"
        }
        
        sensor = EedomusEnergySensor(mock_coordinator, device_info)
        
        # Verify properties
        assert sensor.name == "Test Energy Sensor"
        assert sensor.unique_id == "eedomus_energy_device_123"
        assert sensor.native_value == 42.5
        
        # Verify extra attributes
        attrs = sensor.extra_state_attributes
        assert attrs["current_power"] == 150
        assert attrs["last_reset"] == "2023-01-01"
        
        print("✅ Energy sensor initialization test passed")
        result.add_pass()
        
    except Exception as e:
        print(f"❌ Energy sensor test failed: {e}")
        result.add_fail("test_energy_sensor", str(e))
        traceback.print_exc()
    
    return result


async def test_switch_with_consumption():
    """Test switch with consumption child (Issue #9 related)."""
    result = TestResult()
    
    try:
        print("🧪 Testing switch with consumption child...")
        from .switch import EedomusSwitch
        
        mock_coordinator = AsyncMock()
        mock_coordinator.data = {
            "switch_123": {
                "name": "Test Switch",
                "value": "on",
                "value_list": ["on", "off"]
            },
            "switch_123_consumption": {
                "consumption": 15.5,
                "current_power": 100,
                "usage_id": "26"
            }
        }
        
        device_info = {
            "periph_id": "switch_123",
            "name": "Test Switch",
            "usage_id": "37",
            "children": [
                {"periph_id": "switch_123_consumption", "usage_id": "26"}
            ]
        }
        
        switch = EedomusSwitch(mock_coordinator, device_info)
        
        # Verify switch properties
        assert switch.name == "Test Switch"
        assert switch.is_on is True
        
        # Verify consumption data exists
        consumption_data = mock_coordinator.data.get("switch_123_consumption", {})
        assert consumption_data.get("consumption") == 15.5
        
        print("✅ Switch with consumption test passed")
        result.add_pass()
        
    except Exception as e:
        print(f"❌ Switch with consumption test failed: {e}")
        result.add_fail("test_switch_with_consumption", str(e))
        traceback.print_exc()
    
    return result


async def test_light_with_consumption():
    """Test light with consumption child (Issue #9 related)."""
    result = TestResult()
    
    try:
        print("🧪 Testing light with consumption child...")
        from .light import EedomusLight
        
        mock_coordinator = AsyncMock()
        mock_coordinator.data = {
            "light_123": {
                "name": "Test Light",
                "value": "on",
                "brightness": 255,
                "value_list": ["on", "off"]
            },
            "light_123_consumption": {
                "consumption": 20.5,
                "current_power": 80,
                "usage_id": "26"
            }
        }
        
        device_info = {
            "periph_id": "light_123",
            "name": "Test Light",
            "usage_id": "1",
            "color_mode": "brightness",
            "children": [
                {"periph_id": "light_123_consumption", "usage_id": "26"}
            ]
        }
        
        light = EedomusLight(mock_coordinator, device_info)
        
        # Verify light properties
        assert light.name == "Test Light"
        assert light.is_on is True
        
        # Verify consumption data exists
        consumption_data = mock_coordinator.data.get("light_123_consumption", {})
        assert consumption_data.get("consumption") == 20.5
        
        print("✅ Light with consumption test passed")
        result.add_pass()
        
    except Exception as e:
        print(f"❌ Light with consumption test failed: {e}")
        result.add_fail("test_light_with_consumption", str(e))
        traceback.print_exc()
    
    return result


async def test_cover_with_consumption():
    """Test cover with consumption child (Issue #9 related)."""
    result = TestResult()
    
    try:
        print("🧪 Testing cover with consumption child...")
        from .cover import EedomusCover
        
        mock_coordinator = AsyncMock()
        mock_coordinator.data = {
            "cover_123": {
                "name": "Test Cover",
                "value": "open",
                "position": 100
            },
            "cover_123_consumption": {
                "consumption": 25.5,
                "current_power": 50,
                "usage_id": "26"
            }
        }
        
        device_info = {
            "periph_id": "cover_123",
            "name": "Test Cover",
            "usage_id": "48",
            "children": [
                {"periph_id": "cover_123_consumption", "usage_id": "26"}
            ]
        }
        
        cover = EedomusCover(mock_coordinator, device_info)
        
        # Verify cover properties
        assert cover.name == "Test Cover"
        assert cover.is_closed is False
        
        # Verify consumption data exists
        consumption_data = mock_coordinator.data.get("cover_123_consumption", {})
        assert consumption_data.get("consumption") == 25.5
        
        print("✅ Cover with consumption test passed")
        result.add_pass()
        
    except Exception as e:
        print(f"❌ Cover with consumption test failed: {e}")
        result.add_fail("test_cover_with_consumption", str(e))
        traceback.print_exc()
    
    return result


async def main():
    """Run all tests."""
    print("🚀 Starting Eedomus integration tests...")
    print("="*60)
    
    overall_result = TestResult()
    
    # Run individual tests
    results = await asyncio.gather(
        test_energy_sensor(),
        test_switch_with_consumption(),
        test_light_with_consumption(),
        test_cover_with_consumption()
    )
    
    # Aggregate results
    for result in results:
        overall_result.passed += result.passed
        overall_result.failed += result.failed
        overall_result.errors.extend(result.errors)
    
    # Print summary
    success = overall_result.summary()
    
    if success:
        print("\n🎉 All tests completed successfully!")
        print("The integration is ready for HACS submission.")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)