"""Support for Eedomus lights."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ColorMode,
    LightEntity,
    LightEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import EedomusEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Eedomus light platform."""
    # Récupère le client eedomus depuis hass.data
    client = hass.data[DOMAIN][entry.entry_id]

    # Exemple: suppose que client.get_lights() retourne une liste de lumières
    lights = await client.get_lights()

    entities = [
        EedomusLight(light, client)
        for light in lights
    ]
    async_add_entities(entities)

class EedomusLight(EedomusEntity, LightEntity):
    """Representation of an Eedomus light."""

    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, light: dict[str, Any], client: Any) -> None:
        """Initialize the light."""
        super().__init__(light, client)
        self._attr_unique_id = light["id"]
        self._attr_name = light["name"]
        self._attr_is_on = light["state"] == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        await self._client.set_light_state(self._attr_unique_id, True)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self._client.set_light_state(self._attr_unique_id, False)
        self._attr_is_on = False
        self.async_write_ha_state()
