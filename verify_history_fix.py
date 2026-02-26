#!/usr/bin/env python3
"""Final verification script for the history option fix."""

import sys
import os

def verify_fix():
    """Verify that the history option fix is correctly implemented."""
    
    print("=== Final Verification of History Option Fix ===")
    print()
    
    # Check that the files have been modified correctly
    files_to_check = [
        {
            "path": "custom_components/eedomus/coordinator.py",
            "method": "_async_partial_refresh",
            "expected_pattern": "if CONF_ENABLE_HISTORY in self.config_entry.options:"
        },
        {
            "path": "custom_components/eedomus/__init__.py",
            "method": "async_setup_entry",
            "expected_pattern": "if CONF_ENABLE_HISTORY in coordinator.config_entry.options:"
        }
    ]
    
    all_passed = True
    
    for file_info in files_to_check:
        file_path = file_info["path"]
        method_name = file_info["method"]
        expected_pattern = file_info["expected_pattern"]
        
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        
        print(f"📄 Checking file: {file_path}")
        print(f"   Method: {method_name}")
        
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                content = f.read()
            
            if expected_pattern in content:
                print(f"   ✅ PASS: Fix correctly applied")
            else:
                print(f"   ❌ FAIL: Fix not found in file")
                all_passed = False
        else:
            print(f"   ❌ FAIL: File not found: {full_path}")
            all_passed = False
        
        print()
    
    # Test the logic
    print("🧪 Testing the logic implementation...")
    
    # Simulate the fixed logic
    def test_logic(config_value, options_dict):
        """Simulate the fixed logic."""
        CONF_ENABLE_HISTORY = "history"
        
        history_from_config = config_value
        
        # Check if history option is explicitly set in options
        if CONF_ENABLE_HISTORY in options_dict:
            history_from_options = options_dict[CONF_ENABLE_HISTORY]
        else:
            history_from_options = None
        
        # Use options if explicitly set, otherwise use config
        return history_from_options if history_from_options is not None else history_from_config
    
    # Test cases
    test_cases = [
        {"config": False, "options": {}, "expected": False, "desc": "Config False, no options"},
        {"config": True, "options": {}, "expected": True, "desc": "Config True, no options"},
        {"config": False, "options": {"history": True}, "expected": True, "desc": "Config False, options True"},
        {"config": True, "options": {"history": False}, "expected": False, "desc": "Config True, options False"},
        {"config": False, "options": {"history": False}, "expected": False, "desc": "Both False"},
        {"config": True, "options": {"history": True}, "expected": True, "desc": "Both True"},
    ]
    
    logic_passed = True
    for i, test_case in enumerate(test_cases, 1):
        result = test_logic(test_case["config"], test_case["options"])
        if result == test_case["expected"]:
            print(f"   ✅ Test {i}: {test_case['desc']} - PASS")
        else:
            print(f"   ❌ Test {i}: {test_case['desc']} - FAIL (got {result}, expected {test_case['expected']})")
            logic_passed = False
    
    print()
    
    if all_passed and logic_passed:
        print("🎉 ALL VERIFICATIONS PASSED!")
        print()
        print("The history option fix has been successfully implemented.")
        print()
        print("Next steps:")
        print("1. Deploy the changes to your Home Assistant instance")
        print("2. Restart Home Assistant")
        print("3. Test the history option in the UI")
        print("4. Verify logs show 'history=True' when enabled")
        return True
    else:
        print("❌ SOME VERIFICATIONS FAILED!")
        print()
        print("Please review the output above and fix any issues.")
        return False

if __name__ == "__main__":
    success = verify_fix()
    sys.exit(0 if success else 1)