"""Eedomus integration services."""

from __future__ import annotations

import logging
from datetime import datetime
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

    async def handle_import_history(call: ServiceCall) -> dict:
        """Handle history import service call."""
        device_id = call.data.get("device_id")
        start_time = call.data.get("start_time")
        end_time = call.data.get("end_time")
        batch_size = call.data.get("batch_size", 200)
        
        _LOGGER.info("📥 History import requested for device %s (from %s to %s)", 
                    device_id, start_time, end_time)
        
        try:
            if not coordinator:
                _LOGGER.error("❌ No coordinator available - cannot import history")
                raise ValueError("Coordinator not available")
            
            # Validate parameters
            if not device_id:
                raise ValueError("device_id is required")
            
            # Convert timestamps if needed
            try:
                if start_time:
                    start_time = datetime.fromisoformat(start_time)
                if end_time:
                    end_time = datetime.fromisoformat(end_time)
            except ValueError as err:
                raise ValueError(f"Invalid timestamp format: {err}")
            
            # Fetch history data from eedomus
            _LOGGER.info("🔍 Fetching history data from eedomus API...")
            chunk = await coordinator.client.get_device_history(
                device_id,
                start_timestamp=int(start_time.timestamp()) if start_time else 0,
                end_timestamp=int(end_time.timestamp()) if end_time else None
            )
            
            if not chunk:
                _LOGGER.warning("⚠️ No history data received from eedomus API")
                return {"status": "no_data", "device_id": device_id, "imported": 0}
            
            _LOGGER.info("✅ Retrieved %d history data points from eedomus", len(chunk))
            
            # Import data using the optimized method
            _LOGGER.info("💾 Importing data into Home Assistant...")
            await coordinator.async_import_history_chunk(device_id, chunk)
            
            # Update progress
            if device_id not in coordinator._history_progress:
                coordinator._history_progress[device_id] = {}
            
            coordinator._history_progress[device_id]["last_timestamp"] = max(
                int(datetime.fromisoformat(entry["timestamp"]).timestamp())
                for entry in chunk
            )
            coordinator._history_progress[device_id]["completed"] = True
            
            await coordinator._save_history_progress()
            
            _LOGGER.info("✅ Successfully imported history for device %s", device_id)
            return {"status": "success", "device_id": device_id, "imported": len(chunk)}
            
        except Exception as err:
            _LOGGER.error("❌ Failed to import history for device %s: %s", device_id, err)
            raise err

    # Register services
    try:
        hass.services.async_register("eedomus", "refresh", handle_refresh)
        hass.services.async_register("eedomus", "set_value", handle_set_value)
        hass.services.async_register("eedomus", "reload", handle_reload)
        hass.services.async_register("eedomus", "import_history", handle_import_history)
        _LOGGER.info("🛠️  Eedomus services registered: refresh, set_value, reload, import_history")
    except Exception as err:
        _LOGGER.error("❌ Failed to register eedomus services: %s", err)
        raise err
