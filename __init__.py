"""The eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceResponse, callback
from homeassistant.helpers import aiohttp_client
from homeassistant.const import Platform
from .const import DOMAIN, PLATFORMS, COORDINATOR, CONF_ENABLE_HISTORY, CLASS_MAPPING, CONF_API_HOST
from .coordinator import EedomusDataUpdateCoordinator
from .eedomus_client import EedomusClient
from .sensor import EedomusSensor, EedomusHistoryProgressSensor




from .webhook import EedomusWebhookView
from .api_proxy import EedomusApiProxyView

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eedomus from a config entry."""
    _LOGGER.debug("Setting up eedomus integration with entry_id: %s", entry.entry_id)

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


    # Stockage sécurisé
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN][entry.entry_id] = {COORDINATOR: coordinator}
    _LOGGER.debug("Coordinator stored successfully for entry_id: %s", entry.entry_id)

    # Enregistrement du webhook et service
    hass.http.register_view(EedomusWebhookView(entry.entry_id, allowed_ips = [entry.data.get(CONF_API_HOST)]))
    hass.http.register_view(EedomusApiProxyView(entry.entry_id, allowed_ips = [entry.data.get(CONF_API_HOST)]))
    
#    async def refresh_service(_):
#        if entry.entry_id in hass.data[DOMAIN] and COORDINATOR in hass.data[DOMAIN][entry.entry_id]:
#            await hass.data[DOMAIN][entry.entry_id][COORDINATOR].request_full_refresh()
#        else:
#            _LOGGER.error("Coordinator not available for refresh")
#
#    hass.services.async_register(DOMAIN, "refresh", refresh_service)
#
                        
    #hass.data.setdefault("eedomus_entry_id", entry.entry_id) 

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("eedomus integration setup completed")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("eedomus integration unloaded")
    return unload_ok

