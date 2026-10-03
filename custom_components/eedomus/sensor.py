"""Sensor entity for eedomus integration."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

from .const import COORDINATOR, DOMAIN
from .entity import EedomusEntity, map_device_to_ha_entity
from .text_sensor import EedomusTextSensor

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


# --- AJOUT: Fonction d'extraction du nom de la box ---
def get_clean_box_name(entry: ConfigEntry) -> tuple[str, str]:
    """Extrait proprement l'IP pour formater le nom de la Box."""
    host = entry.data.get("host") or entry.title
    if "Eedomus (" in host:
        try:
            host = host.split("Eedomus (")[1].split(")")[0]
        except Exception:
            pass
    return host, f"Box eedomus ({host})"


# ---------------------------------------------------


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

    # 🌟 SÉCURITÉ MULTI-BOX : On lie l'entry au coordinator pour la rendre accessible partout
    coordinator.config_entry = entry

    entities = []

    # Get all peripherals (Mapping is now managed globally by the coordinator's Phase 3)
    all_peripherals = getattr(coordinator, "data", {})

    # Get parent-to-children mapping built globally by the coordinator
    parent_to_children = getattr(coordinator, "parent_child_relations", {})

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
            if eedomus_mapping is not None:
                coordinator.data[periph_id].update(eedomus_mapping)
                _LOGGER.debug(
                    "Created energy sensor for %s (%s) - consumption monitoring",
                    periph.get("name", "Unknown"),
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
            "Creating sensor entity for %s (periph_id=%s)",
            periph.get("name", "Unknown"),
            periph_id,
        )

        # Check if this is a text sensor with dynamic value mapping
        entity_specifics = coordinator.data[periph_id].get("entity_specifics", {})
        if entity_specifics.get("value_mapping") == "dynamic_from_values":
            _LOGGER.info(
                "🆕 Creating dynamic text sensor for %s (%s)",
                periph.get("name", "Unknown"),
                periph_id,
            )
            entities.append(EedomusTextSensor(coordinator, periph_id))
            continue

        # Check if this sensor has children that should be aggregated
        if periph_id in parent_to_children and len(parent_to_children[periph_id]) > 0:
            # Create aggregated sensor entity (similar to RGBW light)
            child_devices = [
                all_peripherals[c_id]
                for c_id in parent_to_children[periph_id]
                if c_id in all_peripherals
            ]
            entities.append(
                EedomusAggregatedSensor(
                    coordinator,
                    periph_id,
                    child_devices,
                )
            )
        else:
            # Create regular sensor entity
            entities.append(EedomusSensor(coordinator, periph_id))

    # Create battery sensor entities for devices with battery information
    for periph_id, periph in all_peripherals.items():
        battery_level = periph.get("battery")

        if battery_level:
            _LOGGER.debug(
                "🔋 Battery info found for %s (%s): %s",
                periph.get("name", "unknown"),
                periph_id,
                battery_level,
            )

        if battery_level and str(battery_level).strip():
            try:
                battery_value = int(battery_level)
                if 0 <= battery_value <= 100:
                    parent_id = periph.get("parent_periph_id")
                    if parent_id and parent_id in all_peripherals:
                        parent_battery = all_peripherals[parent_id].get("battery")
                        if parent_battery and str(parent_battery) == str(battery_level):
                            _LOGGER.debug(
                                "⏭️ Skipping duplicate battery for child %s (same as parent %s)",
                                periph_id,
                                parent_id,
                            )
                            continue

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

    # --- SUPPRESSION DES BLOCS de TIMING ET VOLUME D'ICI ---
    # Ces capteurs sont désormais gérés de bout-en-bout (nom, id unique et rattachement d'appareil)
    # dans leurs fichiers respectifs lors de leur création (async_setup_refresh_timing_sensors, etc.).
    # Il suffit de les ajouter à la liste.

    if hasattr(coordinator, "_timing_sensors") and coordinator._timing_sensors:
        entities.extend(coordinator._timing_sensors)
        _LOGGER.info(
            "📊 Added %d refresh timing sensors to Box",
            len(coordinator._timing_sensors),
        )

    if hasattr(coordinator, "_volume_sensors") and coordinator._volume_sensors:
        entities.extend(coordinator._volume_sensors)
        _LOGGER.info(
            "📊 Added %d endpoint volume sensors to Box",
            len(coordinator._volume_sensors),
        )
    else:
        _LOGGER.warning(
            "⚠️  No volume sensors found in coordinator (hasattr: %s, value: %s)",
            hasattr(coordinator, "_volume_sensors"),
            getattr(coordinator, "_volume_sensors", "N/A"),
        )
    # -----------------------------------------------------

    async_add_entities(entities)


