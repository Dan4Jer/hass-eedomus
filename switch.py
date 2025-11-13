"""Switch entity for eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .entity import EedomusEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up eedomus switch entities from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Filter peripherals that are switches
    switches = []
    for periph_id, periph_data in coordinator.data.items():
        periph_info = periph_data["info"]
        if periph_info.get("value_type") == "list" and "Interrupteur" in periph_info.get("usage_name", ""):
            switches.append(EedomusSwitch(coordinator, periph_id))

    async_add_entities(switches, True)

class EedomusSwitch(EedomusEntity, SwitchEntity):
    """Representation of an eedomus switch."""

    def __init__(self, coordinator, periph_id):
        """Initialize the switch."""
        super().__init__(coordinator, periph_id, periph_id)
        _LOGGER.debug("Initializing switch entity for periph_id=%s", periph_id)

    @property
    def is_on(self):
        """Return true if the switch is on."""
        value = self.coordinator.data[self._periph_id].get("current_value")
        _LOGGER.debug("Switch %s is_on: %s", self._periph_id, value == "on")
        return value == "on"

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Turning on switch %s", self._periph_id)
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.client.set_periph_value, self._periph_id, "on"
            )
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to turn on switch %s: %s", self._periph_id, e)
            raise

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("Turning off switch %s", self._periph_id)
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.client.set_periph_value, self._periph_id, "off"
            )
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to turn off switch %s: %s", self._periph_id, e)
            raise
