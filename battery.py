"""Battery sensor entity for eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .entity import EedomusEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, 
    entry: ConfigEntry, 
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up eedomus battery sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    battery_sensors = []

    all_peripherals = coordinator.get_all_peripherals()
    
    # Create battery sensors for devices that have battery information
    for periph_id, periph in all_peripherals.items():
        battery_level = periph.get("battery", "")
        
        # Only create battery sensor if device has battery information and it's not empty
        if battery_level and battery_level.strip():
            try:
                # Try to convert to int to validate it's a numeric battery level
                battery_int = int(battery_level)
                if 0 <= battery_int <= 100:
                    _LOGGER.debug("Creating battery sensor for %s (%s) with battery level: %s%%", 
                                periph["name"], periph_id, battery_level)
                    battery_sensors.append(EedomusBatterySensor(coordinator, periph_id))
            except ValueError:
                # Battery level is not numeric, skip this device
                _LOGGER.debug("Skipping battery sensor for %s (%s) - battery level not numeric: %s", 
                            periph["name"], periph_id, battery_level)

    async_add_entities(battery_sensors, True)


class EedomusBatterySensor(EedomusEntity, SensorEntity):
    """Representation of an eedomus battery sensor."""

    def __init__(self, coordinator, periph_id: str):
        """Initialize the battery sensor."""
        super().__init__(coordinator, periph_id)
        self._attr_name = f"{self.coordinator.data[periph_id]['name']} Battery"
        self._attr_unique_id = f"{periph_id}_battery"
        self._attr_device_class = "battery"
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = "measurement"
        
        _LOGGER.debug("Initializing battery sensor for %s (%s)", self._attr_name, periph_id)

    @property
    def native_value(self) -> int | None:
        """Return the battery level."""
        battery_level = self.coordinator.data[self._periph_id].get("battery", "")
        
        if battery_level and battery_level.strip():
            try:
                return int(battery_level)
            except ValueError:
                _LOGGER.warning("Invalid battery level for %s (%s): %s", 
                              self._attr_name, self._periph_id, battery_level)
                return None
        
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        battery_level = self.coordinator.data[self._periph_id].get("battery", "")
        return battery_level and battery_level.strip() and battery_level.isdigit()

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        periph_data = self.coordinator.data[self._periph_id]
        return {
            "device_name": periph_data.get("name", ""),
            "device_id": self._periph_id,
            "device_type": periph_data.get("usage_name", ""),
            "battery_status": self._get_battery_status()
        }

    def _get_battery_status(self) -> str:
        """Get battery status description."""
        battery_level = self.native_value
        
        if battery_level is None:
            return "Unknown"
        elif battery_level >= 75:
            return "High"
        elif battery_level >= 50:
            return "Medium"
        elif battery_level >= 25:
            return "Low"
        else:
            return "Critical"

    async def async_update(self) -> None:
        """Update the battery sensor state."""
        await super().async_update()
        battery_level = self.coordinator.data[self._periph_id].get("battery", "")
        
        _LOGGER.debug("Updated battery sensor %s (%s) - battery level: %s%%", 
                    self._attr_name, self._periph_id, battery_level)