def is_system_sensor(periph, mapping=None):
    """Check if a peripheral is a system sensor that should be attached to eedomus box."""
    if not periph:
        return False

    name = periph.get("name", "").lower()

    # 1. Vérification explicite via le mapping personnalisé YAML (la méthode la plus propre)
    if mapping and mapping.get("internal_box_eedomus", False):
        return True

    # 2. Filtrage par nom strict (évite le "in" générique pour ne pas intercepter des périphériques tiers)
    system_names = [
        "box eedomus cpu",
        "eedomus espace libre",
        "box eedomus espace libre",
        "eedomus notifications",
    ]
    if name in system_names:
        return True

    return False


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

        periph_data = self._get_periph_data()
        all_devices = (
            self.coordinator._all_peripherals
            if hasattr(self.coordinator, "_all_peripherals")
            else {}
        )
        device_mapping = (
            map_device_to_ha_entity(
                periph_data, all_devices, coordinator=self.coordinator
            )
            if periph_data
            else {}
        )

        # --- MODIFICATION: Rattachement des capteurs système à l'appareil Box unifié ---
        if is_system_sensor(periph_data, device_mapping):
            host, box_name = get_clean_box_name(coordinator.config_entry)

            self._attr_device_info = DeviceInfo(
                identifiers={
                    (DOMAIN, f"eedomus_box_{coordinator.config_entry.entry_id}")
                },
                name=box_name,
                manufacturer="Eedomus",
                model="Eedomus Box",
                sw_version="Unknown",
            )
            _LOGGER.info(
                "🔗 Attached system sensor %s to Box eedomus.",
                periph_info.get("name", "unknown"),
            )
        # -----------------------------------------------------------------------------

        # Set default device class for all sensors
        self._attr_device_class = None
        self._attr_native_unit_of_measurement = None

        # ✅ CORRECTION : Définition de periph_type (qui manquait dans votre fichier !)
        periph_type = device_mapping.get("ha_subtype")

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
        elif periph_type == "cpu_usage" or periph_type == "cpu":
            self._attr_device_class = "cpu"
            self._attr_native_unit_of_measurement = "%"
        elif periph_type == "disk_free_space":
            self._attr_device_class = "data_size"
            self._attr_native_unit_of_measurement = "B"
        elif periph_type == "text":
            # Text sensors explicitly have no device class
            pass

        # Set icon from entity_specifics if available
        entity_specifics = periph_info.get("entity_specifics", {})
        if "icon" in entity_specifics:
            self._attr_icon = entity_specifics["icon"]
        elif periph_type == "cpu_usage" or periph_type == "cpu":
            self._attr_icon = "mdi:cpu-64-bit"
        elif periph_type == "disk_free_space":
            self._attr_icon = "mdi:harddisk"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        periph_data = self._get_periph_data()
        if periph_data is None:
            _LOGGER.warning(
                f"Cannot get native_value: peripheral data not found for {self._periph_id}"
            )
            return None

        value = periph_data.get("last_value")
        _LOGGER.debug(
            "Sensor %s (periph_id=%s) native_value: %s",
            periph_data.get("name", "unknown"),
            self._periph_id,
            value,
        )

        # 1. Capteurs texte
        if (
            self._attr_device_class == "text"
            or (hasattr(self, "_attr_ha_subtype") and self._attr_ha_subtype == "text")
            or self.coordinator.data.get(self._periph_id, {}).get("ha_subtype")
            == "text"
        ):
            _LOGGER.debug(
                "📝 Text sensor %s (periph_id=%s) - returning raw value: '%s'",
                self.coordinator.data.get(self._periph_id, {}).get("name", "unknown"),
                self._periph_id,
                value,
            )
            return str(value) if value is not None else None

        # 2. Valeurs vides ou None
        if value is None or str(value).strip() == "":
            _LOGGER.debug(
                "Missing or empty value for sensor %s (periph_id=%s)",
                self.coordinator.data.get(self._periph_id, {}).get("name", "unknown"),
                self._periph_id,
            )
            return None

        # 3. Sécurisation "Silvère" : str() forcé + conversion des virgules en points
        val_str = str(value).strip()

        if "(" in val_str:
            val_str = val_str.split("(")[0].strip()

        clean_value = val_str.replace(",", ".")

        # 4. Conversion numérique finale
        try:
            return float(clean_value)
        except ValueError:
            _LOGGER.debug(
                "Non-numeric value for sensor %s (periph_id=%s): '%s' - returning as None",
                self.coordinator.data.get(self._periph_id, {}).get("name", "unknown"),
                self._periph_id,
                value,
            )
            return None

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        periph_data = self.coordinator.data.get(self._periph_id, {})

        # ✅ PRIORITÉ 1 : Support du custom YAML (ex: atmospheric_pressure)
        if "device_class" in periph_data:
            return periph_data["device_class"]

        # ✅ PRIORITÉ 2 : (VOTRE CODE RÉPARÉ avec "is not None" pour éviter les faux positifs)
        if hasattr(self, "_attr_device_class") and self._attr_device_class is not None:
            return self._attr_device_class

        # ✅ PRIORITÉ 3 : Réunification de la détection dynamique (qui était coupée !)
        value_type = periph_data.get("value_type")
        unit = periph_data.get("unit")

        if value_type == "float":
            if unit == "°C":
                return "temperature"
            elif unit == "%":
                return "humidity"
            elif unit == "Lux":
                return "illuminance"
            elif unit in ["W", "Wh"]:
                return "power" if unit == "W" else "energy"
            elif unit == "mm/h":
                return "precipitation_intensity"
            elif unit == "mm":
                return "precipitation"
        return None

    @property
    def state_class(self):
        """Return the state class of the sensor."""
        periph_data = self.coordinator.data.get(self._periph_id, {})

        # ✅ PRIORITÉ 1 : Support du custom YAML (ex: measurement)
        if "state_class" in periph_data:
            return periph_data["state_class"]

        # ✅ PRIORITÉ 2 : Attribution automatique par exclusion positive
        if self.device_class in [
            "temperature",
            "humidity",
            "power",
            "illuminance",
            "atmospheric_pressure",
            "precipitation_intensity",
            "precipitation",
        ]:
            return "measurement"
        if self.device_class == "energy":
            return "total_increasing"
        return None

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        periph_data = self.coordinator.data.get(self._periph_id, {})

        # ✅ PRIORITÉ 1 : Support du custom YAML (ex: hPa)
        if "unit_of_measurement" in periph_data:
            return periph_data["unit_of_measurement"]

        if (
            hasattr(self, "_attr_native_unit_of_measurement")
            and self._attr_native_unit_of_measurement is not None
        ):
            return self._attr_native_unit_of_measurement

        unit = periph_data.get("unit")
        """
        _LOGGER.debug(
            "Sensor %s (periph_id=%s) unit_of_measurement: %s",
            periph_data.get("name", "unknown"),
            self._periph_id,
            unit,
        )
        """

        # ✅ PRIORITÉ 2 : AJOUT DE LA SÉCURITÉ ANTI-ESPACE VIDE (' ')
        if isinstance(unit, str) and not unit.strip():
            return None

        if unit is None:
            device_class = self.device_class
            if device_class in DEVICE_CLASS_UNITS:
                return DEVICE_CLASS_UNITS[device_class]
            else:
                _LOGGER.debug(
                    "Missing unit of measurement for sensor %s (periph_id=%s, device_class=%s)",
                    self.coordinator.data.get(self._periph_id, {}).get(
                        "name", "unknown"
                    ),
                    self._periph_id,
                    device_class,
                )
            return None

        if self.device_class == "illuminance" and unit == "Lux":
            return "lx"

        return unit

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        # Récupère les attributs définis par la classe parente EedomusEntity (s'il y en a)
        attrs = super().extra_state_attributes
        attrs = dict(attrs) if attrs else {}
        allowed_attributes = [
            "history",
            "value_list",
            "current_power",
            "last_reset",
            "consumption",
        ]

        if self.coordinator.data is not None:
            periph_data = self.coordinator.data.get(self._periph_id, {})
        else:
            periph_data = {}

        for key in allowed_attributes:
            if key in periph_data:
                attrs[key] = periph_data[key]

        return attrs


