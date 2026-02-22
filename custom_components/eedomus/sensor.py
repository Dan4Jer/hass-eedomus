"""Sensor entity for eedomus integration."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, SENSOR_DEVICE_CLASSES, COORDINATOR
from .entity import EedomusEntity, map_device_to_ha_entity

_LOGGER = logging.getLogger(__name__)

# Mapping of device_class to default units
DEVICE_CLASS_UNITS = {
    "temperature": "°C",
    "humidity": "%",
    "illuminance": "lx",
    "power": "W",
    "energy": "Wh",
    "voltage": "V",
    "current": "A",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up eedomus sensor entities from config entry."""
    # Check if coordinator exists in the new structure
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        entry_data = hass.data[DOMAIN][entry.entry_id]
        coordinator = entry_data.get(COORDINATOR) if COORDINATOR in entry_data else None
    else:
        coordinator = None
    
    if coordinator is None:
        _LOGGER.error("Coordinator not found for entry %s", entry.entry_id)
        return False
    
    entities = []

    # Get all peripherals and build parent-to-children mapping similar to light.py
    all_peripherals = coordinator.get_all_peripherals()
    parent_to_children = {}

    for periph_id, periph in all_peripherals.items():
        if periph.get("parent_periph_id"):
            parent_id = periph["parent_periph_id"]
            if parent_id not in parent_to_children:
                parent_to_children[parent_id] = []
            parent_to_children[parent_id].append(periph)
        if not "ha_entity" in coordinator.data[periph_id]:
            eedomus_mapping = map_device_to_ha_entity(periph, coordinator.data)
            coordinator.data[periph_id].update(eedomus_mapping)
            # S'assurer que le mapping est enregistré dans le registre global
            from .entity import _register_device_mapping
            _register_device_mapping(eedomus_mapping, periph["name"], periph_id, periph)

    # Handle parent-child relationships for sensors similar to light.py
    for periph_id, periph in all_peripherals.items():
        ha_entity = None
        if "ha_entity" in coordinator.data[periph_id]:
            ha_entity = coordinator.data[periph_id]["ha_entity"]

        parent_id = periph.get("parent_periph_id", None)
        if parent_id:
            # Children are managed by parent... similar to light logic
            eedomus_mapping = None
            if periph.get("usage_id") == "26":  # Energy meter like in light.py
                # Create energy sensor for consumption monitoring
                eedomus_mapping = {
                    "ha_entity": "sensor",
                    "ha_subtype": "energy",
                    "justification": "Energy consumption meter (usage_id=26)",
                }
            # Removed usage_id=82 mapping as it's now handled by the main mapping system as "select"
            if not eedomus_mapping is None:
                coordinator.data[periph_id].update(eedomus_mapping)
                _LOGGER.debug(
                    "Created energy sensor for %s (%s) - consumption monitoring",
                    periph["name"],
                    periph_id,
                )

    # Create sensor entities
    for periph_id, periph in all_peripherals.items():
        ha_entity = None
        if "ha_entity" in coordinator.data[periph_id]:
            ha_entity = coordinator.data[periph_id]["ha_entity"]

        if ha_entity is None or not ha_entity == "sensor":
            continue

        _LOGGER.debug(
            "Creating sensor entity for %s (periph_id=%s) mapping=%s",
            periph["name"],
            periph_id,
            coordinator.data[periph_id],
        )

        # Check if this sensor has children that should be aggregated
        if periph_id in parent_to_children and len(parent_to_children[periph_id]) > 0:
            # Create aggregated sensor entity (similar to RGBW light)
            entities.append(
                EedomusAggregatedSensor(
                    coordinator,
                    periph_id,
                    parent_to_children[periph_id],
                )
            )
        else:
            # Create regular sensor entity
            entities.append(EedomusSensor(coordinator, periph_id))

    # Create battery sensor entities for devices with battery information
    # EXCEPT for children that should be mapped as other sensor types
    for periph_id, periph in all_peripherals.items():
        battery_level = periph.get("battery")

        # Debug: Log all devices with battery info
        if battery_level:
            _LOGGER.debug(
                "🔋 Battery info found for %s (%s): %s",
                periph.get("name", "unknown"),
                periph_id,
                battery_level,
            )

        # Check if device has valid battery information
        if battery_level and str(battery_level).strip():
            try:
                battery_value = int(battery_level)
                if 0 <= battery_value <= 100:
                    # Skip if this device should be mapped as a different sensor type
                    # based on usage_id (children of motion sensors, etc.)
                    ha_entity = coordinator.data[periph_id].get("ha_entity")
                    usage_id = periph.get("usage_id")

                    # Create battery sensor entity
                    battery_entity = EedomusBatterySensor(coordinator, periph_id)
                    entities.append(battery_entity)
                    _LOGGER.debug(
                        "Created battery sensor for %s (%s%%)",
                        periph.get("name", "unknown"),
                        battery_value,
                    )
            except ValueError:
                _LOGGER.warning(
                    "Invalid battery level for %s: %s",
                    periph.get("name", "unknown"),
                    battery_level,
                )

    # Add timing sensors if they exist in the coordinator
    if hasattr(coordinator, '_timing_sensors') and coordinator._timing_sensors:
        entities.extend(coordinator._timing_sensors)
        _LOGGER.info("📊 Added %d refresh timing sensors", len(coordinator._timing_sensors))
    
    async_add_entities(entities)


