"""The eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceResponse, callback
from homeassistant.helpers import aiohttp_client
from homeassistant.const import Platform
from .const import (
    DOMAIN, PLATFORMS, COORDINATOR, CONF_ENABLE_HISTORY, 
    CLASS_MAPPING, CONF_API_HOST, DEFAULT_SCAN_INTERVAL, 
    CONF_SCAN_INTERVAL, CONF_ENABLE_API_EEDOMUS, CONF_ENABLE_API_PROXY,
    DEFAULT_CONF_ENABLE_API_EEDOMUS, DEFAULT_CONF_ENABLE_API_PROXY,
    CONF_API_PROXY_DISABLE_SECURITY, DEFAULT_API_PROXY_DISABLE_SECURITY
)
from .coordinator import EedomusDataUpdateCoordinator
from .eedomus_client import EedomusClient
from .sensor import EedomusSensor, EedomusHistoryProgressSensor




from .webhook import EedomusWebhookView
from .api_proxy import EedomusApiProxyView

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eedomus from a config entry."""
    _LOGGER.info("🚀 Starting eedomus integration setup - Version 0.9.4")
    _LOGGER.debug("Setting up eedomus integration with entry_id: %s", entry.entry_id)

    # Check which modes are enabled
    api_eedomus_enabled = entry.data.get(CONF_ENABLE_API_EEDOMUS, DEFAULT_CONF_ENABLE_API_EEDOMUS)
    api_proxy_enabled = entry.data.get(CONF_ENABLE_API_PROXY, DEFAULT_CONF_ENABLE_API_PROXY)
    
    _LOGGER.info("Starting eedomus integration - API Eedomus: %s, API Proxy: %s", 
                api_eedomus_enabled, api_proxy_enabled)

    # Create session and client
    session = aiohttp_client.async_get_clientsession(hass)
    
    # Initialize coordinator only if API Eedomus mode is enabled
    coordinator = None
    client = None
    
    if api_eedomus_enabled:
        try:
            client = EedomusClient(session=session, config_entry=entry)
        except Exception as err:
            _LOGGER.error("Failed to create eedomus client: %s", err)
            return False

        # Initialize coordinator with custom scan interval
        scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        coordinator = EedomusDataUpdateCoordinator(hass, client, scan_interval)

        # Perform initial full refresh only for API Eedomus mode
        try:
            await coordinator.async_config_entry_first_refresh()
            _LOGGER.info("API Eedomus mode initialized successfully")
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to fetch data from eedomus: %s", err)
            return False
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout while fetching data from eedomus")
            return False
    
    if api_proxy_enabled:
        _LOGGER.info("API Proxy mode enabled - setting up webhook endpoints")
        # For proxy mode, we need a client for webhook registration even if API Eedomus is disabled
        if not client:
            try:
                client = EedomusClient(session=session, config_entry=entry)
                _LOGGER.info("Proxy mode client created successfully")
            except Exception as err:
                _LOGGER.warning("Failed to create client for proxy mode: %s", err)
                # Proxy mode can work without a full client, but we need basic connectivity
    
    # If neither mode is enabled, this shouldn't happen due to validation, but handle it anyway
    if not api_eedomus_enabled and not api_proxy_enabled:
        _LOGGER.error("No connection mode enabled - this should not happen")
        return False

    # Create entities based on supported classes (only if API Eedomus mode is enabled)
    # NOTE: History sensor creation is temporarily disabled due to refactoring
    # This will be addressed in a separate branch: feature/history-refactor
    if api_eedomus_enabled and entry.data.get(CONF_ENABLE_HISTORY, False):
        _LOGGER.warning("History sensor creation is temporarily disabled - will be implemented in feature/history-refactor branch")
        # entities = []
        # for device_id, device_data in coordinator.data.items():
        #     # Add history sensor if enabled
        #     _LOGGER.info("Retrieve history enabled for device=%s", device_id)
        #     entities.append(EedomusHistoryProgressSensor(coordinator, {
        #         "periph_id": device_id,
        #         "name": device_data["name"],
        #     }))
        #
        # # Add entities to Home Assistant
        # if entities:
        #     async_add_entities(entities, True)


    # Stockage sécurisé
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    
    # Store coordinator only if it was initialized
    entry_data = {}
    if coordinator:
        entry_data[COORDINATOR] = coordinator
        _LOGGER.debug("Coordinator stored successfully for entry_id: %s", entry.entry_id)
    else:
        _LOGGER.info("No coordinator stored - running in proxy mode only")
    
    hass.data[DOMAIN][entry.entry_id] = entry_data

    # Enregistrement du webhook et service (always register webhooks)
    disable_security = entry.data.get(CONF_API_PROXY_DISABLE_SECURITY, DEFAULT_API_PROXY_DISABLE_SECURITY)
    
    # Log security warning if disabled
    if disable_security:
        _LOGGER.warning("⚠️ SECURITY WARNING: API Proxy IP validation has been disabled for debugging purposes.")
        _LOGGER.warning("   This exposes your webhook endpoints to potential abuse from any IP address.")
        _LOGGER.warning("   Only use this setting temporarily for debugging in secure environments.")
    
    hass.http.register_view(EedomusWebhookView(
        entry.entry_id, 
        allowed_ips=[entry.data.get(CONF_API_HOST)], 
        disable_security=disable_security
    ))
    hass.http.register_view(EedomusApiProxyView(
        entry.entry_id, 
        allowed_ips=[entry.data.get(CONF_API_HOST)], 
        disable_security=disable_security
    ))
    
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
    
    # Define update listener first
    async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Handle options update."""
        _LOGGER.info("🔧 Eedomus configuration options updated - reloading integration")
        await hass.config_entries.async_reload(entry.entry_id)
    
    # Set up options flow handler
    entry.async_on_unload(entry.add_update_listener(update_listener))
    
    _LOGGER.debug("eedomus integration setup completed")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id)
            _LOGGER.debug("eedomus integration unloaded")
        else:
            _LOGGER.warning("eedomus integration entry not found during unload")
    return unload_ok

