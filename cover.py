"""Cover entity for eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .entity import EedomusEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up eedomus cover entities from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []

    # Get all peripherals
    all_peripherals = coordinator.get_all_peripherals()

    for periph_id, periph in all_peripherals.items():
        if "ha_entity" in coordinator.data[periph_id] and coordinator.data[periph_id]["ha_entity"] == "cover":
            _LOGGER.debug("Creating cover entity for %s (periph_id=%s)", periph["name"], periph_id)
            entities.append(EedomusCover(coordinator, periph_id))

    async_add_entities(entities)

class EedomusCover(EedomusEntity, CoverEntity):
    """Representation of an eedomus cover entity (shutter/blind)."""

    def __init__(self, coordinator, periph_id):
        """Initialize the cover."""
        super().__init__(coordinator, periph_id)
        _LOGGER.debug("Initializing cover entity for %s (periph_id=%s)", self.coordinator.data[periph_id].get("name", "unknown"), periph_id)

        # Set cover-specific attributes
        self._attr_device_class = "shutter"  # Use "shutter" for shutters
        self._attr_supported_features = CoverEntityFeature.SET_POSITION  # Only position setting is supported

    @property
    def is_closed(self):
        """Return if the cover is closed (position = 0)."""
        position = self.coordinator.data[self._periph_id].get("last_value")
        return position == "0" or position == 0

    @property
    def current_cover_position(self):
        """Return the current position of the cover (0-100)."""
        position = self.coordinator.data[self._periph_id].get("last_value")
        try:
            return int(position)
        except (ValueError, TypeError):
            return 0

    async def async_open_cover(self, **kwargs):
        """Open the cover to 100%."""
        await self.async_set_cover_position(position=100)

    async def async_close_cover(self, **kwargs):
        """Close the cover to 0%."""
        await self.async_set_cover_position(position=0)

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position (0-100)."""
        position = kwargs.get("position")
        if position is None:
            _LOGGER.error("Position is None for cover %s (periph_id=%s)", self.coordinator.data[self._periph_id].get("name", "unknown"), self._periph_id)
            return

        # Ensure position is within valid range
        position = max(0, min(100, position))
        _LOGGER.debug("Setting cover position to %s for %s (periph_id=%s)", position, self.coordinator.data[self._periph_id].get("name", "unknown"), self._periph_id)

        # Use coordinator method to set position
        await self.coordinator.async_set_periph_value(self._periph_id, str(position))

    async def async_stop_cover(self, **kwargs):
        """Stop the cover (not supported by eedomus shutters)."""
        _LOGGER.warning("Stopping cover is not supported by eedomus shutters for %s (periph_id=%s)", self.coordinator.data[self._periph_id].get("name", "unknown"), self._periph_id)
