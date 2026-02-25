"""Climate entity for eedomus integration."""

from __future__ import annotations
from datetime import datetime

import logging

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, COORDINATOR
from .entity import EedomusEntity, map_device_to_ha_entity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up eedomus climate entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    climates = []

    all_peripherals = coordinator.get_all_peripherals()

    # First pass: ensure all peripherals have proper mapping
    for periph_id, periph in all_peripherals.items():
        if "ha_entity" not in coordinator.data[periph_id]:
            eedomus_mapping = map_device_to_ha_entity(periph, coordinator.data, coordinator=coordinator)
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
    """Representation of an eedomus climate device."""

    def __init__(self, coordinator, periph_id: str):
        """Initialize the climate device."""
        super().__init__(coordinator, periph_id)
        self._attr_name = self.coordinator.data[periph_id]["name"]
        self._attr_unique_id = f"{periph_id}_climate"

        # Load YAML configuration for this device
        yaml_config = coordinator.get_yaml_config_sync() if hasattr(coordinator, 'get_yaml_config_sync') else {}
        usage_id = self.coordinator.data[periph_id].get("usage_id", "unknown")
        
        # Get entity-specific configuration from YAML
        entity_specifics = {}
        if 'usage_id_mappings' in yaml_config and usage_id in yaml_config['usage_id_mappings']:
            entity_specifics = yaml_config['usage_id_mappings'][usage_id].get('entity_specifics', {})
        
        # Climate-specific attributes with YAML overrides
        self._attr_hvac_modes = entity_specifics.get('hvac_modes', [HVACMode.HEAT, HVACMode.OFF])
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        
        # Temperature unit (required by Home Assistant)
        self._attr_temperature_unit = entity_specifics.get('temperature_unit', "°C")

        # Temperature range and precision from YAML (with defaults)
        self._attr_min_temp = entity_specifics.get('min_temp', 7.0)
        self._attr_max_temp = entity_specifics.get('max_temp', 30.0)
        self._attr_target_temperature_step = entity_specifics.get('target_temp_step', 0.5)
        
        # Precision for temperature display
        self._attr_precision = entity_specifics.get('precision', 0.5)

        # Initialize default values
        self._attr_target_temperature = 19.0  # Default target temperature
        self._attr_current_temperature = None  # Will be set if available
        
        # Load temperature sensor mapping if available
        self._linked_temperature_sensor = None
        
        # First try custom mappings (from custom_mapping.yaml)
        custom_mappings = {}
        try:
            from .device_mapping import load_custom_yaml_mappings
            custom_mappings = load_custom_yaml_mappings() or {}
        except Exception as e:
            _LOGGER.debug("No custom mappings found or error loading: %s", e)
        
        if 'temperature_setpoint_mappings' in custom_mappings:
            sensor_id = custom_mappings['temperature_setpoint_mappings'].get(periph_id, '')
            if sensor_id:
                self._linked_temperature_sensor = sensor_id
                _LOGGER.info(
                    "🔗 Climate entity %s (%s) linked to temperature sensor %s (from custom config)",
                    self._attr_name, periph_id, sensor_id
                )
        elif 'temperature_setpoint_mappings' in yaml_config:
            # Fallback to device_mapping.yaml (for backward compatibility)
            sensor_id = yaml_config['temperature_setpoint_mappings'].get(periph_id, '')
            if sensor_id:
                self._linked_temperature_sensor = sensor_id
                _LOGGER.info(
                    "🔗 Climate entity %s (%s) linked to temperature sensor %s (from device mapping)",
                    self._attr_name, periph_id, sensor_id
                )

        _LOGGER.debug(
            "Initializing climate entity for %s (%s)", self._attr_name, periph_id
        )
        self._update_climate_state()
        self._update_current_temperature()

    @property
    def extra_state_attributes(self):
        """Return device-specific state attributes for monitoring and diagnostics."""
        attrs = {}
        
        try:
            periph_data = self._get_periph_data()
            if periph_data:
                # Basic device information
                attrs["usage_id"] = periph_data.get("usage_id", "unknown")
                attrs["device_type"] = periph_data.get("usage_name", "unknown")
                attrs["last_value"] = periph_data.get("last_value", "unknown")
                attrs["last_updated"] = periph_data.get("last_updated", "unknown")
                
                # Temperature range information
                attrs["temperature_range"] = f"{self._attr_min_temp}°C - {self._attr_max_temp}°C"
                attrs["temperature_step"] = self._attr_target_temperature_step
                
                # Device health and status
                attrs["device_health"] = self._get_device_health()
                attrs["connection_status"] = self._get_connection_status()
                
                # Climate-specific attributes
                usage_id = periph_data.get("usage_id", "")
                if usage_id == "15":
                    attrs["climate_type"] = "temperature_setpoint"
                    attrs["control_method"] = "direct_temperature"
                elif usage_id in ["19", "20", "38"]:
                    attrs["climate_type"] = "fil_pilote"
                    attrs["control_method"] = "mode_mapping"
                    attrs["supported_modes"] = "Confort, Eco, Hors Gel, Arret"
                
                # Available values for troubleshooting
                if "values" in periph_data and len(periph_data["values"]) > 0:
                    attrs["available_values_count"] = len(periph_data["values"])
                    # Show first few values as examples
                    example_values = [v.get("value", "") for v in periph_data["values"][:3]]
                    attrs["example_values"] = ", ".join(example_values)
                
                # Temperature sensor mapping information
                if self._linked_temperature_sensor:
                    attrs["linked_temperature_sensor"] = self._linked_temperature_sensor
                    if self._attr_current_temperature is not None:
                        attrs["current_temperature"] = f"{self._attr_current_temperature}°C"
                
        except Exception as e:
            _LOGGER.debug("Failed to generate extra state attributes: %s", e)
            attrs["error"] = "Failed to generate attributes"
        
        return attrs

    def _get_device_health(self):
        """Assess device health and return status."""
        try:
            periph_data = self._get_periph_data()
            if not periph_data:
                return "unavailable"
            
            last_value = periph_data.get("last_value", "")
            last_updated = periph_data.get("last_updated")
            
            if not last_value or last_value == "":
                return "no_data"
            
            if last_updated:
                try:
                    last_updated_dt = datetime.fromisoformat(last_updated)
                    time_since_update = (datetime.now() - last_updated_dt).total_seconds()
                    
                    if time_since_update > 3600:  # 1 hour
                        return "stale_data"
                    elif time_since_update > 1800:  # 30 minutes
                        return "delayed_update"
                except:
                    pass
            
            # Check if temperature is within expected range
            if (self._attr_target_temperature < self._attr_min_temp or
                self._attr_target_temperature > self._attr_max_temp):
                return "invalid_temperature"
            
            return "healthy"
            
        except Exception as e:
            _LOGGER.debug("Failed to assess device health: %s", e)
            return "unknown"

    def _get_connection_status(self):
        """Assess connection status to eedomus API."""
        try:
            # Check if we have recent data
            periph_data = self._get_periph_data()
            if not periph_data:
                return "disconnected"
            
            last_updated = periph_data.get("last_updated")
            if last_updated:
                try:
                    last_updated_dt = datetime.fromisoformat(last_updated)
                    time_since_update = (datetime.now() - last_updated_dt).total_seconds()
                    
                    if time_since_update < 60:
                        return "real_time"
                    elif time_since_update < 300:
                        return "recent"
                    elif time_since_update < 1800:
                        return "normal"
                    else:
                        return "delayed"
                except:
                    return "unknown_timestamp"
            
            return "no_timestamp"
            
        except Exception as e:
            _LOGGER.debug("Failed to assess connection status: %s", e)
            return "error"

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

    def _update_current_temperature(self):
        """Update current temperature from linked sensor or child devices."""
        if not self._linked_temperature_sensor:
            # No linked sensor, try to find temperature from child devices
            all_peripherals = self.coordinator.get_all_peripherals()
            for child_periph_id, child_periph in all_peripherals.items():
                if child_periph.get("parent_periph_id") == self._periph_id:
                    if child_periph.get("usage_id") == "7":  # Temperature sensor
                        child_value = child_periph.get("last_value", "")
                        if (
                            child_value
                            and child_value.replace(".", "").replace("-", "").isdigit()
                        ):
                            self._attr_current_temperature = float(child_value)
                            _LOGGER.debug(
                                "🌡️ Updated current temperature from child sensor %s: %.1f°C",
                                child_periph_id, self._attr_current_temperature
                            )
                            return
        else:
            # Get temperature from linked sensor
            sensor_data = self.coordinator.data.get(self._linked_temperature_sensor)
            if sensor_data and "last_value" in sensor_data:
                try:
                    temp_value = float(sensor_data["last_value"])
                    self._attr_current_temperature = temp_value
                    _LOGGER.debug(
                        "🌡️ Updated current temperature from linked sensor %s: %.1f°C",
                        self._linked_temperature_sensor, self._attr_current_temperature
                    )
                    return
                except (ValueError, TypeError) as e:
                    _LOGGER.warning(
                        "⚠️ Failed to parse temperature from linked sensor %s: %s",
                        self._linked_temperature_sensor, e
                    )

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
                # For eedomus, we should always use integers for temperature setpoints
                # First try exact match with integer
                temp_int = int(round(temperature))  # Always use integer
                temp_str = str(temp_int)
                if temp_str in acceptable_values:
                    eedomus_value = acceptable_values[temp_str]
                else:
                    # Try to find the closest integer value
                    numeric_values = []
                    for val in acceptable_values.values():
                        try:
                            numeric_values.append(int(float(val)))
                        except ValueError:
                            pass

                    if numeric_values:
                        closest_value = min(
                            numeric_values, key=lambda x: abs(x - temperature)
                        )
                        eedomus_value = str(int(closest_value))  # Always use integer

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

            try:
                result = await self.coordinator.async_set_periph_value(
                    self._periph_id, str(eedomus_value)
                )

                if result.get("success", 0) == 1:
                    _LOGGER.info(
                        "✅ Successfully set temperature for %s to %.1f°C",
                        self._attr_name,
                        temperature,
                    )
                    # Update local state to reflect the change immediately
                    self._attr_target_temperature = temperature
                    self.async_write_ha_state()
                    
                    # Force refresh to ensure coordinator has latest data
                    await self.coordinator.async_request_refresh()
                    
                else:
                    error_msg = result.get("error", "Unknown error")
                    error_code = result.get("error_code", "unknown")
                    _LOGGER.error(
                        "❌ Failed to set temperature for %s: %s (code: %s)",
                        self._attr_name,
                        error_msg,
                        error_code,
                    )
                    raise ValueError(f"Failed to set temperature: {error_msg}")
                    
            except Exception as err:
                _LOGGER.error(
                    "❌ Exception setting temperature for %s to %.1f°C: %s",
                    self._attr_name,
                    temperature,
                    str(err),
                )
                # Provide specific guidance for common errors
                if "connection" in str(err).lower():
                    _LOGGER.error(
                        "💡 Check eedomus API connection and network connectivity"
                    )
                elif "timeout" in str(err).lower():
                    _LOGGER.error(
                        "💡 API request timed out - check eedomus box responsiveness"
                    )
                elif "value refused" in str(err).lower() or "error_code" in str(err).lower():
                    _LOGGER.error(
                        "💡 Temperature value may be outside device's acceptable range"
                    )
                    _LOGGER.error(
                        "💡 Check device configuration in eedomus for valid temperature values"
                    )
                raise
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
                for heat_variant in ["on", "heat", "chauffage", "marche", "1", "reprendre", "resume"]:
                    if heat_variant in acceptable_values:
                        eedomus_value = acceptable_values[heat_variant]
                        break
            elif hvac_mode == HVACMode.OFF:
                # Try different variations for off (including French variants)
                for off_variant in ["off", "arrêt", "0", "stop", "désactiver", "pause"]:
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

            result = await self.coordinator.async_set_periph_value(
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
