#!/usr/bin/env python3
"""Test script for disabled entities functionality."""

import asyncio
from unittest.mock import MagicMock, AsyncMock
from custom_components.eedomus.coordinator import EedomusDataUpdateCoordinator
from custom_components.eedomus.entity import EedomusEntity
from custom_components.eedomus.const import CONF_DISABLED_ENTITIES


def test_disabled_entities_parsing():
    """Test parsing of disabled entities from string to list."""
    
    # Test empty string
    disabled_entities = ""
    if isinstance(disabled_entities, str) and disabled_entities.strip():
        result = [item.strip() for item in disabled_entities.split(",")]
    else:
        result = []
    assert result == [], f"Expected empty list, got {result}"
    print("✅ Empty string test passed")
    
    # Test single entity
    disabled_entities = "12345"
    result = [item.strip() for item in disabled_entities.split(",")]
    assert result == ["12345"], f"Expected ['12345'], got {result}"
    print("✅ Single entity test passed")
    
    # Test multiple entities
    disabled_entities = "12345, 67890, 11111"
    result = [item.strip() for item in disabled_entities.split(",")]
    assert result == ["12345", "67890", "11111"], f"Expected ['12345', '67890', '11111'], got {result}"
    print("✅ Multiple entities test passed")
    
    # Test with spaces
    disabled_entities = " 12345 , 67890 , 11111 "
    result = [item.strip() for item in disabled_entities.split(",")]
    assert result == ["12345", "67890", "11111"], f"Expected ['12345', '67890', '11111'], got {result}"
    print("✅ Entities with spaces test passed")


def test_coordinator_initialization():
    """Test coordinator initialization with disabled entities."""
    
    # Create mock objects
    hass = MagicMock()
    client = MagicMock()
    
    # Test with no disabled entities
    coordinator = EedomusDataUpdateCoordinator(hass, client, 300, None)
    assert coordinator._disabled_entities == set(), f"Expected empty set, got {coordinator._disabled_entities}"
    print("✅ Coordinator with no disabled entities test passed")
    
    # Test with disabled entities
    disabled_entities = ["12345", "67890"]
    coordinator = EedomusDataUpdateCoordinator(hass, client, 300, disabled_entities)
    assert coordinator._disabled_entities == set(["12345", "67890"]), f"Expected {{'12345', '67890'}}, got {coordinator._disabled_entities}"
    print("✅ Coordinator with disabled entities test passed")


def test_is_entity_disabled():
    """Test the is_entity_disabled method."""
    
    # Create mock objects
    hass = MagicMock()
    client = MagicMock()
    
    # Test with disabled entities
    disabled_entities = ["12345", "67890"]
    coordinator = EedomusDataUpdateCoordinator(hass, client, 300, disabled_entities)
    
    # Test disabled entity
    assert coordinator.is_entity_disabled("12345") == True, "Entity 12345 should be disabled"
    assert coordinator.is_entity_disabled("67890") == True, "Entity 67890 should be disabled"
    print("✅ Disabled entities check test passed")
    
    # Test enabled entity
    assert coordinator.is_entity_disabled("11111") == False, "Entity 11111 should be enabled"
    assert coordinator.is_entity_disabled("99999") == False, "Entity 99999 should be enabled"
    print("✅ Enabled entities check test passed")


async def test_entity_set_value_blocked():
    """Test that setting value on disabled entity is blocked."""
    
    # Create mock objects
    hass = MagicMock()
    client = MagicMock()
    disabled_entities = ["12345"]
    coordinator = EedomusDataUpdateCoordinator(hass, client, 300, disabled_entities)
    
    # Create mock entity
    entity = EedomusEntity(coordinator, "12345")
    entity._attr_name = "Test Entity"
    
    # Mock the coordinator method to track if it's called
    coordinator.async_set_periph_value = AsyncMock()
    
    # Test setting value on disabled entity
    try:
        await entity.async_set_value("100")
        assert False, "Expected exception when setting value on disabled entity"
    except Exception as e:
        assert "Cannot set value on disabled entity" in str(e), f"Expected 'Cannot set value on disabled entity' in error, got {e}"
        # Verify that the coordinator method was not called
        coordinator.async_set_periph_value.assert_not_called()
        print("✅ Setting value on disabled entity blocked test passed")


async def test_entity_set_value_allowed():
    """Test that setting value on enabled entity is allowed."""
    
    # Create mock objects
    hass = MagicMock()
    client = MagicMock()
    disabled_entities = ["12345"]  # Only 12345 is disabled
    coordinator = EedomusDataUpdateCoordinator(hass, client, 300, disabled_entities)
    
    # Create mock entity with different ID (not disabled)
    entity = EedomusEntity(coordinator, "67890")
    entity._attr_name = "Test Entity"
    
    # Mock the coordinator method
    mock_response = {"success": 1}
    coordinator.async_set_periph_value = AsyncMock(return_value=mock_response)
    coordinator.async_request_refresh = AsyncMock()
    
    # Mock the async_force_state_update method
    entity.async_force_state_update = AsyncMock()
    
    # Test setting value on enabled entity
    try:
        result = await entity.async_set_value("100")
        assert result == mock_response, f"Expected {mock_response}, got {result}"
        # Verify that the coordinator method was called
        coordinator.async_set_periph_value.assert_called_once_with("67890", "100")
        print("✅ Setting value on enabled entity allowed test passed")
    except Exception as e:
        assert False, f"Unexpected exception when setting value on enabled entity: {e}"


if __name__ == "__main__":
    print("🧪 Running disabled entities functionality tests...\n")
    
    # Run synchronous tests
    test_disabled_entities_parsing()
    test_coordinator_initialization()
    test_is_entity_disabled()
    
    # Run asynchronous tests
    asyncio.run(test_entity_set_value_blocked())
    asyncio.run(test_entity_set_value_allowed())
    
    print("\n🎉 All tests passed! Disabled entities functionality is working correctly.")