"""Cover entity for eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.components.cover import CoverEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .entity import EedomusEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up eedomus cover entities from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    all_peripherals = coordinator.get_all_peripherals()

    covers = []
    for periph_id, periph in all_peripherals.items():
        usage_name = periph.get("usage_name", "").lower()
        name = periph.get("name", "").lower()

        if ("ouverture" in usage_name or
            "shutter" in usage_name or
            "volet" in name or
            "store" in name):
            covers.append(EedomusCover(coordinator, periph_id))

    async_add_entities(covers, True)

class EedomusCover(EedomusEntity, CoverEntity):
    """Representation of an eedomus cover (shutter/blind)."""

    def __init__(self, coordinator, periph_id):
        """Initialize the cover."""
        super().__init__(coordinator, periph_id, periph_id)
        _LOGGER.debug("Initializing cover entity for periph_id=%s", periph_id)

    @property
    def is_closed(self):
        """Return true if the cover is closed."""
        value = self.coordinator.data[self._periph_id].get("current_value")
        is_closed = value == "closed"
        _LOGGER.debug("Cover %s is_closed: %s", self._periph_id, is_closed)
        return is_closed

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        _LOGGER.debug("Opening cover %s", self._periph_id)
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.client.set_periph_value, self._periph_id, "open"
            )
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to open cover %s: %s", self._periph_id, e)
            raise

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        _LOGGER.debug("Closing cover %s", self._periph_id)
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.client.set_periph_value, self._periph_id, "closed"
            )
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to close cover %s: %s", self._periph_id, e)
            raise

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        _LOGGER.debug("Stopping cover %s", self._periph_id)
        try:
            await self.hass.async_add_executor_job(
                self.coordinator.client.set_periph_value, self._periph_id, "stop"
            )
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to stop cover %s: %s", self._periph_id, e)
            raise
