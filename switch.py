"""Support for eedomus switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up eedomus switches dynamically."""
    coordinator: EedomusDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    switches = []
    for peripheral in coordinator.data:
        if peripheral.get("usage_id") in ["2", "43"]:  # Appareil électrique and Autre
            switches.append(EedomusSwitch(coordinator, peripheral))

    async_add_entities(switches)

class EedomusSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of an eedomus switch."""

    def __init__(self, coordinator: EedomusDataUpdateCoordinator, peripheral: dict) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._peripheral = peripheral
        self._attr_unique_id = peripheral["periph_id"]
        self._attr_name = peripheral["name"]

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        # Placeholder: need to fetch current state from API
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        # Placeholder: need to implement based on API
        pass

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        # Placeholder: need to implement based on API
        pass