class EedomusSensor(EedomusEntity, SensorEntity):
    """Representation of an eedomus sensor."""

    def __init__(self, coordinator, periph_id):
        """Initialize the sensor."""
        super().__init__(coordinator, periph_id)
        periph_info = self._get_periph_data(periph_id)
        if periph_info is None:
            _LOGGER.warning(f"Peripheral data not found for sensor {periph_id}")
            return
            
        _LOGGER.debug(
            "Initializing sensor entity for %s (periph_id=%s)",
            periph_info.get("name", "unknown"),
            periph_id,
        )

        # Set sensor-specific attributes based on ha_subtype
        periph_type = periph_info.get("ha_subtype")

        # Set default device class for all sensors
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = None

        if periph_type == "temperature":
            self._attr_device_class = "temperature"
            self._attr_native_unit_of_measurement = "°C"
        elif periph_type == "humidity":
            self._attr_device_class = "humidity"
            self._attr_native_unit_of_measurement = "%"
        elif periph_type == "energy":
            self._attr_device_class = "energy"
            self._attr_native_unit_of_measurement = "Wh"
        elif periph_type == "power":
            self._attr_device_class = "power"
            self._attr_native_unit_of_measurement = "W"
        elif periph_type == "time":
            self._attr_device_class = "duration"
            self._attr_native_unit_of_measurement = "h"
        elif periph_type == "text":
            # Text sensors explicitly have no device class
            pass
        # Add more specific types as needed

    @property
    def native_value(self):
        """Return the state of the sensor."""
        periph_data = self._get_periph_data()
        if periph_data is None:
            _LOGGER.warning(f"Cannot get native_value: peripheral data not found for {self._periph_id}")
            return None
            
        value = periph_data.get("last_value")
        _LOGGER.debug(
            "Sensor %s (periph_id=%s) native_value: %s",
            periph_data.get("name", "unknown"),
            self._periph_id,
            value,
        )

        # Check if this is a text sensor - return as-is without conversion
        if self._attr_device_class == "text" or (
            hasattr(self, "_attr_ha_subtype") and self._attr_ha_subtype == "text"
        ):
            _LOGGER.debug(
                "📝 Text sensor %s (periph_id=%s) - returning raw value: '%s'",
                self.coordinator.data[self._periph_id].get("name", "unknown"),
                self._periph_id,
                value,
            )
            return value

        # Handle empty or invalid values
        if not value or value == "":
            _LOGGER.debug(
                "Missing or empty value for sensor %s (periph_id=%s)",
                self.coordinator.data[self._periph_id].get("name", "unknown"),
                self._periph_id,
            )
            return None  # Return None to indicate unavailable value

        # Handle non-standard value formats (e.g., "8 (31)")
        if isinstance(value, str) and "(" in value:
            # Extract the first part of the value (e.g., "8" from "8 (31)")
            value = value.split("(")[0].strip()
            _LOGGER.debug(
                "Non-standard value format corrected for sensor %s (periph_id=%s): %s -> %s",
                self.coordinator.data[self._periph_id].get("name", "unknown"),
                self._periph_id,
                value,
                value,
            )

        # Check if value is numeric before conversion
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str) and value.replace(".", "", 1).lstrip("-").isdigit():
            return float(value)
        else:
            _LOGGER.debug(
                "Non-numeric value for sensor %s (periph_id=%s): '%s' - returning as None",
                self.coordinator.data[self._periph_id].get("name", "unknown"),
                self._periph_id,
                value,
            )
            return None  # Return None if not numeric

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        # Use the device_class set in __init__ or fall back to dynamic detection
        if hasattr(self, "_attr_device_class"):
            return self._attr_device_class

        periph_info = self.coordinator.data[self._periph_id]
        value_type = periph_info.get("value_type")
        unit = periph_info.get("unit")

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        # Text sensors should not have a state class
        if hasattr(self, "_attr_device_class") and self._attr_device_class is None:
            return None
        # For numeric sensors, we could add measurement state class
        # But for now, we'll keep it simple
        return None

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
        # Use the unit set in __init__ or fall back to dynamic detection
        if hasattr(self, "_attr_native_unit_of_measurement"):
            return self._attr_native_unit_of_measurement

        unit = self.coordinator.data[self._periph_id].get("unit")
        _LOGGER.debug(
            "Sensor %s (periph_id=%s) unit_of_measurement: %s",
            self.coordinator.data[self._periph_id].get("name", "unknown"),
            self._periph_id,
            unit,
        )

        # If unit is None, use default unit based on device_class
        if unit is None:
            device_class = self.device_class
            if device_class in DEVICE_CLASS_UNITS:
                return DEVICE_CLASS_UNITS[device_class]
            else:
                _LOGGER.warning(
                    "Missing unit of measurement for sensor %s (periph_id=%s, device_class=%s)",
                    self.coordinator.data[self._periph_id].get("name", "unknown"),
                    self._periph_id,
                    device_class,
                )
                return None

        # Normalize unit for 'illuminance' device_class
        if self.device_class == "illuminance" and unit == "Lux":
            return "lx"

        return unit

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {}
        if self.coordinator.data is not None:
            periph_data = self.coordinator.data.get(self._periph_id, {})
        else:
            periph_data = {}

        if "history" in periph_data:
            attrs["history"] = periph_data["history"]

        if "value_list" in periph_data:
            attrs["value_list"] = periph_data["value_list"]

        return attrs


