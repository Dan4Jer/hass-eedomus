"""Climate entity for eedomus integration."""

from __future__ import annotations

import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import EedomusEntity, map_device_to_ha_entity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up eedomus climate entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    climates = []

    all_peripherals = coordinator.get_all_peripherals()

    # First pass: ensure all peripherals have proper mapping
    for periph_id, periph in all_peripherals.items():
        if "ha_entity" not in coordinator.data[periph_id]:
            eedomus_mapping = map_device_to_ha_entity(periph)
            coordinator.data[periph_id].update(eedomus_mapping)
            # S'assurer que le mapping est enregistré dans le registre global
            from .entity import _register_device_mapping
            _register_device_mapping(eedomus_mapping, periph["name"], periph_id, periph)

    # Second pass: create climate entities
    for periph_id, periph in all_peripherals.items():
        ha_entity = coordinator.data[periph_id].get("ha_entity")

        if ha_entity != "climate":
            continue

        _LOGGER.debug("Creating climate entity for %s (%s)", periph["name"], periph_id)
        climates.append(EedomusClimate(coordinator, periph_id))

    async_add_entities(climates, True)


class EedomusClimate(EedomusEntity, ClimateEntity):
                # Log pour confirmer que le device a été mappé
                _LOGGER.debug("✅ Device mapped: %s (%s) → %s:%s", 
                            periph["name"], periph_id, eedomus_mapping["ha_entity"], eedomus_mapping["ha_subtype"])
    """Representation of an eedomus climate device."""

    def __init__(self, coordinator, periph_id: str):
        """Initialize the climate device."""
        super().__init__(coordinator, periph_id)
        self._attr_name = self.coordinator.data[periph_id]["name"]
        self._attr_unique_id = f"{periph_id}_climate"

        # Climate-specific attributes
        self._attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

        # Temperature unit (required by Home Assistant)
        self._attr_temperature_unit = "°C"  # Celsius

        # Default temperature range (can be adjusted based on device capabilities)
        self._attr_min_temp = 7.0
        self._attr_max_temp = 30.0
        self._attr_target_temperature_step = 0.5

        # Initialize default values
        self._attr_target_temperature = 19.0  # Default target temperature
        self._attr_current_temperature = None  # Will be set if available

        _LOGGER.debug(
            "Initializing climate entity for %s (%s)", self._attr_name, periph_id
        )
        self._update_climate_state()

    def _update_climate_state(self):
        """Update the climate state from eedomus data."""
        periph_data = self.coordinator.data[self._periph_id]

        # Map eedomus values to Home Assistant HVAC modes
        current_value = periph_data.get("last_value", "")

        # Improved HVAC mode mapping based on usage_id
        usage_id = periph_data.get("usage_id", "")

        # For temperature setpoints (usage_id=15), the value is typically the temperature
        if usage_id == "15":
            # For consignes de température, last_value is usually the target temperature
            if current_value.replace(".", "").isdigit():
                self._attr_hvac_mode = HVACMode.HEAT
            else:
                self._attr_hvac_mode = HVACMode.OFF
        # For fil pilote heating (usage_id=19,20,38)
        elif usage_id in ["19", "20", "38"]:
            if current_value in ["1", "on", "heat", "chauffage", "marche"]:
                self._attr_hvac_mode = HVACMode.HEAT
            else:
                self._attr_hvac_mode = HVACMode.OFF
        # Default mapping
        else:
            if current_value in ["1", "on", "heat"]:
                self._attr_hvac_mode = HVACMode.HEAT
            else:
                self._attr_hvac_mode = HVACMode.OFF

        # Try to get target temperature if available
        target_temp = None
        if "target_temperature" in periph_data:
            target_temp = float(periph_data["target_temperature"])
        elif (
            "last_value" in periph_data
            and periph_data["last_value"].replace(".", "").isdigit()
        ):
            # If last_value looks like a temperature
            target_temp = float(periph_data["last_value"])

        if target_temp is not None:
            self._attr_target_temperature = target_temp

        # Get current temperature from associated sensor if available
        current_temp = None

        # Try to find temperature sensor in child devices
        all_peripherals = self.coordinator.get_all_peripherals()
        for child_periph_id, child_periph in all_peripherals.items():
            if child_periph.get("parent_periph_id") == self._periph_id:
                if child_periph.get("usage_id") == "7":  # Temperature sensor
                    child_value = child_periph.get("last_value", "")
                    if (
                        child_value
                        and child_value.replace(".", "").replace("-", "").isdigit()
                    ):
                        current_temp = float(child_value)
                        break

        if current_temp is None and "current_temperature" in periph_data:
            current_temp = float(periph_data["current_temperature"])

        if current_temp is not None:
            self._attr_current_temperature = current_temp

        # Set temperature range based on eedomus values if available
        self._attr_min_temp = 7.0  # Default minimum
        self._attr_max_temp = 30.0  # Default maximum

        # Try to determine temperature range from acceptable values
        values_data = periph_data.get("values", [])
        if values_data:
            numeric_values = []
            for value_item in values_data:
                if isinstance(value_item, dict):
                    value = value_item.get("value", "")
                    if value.replace(".", "").isdigit():
                        numeric_values.append(float(value))

            if numeric_values:
                self._attr_min_temp = min(numeric_values)
                self._attr_max_temp = max(numeric_values)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        periph_data = self._get_periph_data()
        if periph_data is None:
            return False
            
        return periph_data.get("last_value", "") != ""

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        _LOGGER.info(
            "Setting temperature for %s to %.1f°C", self._attr_name, temperature
        )

        try:
            periph_data = self.coordinator.data[self._periph_id]
            eedomus_value = None

            # For usage_id=15 (temperature setpoints), we can send the temperature directly
            usage_id = periph_data.get("usage_id", "")

            if usage_id == "15":
                # For consignes de température, send the temperature directly
                # Round to nearest 0.5 as that's the typical step for eedomus
                rounded_temp = round(temperature * 2) / 2
                eedomus_value = str(rounded_temp)

                _LOGGER.debug(
                    "Setting %s temperature directly to %.1f°C (usage_id=15)",
                    self._attr_name,
                    rounded_temp,
                )
            else:
                # For other devices, use the acceptable values approach
                acceptable_values = {}

                # Build a mapping of description to value from the peripheral's value list
                if "values" in periph_data:
                    for value_item in periph_data["values"]:
                        value = value_item.get("value", "")
                        description = value_item.get("description", "").lower()
                        acceptable_values[description] = value
                        acceptable_values[value] = (
                            value  # Also allow direct value matching
                        )

                _LOGGER.debug(
                    "Acceptable temperature values for %s: %s",
                    self._attr_name,
                    acceptable_values,
                )

                # Find the closest acceptable temperature value
                # First try exact match
                temp_str = str(int(temperature))  # Try as integer first
                if temp_str in acceptable_values:
                    eedomus_value = acceptable_values[temp_str]
                else:
                    # Try to find the closest value
                    numeric_values = []
                    for val in acceptable_values.values():
                        try:
                            numeric_values.append(float(val))
                        except ValueError:
                            pass

                    if numeric_values:
                        closest_value = min(
                            numeric_values, key=lambda x: abs(x - temperature)
                        )
                        eedomus_value = (
                            str(int(closest_value))
                            if closest_value.is_integer()
                            else str(closest_value)
                        )

                if eedomus_value is None:
                    _LOGGER.error(
                        "No acceptable temperature value found for %s. Available: %s",
                        self._attr_name,
                        list(acceptable_values.keys()),
                    )
                    return

                _LOGGER.debug(
                    "Setting %s temperature to eedomus value: %s (requested: %.1f°C)",
                    self._attr_name,
                    eedomus_value,
                    temperature,
                )

            if eedomus_value is None:
                _LOGGER.error(
                    "Could not determine eedomus value for temperature %.1f°C",
                    temperature,
                )
                return

            result = await self._client.set_periph_value(
                self._periph_id, str(eedomus_value)
            )

            if result.get("success", 0) == 1:
                _LOGGER.debug(
                    "Successfully set temperature for %s to %.1f°C (eedomus value: %s)",
                    self._attr_name,
                    temperature,
                    eedomus_value,
                )
                # Update the target temperature immediately
                self._attr_target_temperature = temperature
                await self.coordinator.async_request_refresh()
                self.async_write_ha_state()
            else:
                _LOGGER.error(
                    "Failed to set temperature for %s: %s (tried value: %s, requested: %.1f°C)",
                    self._attr_name,
                    result.get("error", "Unknown error"),
                    eedomus_value,
                    temperature,
                )
        except Exception as e:
            _LOGGER.error(
                "Exception while setting temperature for %s: %s",
                self._attr_name,
                str(e),
            )
            raise

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new HVAC mode."""
        _LOGGER.info("Setting HVAC mode for %s to %s", self._attr_name, hvac_mode)

        try:
            # Get the list of acceptable values for this peripheral
            periph_data = self.coordinator.data[self._periph_id]
            acceptable_values = {}

            # Build a mapping of description to value from the peripheral's value list
            if "values" in periph_data:
                for value_item in periph_data["values"]:
                    value = value_item.get("value", "")
                    description = value_item.get("description", "").lower()
                    acceptable_values[description] = value
                    acceptable_values[value] = value  # Also allow direct value matching

            _LOGGER.debug(
                "Acceptable values for %s: %s", self._attr_name, acceptable_values
            )

            # Map Home Assistant HVAC mode to eedomus command using acceptable values
            eedomus_value = None
            if hvac_mode == HVACMode.HEAT:
                # Try different variations that might be in the acceptable values
                for heat_variant in ["on", "heat", "chauffage", "marche", "1"]:
                    if heat_variant in acceptable_values:
                        eedomus_value = acceptable_values[heat_variant]
                        break
            elif hvac_mode == HVACMode.OFF:
                # Try different variations for off
                for off_variant in ["off", "arrêt", "0", "stop"]:
                    if off_variant in acceptable_values:
                        eedomus_value = acceptable_values[off_variant]
                        break

            if eedomus_value is None:
                _LOGGER.error(
                    "No acceptable value found for HVAC mode %s for %s. Available: %s",
                    hvac_mode,
                    self._attr_name,
                    list(acceptable_values.keys()),
                )
                return

            _LOGGER.debug(
                "Setting %s HVAC mode to eedomus value: %s",
                self._attr_name,
                eedomus_value,
            )

            result = await self._client.set_periph_value(
                self._periph_id, str(eedomus_value)
            )

            if result.get("success", 0) == 1:
                _LOGGER.debug(
                    "Successfully set HVAC mode for %s to %s (eedomus value: %s)",
                    self._attr_name,
                    hvac_mode,
                    eedomus_value,
                )
                self._attr_hvac_mode = hvac_mode
                await self.coordinator.async_request_refresh()
                self.async_write_ha_state()
            else:
                _LOGGER.error(
                    "Failed to set HVAC mode for %s: %s (tried value: %s)",
                    self._attr_name,
                    result.get("error", "Unknown error"),
                    eedomus_value,
                )
        except Exception as e:
            _LOGGER.error(
                "Exception while setting HVAC mode for %s: %s", self._attr_name, str(e)
            )
            raise

    @property
    def temperature_unit(self) -> str:
        """Return the temperature unit."""
        return self._attr_temperature_unit

    async def async_update(self) -> None:
        """Update the climate state."""
        await super().async_update()
        self._update_climate_state()

        # Format the debug message safely
        target_temp = (
            self._attr_target_temperature if self._attr_target_temperature else "N/A"
        )
        if isinstance(target_temp, (int, float)):
            target_str = f"{target_temp:.1f}°C"
        else:
            target_str = str(target_temp)

        _LOGGER.debug(
            "Updated climate state for %s: mode=%s, target=%s",
            self._attr_name,
            self._attr_hvac_mode,
            target_str,
        )
