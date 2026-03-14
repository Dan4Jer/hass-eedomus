"""Endpoint volume sensors for eedomus integration.

Provides virtual sensors to monitor and analyze API endpoint data volume metrics.
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

class EedomusEndpointVolumeSensor(CoordinatorEntity, SensorEntity):
    """Base class for endpoint volume sensors."""

    def __init__(self, coordinator, endpoint_name: str, icon: str):
        """Initialize the endpoint volume sensor."""
        super().__init__(coordinator)
        self._endpoint_name = endpoint_name
        self._attr_native_unit_of_measurement = "items"
        self._attr_icon = icon
        self._attr_device_class = None  # Not a standard device class for volume
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
        return f"Eedomus {self._endpoint_name} Volume"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return f"eedomus_{self._endpoint_name.lower()}_volume"

    @property
    def native_value(self):
        """Return the current volume for this endpoint in KB."""
        if hasattr(self.coordinator, '_endpoint_data_sizes'):
            bytes_value = int(self.coordinator._endpoint_data_sizes.get(self._endpoint_name, 0))
            return round(bytes_value / 1024, 2)
        return 0

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return "KB"

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        bytes_value = int(self.coordinator._endpoint_data_sizes.get(self._endpoint_name, 0)) if hasattr(self.coordinator, '_endpoint_data_sizes') else 0
        kb_value = round(bytes_value / 1024, 2)
        mb_value = round(kb_value / 1024, 2)
        
        return {
            "last_updated": datetime.now().isoformat(),
            "endpoint": self._endpoint_name,
            "description": f"Data size returned by {self._endpoint_name} endpoint",
            "unit": "kilobytes",
            "call_count": self.coordinator._endpoint_call_counts.get(self._endpoint_name, 0) if hasattr(self.coordinator, '_endpoint_call_counts') else 0,
            "bytes": bytes_value,
            "kilobytes": kb_value,
            "megabytes": mb_value
        }


class EedomusGetPeriphListVolumeSensor(EedomusEndpointVolumeSensor):
    """Sensor for tracking get_periph_list endpoint volume."""

    def __init__(self, coordinator):
        """Initialize the get_periph_list volume sensor."""
        super().__init__(coordinator, "get_periph_list", "mdi:format-list-bulleted")


class EedomusGetPeriphValueListVolumeSensor(EedomusEndpointVolumeSensor):
    """Sensor for tracking get_periph_value_list endpoint volume."""

    def __init__(self, coordinator):
        """Initialize the get_periph_value_list volume sensor."""
        super().__init__(coordinator, "get_periph_value_list", "mdi:format-list-text")


class EedomusGetPeriphCaractVolumeSensor(EedomusEndpointVolumeSensor):
    """Sensor for tracking get_periph_caract endpoint volume."""

    def __init__(self, coordinator):
        """Initialize the get_periph_caract volume sensor."""
        super().__init__(coordinator, "get_periph_caract", "mdi:cog")


class EedomusPartialRefreshVolumeSensor(EedomusEndpointVolumeSensor):
    """Sensor for tracking partial refresh endpoint volume."""

    def __init__(self, coordinator):
        """Initialize the partial refresh volume sensor."""
        super().__init__(coordinator, "partial_refresh", "mdi:refresh")


class EedomusTotalDataVolumeSensor(EedomusEndpointVolumeSensor):
    """Sensor for tracking total data volume across all endpoints."""

    def __init__(self, coordinator):
        """Initialize the total data volume sensor."""
        super().__init__(coordinator, "Total Data", "mdi:database")

    @property
    def native_value(self):
        """Return the total volume across all endpoints in KB."""
        if hasattr(self.coordinator, '_endpoint_data_sizes'):
            total_bytes = sum(int(size) for size in self.coordinator._endpoint_data_sizes.values())
            return round(total_bytes / 1024, 2)
        return 0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        if hasattr(self.coordinator, '_endpoint_data_sizes'):
            endpoint_details = {}
            for endpoint, size in self.coordinator._endpoint_data_sizes.items():
                if size > 0:
                    endpoint_details[endpoint] = {
                        "bytes": size,
                        "kilobytes": round(size / 1024, 2),
                        "megabytes": round(size / 1024 / 1024, 2)
                    }
            attrs["endpoint_breakdown"] = endpoint_details
        return attrs


async def async_setup_endpoint_volume_sensors(hass: HomeAssistant, coordinator, device_registry):
    """Set up endpoint volume sensors and attach them to the eedomus box device."""
    
    # Get or create the main eedomus box device
    box_device = device_registry.async_get_or_create(
        config_entry_id=coordinator.config_entry.entry_id,
        identifiers={(DOMAIN, "eedomus_box_main")},
        name="Box eedomus",
        manufacturer="Eedomus",
        model="Eedomus Box",
        sw_version="Unknown",
    )

    # Create volume sensors
    sensors = [
        EedomusGetPeriphListVolumeSensor(coordinator),
        EedomusGetPeriphValueListVolumeSensor(coordinator),
        EedomusGetPeriphCaractVolumeSensor(coordinator),
        EedomusPartialRefreshVolumeSensor(coordinator),
        EedomusTotalDataVolumeSensor(coordinator),
    ]

    # Register sensors
    for sensor in sensors:
        _LOGGER.info("📊 Registering endpoint volume sensor: %s", sensor.name)

    return sensors