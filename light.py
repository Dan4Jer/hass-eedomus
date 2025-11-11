"""Support for eedomus lights."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EedomusDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up eedomus lights dynamically."""
    coordinator: EedomusDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    lights = []
    for peripheral in coordinator.data:
        if peripheral.get("usage_id") in ["1", "82"]:  # Lampe and Couleur lumière
            lights.append(EedomusLight(coordinator, peripheral))

    async_add_entities(lights)

class EedomusLight(CoordinatorEntity, LightEntity):
    """Representation of an eedomus light."""

    def __init__(self, coordinator: EedomusDataUpdateCoordinator, peripheral: dict) -> None:
        """Initialize the light."""
        super().__init__(coordinator)
        self._peripheral = peripheral
        self._attr_unique_id = peripheral["periph_id"]
        self._attr_name = peripheral["name"]
        self._attr_supported_color_modes = {ColorMode.ONOFF}

        # Determine if the light supports color or color temperature
        if peripheral.get("usage_id") == "82":  # Couleur lumière
            self._attr_supported_color_modes = {ColorMode.RGB}
        elif "Température" in peripheral["name"]:  # Check if it's a color temperature light
            self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        # Placeholder: need to fetch current state from API
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # Placeholder: need to implement based on API
        pass

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        # Placeholder: need to implement based on API
        pass
