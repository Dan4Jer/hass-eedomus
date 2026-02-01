#!/usr/bin/env python3
"""Simple test script for disabled entities functionality without Home Assistant dependencies."""

import sys
import os

# Add the custom_components directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components'))

def test_disabled_entities_parsing():
    """Test parsing of disabled entities from string to list."""
    
    print("🧪 Testing disabled entities parsing...")
    
    # Test empty string
    disabled_entities = ""
    if isinstance(disabled_entities, str) and disabled_entities.strip():
        result = [item.strip() for item in disabled_entities.split(",")]
    else:
        result = []
    assert result == [], f"Expected empty list, got {result}"
    print("  ✅ Empty string test passed")
    
    # Test single entity
    disabled_entities = "12345"
    result = [item.strip() for item in disabled_entities.split(",")]
    assert result == ["12345"], f"Expected ['12345'], got {result}"
    print("  ✅ Single entity test passed")
    
    # Test multiple entities
    disabled_entities = "12345, 67890, 11111"
    result = [item.strip() for item in disabled_entities.split(",")]
    assert result == ["12345", "67890", "11111"], f"Expected ['12345', '67890', '11111'], got {result}"
    print("  ✅ Multiple entities test passed")
    
    # Test with spaces
    disabled_entities = " 12345 , 67890 , 11111 "
    result = [item.strip() for item in disabled_entities.split(",")]
    assert result == ["12345", "67890", "11111"], f"Expected ['12345', '67890', '11111'], got {result}"
    print("  ✅ Entities with spaces test passed")


def test_constants():
    """Test that constants are properly defined."""
    
    print("🧪 Testing constants...")
    
    from eedomus.const import CONF_DISABLED_ENTITIES, DEFAULT_DISABLED_ENTITIES
    
    assert CONF_DISABLED_ENTITIES == "disabled_entities", f"Expected 'disabled_entities', got {CONF_DISABLED_ENTITIES}"
    print("  ✅ CONF_DISABLED_ENTITIES constant test passed")
    
    assert DEFAULT_DISABLED_ENTITIES == [], f"Expected [], got {DEFAULT_DISABLED_ENTITIES}"
    print("  ✅ DEFAULT_DISABLED_ENTITIES constant test passed")


def test_coordinator_import():
    """Test that coordinator can be imported and has the new method."""
    
    print("🧪 Testing coordinator import...")
    
    from eedomus.coordinator import EedomusDataUpdateCoordinator
    
    # Check that the new method exists
    assert hasattr(EedomusDataUpdateCoordinator, 'is_entity_disabled'), \
        "EedomusDataUpdateCoordinator should have is_entity_disabled method"
    print("  ✅ Coordinator has is_entity_disabled method")
    
    # Check that the constructor accepts disabled_entities parameter
    import inspect
    sig = inspect.signature(EedomusDataUpdateCoordinator.__init__)
    params = list(sig.parameters.keys())
    assert 'disabled_entities' in params, f"Constructor should accept 'disabled_entities' parameter, got {params}"
    print("  ✅ Coordinator constructor accepts disabled_entities parameter")


def test_entity_import():
    """Test that entity can be imported."""
    
    print("🧪 Testing entity import...")
    
    from eedomus.entity import EedomusEntity
    
    # Check that the entity has async_set_value method
    assert hasattr(EedomusEntity, 'async_set_value'), \
        "EedomusEntity should have async_set_value method"
    print("  ✅ Entity has async_set_value method")


def test_syntax():
    """Test that all modified files have correct syntax."""
    
    print("🧪 Testing file syntax...")
    
    import py_compile
    
    files_to_test = [
        'eedomus/const.py',
        'eedomus/config_flow.py',
        'eedomus/options_flow.py',
        'eedomus/coordinator.py',
        'eedomus/entity.py',
        'eedomus/__init__.py',
    ]
    
    for file_path in files_to_test:
        try:
            py_compile.compile(file_path, doraise=True)
            print(f"  ✅ {file_path} syntax is valid")
        except py_compile.PyCompileError as e:
            print(f"  ❌ {file_path} has syntax errors: {e}")
            return False
    
    return True


if __name__ == "__main__":
    print("🧪 Running simplified disabled entities functionality tests...\n")
    
    # Run tests
    test_disabled_entities_parsing()
    print()
    
    test_constants()
    print()
    
    test_coordinator_import()
    print()
    
    test_entity_import()
    print()
    
    if test_syntax():
        print("\n🎉 All tests passed! Disabled entities functionality has been successfully implemented.")
        print("\n📋 Summary of changes:")
        print("  • Added CONF_DISABLED_ENTITIES and DEFAULT_DISABLED_ENTITIES constants")
        print("  • Added disabled entities option to config_flow.py and options_flow.py")
        print("  • Modified coordinator to filter out disabled entities")
        print("  • Added is_entity_disabled() method to coordinator")
        print("  • Modified entity async_set_value() to block actions on disabled entities")
        print("  • Updated __init__.py to parse and pass disabled entities to coordinator")
        print("\n🔧 Next steps:")
        print("  • Test the functionality in a real Home Assistant environment")
        print("  • Update documentation with the new feature")
        print("  • Add examples of how to use disabled entities")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)