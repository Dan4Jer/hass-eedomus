"""History sensor entities for eedomus integration."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class EedomusHistorySensor(CoordinatorEntity, SensorEntity):
    """Represents historical data for a specific device.

    This is a dedicated entity for storing historical data with proper configuration
    to avoid UI pollution while maintaining data accessibility.
    """

    def __init__(
        self, coordinator, periph_id: str, periph_name: str, device_info: DeviceInfo
    ):
        """Initialize the history sensor."""
        super().__init__(coordinator)
        self._periph_id = periph_id
        self._periph_name = periph_name

        # --- MODIFICATION: Unique ID Multi-Box ---
        box_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"eedomus_{box_id}_{periph_id}_history"
        # -----------------------------------------

        self._attr_device_info = device_info
        self._attr_name = f"{periph_name} (History)"

        # --- CORRECTION: Suppression des attributs TEMPERATURE / °C imposés en dur ---
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:history"
        self._attr_entity_category = "diagnostic"
        self._attr_has_entity_name = True

    @property
    def native_value(self):
        """Return the current historical value."""
        # --- CORRECTION: Protection contre coordinator.data == None ---
        coordinator_data = self.coordinator.data or {}
        periph_data = coordinator_data.get(self._periph_id, {})
        return periph_data.get("last_value", "unknown")

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        coordinator_data = self.coordinator.data or {}
        periph_data = coordinator_data.get(self._periph_id, {})
        history_progress = getattr(self.coordinator, "_history_progress", {})
        progress = history_progress.get(self._periph_id, {})

        return {
            "device_id": self._periph_id,
            "last_updated": periph_data.get("last_changed"),
            "history_completed": progress.get("completed", False),
            "last_timestamp": progress.get("last_timestamp", 0),
            "data_points_retrieved": progress.get("retrieved_points", 0),
            "data_points_estimated": progress.get("total_points", 0),
        }


class EedomusHistoryProgressSensor(CoordinatorEntity, SensorEntity):
    """Represents the history retrieval progress for a specific device."""

    def __init__(
        self, coordinator, periph_id: str, periph_name: str, device_info: DeviceInfo
    ):
        """Initialize the history progress sensor."""
        super().__init__(coordinator)
        self._periph_id = periph_id
        self._periph_name = periph_name

        # --- MODIFICATION: Unique ID Multi-Box ---
        box_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"eedomus_{box_id}_history_progress_{periph_id}"
        # -----------------------------------------

        self._attr_device_info = device_info
        self._attr_name = f"History Progress: {periph_name}"

        # --- CORRECTION: Suppression de SensorDeviceClass.ENUM ---
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:progress-clock"
        self._attr_entity_category = "diagnostic"

    @property
    def native_value(self):
        """Return the current progress percentage."""
        history_progress = getattr(self.coordinator, "_history_progress", {})
        progress = history_progress.get(self._periph_id, {})

        total_points = progress.get("total_points", 1)
        retrieved_points = progress.get("retrieved_points", 0)

        if total_points > 0:
            return min(100.0, (retrieved_points / total_points) * 100)
        return 0.0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        history_progress = getattr(self.coordinator, "_history_progress", {})
        progress = history_progress.get(self._periph_id, {})
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
        if hasattr(self.coordinator, "_history_progress"):
            self.async_on_remove(
                self.coordinator.async_add_listener(lambda: self.async_write_ha_state())
            )


class EedomusGlobalHistoryProgressSensor(CoordinatorEntity, SensorEntity):
    """Represents the global history retrieval progress."""

    def __init__(self, coordinator, device_info: DeviceInfo):
        """Initialize the global history progress sensor."""
        super().__init__(coordinator)

        # --- MODIFICATION: Unique ID Multi-Box ---
        box_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"eedomus_{box_id}_history_progress_global"
        # -----------------------------------------

        self._attr_device_info = device_info
        self._attr_name = "Eedomus History Retrieval Progress"

        # --- CORRECTION: Suppression de SensorDeviceClass.ENUM ---
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:progress-wrench"

    @property
    def native_value(self):
        """Return the global progress percentage."""
        history_progress = getattr(self.coordinator, "_history_progress", {})
        if not history_progress:
            return 0.0

        total_devices = len(history_progress)
        if total_devices == 0:
            return 0.0

        completed_devices = sum(
            1 for p in history_progress.values() if p.get("completed", False)
        )

        return min(100.0, (completed_devices / total_devices) * 100)

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        history_progress = getattr(self.coordinator, "_history_progress", {})
        if not history_progress:
            return {}

        total_devices = len(history_progress)
        completed_devices = sum(
            1 for p in history_progress.values() if p.get("completed", False)
        )

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

        # --- MODIFICATION: Unique ID Multi-Box ---
        box_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"eedomus_{box_id}_history_stats"
        # -----------------------------------------

        self._attr_device_info = device_info
        self._attr_name = "Eedomus History Retrieval Stats"
        self._attr_device_class = SensorDeviceClass.DATA_SIZE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "MB"
        self._attr_icon = "mdi:database-clock"

    @property
    def native_value(self):
        """Return the downloaded size in MB."""
        history_progress = getattr(self.coordinator, "_history_progress", {})
        if not history_progress:
            return 0.0

        total_points = sum(
            p.get("total_points", 0) for p in history_progress.values()
        )
        retrieved_points = sum(
            p.get("retrieved_points", 0) for p in history_progress.values()
        )

        if total_points > 0:
            downloaded_mb = (retrieved_points * 100) / (1024 * 1024)
            return round(downloaded_mb, 2)
        return 0.0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        history_progress = getattr(self.coordinator, "_history_progress", {})
        if not history_progress:
            return {}

        total_devices = len(history_progress)
        completed_devices = sum(
            1 for p in history_progress.values() if p.get("completed", False)
        )

        return {
            "total_size": "N/A",
            "downloaded_size": str(self.native_value),
            "devices_with_history": completed_devices,
            "devices_without_history": total_devices - completed_devices,
        }


async def async_setup_history_sensors(
    hass: HomeAssistant, coordinator, device_registry
):
    """Set up history sensors and attach them to the eedomus box device."""
    box_id = coordinator.config_entry.entry_id

    device_registry.async_get_or_create(
        config_entry_id=box_id,
        identifiers={(DOMAIN, f"eedomus_box_{box_id}")},
        name="Box eedomus",
        manufacturer="Eedomus",
        model="Eedomus Box",
        sw_version="Unknown",
    )

    device_info = DeviceInfo(
        identifiers={(DOMAIN, f"eedomus_box_{box_id}")},
        name="Box eedomus",
        manufacturer="Eedomus",
        model="Eedomus Box",
        sw_version="Unknown",
    )

    sensors = [
        EedomusGlobalHistoryProgressSensor(coordinator, device_info),
        EedomusHistoryStatsSensor(coordinator, device_info),
    ]

    history_progress = getattr(coordinator, "_history_progress", {})
    coordinator_data = coordinator.data or {}

    if history_progress:
        for periph_id in history_progress:
            periph_name = coordinator_data.get(periph_id, {}).get(
                "name", f"Device {periph_id}"
            )
            # Create dedicated history sensor for each device
            sensors.append(
                EedomusHistorySensor(coordinator, periph_id, periph_name, device_info)
            )
            # Create progress sensor for each device
            sensors.append(
                EedomusHistoryProgressSensor(
                    coordinator, periph_id, periph_name, device_info
                )
            )

    return sensors
