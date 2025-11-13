"""Switch entity for eedomus integration."""
import logging
from homeassistant.components.switch import SwitchEntity
from .entity import EedomusEntity

_LOGGER = logging.getLogger(__name__)

class EedomusSwitch(EedomusEntity, SwitchEntity):
    """Representation of an eedomus switch."""

    def __init__(self, coordinator, periph_id, caract_id):
        """Initialize the switch."""
        super().__init__(coordinator, periph_id, caract_id)
        _LOGGER.debug("Initializing switch entity for periph_id=%s, caract_id=%s", periph_id, caract_id)

    @property
    def is_on(self):
        """Return true if the switch is on."""
        value = self.coordinator.data[self._periph_id]["caracts"][self._caract_id]["current_value"]
        _LOGGER.debug("Switch %s is_on: %s", self._caract_id, value == "on")
        return value == "on"

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Turning on switch %s", self._caract_id)
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_periph_value, self._periph_id, self._caract_id, "on"
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("Turning off switch %s", self._caract_id)
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_periph_value, self._periph_id, self._caract_id, "off"
        )
        await self.coordinator.async_request_refresh()
