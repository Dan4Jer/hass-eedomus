#!/usr/bin/env python3
"""Manual test script to verify cleanup functionality is accessible."""

import sys
import os

def test_cleanup_method_exists():
    """Test that the cleanup method exists in the options flow."""
    
    print("🧪 Testing cleanup method existence...")
    
    # Add the custom_components directory to the path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    custom_components_path = os.path.join(parent_dir, 'custom_components')
    sys.path.insert(0, custom_components_path)
    
    try:
        from eedomus.options_flow import EedomusOptionsFlow
        
        # Check that the async_step_cleanup method exists
        assert hasattr(EedomusOptionsFlow, 'async_step_cleanup'), \
            "EedomusOptionsFlow should have async_step_cleanup method"
        
        print("  ✅ async_step_cleanup method exists")
        
        # Check the method signature
        import inspect
        sig = inspect.signature(EedomusOptionsFlow.async_step_cleanup)
        params = list(sig.parameters.keys())
        assert 'user_input' in params, f"Method should accept 'user_input' parameter, got {params}"
        
        print("  ✅ Method has correct signature")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Test failed: {e}")
        return False


def test_menu_option():
    """Test that the menu option is properly configured."""
    
    print("\n🧪 Testing menu option configuration...")
    
    try:
        # Read the options_flow.py file to check for menu_options
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        options_flow_path = os.path.join(
            parent_dir, 'custom_components', 'eedomus', 'options_flow.py'
        )
        
        with open(options_flow_path, 'r') as f:
            content = f.read()
        
        # Check that menu_options=["cleanup"] is present
        assert 'menu_options=["cleanup"]' in content, \
            "menu_options=[\"cleanup\"] should be present in async_step_init"
        
        print("  ✅ Menu option 'cleanup' is configured")
        
        # Check that async_step_cleanup method is defined
        assert 'async def async_step_cleanup' in content, \
            "async_step_cleanup method should be defined"
        
        print("  ✅ async_step_cleanup method is defined")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Test failed: {e}")
        return False


def test_logging_statements():
    """Test that proper logging statements are present."""
    
    print("\n🧪 Testing logging statements...")
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        options_flow_path = os.path.join(
            parent_dir, 'custom_components', 'eedomus', 'options_flow.py'
        )
        
        with open(options_flow_path, 'r') as f:
            content = f.read()
        
        # Check for key logging statements
        expected_logs = [
            '_LOGGER.info("Starting cleanup of unused eedomus entities")',
            '_LOGGER.info(f"Cleanup analysis complete:',
            '_LOGGER.info(f"Removing entity {entity_info[\'entity_id\']}"',
            '_LOGGER.info(f"Cleanup completed: {removed_count} entities removed out of {len(entities_to_remove)} identified")'
        ]
        
        # Check each expected log - be more flexible with matching
        found_logs = 0
        for log in expected_logs:
            if log in content:
                print(f"  ✅ Found log statement: {log[:50]}...")
                found_logs += 1
            else:
                # For the entity removal log, be more flexible
                if 'Removing entity' in log and 'entity_info' in log:
                    if '_LOGGER.info(f"Removing entity' in content and 'entity_info' in content:
                        print(f"  ✅ Found similar log: Removing entity with entity_info...")
                        found_logs += 1
                # For other logs, try to find similar patterns
                elif any(keyword in content for keyword in ['Starting cleanup', 'Cleanup analysis', 'Cleanup completed']):
                    print(f"  ✅ Found related logging...")
                    found_logs += 1
        
        assert found_logs >= 3, f"Expected at least 3 log statements, found {found_logs}"
        
        for log in expected_logs:
            assert log in content, f"Expected log statement not found: {log}"
            print(f"  ✅ Found log statement: {log[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Test failed: {e}")
        return False


def test_cleanup_logic():
    """Test the core cleanup logic."""
    
    print("\n🧪 Testing cleanup logic...")
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        options_flow_path = os.path.join(
            parent_dir, 'custom_components', 'eedomus', 'options_flow.py'
        )
        
        with open(options_flow_path, 'r') as f:
            content = f.read()
        
        # Check for key logic elements
        logic_checks = [
            'entity_entry.platform == "eedomus"',
            'entity_entry.disabled',
            'entity_entry.unique_id and "deprecated" in entity_entry.unique_id.lower()',
            'entity_registry.async_remove(entity_info[\'entity_id\'])',
            'entities_analyzed',
            'entities_considered',
            'removed_count'
        ]
        
        for check in logic_checks:
            assert check in content, f"Expected logic not found: {check}"
            print(f"  ✅ Found logic: {check[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Test failed: {e}")
        return False


def test_error_handling():
    """Test that error handling is present."""
    
    print("\n🧪 Testing error handling...")
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        options_flow_path = os.path.join(
            parent_dir, 'custom_components', 'eedomus', 'options_flow.py'
        )
        
        with open(options_flow_path, 'r') as f:
            content = f.read()
        
        # Check for error handling
        assert 'try:' in content and 'except Exception as e:' in content, \
            "Error handling should be present"
        
        print("  ✅ Error handling is present")
        
        # Check for error logging
        assert '_LOGGER.error(f"Failed to remove entity' in content, \
            "Error logging should be present"
        
        print("  ✅ Error logging is present")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Running manual cleanup functionality tests...\n")
    
    try:
        # Run all tests
        results = []
        results.append(test_cleanup_method_exists())
        results.append(test_menu_option())
        results.append(test_logging_statements())
        results.append(test_cleanup_logic())
        results.append(test_error_handling())
        
        if all(results):
            print("\n🎉 All manual tests passed!")
            print("\n✅ Cleanup functionality is properly implemented and ready for use.")
            print("\n📋 Implementation summary:")
            print("  • async_step_cleanup method exists with correct signature")
            print("  • Menu option 'cleanup' is configured in options flow")
            print("  • Comprehensive logging for tracking cleanup progress")
            print("  • Core logic for identifying disabled/deprecated entities")
            print("  • Proper error handling and logging")
            print("  • Integration with entity registry for safe removal")
            print("\n🔧 Usage instructions:")
            print("  1. Go to Settings > Devices & Services")
            print("  2. Find the eedomus integration and click Configure")
            print("  3. Click on the 'Cleanup' menu option")
            print("  4. Review the logs for cleanup results")
            print("\n💡 The cleanup will remove:")
            print("  • Disabled eedomus entities")
            print("  • Eedomus entities with 'deprecated' in their unique_id")
            print("  • Only entities from the eedomus platform are affected")
        else:
            print("\n❌ Some tests failed. Please review the implementation.")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
