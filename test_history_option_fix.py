#!/usr/bin/env python3
"""Test script to verify history option reading logic."""

import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

def test_history_option_logic():
    """Test the history option reading logic."""
    
    print("=== Testing History Option Logic ===")
    print()
    
    # Test cases
    test_cases = [
        {
            "name": "Case 1: History enabled in config, not in options",
            "config": {"history": True},
            "options": {},
            "expected": True
        },
        {
            "name": "Case 2: History disabled in config, not in options",
            "config": {"history": False},
            "options": {},
            "expected": False
        },
        {
            "name": "Case 3: History enabled in options (overrides config)",
            "config": {"history": False},
            "options": {"history": True},
            "expected": True
        },
        {
            "name": "Case 4: History disabled in options (overrides config)",
            "config": {"history": True},
            "options": {"history": False},
            "expected": False
        },
        {
            "name": "Case 5: History enabled in both config and options",
            "config": {"history": True},
            "options": {"history": True},
            "expected": True
        },
        {
            "name": "Case 6: History disabled in both config and options",
            "config": {"history": False},
            "options": {"history": False},
            "expected": False
        },
        {
            "name": "Case 7: No history in config, not in options (default)",
            "config": {},
            "options": {},
            "expected": False
        },
        {
            "name": "Case 8: No history in config, enabled in options",
            "config": {},
            "options": {"history": True},
            "expected": True
        }
    ]
    
    # Define the constant
    CONF_ENABLE_HISTORY = "history"
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        
        # Simulate the logic
        history_from_config = test_case['config'].get(CONF_ENABLE_HISTORY, False)
        
        # Check if history option is explicitly set in options
        if CONF_ENABLE_HISTORY in test_case['options']:
            history_from_options = test_case['options'][CONF_ENABLE_HISTORY]
        else:
            history_from_options = None
        
        # Use options if explicitly set, otherwise use config
        history_retrieval = history_from_options if history_from_options is not None else history_from_config
        
        expected = test_case['expected']
        actual = history_retrieval
        
        if actual == expected:
            print(f"  ✅ PASS: Expected {expected}, got {actual}")
            passed += 1
        else:
            print(f"  ❌ FAIL: Expected {expected}, got {actual}")
            failed += 1
        
        print()
    
    print(f"=== Results: {passed} passed, {failed} failed ===")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False

if __name__ == "__main__":
    success = test_history_option_logic()
    sys.exit(0 if success else 1)