"""The eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceResponse, callback
from homeassistant.helpers import aiohttp_client
from homeassistant.const import Platform
from .const import DOMAIN, PLATFORMS, COORDINATOR, CONF_ENABLE_HISTORY, CLASS_MAPPING
from .coordinator import EedomusDataUpdateCoordinator
from .eedomus_client import EedomusClient
from .sensor import EedomusSensor, EedomusHistoryProgressSensor


_LOGGER = logging.getLogger(__name__)

async def async_setup_entry_old(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eedomus from a config entry."""
    _LOGGER.debug("Setting up eedomus integration")

    # Create session and client
    session = aiohttp_client.async_get_clientsession(hass)
    client = EedomusClient(
        session=session,
        config_entry=entry,
    )

    # Initialize coordinator
    coordinator = EedomusDataUpdateCoordinator(hass, client)

    # Perform initial full refresh
    await coordinator.async_config_entry_first_refresh()

    entities = []
    for device in coordinator.data:
        entities.append(EedomusSensor(coordinator, device))
        if entry.data.get(CONF_ENABLE_HISTORY):
            _LOGGER.info("Retrieve history enabled device=%s", device)
            _LOGGER.debug("Retrieve history enabled device.data=%s", coordinator.data[device])
            entities.append(EedomusHistoryProgressSensor(coordinator, {
                "periph_id": device,
                "name": coordinator.data[device]["name"],
            }))

        # Store coordinator for later use
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eedomus from a config entry."""
    _LOGGER.debug("Setting up eedomus integration")

    # Create session and client
    session = aiohttp_client.async_get_clientsession(hass)
    try:
        client = EedomusClient(session=session, config_entry=entry)
    except Exception as err:
        _LOGGER.error("Failed to create eedomus client: %s", err)
        return False

    # Initialize coordinator
    coordinator = EedomusDataUpdateCoordinator(hass, client)

    # Perform initial full refresh
    try:
        await coordinator.async_config_entry_first_refresh()
    except aiohttp.ClientError as err:
        _LOGGER.error("Failed to fetch data from eedomus: %s", err)
        return False
    except asyncio.TimeoutError:
        _LOGGER.error("Timeout while fetching data from eedomus")
        return False

    # Create entities based on supported classes
    if entry.data.get(CONF_ENABLE_HISTORY, False):
        entities = []
        for device_id, device_data in coordinator.data.items():
            # Add history sensor if enabled
            _LOGGER.info("Retrieve history enabled for device=%s", device_id)
            entities.append(EedomusHistoryProgressSensor(coordinator, {
                "periph_id": device_id,
                "name": device_data["name"],
            }))

            # Add entities to Home Assistant
        if entities:
            async_add_entities(entities, True)

    # Store coordinator and client for later use
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

    
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
