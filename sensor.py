"""Support for eedomus sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
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
    """Set up eedomus sensors dynamically."""
    coordinator: EedomusDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors = []
    for peripheral in coordinator.data:
        if peripheral.get("value_type") in ["float", "string"]:  # Sensors typically have float or string values
            sensors.append(EedomusSensor(coordinator, peripheral))

    async_add_entities(sensors)

class EedomusSensor(CoordinatorEntity, SensorEntity):
    """Representation of an eedomus sensor."""

    def __init__(self, coordinator: EedomusDataUpdateCoordinator, peripheral: dict) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._peripheral = peripheral
        self._attr_unique_id = peripheral["periph_id"]
        self._attr_name = peripheral["name"]
        self._attr_native_unit_of_measurement = peripheral.get("unit", "")
        self._attr_device_class = self._get_device_class(peripheral)

    def _get_device_class(self, peripheral: dict) -> str | None:
        """Determine the device class based on the peripheral's usage and unit."""
        unit = peripheral.get("unit", "")
        usage_name = peripheral.get("usage_name", "")

        if unit == "°C" or "Température" in usage_name:
            return "temperature"
        elif unit == "%" or "Humidité" in usage_name:
            return "humidity"
        elif unit == "W" or "Consommation" in usage_name:
            return "power"
        elif unit == "Wh" or "Consommation cumulée" in usage_name:
            return "energy"
        elif unit == "Lux" or "Luminosité" in usage_name:
            return "illuminance"
        else:
            return None

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        # Placeholder: need to fetch current state from API
        return None
