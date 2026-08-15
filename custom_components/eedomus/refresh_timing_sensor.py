"""Refresh timing sensors for eedomus integration.

Provides virtual sensors to monitor and analyze refresh performance metrics.
"""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


# --- MODIFICATION: Logique unifiée d'extraction de l'IP ---
def get_clean_box_name_from_coord(coordinator) -> tuple[str, str]:
    """Extrait proprement l'IP pour formater le nom de la Box."""
    host = str(
        coordinator.config_entry.data.get("host", coordinator.config_entry.title)
    )
    if "Eedomus (" in host:
        try:
            host = host.split("Eedomus (")[1].split(")")[0]
        except Exception:
            pass
    return host, f"Box eedomus ({host})"


class EedomusRefreshTimingSensor(CoordinatorEntity, SensorEntity):
    """Base class for refresh timing sensors."""

    def __init__(self, coordinator, sensor_type: str, unit: str, icon: str):
        """Initialize the refresh timing sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type

        # --- MODIFICATION: Extraction propre de l'IP pour garantir des identifiants uniques ---
        host, box_name = get_clean_box_name_from_coord(coordinator)
        box_id = coordinator.config_entry.entry_id

        # Attributs définis directement en mémoire pour éviter d'être écrasés
        self._attr_name = f"Eedomus {sensor_type} ({host})"

        slug = sensor_type.lower().replace(" ", "_").replace("eedomus_", "")
        # unique_id basé sur l'entry_id pour éviter les collisions multi-box
        self._attr_unique_id = f"eedomus_{box_id}_{slug}_timing"

        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_has_entity_name = True

        # Rattachement strict à l'appareil unique de la Box
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"eedomus_box_{box_id}")},
            name=box_name,
            manufacturer="Eedomus",
            model="Eedomus Box",
            sw_version="Unknown",
        )
        # ----------------------------------------------------------------------------------

    @property
    def native_value(self):
        """Return the current value of the sensor."""
        return 0.0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return {
            "sensor_type": self._sensor_type,
        }


class EedomusAPITimeSensor(EedomusRefreshTimingSensor):
    """Sensor for tracking API response time."""

    def __init__(self, coordinator):
        """Initialize the API time sensor."""
        super().__init__(coordinator, "API Time", UnitOfTime.SECONDS, "mdi:clock-outline")

    @property
    def native_value(self):
        """Return the current API time."""
        val = getattr(self.coordinator, "_last_api_time", None)
        return round(val, 3) if isinstance(val, (int, float)) else 0.0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs.update(
            {
                "description": "Time spent waiting for eedomus API responses",
                "component": "api",
                "unit": "seconds",
            }
        )
        return attrs


class EedomusProcessingTimeSensor(EedomusRefreshTimingSensor):
    """Sensor for tracking data processing time."""

    def __init__(self, coordinator):
        """Initialize the processing time sensor."""
        super().__init__(coordinator, "Processing Time", UnitOfTime.SECONDS, "mdi:cog-outline")

    @property
    def native_value(self):
        """Return the current processing time."""
        val = getattr(self.coordinator, "_last_processing_time", None)
        return round(val, 3) if isinstance(val, (int, float)) else 0.0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs.update(
            {
                "description": "Time spent processing eedomus API responses",
                "component": "processing",
                "unit": "seconds",
            }
        )
        return attrs


class EedomusTotalRefreshTimeSensor(EedomusRefreshTimingSensor):
    """Sensor for tracking total refresh time."""

    def __init__(self, coordinator):
        """Initialize the total refresh time sensor."""
        super().__init__(coordinator, "Total Refresh Time", UnitOfTime.SECONDS, "mdi:timer-outline")

    @property
    def native_value(self):
        """Return the current total refresh time."""
        val = getattr(self.coordinator, "_last_refresh_time", None)
        return round(val, 3) if isinstance(val, (int, float)) else 0.0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs.update(
            {
                "description": "Total time for complete refresh cycle",
                "component": "total",
                "unit": "seconds",
            }
        )
        return attrs


class EedomusProcessedDevicesSensor(EedomusRefreshTimingSensor):
    """Sensor for tracking number of processed devices."""

    def __init__(self, coordinator):
        """Initialize the processed devices sensor."""
        super().__init__(coordinator, "Processed Devices", "devices", "mdi:devices")
        self._attr_device_class = None

    @property
    def native_value(self):
        """Return the current number of processed devices."""
        val = getattr(self.coordinator, "_last_processed_devices", None)
        return int(val) if isinstance(val, (int, float)) else 0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs.update(
            {
                "description": "Number of devices processed in last refresh",
                "component": "devices",
                "unit": "count",
            }
        )
        return attrs


class EedomusEndpointTimingSensor(EedomusRefreshTimingSensor):
    """Base class for endpoint-specific timing sensors."""

    def __init__(self, coordinator, endpoint_name: str, icon: str):
        """Initialize the endpoint timing sensor."""
        super().__init__(coordinator, f"{endpoint_name} Time", UnitOfTime.SECONDS, icon)
        self._endpoint_name = endpoint_name

    @property
    def native_value(self):
        """Return the current timing for this endpoint."""
        timings = getattr(self.coordinator, "_endpoint_timings", None)
        if isinstance(timings, dict):
            val = timings.get(self._endpoint_name, 0.0)
            return round(val, 3) if isinstance(val, (int, float)) else 0.0
        return 0.0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        counts = getattr(self.coordinator, "_endpoint_call_counts", None)
        call_count = (
            counts.get(self._endpoint_name, 0) if isinstance(counts, dict) else 0
        )

        attrs.update(
            {
                "description": f"Time spent on {self._endpoint_name} API endpoint",
                "endpoint": self._endpoint_name,
                "unit": "seconds",
                "call_count": call_count,
            }
        )
        return attrs


class EedomusGetPeriphListSensor(EedomusEndpointTimingSensor):
    """Sensor for tracking get_periph_list endpoint timing."""

    def __init__(self, coordinator):
        """Initialize the get_periph_list timing sensor."""
        super().__init__(coordinator, "get_periph_list", "mdi:format-list-bulleted")


class EedomusGetPeriphValueListSensor(EedomusEndpointTimingSensor):
    """Sensor for tracking get_periph_value_list endpoint timing."""

    def __init__(self, coordinator):
        """Initialize the get_periph_value_list timing sensor."""
        super().__init__(coordinator, "get_periph_value_list", "mdi:format-list-text")


class EedomusGetPeriphCaractSensor(EedomusEndpointTimingSensor):
    """Sensor for tracking get_periph_caract endpoint timing."""

    def __init__(self, coordinator):
        """Initialize the get_periph_caract timing sensor."""
        super().__init__(coordinator, "get_periph_caract", "mdi:cog")


class EedomusPartialRefreshSensor(EedomusEndpointTimingSensor):
    """Sensor for tracking partial refresh endpoint timing."""

    def __init__(self, coordinator):
        """Initialize the partial refresh timing sensor."""
        super().__init__(coordinator, "partial_refresh", "mdi:refresh")


async def async_setup_refresh_timing_sensors(
    hass: HomeAssistant, coordinator, device_registry
):
    """Set up refresh timing sensors and attach them to the eedomus box device."""
    host, box_name = get_clean_box_name_from_coord(coordinator)

    # Get or create the main eedomus box device
    # --- MODIFICATION: Utilisation de l'entry_id pour l'identifiant d'appareil et du nom unifié ---
    device_registry.async_get_or_create(
        config_entry_id=coordinator.config_entry.entry_id,
        identifiers={(DOMAIN, f"eedomus_box_{coordinator.config_entry.entry_id}")},
        name=box_name,
        manufacturer="Eedomus",
        model="Eedomus Box",
        sw_version="Unknown",
    )
    # ------------------------------------------------------------------------------------------

    # Create timing sensors
    sensors = [
        EedomusAPITimeSensor(coordinator),
        EedomusProcessingTimeSensor(coordinator),
        EedomusTotalRefreshTimeSensor(coordinator),
        EedomusProcessedDevicesSensor(coordinator),
        # Endpoint-specific sensors
        EedomusGetPeriphListSensor(coordinator),
        EedomusGetPeriphValueListSensor(coordinator),
        EedomusGetPeriphCaractSensor(coordinator),
        EedomusPartialRefreshSensor(coordinator),
    ]

    # Register sensors
    for sensor in sensors:
        _LOGGER.info("📊 Registering refresh timing sensor: %s", sensor.name)

    return sensors
