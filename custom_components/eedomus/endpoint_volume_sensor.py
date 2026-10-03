"""Endpoint volume sensors for eedomus integration.

Provides virtual sensors to monitor and analyze API endpoint data volume metrics.
"""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory
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


# --------------------------------------------------------


class EedomusEndpointVolumeSensor(CoordinatorEntity, SensorEntity):
    """Base class for endpoint volume sensors."""

    def __init__(self, coordinator, endpoint_name: str, icon: str):
        """Initialize the endpoint volume sensor."""
        super().__init__(coordinator)
        self._endpoint_name = endpoint_name

        # --- MODIFICATION: Extraction propre de l'IP pour garantir des identifiants uniques ---
        host, box_name = get_clean_box_name_from_coord(coordinator)
        box_id = coordinator.config_entry.entry_id

        # Configuration des attributs uniques par instance
        self._attr_name = f"Eedomus {endpoint_name} Volume KB ({host})"

        slug = endpoint_name.lower().replace(" ", "_").replace("eedomus_", "")
        # unique_id basé sur l'entry_id pour éviter les collisions multi-box
        self._attr_unique_id = f"eedomus_{box_id}_{slug}_volume_kb"

        self._attr_native_unit_of_measurement = "KB"
        self._attr_icon = icon
        self._attr_device_class = None  # Not a standard device class for volume
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
        """Return the volume for this specific endpoint in KB."""
        if not hasattr(self.coordinator, "_endpoint_data_sizes"):
            return 0

        size_bytes = self.coordinator._endpoint_data_sizes.get(self._endpoint_name, 0)
        return round(int(size_bytes) / 1024, 2)

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        bytes_value = (
            int(self.coordinator._endpoint_data_sizes.get(self._endpoint_name, 0))
            if hasattr(self.coordinator, "_endpoint_data_sizes")
            else 0
        )
        kb_value = bytes_value / 1024
        mb_value = kb_value / 1024

        return {
            "last_updated": datetime.now().isoformat(),
            "endpoint": self._endpoint_name,
            "description": f"Data size returned by {self._endpoint_name} endpoint",
            "unit": "kilobytes",
            "call_count": (
                self.coordinator._endpoint_call_counts.get(self._endpoint_name, 0)
                if hasattr(self.coordinator, "_endpoint_call_counts")
                else 0
            ),
            "bytes": bytes_value,
            "kilobytes": round(kb_value, 2),
            "megabytes": round(mb_value, 2),
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
        if hasattr(self.coordinator, "_endpoint_data_sizes"):
            total_bytes = sum(
                int(size) for size in self.coordinator._endpoint_data_sizes.values()
            )
            return round(total_bytes / 1024, 2)
        return 0

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        attrs = super().extra_state_attributes
        if hasattr(self.coordinator, "_endpoint_data_sizes"):
            endpoint_details = {}
            total_bytes = 0
            total_kb = 0
            total_mb = 0

            for endpoint, size in self.coordinator._endpoint_data_sizes.items():
                if size > 0:
                    endpoint_details[endpoint] = {
                        "bytes": size,
                        "kilobytes": round(size / 1024, 2),
                        "megabytes": round(size / 1024 / 1024, 2),
                    }
                    total_bytes += size
                    total_kb += size / 1024
                    total_mb += size / 1024 / 1024

            attrs["endpoint_breakdown"] = endpoint_details
            attrs["bytes"] = total_bytes
            attrs["kilobytes"] = round(total_kb, 2)
            attrs["megabytes"] = round(total_mb, 2)
        return attrs


async def async_setup_endpoint_volume_sensors(
    hass: HomeAssistant, coordinator, device_registry
):
    """Set up endpoint volume sensors and attach them to the eedomus box device."""
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
