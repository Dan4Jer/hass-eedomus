"""Refresh timing sensors for eedomus integration.

Provides virtual sensors to monitor and analyze refresh performance metrics.
"""

from __future__ import annotations
from datetime import datetime
import logging

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_get_eedomus_box_device(hass: HomeAssistant, coordinator) -> DeviceInfo:
    """Get or create the eedomus box device info."""
    device_registry = async_get_device_registry(hass)
    box_device = device_registry.async_get_or_create(
        config_entry_id=coordinator.config_entry.entry_id,
        identifiers={(DOMAIN, "eedomus_box_main")},
        name="Box eedomus",
        manufacturer="Eedomus",
        model="Eedomus Box",
        sw_version="Unknown",
    )
    
    return DeviceInfo(
        identifiers={(DOMAIN, "eedomus_box_main")},
        name="Box eedomus",
        manufacturer="Eedomus",
        model="Eedomus Box",
        sw_version="Unknown",
    )

class EedomusRefreshTimingSensor(CoordinatorEntity, SensorEntity):
    """Base class for refresh timing sensors."""

    def __init__(self, coordinator, sensor_type: str, unit: str, icon: str):
        """Initialize the refresh timing sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT
        from homeassistant.const import EntityCategory
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_has_entity_name = True
        
        # Set device info to attach to eedomus box
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "eedomus_box_main")},
            name="Box eedomus",
            manufacturer="Eedomus",
            model="Eedomus Box",
            sw_version="Unknown",
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"Eedomus {self._sensor_type}"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return f"eedomus_{self._sensor_type.lower().replace(' ', '_')}_timing"

    @property
    def native_value(self):
        """Return the current value of the sensor."""
        return 0.0  # Will be overridden by specific sensors

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        return {
            "last_updated": datetime.now().isoformat(),
            "sensor_type": self._sensor_type
        }

class EedomusAPITimeSensor(EedomusRefreshTimingSensor):
    """Sensor for tracking API response time."""

    def __init__(self, coordinator):
        """Initialize the API time sensor."""
        super().__init__(coordinator, "API Time", "s", "mdi:clock-outline")

    @property
    def native_value(self):
        """Return the current API time."""
        return round(self.coordinator._last_api_time, 3) if hasattr(self.coordinator, '_last_api_time') else 0.0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs.update({
            "description": "Time spent waiting for eedomus API responses",
            "component": "api",
            "unit": "seconds"
        })
        return attrs

class EedomusProcessingTimeSensor(EedomusRefreshTimingSensor):
    """Sensor for tracking data processing time."""

    def __init__(self, coordinator):
        """Initialize the processing time sensor."""
        super().__init__(coordinator, "Processing Time", "s", "mdi:cog-outline")

    @property
    def native_value(self):
        """Return the current processing time."""
        return round(self.coordinator._last_processing_time, 3) if hasattr(self.coordinator, '_last_processing_time') else 0.0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs.update({
            "description": "Time spent processing eedomus API responses",
            "component": "processing",
            "unit": "seconds"
        })
        return attrs

class EedomusTotalRefreshTimeSensor(EedomusRefreshTimingSensor):
    """Sensor for tracking total refresh time."""

    def __init__(self, coordinator):
        """Initialize the total refresh time sensor."""
        super().__init__(coordinator, "Total Refresh Time", "s", "mdi:timer-outline")

    @property
    def native_value(self):
        """Return the current total refresh time."""
        return round(self.coordinator._last_refresh_time, 3) if hasattr(self.coordinator, '_last_refresh_time') else 0.0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs.update({
            "description": "Total time for complete refresh cycle",
            "component": "total",
            "unit": "seconds"
        })
        return attrs

class EedomusProcessedDevicesSensor(EedomusRefreshTimingSensor):
    """Sensor for tracking number of processed devices."""

    def __init__(self, coordinator):
        """Initialize the processed devices sensor."""
        super().__init__(coordinator, "Processed Devices", "devices", "mdi:devices")
        self._attr_device_class = None  # Not a duration for this sensor

    @property
    def native_value(self):
        """Return the current number of processed devices."""
        return int(self.coordinator._last_processed_devices) if hasattr(self.coordinator, '_last_processed_devices') else 0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs.update({
            "description": "Number of devices processed in last refresh",
            "component": "devices",
            "unit": "count"
        })
        return attrs


class EedomusEndpointTimingSensor(EedomusRefreshTimingSensor):
    """Base class for endpoint-specific timing sensors."""

    def __init__(self, coordinator, endpoint_name: str, icon: str):
        """Initialize the endpoint timing sensor."""
        super().__init__(coordinator, f"{endpoint_name} Time", "s", icon)
        self._endpoint_name = endpoint_name

    @property
    def native_value(self):
        """Return the current timing for this endpoint."""
        if hasattr(self.coordinator, '_endpoint_timings'):
            return round(self.coordinator._endpoint_timings.get(self._endpoint_name, 0.0), 3)
        return 0.0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        attrs.update({
            "description": f"Time spent on {self._endpoint_name} API endpoint",
            "endpoint": self._endpoint_name,
            "unit": "seconds",
            "call_count": self.coordinator._endpoint_call_counts.get(self._endpoint_name, 0) if hasattr(self.coordinator, '_endpoint_call_counts') else 0
        })
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

async def async_setup_refresh_timing_sensors(hass: HomeAssistant, coordinator, device_registry):
    """Set up refresh timing sensors and attach them to the eedomus box device."""
    
    # Get or create the main eedomus box device
    box_device = device_registry.async_get_or_create(
        config_entry_id=coordinator.config_entry.entry_id,
        identifiers={(DOMAIN, "eedomus_box_main")},
        name="Box eedomus",
        manufacturer="Eedomus",
        model="Eedomus Box",
        sw_version="Unknown",
    )

    device_info = DeviceInfo(
        identifiers={(DOMAIN, "eedomus_box_main")},
        name="Box eedomus",
        manufacturer="Eedomus",
        model="Eedomus Box",
        sw_version="Unknown",
        via_device=(DOMAIN, "eedomus_box_main"),
    )

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