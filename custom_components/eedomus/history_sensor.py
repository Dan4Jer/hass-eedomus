"""History sensor entities for eedomus integration."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import (SensorEntity, SensorDeviceClass, SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EedomusHistoryProgressSensor(CoordinatorEntity, SensorEntity):
    """Represents the history retrieval progress for a specific device."""

    def __init__(self, coordinator, periph_id: str, periph_name: str, device_info: DeviceInfo):
        """Initialize the history progress sensor."""
        super().__init__(coordinator)
        self._periph_id = periph_id
        self._periph_name = periph_name
        self._attr_unique_id = f"eedomus_history_progress_{periph_id}"
        self._attr_device_info = device_info
        self._attr_name = f"History Progress: {periph_name}"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "%"
        self._attr_icon = "mdi:progress-clock"

    @property
    def native_value(self):
        """Return the current progress percentage."""
        progress = self.coordinator._history_progress.get(self._periph_id, {})
        total_points = self.coordinator._history_progress.get(self._periph_id, {}).get("total_points", 1)
        retrieved_points = self.coordinator._history_progress.get(self._periph_id, {}).get("retrieved_points", 0)
        
        if total_points > 0:
            return min(100, (retrieved_points / total_points) * 100)
        return 0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        progress = self.coordinator._history_progress.get(self._periph_id, {})
        return {
            "periph_id": self._periph_id,
            "periph_name": self._periph_name,
            "data_points_retrieved": progress.get("retrieved_points", 0),
            "data_points_estimated": progress.get("total_points", 0),
            "last_timestamp": progress.get("last_timestamp", 0),
            "completed": progress.get("completed", False),
        }

    async def async_added_to_hass(self):
        """Call when the sensor is added to Home Assistant."""
        await super().async_added_to_hass()
        # Register for updates
        if hasattr(self.coordinator, '_history_progress'):
            self.async_on_remove(self.coordinator.async_add_listener(
                lambda: self.async_write_ha_state()
            ))


class EedomusGlobalHistoryProgressSensor(CoordinatorEntity, SensorEntity):
    """Represents the global history retrieval progress."""

    def __init__(self, coordinator, device_info: DeviceInfo):
        """Initialize the global history progress sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = "eedomus_history_progress_global"
        self._attr_device_info = device_info
        self._attr_name = "Eedomus History Retrieval Progress"
        self._attr_device_class = SensorDeviceClass.ENUM
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "%"
        self._attr_icon = "mdi:progress-wrench"

    @property
    def native_value(self):
        """Return the global progress percentage."""
        if not hasattr(self.coordinator, '_history_progress') or not self.coordinator._history_progress:
            return 0
        
        total_devices = len(self.coordinator._history_progress)
        if total_devices == 0:
            return 0
        
        completed_devices = sum(1 for p in self.coordinator._history_progress.values() if p.get("completed", False))
        
        # Simple average-based progress
        return min(100, (completed_devices / total_devices) * 100)

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        if not hasattr(self.coordinator, '_history_progress'):
            return {}
        
        total_devices = len(self.coordinator._history_progress)
        completed_devices = sum(1 for p in self.coordinator._history_progress.values() if p.get("completed", False))
        
        return {
            "devices_total": total_devices,
            "devices_completed": completed_devices,
            "devices_remaining": total_devices - completed_devices,
        }


class EedomusHistoryStatsSensor(CoordinatorEntity, SensorEntity):
    """Represents history retrieval statistics."""

    def __init__(self, coordinator, device_info: DeviceInfo):
        """Initialize the history stats sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = "eedomus_history_stats"
        self._attr_device_info = device_info
        self._attr_name = "Eedomus History Retrieval Stats"
        self._attr_device_class = SensorDeviceClass.DATA_SIZE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "MB"
        self._attr_icon = "mdi:database-clock"

    @property
    def native_value(self):
        """Return the downloaded size in MB."""
        # Estimate based on progress
        if not hasattr(self.coordinator, '_history_progress') or not self.coordinator._history_progress:
            return 0
        
        # Simple estimation: assume 100 bytes per data point
        total_points = sum(p.get("total_points", 0) for p in self.coordinator._history_progress.values())
        retrieved_points = sum(p.get("retrieved_points", 0) for p in self.coordinator._history_progress.values())
        
        if total_points > 0:
            downloaded_mb = (retrieved_points * 100) / (1024 * 1024)
            return round(downloaded_mb, 2)
        return 0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        if not hasattr(self.coordinator, '_history_progress') or not self.coordinator._history_progress:
            return {}
        
        total_devices = len(self.coordinator._history_progress)
        completed_devices = sum(1 for p in self.coordinator._history_progress.values() if p.get("completed", False))
        
        return {
            "total_size": "N/A",  # Would need estimation
            "downloaded_size": str(self.native_value),
            "devices_with_history": completed_devices,
            "devices_without_history": total_devices - completed_devices,
        }


async def async_setup_history_sensors(hass: HomeAssistant, coordinator, device_registry):
    """Set up history sensors and attach them to the eedomus box device."""
    
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
    
    # Create global sensors
    sensors = [
        EedomusGlobalHistoryProgressSensor(coordinator, device_info),
        EedomusHistoryStatsSensor(coordinator, device_info),
    ]
    
    # Create per-device sensors if history is enabled
    if hasattr(coordinator, '_history_progress') and coordinator._history_progress:
        for periph_id, progress in coordinator._history_progress.items():
            periph_name = coordinator.data.get(periph_id, {}).get("name", f"Device {periph_id}")
            sensors.append(EedomusHistoryProgressSensor(coordinator, periph_id, periph_name, device_info))
    
    return sensors