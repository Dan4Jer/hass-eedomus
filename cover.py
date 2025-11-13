"""Cover entity for eedomus integration."""
import logging
from homeassistant.components.cover import CoverEntity
from .entity import EedomusEntity

_LOGGER = logging.getLogger(__name__)

class EedomusCover(EedomusEntity, CoverEntity):
    """Representation of an eedomus cover."""

    def __init__(self, coordinator, periph_id, caract_id):
        """Initialize the cover."""
        super().__init__(coordinator, periph_id, caract_id)
        _LOGGER.debug("Initializing cover entity for periph_id=%s, caract_id=%s", periph_id, caract_id)

    @property
    def is_closed(self):
        """Return true if the cover is closed."""
        value = self.coordinator.data[self._periph_id]["caracts"][self._caract_id]["current_value"]
        is_closed = value == "closed"
        _LOGGER.debug("Cover %s is_closed: %s", self._caract_id, is_closed)
        return is_closed

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        _LOGGER.debug("Opening cover %s", self._caract_id)
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_periph_value, self._periph_id, self._caract_id, "open"
        )
        await self.coordinator.async_request_refresh()

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        _LOGGER.debug("Closing cover %s", self._caract_id)
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_periph_value, self._periph_id, self._caract_id, "closed"
        )
        await self.coordinator.async_request_refresh()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        _LOGGER.debug("Stopping cover %s", self._caract_id)
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_periph_value, self._periph_id, self._caract_id, "stop"
        )
        await self.coordinator.async_request_refresh()
