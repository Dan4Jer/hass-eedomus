"""Sensor entity for eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .entity import EedomusEntity
from .const import DOMAIN, SENSOR_DEVICE_CLASSES

_LOGGER = logging.getLogger(__name__)

# Mapping des device_class vers les unités par défaut
DEVICE_CLASS_UNITS = {
    "temperature": "°C",
    "humidity": "%",
    "illuminance": "lx",
    "power": "W",
    "energy": "Wh",
    "voltage": "V",
    "current": "A",
}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up eedomus sensor entities from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    all_peripherals = coordinator.get_all_peripherals()

    sensors = []
    for periph_id, periph in all_peripherals.items():
        value_type = periph.get("value_type")
        unit = periph.get("unit")
        usage_name = periph.get("usage_name", "").lower()
        _LOGGER.debug("Setup sensor entity for periph_id=%s data=%s", periph_id, coordinator.data[periph_id])
        if ((value_type in ["float", "string"] and unit in ["°C", "%", "Lux", "W", "Wh"]) or
            ("température" in usage_name or
             "humidité" in usage_name or
             "luminosité" in usage_name or
             "consommation" in usage_name)):
            sensors.append(EedomusSensor(coordinator, periph_id))

    async_add_entities(sensors, True)

class EedomusSensor(EedomusEntity, SensorEntity):
    """Representation of an eedomus sensor."""

    def __init__(self, coordinator, periph_id):
        """Initialize the sensor."""
        super().__init__(coordinator, periph_id, periph_id)
        _LOGGER.debug("Initializing sensor entity for periph_id=%s", periph_id)

    @property
    def native_value(self):
        """Return the state of the sensor."""
        value = self.coordinator.data[self._periph_id].get("current_value")
        _LOGGER.debug("Sensor %s native_value: %s", self._periph_id, value)
        # Gestion des valeurs vides ou invalides
        if not value or value == "":
            return None  # Renvoie None pour indiquer une valeur indisponible

        try:
            return float(value)  # Conversion en float
        except (ValueError, TypeError):
            return None  # En cas d'erreur de conversion
        return value

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        periph_info = self.coordinator.data[self._periph_id]["info"]
        value_type = periph_info.get("value_type")
        unit = periph_info.get("unit")

        if value_type == "float":
            if unit == "°C":
                return "temperature"
            elif unit == "%":
                return "humidity"
            elif unit == "Lux":
                return "illuminance"
            elif unit in ["W", "Wh"]:
                return "power" if unit == "W" else "energy"
        return None

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        unit = self.coordinator.data[self._periph_id]["info"].get("unit")
        _LOGGER.debug("Sensor %s unit_of_measurement: %s", self._periph_id, unit)
        # Si l'unité est None, utiliser une unité par défaut en fonction de la device_class
        if unit is None:
            device_class = self.device_class
            if device_class in DEVICE_CLASS_UNITS:
                return DEVICE_CLASS_UNITS[device_class]

        # Normaliser l'unité pour la device_class 'illuminance'
        if self.device_class == "illuminance" and unit == "Lux":
            return "lx"
        
        return unit



    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {}
        periph_data = self.coordinator.data.get(self._periph_id, {})

        if "history" in periph_data:
            attrs["history"] = periph_data["history"]

        if "value_list" in periph_data:
            attrs["value_list"] = periph_data["value_list"]

        return attrs



# Dans sensor.py
class EedomusHistoryProgressSensor(EedomusEntity, SensorEntity):
    """Capteur pour afficher la progression de l'import de l'historique."""

    def __init__(self, coordinator, device_data):
        super().__init__(coordinator, device_data)
        self._attr_unique_id = f"eedomus_history_progress_{device_data['id']}"
        self._attr_name = f"{device_data['name']} (History Progress)"
        self._attr_icon = "mdi:progress-clock"

    @property
    def native_value(self):
        """Retourne le pourcentage de progression."""
        progress = self.coordinator._history_progress.get(self._device_id, {})
        if progress.get("completed"):
            return 100
        return 0  # À améliorer avec une estimation réelle

    @property
    def extra_state_attributes(self):
        """Retourne des détails sur la progression."""
        progress = self.coordinator._history_progress.get(self._device_id, {})
        return {
            "last_timestamp": progress.get("last_timestamp", 0),
            "completed": progress.get("completed", False),
            "last_import": datetime.fromtimestamp(progress.get("last_timestamp", 0)).isoformat()
            if progress.get("last_timestamp")
            else "Not started",
        }
