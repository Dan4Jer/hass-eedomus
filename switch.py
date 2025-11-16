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
    all_peripherals = coordinator.get_all_peripherals()

    switches = []
    for periph_id, periph in all_peripherals.items():
        usage_name = periph.get("usage_name", "").lower()
        name = periph.get("name", "").lower()

        if ("interrupteur" in usage_name or
            "switch" in usage_name or
            "interrupteur" in name or
            "decoration" in name.lower()):
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
        _LOGGER.debug("Switch %s is_on: %s", self._periph_id, value)
        return value == "on"

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Turning on switch %s", self._periph_id)
        try:
            response = await self.coordinator.client.set_periph_value(self._periph_id, "100")
            if isinstance(response, dict) and response.get("success") != 1:
                _LOGGER.error("Failed to turn on switch %s: %s", self._periph_id, response.get("error", "Unknown error"))
                raise Exception(f"Failed to turn on switch: {response.get('error', 'Unknown error')}")
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to turn on switch %s: %s", self._periph_id, e)
            raise

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("Turning off switch %s", self._periph_id)
        try:
            response = await self.coordinator.client.set_periph_value(self._periph_id, "0")
            if isinstance(response, dict) and response.get("success") != 1:
                _LOGGER.error("Failed to turn off switch %s: %s", self._periph_id, response.get("error", "Unknown error"))
                raise Exception(f"Failed to turn off switch: {response.get('error', 'Unknown error')}")

            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.error("Failed to turn off switch %s: %s", self._periph_id, e)
            raise
