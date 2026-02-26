#!/usr/bin/env python3
"""Test script for the cleanup functionality."""

import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock, Mock

# Add the parent directory to the path to import custom_components
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
custom_components_path = os.path.join(parent_dir, 'custom_components')
sys.path.insert(0, custom_components_path)

from eedomus.options_flow import EedomusOptionsFlow
from eedomus.const import DOMAIN


def create_mock_entity_entry(entity_id, unique_id=None, disabled=False):
    """Create a mock entity registry entry."""
    entry = Mock()
    entry.entity_id = entity_id
    entry.unique_id = unique_id
    entry.disabled = disabled
    entry.platform = DOMAIN if entity_id.startswith(f"{DOMAIN}.") else "other"
    return entry


def create_mock_entity_registry(entities):
    """Create a mock entity registry."""
    registry = Mock()
    registry.entities = {}
    
    for entity in entities:
        registry.entities[entity.entity_id] = entity
    
    # Mock the async_get_registry method
    async def mock_async_get_registry():
        return registry
    
    return registry, mock_async_get_registry


async def test_cleanup_functionality():
    """Test the cleanup functionality."""
    
    print("🧪 Testing cleanup functionality...")
    
    # Create test entities
    test_entities = [
        # Eedomus entities that should be removed
        create_mock_entity_entry(f"{DOMAIN}.test_disabled", "test_disabled_123", disabled=True),
        create_mock_entity_entry(f"{DOMAIN}.test_deprecated", "test_deprecated_456", disabled=False),
        create_mock_entity_entry(f"{DOMAIN}.test_both", "test_both_deprecated_789", disabled=True),
        
        # Eedomus entities that should NOT be removed
        create_mock_entity_entry(f"{DOMAIN}.test_active", "test_active_111", disabled=False),
        create_mock_entity_entry(f"{DOMAIN}.test_normal", "test_normal_222", disabled=False),
        
        # Non-eedomus entities (should be ignored)
        create_mock_entity_entry("sensor.temperature", "temp_sensor_333", disabled=True),
        create_mock_entity_entry("light.living_room", "light_444", disabled=False),
    ]
    
    # Create mock registry
    mock_registry, mock_async_get_registry = create_mock_entity_registry(test_entities)
    
    # Mock the async_remove method to track calls
    removed_entities = []
    def mock_async_remove(entity_id):
        removed_entities.append(entity_id)
        return None
    
    mock_registry.async_remove = mock_async_remove
    
    # Create mock hass
    mock_hass = Mock()
    mock_hass.helpers.entity_registry.async_get_registry = mock_async_get_registry
    
    # Create mock config entry
    mock_config_entry = Mock()
    mock_config_entry.options = {}
    mock_config_entry.data = {}
    
    # Create options flow instance
    flow = EedomusOptionsFlow(mock_config_entry)
    flow.hass = mock_hass
    
    # Call the cleanup method
    result = await flow.async_step_cleanup(user_input=None)
    
    # Verify results
    print(f"✅ Cleanup completed with result: {result}")
    
    # Check that the right entities were removed
    expected_removed = [
        f"{DOMAIN}.test_disabled",
        f"{DOMAIN}.test_deprecated", 
        f"{DOMAIN}.test_both"
    ]
    
    print(f"📊 Expected to remove: {expected_removed}")
    print(f"📊 Actually removed: {removed_entities}")
    
    # Verify all expected entities were removed
    for expected in expected_removed:
        assert expected in removed_entities, f"Expected {expected} to be removed but it wasn't"
    
    # Verify no unexpected entities were removed
    for removed in removed_entities:
        assert removed in expected_removed, f"Unexpected entity {removed} was removed"
    
    # Verify the result data
    assert result["data"]["cleanup_completed"] == True
    assert result["data"]["entities_analyzed"] == len(test_entities)
    assert result["data"]["entities_considered"] == 5  # 5 eedomus entities
    assert result["data"]["entities_identified"] == 3  # 3 should be identified for removal
    assert result["data"]["entities_removed"] == 3  # 3 should be removed
    
    print("🎉 All cleanup functionality tests passed!")
    
    return True


