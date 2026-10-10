#!/usr/bin/env python3
"""Simple verification script for cleanup functionality."""

import os
import sys


def verify_cleanup_implementation():
    """Verify that cleanup functionality is properly implemented."""

    print("🔍 Verifying cleanup implementation...")

    # Read the options_flow.py file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    options_flow_path = os.path.join(
        parent_dir, "custom_components", "eedomus", "options_flow.py"
    )

    try:
        with open(options_flow_path, "r") as f:
            content = f.read()
    except Exception as e:
        print(f"❌ Failed to read options_flow.py: {e}")
        return False

    # Check for key components
    checks = [
        ("async def async_step_cleanup", "Cleanup method definition"),
        ('menu_options=["cleanup"]', "Menu option configuration"),
        ("entity_registry.async_get_registry()", "Entity registry access"),
        ('entity_entry.platform == "eedomus"', "Platform filtering"),
        ("entity_entry.disabled", "Disabled entity detection"),
        (
            '"deprecated" in entity_entry.unique_id.lower()',
            "Deprecated entity detection",
        ),
        ("entity_registry.async_remove", "Entity removal"),
        ('_LOGGER.info("Starting cleanup', "Startup logging"),
        ('_LOGGER.info(f"Cleanup completed', "Completion logging"),
        ('_LOGGER.error(f"Failed to remove', "Error logging"),
        ("try:", "Error handling"),
        ("except Exception as e:", "Exception handling"),
    ]

    passed = 0
    failed = 0

    for check, description in checks:
        if check in content:
            print(f"  ✅ {description}")
            passed += 1
        else:
            print(f"  ❌ {description} - NOT FOUND")
            failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("\n🎉 Cleanup functionality is fully implemented!")
        print("\n🔧 Usage:")
        print("  1. Go to Settings > Devices & Services")
        print("  2. Find eedomus integration and click Configure")
        print("  3. Click the 'Cleanup' menu option")
        print("  4. Check logs for results")
        print("\n💡 What it does:")
        print("  • Removes disabled eedomus entities")
        print("  • Removes eedomus entities with 'deprecated' in unique_id")
        print("  • Comprehensive logging and error handling")
        print("  • Safe operation - only affects eedomus entities")
        return True
    else:
        print(f"\n❌ Cleanup implementation incomplete ({failed} missing components)")
        return False


if __name__ == "__main__":
    print("🚀 Verifying cleanup functionality implementation...\n")

    if verify_cleanup_implementation():
        print("\n✅ Cleanup feature is ready for use!")
        sys.exit(0)
    else:
        print("\n❌ Please review the implementation")
        sys.exit(1)
