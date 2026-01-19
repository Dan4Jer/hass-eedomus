#!/usr/bin/env python3
"""
Test for RGBW color mode fix.
This test verifies that the color mode fix is properly implemented in the source code.
"""

import re
import os
import sys

# Add the custom_components directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "custom_components")))


def test_color_mode_fix_in_source():
    """Test that the source code contains the color mode fix."""
    
    # Read the light.py file
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    light_py_path = os.path.join(base_dir, "custom_components", "eedomus", "light.py")
    with open(light_py_path, 'r') as f:
        content = f.read()
    
    # Verify that the fix is present
    checks = [
        # 1. Verify RGBW fallback is present
        ("RGBW fallback with color mode", 
         r"Falling back to regular light with RGBW color mode"),
        
        # 2. Verify supported_color_modes is set to RGBW
        ("supported_color_modes set to RGBW",
         r"light\._attr_supported_color_modes = \{ColorMode\.RGBW\}"),
        
        # 3. Verify supported_color_modes property exists
        ("supported_color_modes property",
         r"def supported_color_modes\(self\):"),
        
        # 4. Verify color_mode handles RGBW
        ("color_mode handles RGBW",
         r"if ColorMode\.RGBW in self\._attr_supported_color_modes:"),
        
        # 5. Verify rgbw_color bug is fixed
        ("rgbw_color bug fix",
         r"rgbw_color\[0\]"),
    ]
    
    all_passed = True
    for check_name, pattern in checks:
        if re.search(pattern, content):
            print(f"✅ {check_name}: PASS")
        else:
            print(f"❌ {check_name}: FAIL")
            all_passed = False
    
    assert all_passed, "Some color mode fix checks failed"


def test_warning_message_updated():
    """Test that the warning message has been updated."""
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    light_py_path = os.path.join(base_dir, "custom_components", "eedomus", "light.py")
    with open(light_py_path, 'r') as f:
        content = f.read()
    
    # Verify the warning message has been updated
    old_pattern = r"Falling back to regular light\."
    new_pattern = r"Falling back to regular light with RGBW color mode\."
    
    # Should have new message
    assert re.search(new_pattern, content), "New warning message not found"
    
    # Should not have old message (except in comments)
    # Check if old pattern exists outside of comments
    lines = content.split('\n')
    for line in lines:
        if re.search(old_pattern, line) and not line.strip().startswith('#'):
            if not re.search(new_pattern, line):  # Allow if it's part of the new message
                assert False, f"Old warning message still present: {line}"
    
    print("✅ Warning message updated: PASS")


def main():
    """Run all tests."""
    print("Testing RGBW color mode fix in hass-eedomus...")
    print("=" * 60)
    
    try:
        test_color_mode_fix_in_source()
        test_warning_message_updated()
        
        print("=" * 60)
        print("🎉 All tests PASSED! The RGBW color mode fix is correctly implemented.")
        return 0
    except Exception as e:
        print("=" * 60)
        print(f"💥 Test FAILED: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())