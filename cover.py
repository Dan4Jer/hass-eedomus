"""Support for eedomus covers (volets)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_API_HOST, CONF_API_USER, CONF_API_SECRET, PLATFORMS
from .coordinator import EedomusDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eedomus covers dynamically."""
    coordinator: EedomusDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    covers = []
    for peripheral in coordinator.data:
        if peripheral.get("usage_id") == "48":  # Ouverture (volets)
            covers.append(EedomusCover(coordinator, peripheral))

    async_add_entities(covers)

class EedomusCover(CoordinatorEntity, CoverEntity):
    """Representation of an eedomus cover (volet)."""

    def __init__(self, coordinator: EedomusDataUpdateCoordinator, peripheral: dict) -> None:
        """Initialize the cover."""
        super().__init__(coordinator)
        self._peripheral = peripheral
        self._attr_unique_id = peripheral["periph_id"]
        self._attr_name = peripheral["name"]
        self._attr_device_class = CoverDeviceClass.SHUTTER

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        # Placeholder: need to fetch current state from API
        return None

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        # Placeholder: need to implement based on API
        pass

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        # Placeholder: need to implement based on API
        pass

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        # Placeholder: need to implement based on API
        pass
