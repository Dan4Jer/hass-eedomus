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

from .const import COORDINATOR, DOMAIN
from .entity import EedomusEntity

_LOGGER = logging.getLogger(__name__)

# Mapping des types et sous-types eedomus vers les device_class de Home Assistant
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
    "flood": BinarySensorDeviceClass.MOISTURE,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up eedomus binary sensor entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    binary_sensors = []

    # Le mapping global (y compris les relations parents/enfants) est déjà fait
    # en amont par entity.py et le Coordinator. On se contente de filtrer.

    for periph_id, periph in coordinator.data.items():
        if periph.get("ha_entity") == "binary_sensor":
            _LOGGER.debug(
                "Creating binary sensor entity for %s (%s)",
                periph.get("name"),
                periph_id,
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
            _LOGGER.warning(
                f"Cannot get binary sensor state: peripheral data not found for {self._periph_id}"
            )
            return None

        value = periph_data.get("last_value")
        _LOGGER.debug("Binary sensor %s is_on: %s", self._periph_id, value)

        if value is None or str(value).strip() == "":
            return None

        # 1. Nettoyage systematique de la chaine (securite Silvere)
        val_str = str(value).strip().replace(",", ".")

        # Gestion robuste des valeurs renvoyées par l'API eedomus
        try:
            # Tente de convertir en nombre (ex: "100", "1", "0")
            val_float = float(val_str)
            return val_float > 0
        except (ValueError, TypeError):
            # Si c'est du texte brut (ex: "on", "open", "marche")
            val_str = str(value).strip().lower()
            return val_str in [
                "on",
                "true",
                "open",
                "ouvert",
                "marche",
                "100",
                "actif",
                "active",
            ]

    @property
    def device_class(self) -> BinarySensorDeviceClass | None:
        """Return the device class of the binary sensor."""
        periph_info = self._get_periph_data()
        if not periph_info:
            return None

        # 1. Utilisation prioritaire du sous-type défini par entity_v2.py
        ha_subtype = periph_info.get("ha_subtype", "")
        if ha_subtype and ha_subtype in EEDOMUS_TO_HA_DEVICE_CLASS:
            return EEDOMUS_TO_HA_DEVICE_CLASS[ha_subtype]

        # 2. Fallback robuste basé sur le nom de l'usage eedomus
        usage_name = periph_info.get("usage_name", "").lower()

        if any(keyword in usage_name for keyword in ["mouvement", "motion"]):
            return BinarySensorDeviceClass.MOTION
        if any(keyword in usage_name for keyword in ["présence", "presence"]):
            return BinarySensorDeviceClass.PRESENCE
        if any(
            keyword in usage_name
            for keyword in ["porte", "fenêtre", "contact", "window", "door"]
        ):
            return BinarySensorDeviceClass.DOOR
        if any(keyword in usage_name for keyword in ["fumée", "smoke"]):
            return BinarySensorDeviceClass.SMOKE
        if any(
            keyword in usage_name for keyword in ["inondation", "eau", "flood", "water"]
        ):
            return BinarySensorDeviceClass.MOISTURE
        if "vibration" in usage_name:
            return BinarySensorDeviceClass.VIBRATION

        # 3. Fallback final sur le type interne du périphérique eedomus
        periph_type = periph_info.get("type", "").lower()
        return EEDOMUS_TO_HA_DEVICE_CLASS.get(periph_type, None)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        # Sécurisation : convertit None en dictionnaire vide
        super_attrs = super().extra_state_attributes
        attrs = dict(super_attrs) if super_attrs else {}

        periph_data = self._get_periph_data() or {}

        # Ajout de l'historique et de la liste des valeurs eedomus si disponibles
        if "history" in periph_data:
            attrs["history"] = periph_data["history"]
        if "value_list" in periph_data:
            attrs["value_list"] = periph_data["value_list"]

        return attrs
