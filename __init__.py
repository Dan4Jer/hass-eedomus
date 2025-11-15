"""The eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceResponse, callback
from homeassistant.helpers import aiohttp_client
from .const import DOMAIN, PLATFORMS, COORDINATOR
from .coordinator import EedomusDataUpdateCoordinator
from .eedomus_client import EedomusClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eedomus from a config entry."""
    _LOGGER.debug("Setting up eedomus integration")

    # Create session and client
    session = aiohttp_client.async_get_clientsession(hass)
    client = EedomusClient(
        session=session,
        api_user=entry.data["api_user"],
        api_secret=entry.data["api_secret"],
        api_host=entry.data["api_host"],
    )

    # Initialize coordinator
    coordinator = EedomusDataUpdateCoordinator(hass, client)

    # Perform initial full refresh
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator for later use
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register refresh service
    @callback
    def refresh_service(call: ServiceResponse) -> None:
        """Handle service call to refresh data."""
        hass.async_create_task(coordinator.request_full_refresh())
        call.return_response()

    hass.services.async_register(DOMAIN, "refresh", refresh_service)

    _LOGGER.debug("eedomus integration setup completed")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("eedomus integration unloaded")
    return unload_ok
