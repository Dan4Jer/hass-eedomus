"""Text sensor entity for eedomus integration.

This module provides a specialized text sensor that can dynamically map
values from eedomus device API to human-readable descriptions.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, COORDINATOR
from .entity import EedomusEntity

_LOGGER = logging.getLogger(__name__)


class EedomusTextSensor(EedomusEntity, SensorEntity):
    """Text sensor entity for eedomus devices.
    
    This sensor displays text values from eedomus devices, with support for
    dynamic value mapping from the device's values structure.
    """
    
    def __init__(self, coordinator, periph_id: str):
        """Initialize the text sensor entity."""
        super().__init__(coordinator, periph_id)
        
        # Set entity properties
        self._attr_native_value = None
        self._attr_native_unit_of_measurement = None
        self._attr_device_class = None
        
        # Get device data to check for dynamic mapping
        periph_data = self._get_periph_data(periph_id)
        if periph_data:
            entity_specifics = periph_data.get("entity_specifics", {})
            if entity_specifics.get("value_mapping") == "dynamic_from_values":
                self._dynamic_value_mapping = True
                _LOGGER.debug("🔗 Text sensor %s will use dynamic value mapping", periph_id)
            else:
                self._dynamic_value_mapping = False
        else:
            self._dynamic_value_mapping = False
    
    @property
    def native_value(self) -> str | None:
        """Return the native value of the sensor.
        
        For devices with dynamic value mapping, this maps the raw value
        to the corresponding description from the device's values structure.
        """
        periph_data = self._get_periph_data()
        if not periph_data:
            return None
            
        # Get the current value
        last_value = periph_data.get("last_value")
        
        # If dynamic mapping is enabled, find the corresponding description
        if self._dynamic_value_mapping and "values" in periph_data:
            try:
                # Convert last_value to string for comparison
                last_value_str = str(last_value)
                
                # Search through values to find matching value
                for value_item in periph_data["values"]:
                    if str(value_item.get("value")) == last_value_str:
                        description = value_item.get("description", "Unknown")
                        _LOGGER.debug("📋 Mapped value %s → %s for %s", 
                                     last_value_str, description, self._periph_id)
                        return description
                
                # If no match found, return the raw value
                _LOGGER.warning("⚠️  No description found for value %s in device %s", 
                               last_value_str, self._periph_id)
                return f"Unknown ({last_value})"
                
            except Exception as e:
                _LOGGER.error("❌ Error in dynamic value mapping for %s: %s", 
                             self._periph_id, e)
                return f"Error: {last_value}"
        
        # For non-dynamic mapping, return last_value_text if available
        return periph_data.get("last_value_text", last_value)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes for the sensor."""
        periph_data = self._get_periph_data()
        if not periph_data or not self._dynamic_value_mapping:
            return None
            
        # Return the available values as attributes
        values = periph_data.get("values", [])
        if values:
            return {
                "available_values": {item.get("value"): item.get("description") for item in values},
                "current_raw_value": periph_data.get("last_value")
            }
        return None

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend.
        
        Uses YAML configuration for icons, with dynamic icon mapping based on values.
        Falls back to default icon if no specific configuration found.
        """
        periph_data = self._get_periph_data()
        if not periph_data:
            return None
            
        # Get entity specifics from YAML mapping
        entity_specifics = periph_data.get("entity_specifics", {})
        
        # Check for dynamic value-based icons
        if "value_icons" in entity_specifics:
            try:
                last_value = str(periph_data.get("last_value", ""))
                return entity_specifics["value_icons"].get(last_value, entity_specifics.get("icon", "mdi:text"))
            except:
                pass
        
        # Check for static icon in YAML
        if "icon" in entity_specifics:
            return entity_specifics["icon"]
        
        # Try to get icon from device data (fallback)
        device_icon = periph_data.get("icon")
        if device_icon and device_icon.startswith('/img/mdm/'):
            return "mdi:calendar-text"
            
        # Final fallback to default text sensor icon
        return "mdi:text"
    
    @property
    def device_class(self) -> str | None:
        """Return the device class of the sensor."""
        # Text sensors with enumerated values should use ENUM device class
        return "enum"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up eedomus text sensor entities from config entry."""
    # Check if coordinator exists in the new structure
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        entry_data = hass.data[DOMAIN][entry.entry_id]
        coordinator = entry_data.get(COORDINATOR) if COORDINATOR in entry_data else None
    else:
        coordinator = None

    if coordinator is None:
        _LOGGER.error("Coordinator not found for entry %s", entry.entry_id)
        return False

    entities = []
    all_peripherals = coordinator.get_all_peripherals()

    for periph_id, periph in all_peripherals.items():
        # Check if this device should be a text sensor
        if periph.get("ha_entity") == "sensor" and periph.get("ha_subtype") == "text":
            # Check if it has dynamic value mapping
            entity_specifics = periph.get("entity_specifics", {})
            if entity_specifics.get("value_mapping") == "dynamic_from_values":
                _LOGGER.info("🆕 Adding dynamic text sensor for %s (%s)", 
                           periph.get("name", periph_id), periph_id)
                entities.append(EedomusTextSensor(coordinator, periph_id))
            else:
                _LOGGER.debug("⚠️  Text sensor %s doesn't have dynamic mapping", periph_id)

    if entities:
        async_add_entities(entities)
        _LOGGER.info("✅ Added %d text sensor entities", len(entities))
    else:
        _LOGGER.debug("⚠️  No text sensor entities found")

    return True