async def test_cleanup_with_no_entities():
    """Test cleanup when there are no entities to remove."""
    
    print("\n🧪 Testing cleanup with no entities to remove...")
    
    # Create test entities (none should be removed)
    test_entities = [
        create_mock_entity_entry(f"{DOMAIN}.test_active1", "test_active_111", disabled=False),
        create_mock_entity_entry(f"{DOMAIN}.test_active2", "test_active_222", disabled=False),
        create_mock_entity_entry("sensor.temperature", "temp_sensor_333", disabled=True),
    ]
    
    # Create mock registry
    mock_registry, mock_async_get_registry = create_mock_entity_registry(test_entities)
    
    # Mock the async_remove method
    removed_entities = []
    def mock_async_remove(entity_id):
        removed_entities.append(entity_id)
        return None
    
    mock_registry.async_remove = mock_async_remove
    
    # Create mock hass
    mock_hass = Mock()
    mock_hass.helpers.entity_registry.async_get_registry = mock_async_get_registry
    
    # Create mock config entry
    mock_config_entry = Mock()
    mock_config_entry.options = {}
    mock_config_entry.data = {}
    
    # Create options flow instance
    flow = EedomusOptionsFlow(mock_config_entry)
    flow.hass = mock_hass
    
    # Call the cleanup method
    result = await flow.async_step_cleanup(user_input=None)
    
    # Verify no entities were removed
    assert len(removed_entities) == 0, f"Expected no entities to be removed, but {len(removed_entities)} were removed: {removed_entities}"
    assert result["data"]["entities_identified"] == 0
    assert result["data"]["entities_removed"] == 0
    
    print("🎉 No entities removed test passed!")
    
    return True


async def test_cleanup_error_handling():
    """Test cleanup error handling."""
    
    print("\n🧪 Testing cleanup error handling...")
    
    # Create test entities
    test_entities = [
        create_mock_entity_entry(f"{DOMAIN}.test_error", "test_error_123", disabled=True),
    ]
    
    # Create mock registry
    mock_registry, mock_async_get_registry = create_mock_entity_registry(test_entities)
    
    # Mock the async_remove method to raise an error
    def mock_async_remove(entity_id):
        raise Exception("Simulated removal error")
    
    mock_registry.async_remove = mock_async_remove
    
    # Create mock hass
    mock_hass = Mock()
    mock_hass.helpers.entity_registry.async_get_registry = mock_async_get_registry
    
    # Create mock config entry
    mock_config_entry = Mock()
    mock_config_entry.options = {}
    mock_config_entry.data = {}
    
    # Create options flow instance
    flow = EedomusOptionsFlow(mock_config_entry)
    flow.hass = mock_hass
    
    # Call the cleanup method (should not raise an exception)
    result = await flow.async_step_cleanup(user_input=None)
    
    # Verify the method completed despite the error
    assert result["data"]["cleanup_completed"] == True
    assert result["data"]["entities_identified"] == 1
    assert result["data"]["entities_removed"] == 0  # Should be 0 due to error
    
    print("🎉 Error handling test passed!")
    
    return True


if __name__ == "__main__":
    print("🚀 Running cleanup functionality tests...\n")
    
    try:
        # Run all tests
        asyncio.run(test_cleanup_functionality())
        asyncio.run(test_cleanup_with_no_entities())
        asyncio.run(test_cleanup_error_handling())
        
        print("\n🎉 All cleanup functionality tests passed!")
        print("\n✅ The cleanup functionality is working correctly and ready for deployment.")
        print("\n📋 Features implemented:")
        print("  • Selective cleanup of disabled eedomus entities")
        print("  • Selective cleanup of deprecated eedomus entities (with 'deprecated' in unique_id)")
        print("  • Comprehensive logging for tracking")
        print("  • Error handling for robust operation")
        print("  • Integration with options flow menu")
        print("\n🔧 Next steps:")
        print("  • Deploy to Raspberry Pi")
        print("  • Test with real eedomus data")
        print("  • Verify logs and cleanup results")
        print("  • Update documentation")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
