"""Binary sensor entity for eedomus integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import EedomusEntity

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


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up eedomus binary sensor entities."""
    from .entity import map_device_to_ha_entity

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    binary_sensors = []

    all_peripherals = coordinator.get_all_peripherals()

    # First pass: ensure all peripherals have proper mapping
    for periph_id, periph in all_peripherals.items():
        if "ha_entity" not in coordinator.data[periph_id]:
            eedomus_mapping = map_device_to_ha_entity(periph, coordinator.data)
            coordinator.data[periph_id].update(eedomus_mapping)
            # S'assurer que le mapping est enregistré dans le registre global
            from .entity import _register_device_mapping
            # Log pour confirmer que le device a été mappé
            _LOGGER.debug("✅ Device mapped: %s (%s) → %s:%s", 
                        periph["name"], periph_id, eedomus_mapping["ha_entity"], eedomus_mapping["ha_subtype"])
            _register_device_mapping(eedomus_mapping, periph["name"], periph_id, periph)

    # Handle parent-child relationships for motion sensors
    parent_to_children = {}
    for periph_id, periph in all_peripherals.items():
        parent_id = periph.get("parent_periph_id")
        if parent_id:
            if parent_id not in parent_to_children:
                parent_to_children[parent_id] = []
            parent_to_children[parent_id].append(periph)

    # Map children of motion sensors to appropriate entities
    for parent_id, children in parent_to_children.items():
        if (
            parent_id in coordinator.data
            and coordinator.data[parent_id].get("ha_entity") == "binary_sensor"
        ):
            for child in children:
                child_id = child["periph_id"]
                if (
                    child_id not in coordinator.data
                    or "ha_entity" not in coordinator.data[child_id]
                ):
                    eedomus_mapping = None

                    # Map children based on their usage_id
                    if child.get("usage_id") == "7":  # Temperature sensor
                        eedomus_mapping = {
                            "ha_entity": "sensor",
                            "ha_subtype": "temperature",
                            "justification": "Child of motion sensor - temperature",
                        }
                    elif child.get("usage_id") == "24":  # Illuminance sensor
                        eedomus_mapping = {
                            "ha_entity": "sensor",
                            "ha_subtype": "illuminance",
                            "justification": "Child of motion sensor - illuminance",
                        }
                    elif child.get("usage_id") == "36":  # Flood sensor
                        eedomus_mapping = {
                            "ha_entity": "binary_sensor",
                            "ha_subtype": "flood",
                            "justification": "Child of motion sensor - flood",
                        }

                    if eedomus_mapping is not None:
                        coordinator.data[child_id].update(eedomus_mapping)
                        _LOGGER.info(
                            "Mapped child sensor for motion device %s (%s)",
                            child["name"],
                            child_id,
                        )

    # Second pass: create binary sensor entities
    for periph_id, periph in all_peripherals.items():
        ha_entity = coordinator.data[periph_id].get("ha_entity")

        if ha_entity != "binary_sensor":
            continue

        _LOGGER.debug(
            "Creating binary sensor entity for %s (%s)", periph["name"], periph_id
        )
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
        periph_data = self._get_periph_data()
        if periph_data is None:
            _LOGGER.warning(f"Cannot get binary sensor state: peripheral data not found for {self._periph_id}")
            return None
            
        value = periph_data.get("last_value")
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
        ha_subtype = periph_info.get("ha_subtype", "")
        usage_name = periph_info.get("usage_name", "").lower()

        # D'abord utiliser le ha_subtype si disponible ==> à simplifier
        if ha_subtype:
            return EEDOMUS_TO_HA_DEVICE_CLASS.get(ha_subtype, None)

        # Ensuite utiliser le nom et l'usage_name ==> à revoir
        if "mouvement" in usage_name:
            return BinarySensorDeviceClass.MOTION
        elif "porte" in usage_name or "fenêtre" in usage_name:
            return BinarySensorDeviceClass.DOOR
        elif "fumée" in usage_name or "smoke" in usage_name:
            return BinarySensorDeviceClass.SMOKE
        elif "inondation" in usage_name or "eau" in usage_name or "flood" in usage_name:
            return BinarySensorDeviceClass.MOISTURE
        elif "présence" in usage_name or "presence" in usage_name:
            return BinarySensorDeviceClass.PRESENCE
        elif "contact" in usage_name:
            return BinarySensorDeviceClass.DOOR
        elif "vibration" in usage_name:
            return BinarySensorDeviceClass.VIBRATION
        elif "mouvement" in usage_name or "motion" in usage_name:
            return BinarySensorDeviceClass.MOTION

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
