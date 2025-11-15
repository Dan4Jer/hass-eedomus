"""Light entity for eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .entity import EedomusEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up eedomus light entities from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Get all peripherals
    all_peripherals = coordinator.get_all_peripherals()

    # Filter for lights
    lights = []
    for periph_id, periph in all_peripherals.items():
        usage_name = periph.get("usage_name", "").lower()
        name = periph.get("name", "").lower()

        if ("lampe" in usage_name or
            "light" in usage_name or
            "lampe" in name or
            "light" in name):
            lights.append(EedomusLight(coordinator, periph_id))

    async_add_entities(lights, True)

class EedomusLight(EedomusEntity, LightEntity):
    """Representation of an eedomus light."""

    def __init__(self, coordinator, periph_id):
        """Initialize the light."""
        super().__init__(coordinator, periph_id, periph_id)
        self._attr_supported_color_modes = {ColorMode.ONOFF}

        periph_info = self.coordinator.data[periph_id]["info"]
        periph_type = periph_info.get("value_type")

        if periph_type == "rgb":
            self._attr_supported_color_modes.add(ColorMode.RGB)
        elif periph_type == "color_temp":
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)

        _LOGGER.debug(
            "Initializing light entity for periph_id=%s, supported_color_modes=%s",
            periph_id, self._attr_supported_color_modes
        )

    @property
    def is_on(self):
        """Return true if the light is on."""
        value = self.coordinator.data[self._periph_id].get("current_value")
        _LOGGER.debug("Light %s is_on: %s", self._periph_id, value == "on")
        return value == "on"

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        _LOGGER.debug("Turning on light %s with kwargs: %s", self._periph_id, kwargs)
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        rgb_color = kwargs.get(ATTR_RGB_COLOR)
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)

        value = "on"
        if brightness is not None:
            value = f"on:{brightness}"
        if rgb_color is not None:
            value = f"rgb:{rgb_color[0]},{rgb_color[1]},{rgb_color[2]}"
        if color_temp_kelvin is not None:
            value = f"color_temp:{color_temp_kelvin}"

        try:
            response = await self.coordinator.client.set_periph_value(self._periph_id, "100")

            # Correction: le bloc if doit être correctement indenté
            if isinstance(response, dict) and response.get("success") != 1:
                _LOGGER.error("Failed to set light value: %s", response.get("error", "Unknown error"))
                raise Exception(f"Failed to set light value: {response.get('error', 'Unknown error')}")

            await self.coordinator.async_request_refresh()
            _LOGGER.debug("Light %s turned on with value: %s", self._periph_id, value)

        except Exception as e:
            _LOGGER.error("Failed to turn on light %s: %s", self._periph_id, e)
            raise

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        _LOGGER.debug("Turning off light %s", self._periph_id)
        try:
            response = await self.coordinator.client.set_periph_value(self._periph_id, 0)
            if isinstance(response, dict) and response.get("success") != 1:
                _LOGGER.error("Failed to turn off light %s: %s", self._periph_id, response.get("error", "Unknown error"))
                raise Exception(f"Failed to turn off light: {response.get('error', 'Unknown error')}")

            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.error("Failed to turn off light %s: %s", self._periph_id, e)
            raise
