"""Select entity for eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .entity import EedomusEntity, map_device_to_ha_entity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up eedomus select entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    selects = []

    all_peripherals = coordinator.get_all_peripherals()
    
    # First pass: ensure all peripherals have proper mapping
    for periph_id, periph in all_peripherals.items():
        if "ha_entity" not in coordinator.data[periph_id]:
            eedomus_mapping = map_device_to_ha_entity(periph)
            coordinator.data[periph_id].update(eedomus_mapping)

    # Second pass: create select entities
    for periph_id, periph in all_peripherals.items():
        ha_entity = coordinator.data[periph_id].get("ha_entity")
        
        if ha_entity != "select":
            continue
        
        # Check if this device has a value_list (required for select entities)
        if "value_list" not in periph or not periph["value_list"]:
            _LOGGER.warning("Device %s (%s) mapped to select but has no value_list, skipping", 
                          periph["name"], periph_id)
            continue
            
        _LOGGER.debug("Creating select entity for %s (%s)", periph["name"], periph_id)
        selects.append(EedomusSelect(coordinator, periph_id))

    async_add_entities(selects, True)


class EedomusSelect(EedomusEntity, SelectEntity):
    """Representation of an eedomus select entity."""

    def __init__(self, coordinator, periph_id: str):
        """Initialize the select entity."""
        super().__init__(coordinator, periph_id)
        self._attr_name = self.coordinator.data[periph_id]["name"]
        self._attr_unique_id = f"{periph_id}_select"
        self._attr_current_option = self.coordinator.data[periph_id].get("last_value", "")
        _LOGGER.debug("Initializing select entity for %s (%s)", self._attr_name, periph_id)

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        return self.coordinator.data[self._periph_id].get("last_value", "")

    @property
    def options(self) -> list[str]:
        """Return a list of available options."""
        value_list = self.coordinator.data[self._periph_id].get("value_list", [])
        if isinstance(value_list, list):
            return value_list
        elif isinstance(value_list, str):
            # Handle case where value_list might be a comma-separated string
            return [v.strip() for v in value_list.split(",") if v.strip()]
        else:
            return []

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.info("Selecting option '%s' for %s (%s)", option, self._attr_name, self._periph_id)
        
        try:
            # Send the selected option to eedomus
            result = await self._client.set_periph_value(self._periph_id, option)
            
            if result.get("success", 0) == 1:
                _LOGGER.debug("Successfully selected option '%s' for %s", option, self._attr_name)
                # Update the coordinator data to reflect the change
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to select option '%s' for %s: %s", 
                            option, self._attr_name, result.get("error", "Unknown error"))
        except Exception as e:
            _LOGGER.error("Exception while selecting option '%s' for %s: %s", 
                        option, self._attr_name, str(e))
            raise

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.data[self._periph_id].get("last_value", "") != "" and len(self.options) > 0

    async def async_update(self) -> None:
        """Update the select entity state."""
        await super().async_update()
        # Update current option from the latest data
        self._attr_current_option = self.coordinator.data[self._periph_id].get("last_value", "")
        _LOGGER.debug("Updated select entity %s (%s) - current option: %s", 
                    self._attr_name, self._periph_id, self._attr_current_option)