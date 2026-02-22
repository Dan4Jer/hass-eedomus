"""Select entity for eedomus integration."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, COORDINATOR
from .entity import EedomusEntity, map_device_to_ha_entity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up eedomus select entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    selects = []

    all_peripherals = coordinator.get_all_peripherals()

    # First pass: ensure all peripherals have proper mapping
    for periph_id, periph in all_peripherals.items():
        if "ha_entity" not in coordinator.data[periph_id]:
            eedomus_mapping = map_device_to_ha_entity(periph, coordinator.data)
            coordinator.data[periph_id].update(eedomus_mapping)
            # S'assurer que le mapping est enregistré dans le registre global
            from .entity import _register_device_mapping
            _register_device_mapping(eedomus_mapping, periph["name"], periph_id, periph)

    # Second pass: create select entities
    for periph_id, periph in all_peripherals.items():
        ha_entity = coordinator.data[periph_id].get("ha_entity")

        if ha_entity != "select":
            continue

        # Check if this device has values (required for select entities)
        # Note: eedomus uses "values" field, not "value_list"
        values_data = periph.get("values", [])
        if not values_data:
            _LOGGER.warning(
                "Device %s (%s) mapped to select but has no values, skipping",
                periph["name"],
                periph_id,
            )
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
        self._attr_current_option = self.coordinator.data[periph_id].get(
            "last_value", ""
        )
        _LOGGER.debug(
            "Initializing select entity for %s (%s)", self._attr_name, periph_id
        )

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        current_value = self.coordinator.data[self._periph_id].get("last_value", "")

        # If we have values data, try to find the description for the current value
        values_data = self.coordinator.data[self._periph_id].get("values", [])

        if values_data and current_value:
            # Try to find the matching value and return its description
            for value_item in values_data:
                if isinstance(value_item, dict):
                    if value_item.get("value") == current_value:
                        description = value_item.get("description", "")
                        return description if description else current_value

        # Fallback to raw value if no description found
        return current_value if current_value else None

    @property
    def options(self) -> list[str]:
        """Return a list of available options."""
        # eedomus uses "values" field which contains list of {value, description} items
        values_data = self.coordinator.data[self._periph_id].get("values", [])

        if not values_data:
            return []

        # Extract values from the values list
        options = []
        for value_item in values_data:
            if isinstance(value_item, dict):
                # Use description if available, otherwise use value
                value = value_item.get("value", "")
                description = value_item.get("description", "")
                if description:
                    options.append(description)
                elif value:
                    options.append(value)
            else:
                # Fallback for simple list format
                options.append(str(value_item))

        return options

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        _LOGGER.info(
            "Selecting option '%s' for %s (%s)",
            option,
            self._attr_name,
            self._periph_id,
        )

        try:
            # Find the actual value to send to eedomus API
            # The option parameter might be a description, we need to find the corresponding value
            eedomus_value = option  # Default to option if it's already a value

            values_data = self.coordinator.data[self._periph_id].get("values", [])
            if values_data:
                for value_item in values_data:
                    if isinstance(value_item, dict):
                        description = value_item.get("description", "")
                        value = value_item.get("value", "")
                        if description == option:
                            eedomus_value = value
                            break

            _LOGGER.debug(
                "Selecting option '%s' (eedomus value: '%s') for %s (%s)",
                option,
                eedomus_value,
                self._attr_name,
                self._periph_id,
            )

            # Send the selected option to eedomus
            result = await self.coordinator.client.set_periph_value(self._periph_id, eedomus_value)

            if result.get("success", 0) == 1:
                _LOGGER.debug(
                    "Successfully selected option '%s' for %s", option, self._attr_name
                )
                # Update the coordinator data to reflect the change
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error(
                    "Failed to select option '%s' for %s: %s",
                    option,
                    self._attr_name,
                    result.get("error", "Unknown error"),
                )
        except Exception as e:
            _LOGGER.error(
                "Exception while selecting option '%s' for %s: %s",
                option,
                self._attr_name,
                str(e),
            )
            raise

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.data[self._periph_id].get("last_value", "") != ""
            and len(self.options) > 0
        )

    async def async_update(self) -> None:
        """Update the select entity state."""
        await super().async_update()
        # Update current option from the latest data
        self._attr_current_option = self.coordinator.data[self._periph_id].get(
            "last_value", ""
        )
        _LOGGER.debug(
            "Updated select entity %s (%s) - current option: %s",
            self._attr_name,
            self._periph_id,
            self._attr_current_option,
        )