class EedomusAggregatedSensor(EedomusSensor):
    """Representation of an eedomus aggregated sensor, combining parent and child devices."""

    def __init__(self, coordinator, periph_id, child_devices):
        """Initialize the aggregated sensor with parent and child devices."""
        super().__init__(coordinator, periph_id)
        self._parent_id = periph_id
        self._parent_device = self.coordinator.data[periph_id]
        self._child_devices = {child["periph_id"]: child for child in child_devices}

        _LOGGER.debug(
            "Initializing aggregated sensor %s (periph_id=%s) with children: %s",
            self._parent_device["name"],
            self._parent_id,
            ", ".join(
                f"{child['name']} (periph_id={child['periph_id']})"
                for child in child_devices
            ),
        )

    @property
    def native_value(self):
        """Return the aggregated value from parent and children."""
        parent_value = super().native_value

        # Example: sum values from children for energy sensors
        if self._parent_device.get("ha_subtype") == "energy":
            total = parent_value or 0
            if self.coordinator.data is not None:
                for child_id in self._child_devices:
                    child_data = self.coordinator.data.get(child_id, {})
                    child_value = child_data.get("last_value")
                    try:
                        total += float(child_value or 0)
                    except (ValueError, TypeError):
                        continue
            return total

        # For other types, just return parent value
        return parent_value

    @property
    def extra_state_attributes(self):
        """Return extended state attributes including child values."""
        # Get parent's extra state attributes (which is a dict, not a method)
        attrs = super().extra_state_attributes

        # Create a new dict to avoid modifying the parent's attributes
        result_attrs = dict(attrs) if attrs else {}

        # Add child device values
        child_attrs = {}
        if self.coordinator.data is not None:
            for child_id, child in self._child_devices.items():
                child_data = self.coordinator.data.get(child_id, {})
                child_attrs[child_id] = {
                    "name": child_data.get("name"),
                    "value": child_data.get("last_value"),
                    "unit": child_data.get("unit"),
                    "type": child_data.get("ha_subtype"),
            }

        result_attrs["child_devices"] = child_attrs
        return result_attrs