class EedomusAggregatedSensor(EedomusSensor):
    """Representation of an eedomus aggregated sensor, combining parent and child devices."""

    def __init__(self, coordinator, periph_id, child_devices):
        """Initialize the aggregated sensor with parent and child devices."""
        super().__init__(coordinator, periph_id)
        self._parent_id = periph_id
        self._parent_device = self.coordinator.data.get(periph_id, {})
        self._child_devices = {
            child["periph_id"]: child for child in child_devices if child
        }

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


class EedomusHistoryProgressSensor(EedomusEntity, SensorEntity):
    """Capteur pour afficher la progression de l'import de l'historique."""

    def __init__(self, coordinator, device_data):
        super().__init__(coordinator, periph_id=device_data["periph_id"])

        # --- MODIFICATION: Création unique_id (Multi-Box) ---
        # Ajout de l'entry_id pour assurer la compatibilité multi-box et correspondre à la migration
        box_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{box_id}_history_progress_{device_data['periph_id']}"
        # ----------------------------------------------------

        self._attr_name = f"{device_data['name']} (History Progress)"
        self._attr_icon = "mdi:progress-clock"

    @property
    def native_value(self):
        """Retourne le pourcentage de progression."""
        progress = getattr(self.coordinator, "_history_progress", {}).get(
            self._periph_id, {}
        )
        if progress.get("completed"):
            return 100
        return 0

    @property
    def extra_state_attributes(self):
        """Retourne des détails sur la progression."""
        progress = getattr(self.coordinator, "_history_progress", {}).get(
            self._periph_id, {}
        )
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
        device_name = self.coordinator.data.get(periph_id, {}).get(
            "name", "Unknown Device"
        )
        self._attr_name = f"{device_name} Battery"

        # --- MODIFICATION: Création unique_id (Multi-Box) ---
        # Ajout de l'entry_id pour assurer la compatibilité multi-box et correspondre à la migration
        box_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"eedomus_{box_id}_{periph_id}_battery"
        # ----------------------------------------------------

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
        battery_level = self.coordinator.data.get(self._periph_id, {}).get(
            "battery", ""
        )
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
        periph_data = self.coordinator.data.get(self._periph_id, {})
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
        battery_level = self.coordinator.data.get(self._periph_id, {}).get(
            "battery", ""
        )
        _LOGGER.debug(
            "🔋 Updated battery sensor %s: %s%%", self._attr_name, battery_level
        )
