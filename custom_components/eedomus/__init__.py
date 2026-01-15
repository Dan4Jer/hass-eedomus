"""The eedomus integration."""

from __future__ import annotations
from datetime import timedelta

import json
import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceResponse, callback
from homeassistant.helpers import aiohttp_client

from .api_proxy import EedomusApiProxyView
from .webhook import EedomusWebhookView
from .const import (
    CLASS_MAPPING,
    CONF_API_HOST,
    CONF_API_PROXY_DISABLE_SECURITY,

    CONF_ENABLE_API_EEDOMUS,
    CONF_ENABLE_API_PROXY,
    CONF_ENABLE_HISTORY,
    CONF_ENABLE_WEBHOOK,
    CONF_REMOVE_ENTITIES,
    CONF_SCAN_INTERVAL,
    COORDINATOR,
    DEFAULT_API_PROXY_DISABLE_SECURITY,
    DEFAULT_CONF_ENABLE_API_EEDOMUS,
    DEFAULT_CONF_ENABLE_API_PROXY,
    DEFAULT_ENABLE_WEBHOOK,
    DEFAULT_REMOVE_ENTITIES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import EedomusDataUpdateCoordinator
from .eedomus_client import EedomusClient
from .sensor import EedomusHistoryProgressSensor, EedomusSensor
from .webhook import EedomusWebhookView

# Initialize logger first
_LOGGER = logging.getLogger(__name__)

# Import options flow to ensure it's registered
try:
    from .options_flow import EedomusOptionsFlowHandler
    _LOGGER.debug("Options flow handler loaded successfully")
except ImportError as e:
    _LOGGER.warning("Failed to load options flow handler: %s", e)
except Exception as e:
    _LOGGER.warning("Unexpected error loading options flow handler: %s", e)

# Get version from manifest.json
try:
    manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
    with open(manifest_path, "r") as f:
        manifest_data = json.load(f)
        VERSION = manifest_data.get("version", "unknown")
except Exception as e:
    VERSION = "unknown"
    _LOGGER.warning("Failed to read version from manifest.json: %s", e)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eedomus from a config entry."""
    _LOGGER.info("🚀 Starting eedomus integration setup - Version %s", VERSION)
    _LOGGER.debug("Setting up eedomus integration with entry_id: %s", entry.entry_id)

    # Check which modes are enabled
    api_eedomus_enabled = entry.data.get(
        CONF_ENABLE_API_EEDOMUS, DEFAULT_CONF_ENABLE_API_EEDOMUS
    )
    api_proxy_enabled = entry.data.get(
        CONF_ENABLE_API_PROXY, DEFAULT_CONF_ENABLE_API_PROXY
    )

    _LOGGER.info(
        "Starting eedomus integration - API Eedomus: %s, API Proxy: %s",
        api_eedomus_enabled,
        api_proxy_enabled,
    )

    _LOGGER.debug("Setting up eedomus integration before entry.update_listener: %s", entry.update_listeners)
    # Set up options flow handler
    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    _LOGGER.debug("Setting up eedomus integration after entry.update_listener: %s", entry.update_listeners)

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
        # Check options first, then data, then default
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        
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


    # If neither mode is enabled, this shouldn't happen due to validation, but handle it anyway
    if not api_eedomus_enabled and not api_proxy_enabled:
        _LOGGER.error("No connection mode enabled - this should not happen")
        return False

    # Create entities based on supported classes (only if API Eedomus mode is enabled)
    # NOTE: History sensor creation is temporarily disabled due to refactoring
    # This will be addressed in a separate branch: feature/history-refactor
    if api_eedomus_enabled and entry.data.get(CONF_ENABLE_HISTORY, False):
        _LOGGER.warning(
            "History sensor creation is temporarily disabled - will be implemented in feature/history-refactor branch"
        )
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


    # Store entry data
    if coordinator:
        entry_data[COORDINATOR] = coordinator
        _LOGGER.debug(
            "Coordinator stored successfully for entry_id: %s", entry.entry_id
        )
    else:
        _LOGGER.info("No coordinator stored - running in proxy mode only")

    hass.data[DOMAIN][entry.entry_id] = entry_data

    # Enregistrement du webhook et service (always register webhooks)
    disable_security = entry.data.get(
        CONF_API_PROXY_DISABLE_SECURITY, DEFAULT_API_PROXY_DISABLE_SECURITY
    )

    # Log security warning if disabled
    if disable_security:
        _LOGGER.warning(
            "⚠️ SECURITY WARNING: API Proxy IP validation has been disabled for debugging purposes."
        )
        _LOGGER.warning(
            "   This exposes your webhook endpoints to potential abuse from any IP address."
        )
        _LOGGER.warning(
            "   Only use this setting temporarily for debugging in secure environments."
        )


    # Check if webhook is enabled
    webhook_enabled = entry.options.get(
        CONF_ENABLE_WEBHOOK,
        entry.data.get(CONF_ENABLE_WEBHOOK, DEFAULT_ENABLE_WEBHOOK)
    )

    # Define allowed_ips for webhook
    allowed_ips = [entry.data.get(CONF_API_HOST)]

    # Setup webhook if enabled
    if webhook_enabled:
        _LOGGER.info("Webhook mode enabled - setting up webhook endpoints")
        # Register webhook handler
        hass.http.register_view(
            EedomusWebhookView(
                entry.entry_id,
                allowed_ips=[entry.data.get(CONF_API_HOST)],
                disable_security=disable_security,
            )
        )
    else:
        _LOGGER.info("Webhook mode disabled")

    if api_proxy_enabled:
        _LOGGER.info("API Proxy mode enabled - setting up webhook endpoints")
        hass.http.register_view(
            EedomusApiProxyView(
                entry.entry_id,
                allowed_ips=[entry.data.get(CONF_API_HOST)],
                disable_security=disable_security,
            )
        )
    else:
        _LOGGER.info("Api Proxy mode disabled")


    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.debug("eedomus integration setup completed")
    return True

# Define update listener first
async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.info("🔧 Eedomus configuration options updated - reloading integration")
    
    # Update coordinator scan interval if it exists and scan_interval option changed
    if entry.entry_id in hass.data.get(DOMAIN, {}) and COORDINATOR in hass.data[DOMAIN][entry.entry_id]:
        coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
        new_scan_interval = entry.options.get(CONF_SCAN_INTERVAL)
        if new_scan_interval and hasattr(coordinator, 'update_interval'):
            coordinator.update_interval = timedelta(seconds=new_scan_interval)
            _LOGGER.info(f"🔄 Updated scan interval to {new_scan_interval} seconds")
    
    await hass.config_entries.async_reload(entry.entry_id)



async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id)
            _LOGGER.debug("eedomus integration unloaded")
        else:
            _LOGGER.warning("eedomus integration entry not found during unload")
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry."""
    # Check if the remove_entities option is set
    remove_entities = entry.options.get(CONF_REMOVE_ENTITIES, DEFAULT_REMOVE_ENTITIES)

    if remove_entities:
        _LOGGER.info("Removing all entities associated with eedomus integration")
        
        # Get all entities from the entity registry
        entity_registry = await hass.helpers.entity_registry.async_get(hass)

        # Find all entities that belong to this integration
        entities_to_remove = []
        for entity_entry in entity_registry.entities.values():
            if entity_entry.platform == DOMAIN:
                entities_to_remove.append(entity_entry.entity_id)

        # Remove the entities
        for entity_id in entities_to_remove:
            _LOGGER.info(f"Removing entity: {entity_id}")
            entity_registry.async_remove(entity_id)

        _LOGGER.info(f"Removed {len(entities_to_remove)} entities")
    else:
        _LOGGER.info("Remove entities option is disabled, skipping entity removal")

    # Remove the config entry
    _LOGGER.info("Removing eedomus integration config entry")