# In sensor.py
class EedomusHistoryProgressSensor(EedomusEntity, SensorEntity):
    """Capteur pour afficher la progression de l'import de l'historique."""

    def __init__(self, coordinator, device_data):
        super().__init__(
            coordinator, periph_id=device_data["periph_id"]  # Simple string
        )
        self._attr_unique_id = f"eedomus_history_progress_{device_data['periph_id']}"
        self._attr_name = f"{device_data['name']} (History Progress)"
        self._attr_icon = "mdi:progress-clock"

    @property
    def native_value(self):
        """Retourne le pourcentage de progression."""
        progress = self.coordinator._history_progress.get(self._device_id, {})
        if progress.get("completed"):
            return 100
        return 0  # To be improved with real estimation

    @property
    def extra_state_attributes(self):
        """Retourne des détails sur la progression."""
        progress = self.coordinator._history_progress.get(self._device_id, {})
        return {
            "last_timestamp": progress.get("last_timestamp", 0),
            "completed": progress.get("completed", False),
            "last_import": (
                datetime.fromtimestamp(progress.get("last_timestamp", 0)).isoformat()
                if progress.get("last_timestamp")
                else "Not started"
            ),
        }


class EedomusBatterySensor(EedomusEntity, SensorEntity):
    """
    Battery sensor entity for eedomus devices.

    This class implements battery sensors as child entities of main devices.
    It provides battery level information and status monitoring.
    """

    def __init__(self, coordinator, periph_id):
        """Initialize the battery sensor."""
        super().__init__(coordinator, periph_id)

        # Configure battery sensor attributes
        device_name = self.coordinator.data[periph_id].get("name", "Unknown Device")
        self._attr_name = f"{device_name} Battery"
        self._attr_unique_id = f"{periph_id}_battery"
        self._attr_device_class = "battery"
        self._attr_native_unit_of_measurement = "%"
        self._attr_state_class = "measurement"

        _LOGGER.debug(
            "🔋 Initialized battery sensor for %s (periph_id=%s)",
            device_name,
            periph_id,
        )

    @property
    def native_value(self) -> int | None:
        """Return the battery level."""
        battery_level = self.coordinator.data[self._periph_id].get("battery", "")

        if battery_level and str(battery_level).strip():
            try:
                return int(battery_level)
            except ValueError:
                _LOGGER.warning(
                    "Invalid battery level for %s: %s", self._attr_name, battery_level
                )

        return None

    @property
    def available(self) -> bool:
        """Return True if battery data is available."""
        periph_data = self._get_periph_data()
        if periph_data is None:
            return False
            
        battery_level = periph_data.get("battery", "")
        return (
            battery_level
            and str(battery_level).strip()
            and str(battery_level).isdigit()
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        periph_data = self.coordinator.data[self._periph_id]
        battery_level = self.native_value

        # Determine battery status
        battery_status = "Unknown"
        if battery_level is not None:
            if battery_level >= 75:
                battery_status = "High"
            elif battery_level >= 50:
                battery_status = "Medium"
            elif battery_level >= 25:
                battery_status = "Low"
            else:
                battery_status = "Critical"

        return {
            "device_name": periph_data.get("name", ""),
            "device_id": self._periph_id,
            "device_type": periph_data.get("usage_name", ""),
            "battery_status": battery_status,
            "parent_device": periph_data.get("name", ""),
        }

    async def async_update(self) -> None:
        """Update the battery sensor."""
        await super().async_update()
        battery_level = self.coordinator.data[self._periph_id].get("battery", "")
        _LOGGER.debug(
            "🔋 Updated battery sensor %s: %s%%", self._attr_name, battery_level
        )
