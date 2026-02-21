"""Eedomus integration services."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_entry_flow

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_services(hass: HomeAssistant, coordinator) -> None:
    """Set up eedomus services."""

    async def handle_refresh(call: ServiceCall) -> None:
        """Handle refresh service call."""
        _LOGGER.info("🔄 Manual refresh requested via service call")
        try:
            if coordinator:
                await coordinator.async_request_refresh()
                _LOGGER.info("✅ Eedomus data refreshed successfully")
            else:
                _LOGGER.warning("⚠️  No coordinator available for refresh")
        except Exception as err:
            _LOGGER.error("❌ Failed to refresh eedomus data: %s", err)
            raise err

    async def handle_set_value(call: ServiceCall) -> None:
        """Handle set_value service call."""
        device_id = call.data.get("device_id")
        value = call.data.get("value")

        if not device_id or not value:
            _LOGGER.error("❌ Missing required parameters: device_id and value")
            raise ValueError("device_id and value are required")

        _LOGGER.info("📤 Setting value %s for device %s via service", value, device_id)

        try:
            if not coordinator:
                _LOGGER.error("❌ No coordinator available - cannot set value")
                raise ValueError("Coordinator not available")
            
            # Send the command to eedomus using the coordinator's method
            # This ensures proper fallback and retry logic is applied
            result = await coordinator.async_set_periph_value(device_id, value)

            if result.get("success") == 1:
                _LOGGER.info("✅ Successfully set value for device %s", device_id)
                # Force refresh to get updated state
                await coordinator.async_request_refresh()
            else:
                _LOGGER.warning("⚠️ Set value returned non-success: %s", result)
                raise ValueError(f"Failed to set value: {result.get('error', 'Unknown error')}")

        except Exception as err:
            _LOGGER.error("❌ Failed to set value for device %s: %s", device_id, err)
            raise err

    async def handle_reload(call: ServiceCall) -> None:
        """Handle reload service call."""
        _LOGGER.info("🔄 Reload requested via service call")
        try:
            if not coordinator:
                _LOGGER.error("❌ No coordinator available - cannot reload")
                raise ValueError("Coordinator not available")
            
            # Get the config entry
            config_entry = None
            for entry in hass.config_entries.async_entries(DOMAIN):
                if entry.entry_id == coordinator.config_entry.entry_id:
                    config_entry = entry
                    break
            
            if config_entry:
                # Reload the config entry
                await hass.config_entries.async_reload(config_entry.entry_id)
                _LOGGER.info("✅ Eedomus integration reloaded successfully")
            else:
                _LOGGER.error("❌ Config entry not found")
                raise ValueError("Config entry not found")
        except Exception as err:
            _LOGGER.error("❌ Failed to reload eedomus integration: %s", err)
            raise err

    async def handle_set_climate_temperature(call: ServiceCall) -> None:
        """Handle set_climate_temperature service call with validation."""
        device_id = call.data.get("device_id")
        temperature = call.data.get("temperature")
        
        # Validate required parameters
        if not device_id:
            _LOGGER.error("❌ Missing required parameter: device_id")
            raise ValueError("device_id is required")
        
        if temperature is None:
            _LOGGER.error("❌ Missing required parameter: temperature")
            raise ValueError("temperature is required")
        
        # Validate temperature type and range
        try:
            temperature_float = float(temperature)
            if temperature_float < 7.0 or temperature_float > 30.0:
                _LOGGER.error("❌ Temperature %.1f°C out of valid range (7.0°C-30.0°C)", temperature_float)
                raise ValueError(f"Temperature must be between 7.0°C and 30.0°C, got {temperature_float}°C")
            
            # Round to nearest 0.5°C as that's the typical eedomus precision
            rounded_temp = round(temperature_float * 2) / 2
            _LOGGER.info("🌡️  Setting climate temperature to %.1f°C for device %s", rounded_temp, device_id)
            
        except ValueError as ve:
            if "could not convert string to float" in str(ve):
                _LOGGER.error("❌ Invalid temperature format: %s", temperature)
                raise ValueError(f"Temperature must be a valid number, got {temperature}")
            raise
        
        # Validate coordinator and find climate entity
        if not coordinator:
            _LOGGER.error("❌ No coordinator available - cannot set climate temperature")
            raise ValueError("Coordinator not available")
        
        # Check if device exists and is a climate entity
        periph_data = coordinator.data.get(device_id)
        if not periph_data:
            _LOGGER.error("❌ Device %s not found in coordinator data", device_id)
            raise ValueError(f"Device {device_id} not found")
        
        ha_entity = periph_data.get("ha_entity")
        if ha_entity != "climate":
            _LOGGER.error("❌ Device %s is not a climate entity (found: %s)", device_id, ha_entity)
            raise ValueError(f"Device {device_id} is not a climate entity")
        
        # Find the climate entity and set temperature
        climate_entity = None
        if hasattr(hass, 'data') and DOMAIN in hass.data:
            for entry_data in hass.data[DOMAIN].values():
                if 'entities' in entry_data:
                    for entity in entry_data['entities']:
                        if hasattr(entity, '_periph_id') and entity._periph_id == device_id:
                            climate_entity = entity
                            break
                if climate_entity:
                    break
        
        if not climate_entity:
            _LOGGER.error("❌ No climate entity found for device %s", device_id)
            raise ValueError(f"No climate entity found for device {device_id}")
        
        # Set temperature through climate entity
        try:
            await climate_entity.async_set_temperature(temperature=rounded_temp)
            _LOGGER.info("✅ Successfully set climate temperature to %.1f°C for %s", rounded_temp, device_id)
            
            # Force refresh to get updated state
            await coordinator.async_request_refresh()
            
            return {
                "success": True,
                "device_id": device_id,
                "temperature": rounded_temp,
                "message": f"Temperature set to {rounded_temp}°C"
            }
            
        except Exception as err:
            _LOGGER.error("❌ Failed to set climate temperature for %s: %s", device_id, err)
            raise ValueError(f"Failed to set temperature: {str(err)}")

    # Register services
    try:
        hass.services.async_register("eedomus", "refresh", handle_refresh)
        hass.services.async_register("eedomus", "set_value", handle_set_value)
        hass.services.async_register("eedomus", "reload", handle_reload)
        hass.services.async_register("eedomus", "set_climate_temperature", handle_set_climate_temperature)
        _LOGGER.info("🛠️  Eedomus services registered: refresh, set_value, reload, set_climate_temperature")
    except Exception as err:
        _LOGGER.error("❌ Failed to register eedomus services: %s", err)
        raise err
