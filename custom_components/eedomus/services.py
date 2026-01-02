"""Eedomus integration services."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_entry_flow

_LOGGER = logging.getLogger(__name__)


async def async_setup_services(hass: HomeAssistant, coordinator) -> None:
    """Set up eedomus services."""

    async def handle_refresh(call: ServiceCall) -> None:
        """Handle refresh service call."""
        _LOGGER.info("🔄 Manual refresh requested via service call")
        try:
            await coordinator.async_request_refresh()
            _LOGGER.info("✅ Eedomus data refreshed successfully")
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
            # Send the command to eedomus
            result = await coordinator.client.async_set("set", device_id, value)

            if result.get("success") == 1:
                _LOGGER.info("✅ Successfully set value for device %s", device_id)
                # Force refresh to get updated state
                await coordinator.async_request_refresh()
            else:
                _LOGGER.warning("⚠️ Set value returned non-success: %s", result)

        except Exception as err:
            _LOGGER.error("❌ Failed to set value for device %s: %s", device_id, err)
            # Try PHP fallback if enabled and available
            if coordinator.client.php_fallback_enabled:
                _LOGGER.info("🔄 Trying PHP fallback for device %s", device_id)
                fallback_result = await coordinator.client.php_fallback_set_value(
                    device_id, value
                )
                if fallback_result.get("success") == 1:
                    _LOGGER.info("✅ PHP fallback succeeded for device %s", device_id)
                    await coordinator.async_request_refresh()
                    return
                else:
                    _LOGGER.warning(
                        "⚠️ PHP fallback failed: %s",
                        fallback_result.get("error", "Unknown error"),
                    )
            raise err

    # Register services
    hass.services.async_register("eedomus", "refresh", handle_refresh)
    hass.services.async_register("eedomus", "set_value", handle_set_value)

    _LOGGER.info("🛠️  Eedomus services registered: refresh, set_value")
