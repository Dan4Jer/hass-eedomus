"""Binary sensor entity for eedomus integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .entity import EedomusEntity
from .const import DOMAIN, CLASS_MAPPING

_LOGGER = logging.getLogger(__name__)

# Mapping des types eedomus vers les device_class de Home Assistant
EEDOMUS_TO_HA_DEVICE_CLASS = {
    "motion": BinarySensorDeviceClass.MOTION,
    "door": BinarySensorDeviceClass.DOOR,
    "window": BinarySensorDeviceClass.WINDOW,
    "smoke": BinarySensorDeviceClass.SMOKE,
    "gas": BinarySensorDeviceClass.GAS,
    "water": BinarySensorDeviceClass.MOISTURE,
    "vibration": BinarySensorDeviceClass.VIBRATION,
    "occupancy": BinarySensorDeviceClass.OCCUPANCY,
    "safety": BinarySensorDeviceClass.SAFETY,
    "power": BinarySensorDeviceClass.POWER,
    "presence": BinarySensorDeviceClass.PRESENCE,
}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    binary_sensors = []
    for periph_id, periph in coordinator.get_all_peripherals().items():
        entity_type = None
        supported_classes = periph.get("SUPPORTED_CLASSES", "").split(",")
        for class_id in supported_classes:
            if class_id in CLASS_MAPPING:
                entity_type = CLASS_MAPPING[class_id]["ha_entity"]
        if not entity_type == "binary_sensors":
            continue
        coordinator.data[periph_id]["entity_type"] = entity_type
        binary_sensors.append(EedomusBinarySensor(coordinator, periph_id))

    async_add_entities(binary_sensors, True)

async def async_setup_entry_old(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up eedomus binary sensor entities from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    all_peripherals = coordinator.get_all_peripherals()

    binary_sensors = []
    for periph_id, periph in all_peripherals.items():
        value_type = periph.get("value_type")
        usage_name = periph.get("usage_name", "").lower()

        _LOGGER.debug("Setup binary sensor entity for periph_id=%s data=%s", periph_id, coordinator.data[periph_id])

        # Filtre pour les périphériques binaires
        if value_type == "bool" or (
            "détecteur" in usage_name or
            "mouvement" in usage_name or
            "porte" in usage_name or
            "fenêtre" in usage_name or
            "fumée" in usage_name or
            "inondation" in usage_name or
            "contact" in usage_name
        ):
            binary_sensors.append(EedomusBinarySensor(coordinator, periph_id))

    async_add_entities(binary_sensors, True)

class EedomusBinarySensor(EedomusEntity, BinarySensorEntity):
    """Representation of an eedomus binary sensor."""

    def __init__(self, coordinator, periph_id):
        """Initialize the binary sensor."""
        super().__init__(coordinator, periph_id)
        _LOGGER.debug("Initializing binary sensor entity for periph_id=%s", periph_id)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        value = self.coordinator.data[self._periph_id].get("last_value")
        _LOGGER.debug("Binary sensor %s is_on: %s", self._periph_id, value)

        # Gestion des valeurs vides ou invalides
        if value is None or value == "":
            return None

        try:
            return bool(int(value))
        except (ValueError, TypeError):
            return None

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the device class of the binary sensor."""
        periph_info = self.coordinator.data[self._periph_id]
        usage_name = periph_info.get("usage_name", "").lower()

        if "mouvement" in usage_name:
            return BinarySensorDeviceClass.MOTION
        elif "porte" in usage_name or "fenêtre" in usage_name:
            return BinarySensorDeviceClass.DOOR
        elif "fumée" in usage_name:
            return BinarySensorDeviceClass.SMOKE
        elif "inondation" in usage_name or "eau" in usage_name:
            return BinarySensorDeviceClass.MOISTURE
        elif "présence" in usage_name:
            return BinarySensorDeviceClass.PRESENCE
        elif "contact" in usage_name:
            return BinarySensorDeviceClass.DOOR
        elif "vibration" in usage_name:
            return BinarySensorDeviceClass.VIBRATION

        # Utiliser le mapping par type si disponible
        periph_type = periph_info.get("type", "").lower()
        return EEDOMUS_TO_HA_DEVICE_CLASS.get(periph_type, None)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {}
        periph_data = self.coordinator.data.get(self._periph_id, {})

        if "history" in periph_data:
            attrs["history"] = periph_data["history"]
        if "value_list" in periph_data:
            attrs["value_list"] = periph_data["value_list"]

        return attrs
