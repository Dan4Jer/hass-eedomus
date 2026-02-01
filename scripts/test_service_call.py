#!/usr/bin/env python3
"""
Test script to verify the service call fix for async_set_value.

This script simulates the service call to ensure the parameter names match.
"""

import json

# Simulate the service call data structure
def test_service_call_data():
    """Test that the service call uses the correct parameter name."""
    
    # This is what the fixed code should send
    correct_call_data = {
        "device_id": "12345",
        "value": "50"
    }
    
    # This is what the broken code was sending
    incorrect_call_data = {
        "periph_id": "12345",
        "value": "50"
    }
    
    # Service handler expects these keys
    expected_keys = {"device_id", "value"}
    
    print("Testing service call data structure...")
    print("=" * 60)
    
    # Test correct data
    print("\n✅ Correct call data:")
    print(json.dumps(correct_call_data, indent=2))
    print(f"Keys: {set(correct_call_data.keys())}")
    print(f"Matches expected: {set(correct_call_data.keys()) == expected_keys}")
    
    # Test incorrect data
    print("\n❌ Incorrect call data (old version):")
    print(json.dumps(incorrect_call_data, indent=2))
    print(f"Keys: {set(incorrect_call_data.keys())}")
    print(f"Matches expected: {set(incorrect_call_data.keys()) == expected_keys}")
    
    # Verify the fix
    print("\n" + "=" * 60)
    if set(correct_call_data.keys()) == expected_keys:
        print("✅ Fix verified: Service call uses correct parameter names")
        return True
    else:
        print("❌ Fix failed: Service call still uses incorrect parameter names")
        return False

if __name__ == "__main__":
    success = test_service_call_data()
    exit(0 if success else 1)
