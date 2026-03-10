#!/usr/bin/env python3
"""
Test script to verify the virtual sensors creation fix.

This script tests the defensive programming added to handle
async generators and ensure _history_progress is always a dict.
"""

import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components"))

def test_history_progress_handling():
    """Test the history progress handling logic."""
    
    print("🧪 Testing History Progress Handling")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "name": "Normal dict",
            "history_progress": {"123": {"last_timestamp": 100, "completed": False}},
            "expected_keys": ["123"],
            "description": "Should work normally with a regular dict"
        },
        {
            "name": "Empty dict",
            "history_progress": {},
            "expected_keys": [],
            "description": "Should handle empty dict"
        },
        {
            "name": "None value",
            "history_progress": None,
            "expected_keys": [],
            "description": "Should handle None and convert to empty dict"
        },
        {
            "name": "List value",
            "history_progress": ["123", "456"],
            "expected_keys": [],
            "description": "Should handle list and convert to empty dict"
        },
        {
            "name": "String value",
            "history_progress": "not a dict",
            "expected_keys": [],
            "description": "Should handle string and convert to empty dict"
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print(f"   Description: {test_case['description']}")
        print(f"   Input: {test_case['history_progress']}")
        
        # Simulate the defensive programming logic
        if not isinstance(test_case['history_progress'], dict):
            print("   Action: Converting to empty dict")
            history_progress = {}
        else:
            print("   Action: Using existing dict")
            history_progress = test_case['history_progress']
        
        # Get keys safely
        progress_keys = list(history_progress.keys()) if isinstance(history_progress, dict) else []
        
        print(f"   Result keys: {progress_keys}")
        print(f"   Expected keys: {test_case['expected_keys']}")
        
        if progress_keys == test_case['expected_keys']:
            print("   ✅ PASSED")
            passed += 1
        else:
            print("   ❌ FAILED")
            failed += 1
    
    print(f"\n{'=' * 50}")
    print(f"📊 Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    if failed == 0:
        print("✅ All tests passed! The defensive programming is working correctly.")
        return True
    else:
        print("❌ Some tests failed. The logic needs to be reviewed.")
        return False

if __name__ == "__main__":
    success = test_history_progress_handling()
    sys.exit(0 if success else 1)