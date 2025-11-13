"""Light entity for eedomus integration."""
import logging
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from .entity import EedomusEntity
from .const import ATTR_VALUE_LIST

_LOGGER = logging.getLogger(__name__)

class EedomusLight(EedomusEntity, LightEntity):
    """Representation of an eedomus light."""

    def __init__(self, coordinator, periph_id, caract_id):
        """Initialize the light."""
        super().__init__(coordinator, periph_id, caract_id)
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        caract_type = self.coordinator.data[periph_id]["caracts"][caract_id]["info"].get("type")

        if caract_type == "rgb":
            self._attr_supported_color_modes.add(ColorMode.RGB)
        elif caract_type == "color_temp":
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)

        _LOGGER.debug(
            "Initializing light entity for periph_id=%s, caract_id=%s, supported_color_modes=%s",
            periph_id, caract_id, self._attr_supported_color_modes
        )

    @property
    def is_on(self):
        """Return true if the light is on."""
        value = self.coordinator.data[self._periph_id]["caracts"][self._caract_id]["current_value"]
        _LOGGER.debug("Light %s is_on: %s", self._caract_id, value == "on")
        return value == "on"

    async def async_turn_on(self, **kwargs):
        """Turn the light on."""
        _LOGGER.debug("Turning on light %s with kwargs: %s", self._caract_id, kwargs)
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        rgb_color = kwargs.get(ATTR_RGB_COLOR)
        color_temp = kwargs.get(ATTR_COLOR_TEMP)

        value = "on"
        if brightness is not None:
            value = f"on:{brightness}"
        if rgb_color is not None:
            value = f"rgb:{rgb_color[0]},{rgb_color[1]},{rgb_color[2]}"
        if color_temp is not None:
            value = f"color_temp:{color_temp}"

        await self.hass.async_add_executor_job(
            self.coordinator.client.set_periph_value, self._periph_id, self._caract_id, value
        )
        await self.coordinator.async_request_refresh()
        _LOGGER.debug("Light %s turned on with value: %s", self._caract_id, value)

    async def async_turn_off(self, **kwargs):
        """Turn the light off."""
        _LOGGER.debug("Turning off light %s", self._caract_id)
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_periph_value, self._periph_id, self._caract_id, "off"
        )
        await self.coordinator.async_request_refresh()
