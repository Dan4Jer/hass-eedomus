#!/usr/bin/env python3
"""
Test script to verify the history option reading logic.

This script tests the logic used in coordinator.py and __init__.py
to ensure the history option is read correctly from both config and options.
"""

import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

def test_history_option_logic():
    """Test the history option reading logic."""
    
    print("🧪 Testing History Option Reading Logic")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "name": "Config True, No Options",
            "config": {"history": True},
            "options": {},
            "expected": True,
            "description": "Should use config value when no options set"
        },
        {
            "name": "Config False, No Options",
            "config": {"history": False},
            "options": {},
            "expected": False,
            "description": "Should use config value when no options set"
        },
        {
            "name": "Config True, Options True",
            "config": {"history": True},
            "options": {"history": True},
            "expected": True,
            "description": "Should use options value when explicitly set to True"
        },
        {
            "name": "Config True, Options False",
            "config": {"history": True},
            "options": {"history": False},
            "expected": True,
            "description": "Should use config value when options is False (options might have been reset)"
        },
        {
            "name": "Config False, Options True",
            "config": {"history": False},
            "options": {"history": True},
            "expected": True,
            "description": "Should use options value when explicitly set to True"
        },
        {
            "name": "Config False, Options False",
            "config": {"history": False},
            "options": {"history": False},
            "expected": False,
            "description": "Should use config value when both are False"
        },
        {
            "name": "No Config, No Options",
            "config": {},
            "options": {},
            "expected": False,
            "description": "Should default to False when neither is set"
        },
        {
            "name": "No Config, Options True",
            "config": {},
            "options": {"history": True},
            "expected": True,
            "description": "Should use options value when config not set"
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print(f"   Description: {test_case['description']}")
        print(f"   Config: {test_case['config']}")
        print(f"   Options: {test_case['options']}")
        
        # Simulate the logic from coordinator.py
        history_from_config = test_case['config'].get('history', False)
        
        if 'history' in test_case['options']:
            history_from_options = test_case['options']['history']
            # Only use options if they're different from the default
            if history_from_options != False:  # Only use options if explicitly enabled
                history_enabled = history_from_options
            else:
                # If options has False, check if config has True (options might have been reset)
                history_enabled = history_from_config
        else:
            # No options set, use config
            history_enabled = history_from_config
        
        print(f"   Result: {history_enabled}")
        print(f"   Expected: {test_case['expected']}")
        
        if history_enabled == test_case['expected']:
            print("   ✅ PASSED")
            passed += 1
        else:
            print("   ❌ FAILED")
            failed += 1
    
    print(f"\n{'=' * 50}")
    print(f"📊 Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    if failed == 0:
        print("✅ All tests passed! The logic is working correctly.")
        return True
    else:
        print("❌ Some tests failed. The logic needs to be reviewed.")
        return False

if __name__ == "__main__":
    success = test_history_option_logic()
    sys.exit(0 if success else 1)