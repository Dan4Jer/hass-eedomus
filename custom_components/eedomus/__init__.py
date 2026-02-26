"""The eedomus integration."""

from __future__ import annotations
from datetime import timedelta

import asyncio
import json
import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import aiohttp_client
import aiohttp

from .api_proxy import EedomusApiProxyView
from .webhook import EedomusWebhookView
from .const import (

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
# Note: For HA 2026.02+, we use the modern frontend API (www/config_panel.js)
# The Lovelace card import is kept for backward compatibility but may fail in newer HA versions
from .sensor import EedomusHistoryProgressSensor, EedomusSensor
from .text_sensor import EedomusTextSensor
from .webhook import EedomusWebhookView

# Import service setup
from .services import async_setup_services

# Initialize logger first
_LOGGER = logging.getLogger(__name__)

# Import options flow to ensure it's registered
try:
    from .options_flow import EedomusOptionsFlow
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
    """Set up eedomus from a config entry.
    
    This function initializes the eedomus integration by creating the API client,
    setting up the data coordinator, registering services, and forwarding setup to platforms.
    """
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

        # Create main eedomus box device for proper device hierarchy
        try:
            from homeassistant.helpers.device_registry import async_get as async_get_device_registry
            device_registry = async_get_device_registry(hass)
            
            # Create the main eedomus box device
            box_device = device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, "eedomus_box_main")},
                name="Box eedomus",
                manufacturer="Eedomus",
                model="Eedomus Box",
                sw_version="Unknown",
            )
            _LOGGER.info("Created main eedomus box device: %s", box_device.id)
        except Exception as e:
            _LOGGER.warning("Failed to create main eedomus box device: %s", e)

        # Perform initial full refresh only for API Eedomus mode
        try:
            await coordinator.async_config_entry_first_refresh()
            _LOGGER.info("API Eedomus mode initialized successfully")
            
            # Display device mapping table after first successful refresh
            try:
                from .mapping_registry import print_mapping_table
                print_mapping_table()
            except Exception as e:
                _LOGGER.debug("Failed to display mapping table: %s", e)
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to fetch data from eedomus: %s", err)
            return False
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout while fetching data from eedomus")
            return False

        # Setup services after coordinator is initialized
        try:
            await async_setup_services(hass, coordinator)
            _LOGGER.info("✅ Eedomus services registered successfully")
        except Exception as err:
            _LOGGER.error("Failed to setup eedomus services: %s", err)


    # If neither mode is enabled, this shouldn't happen due to validation, but handle it anyway
    if not api_eedomus_enabled and not api_proxy_enabled:
        _LOGGER.error("No connection mode enabled - this should not happen")
        return False

    # Setup services even if coordinator is not created (for proxy-only mode)
    if not coordinator and api_proxy_enabled:
        try:
            await async_setup_services(hass, None)
            _LOGGER.info("✅ Eedomus services registered in proxy-only mode")
        except Exception as err:
            _LOGGER.error("Failed to setup eedomus services in proxy-only mode: %s", err)

    # Create entities based on supported classes (only if API Eedomus mode is enabled)
    # Setup history sensors if history feature is enabled
    if api_eedomus_enabled and entry.data.get(CONF_ENABLE_HISTORY, False):
        try:
            from .history_sensor import async_setup_history_sensors
            from homeassistant.helpers.device_registry import async_get as async_get_device_registry
            device_registry = async_get_device_registry(hass)
            await async_setup_history_sensors(hass, coordinator, device_registry)
            _LOGGER.info("✅ History sensors registered successfully")
        except Exception as err:
            _LOGGER.error("Failed to setup history sensors: %s", err)

    # Always setup refresh timing sensors (they're lightweight and useful for monitoring)
    try:
        from .refresh_timing_sensor import async_setup_refresh_timing_sensors
        from homeassistant.helpers.device_registry import async_get as async_get_device_registry
        device_registry = async_get_device_registry(hass)
        timing_sensors = await async_setup_refresh_timing_sensors(hass, coordinator, device_registry)
        
        # Note: Timing sensors will be registered with other sensors via PLATFORMS
        # No need for separate registration to avoid double setup
        if timing_sensors:
            _LOGGER.info("✅ Refresh timing sensors ready (will be registered with other sensors)")
            # Store timing sensors in coordinator for access by sensor setup
            if coordinator:
                coordinator._timing_sensors = timing_sensors
    except Exception as err:
        _LOGGER.error("Failed to setup refresh timing sensors: %s", err)


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
    disable_security = entry.options.get(
        CONF_API_PROXY_DISABLE_SECURITY,
        entry.data.get(CONF_API_PROXY_DISABLE_SECURITY, DEFAULT_API_PROXY_DISABLE_SECURITY)
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

    # Note: Configuration manager has been removed - using YAML-based configuration only
    # using the modern frontend.async_register_built_in_panel() method
    # This ensures compatibility with HA 2026.02+ and avoids double registration
    _LOGGER.info("Eedomus integration initialized successfully")
    _LOGGER.debug("eedomus integration setup completed")
    return True

# Define update listener first
async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update.
    
    This function is called when configuration options are updated through the options flow.
    It updates the coordinator scan interval and triggers a reload of the integration.
    """
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
    """Unload a config entry.
    
    This function cleans up the integration by unloading platforms and removing
    the entry data from the Home Assistant data store.
    """
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        if entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id)
            _LOGGER.debug("eedomus integration unloaded")
        else:
            _LOGGER.warning("eedomus integration entry not found during unload")
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove a config entry.
    
    This function handles the removal of a config entry, optionally removing all
    associated entities from the entity registry based on user configuration.
    """
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


# YAML Mapping Management Functions
async def async_load_mapping(hass, config_dir):
    """Load and merge device mappings from YAML files.
    
    This function loads default and custom device mappings from YAML files,
    merges them using a sophisticated algorithm, and validates the result.
    """
    import yaml
    from homeassistant.helpers import config_validation as cv
    from .const import YAML_MAPPING_SCHEMA, CONF_CUSTOM_DEVICES
    
    default_path = os.path.join(config_dir, "device_mapping.yaml")
    custom_path = os.path.join(config_dir, "custom_mapping.yaml")

    # Load default mapping using async executor to avoid blocking event loop
    default_mapping = {}
    try:
        default_path = os.path.join(os.path.dirname(__file__), "config", "device_mapping.yaml")
        default_mapping = await hass.async_add_executor_job(
            lambda: yaml.safe_load(open(default_path, "r", encoding="utf-8")) or {}
        )
        _LOGGER.debug("Loaded default mapping from %s", default_path)
    except FileNotFoundError:
        _LOGGER.warning("Default mapping file not found: %s", default_path)
    except yaml.YAMLError as e:
        _LOGGER.error("Error parsing default mapping YAML: %s", e)
        raise
    except Exception as e:
        _LOGGER.error("Unexpected error loading default mapping: %s", e)
        raise

    # Load custom mapping using async executor to avoid blocking event loop
    custom_mapping = {}
    try:
        custom_path = os.path.join(os.path.dirname(__file__), "config", "custom_mapping.yaml")
        custom_mapping = await hass.async_add_executor_job(
            lambda: yaml.safe_load(open(custom_path, "r", encoding="utf-8")) or {}
        )
        _LOGGER.debug("Loaded custom mapping from %s", custom_path)
    except FileNotFoundError:
        _LOGGER.debug("No custom mapping file found at %s - using defaults only", custom_path)
    except yaml.YAMLError as e:
        _LOGGER.error("Error parsing custom mapping YAML: %s", e)
        raise
    except Exception as e:
        _LOGGER.error("Unexpected error loading custom mapping: %s", e)
        raise

    # Merge mappings using sophisticated approach (same as load_and_merge_yaml_mappings)
    # This ensures proper handling of nested structures like lists and dictionaries
    try:
        from .device_mapping import merge_yaml_mappings
        merged = merge_yaml_mappings(default_mapping, custom_mapping)
        _LOGGER.debug("Mappings merged successfully using sophisticated merge")
    except Exception as e:
        _LOGGER.error("Sophisticated merge failed, falling back to simple merge: %s", e)
        # Fallback to simple merge if sophisticated merge fails
        merged = {**default_mapping, **custom_mapping}

    # Validate merged mapping
    try:
        validated = YAML_MAPPING_SCHEMA(merged)
        _LOGGER.debug("Mapping validation successful")
        return validated
    except vol.Invalid as e:
        _LOGGER.error("Mapping validation failed: %s", e)
        raise


async def async_save_custom_mapping(hass, config_dir, mapping_data):
    """Save custom mapping to YAML file.
    
    This function saves custom device mapping data to a YAML file for persistent
    storage across Home Assistant restarts.
    """
    import yaml
    custom_path = os.path.join(config_dir, "custom_mapping.yaml")

    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(custom_path), exist_ok=True)

        with open(custom_path, "w", encoding="utf-8") as f:
            yaml.dump(mapping_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            _LOGGER.info("Custom mapping saved to %s", custom_path)
            return True
    except Exception as e:
        _LOGGER.error("Failed to save custom mapping: %s", e)
        return False


async def async_get_mapping_for_options(hass, config_dir):
    """Get current mapping data for options flow.
    
    This function retrieves the current device mapping data for use in the
    configuration options flow interface.
    """
    try:
        from .const import CONF_CUSTOM_DEVICES
        mapping = await async_load_mapping(hass, config_dir)
        return mapping.get(CONF_CUSTOM_DEVICES, [])
    except Exception as e:
        _LOGGER.error("Failed to load mapping for options: %s", e)
        return []


async def async_cleanup_unused_entities(hass):
    """Service to cleanup unused eedomus entities.
    
    This service can be called manually to remove disabled and deprecated eedomus entities.
    It provides the same functionality as the options flow cleanup but can be triggered
    via automation, script, or developer tools.
    """
    _LOGGER.info("Starting cleanup of unused eedomus entities via service call")
    
    try:
        # Get entity registry (async_get returns EntityRegistry directly, not a coroutine)
        from homeassistant.helpers import entity_registry as er
        entity_registry = er.async_get(hass)
        
        # Find entities to remove: eedomus domain, disabled, deprecated, or orphaned
        entities_to_remove = []
        entities_analyzed = 0
        entities_considered = 0
        
        # Get current coordinator data to check for orphaned entities
        coordinator_data = hass.data.get(DOMAIN, {}).get("coordinator", {}).get("data", {})
        current_peripheral_ids = set(coordinator_data.keys()) if coordinator_data else set()
        
        for entity_entry in entity_registry.entities.values():
            entities_analyzed += 1
            
            # Check if this is an eedomus entity
            if entity_entry.platform == "eedomus":
                entities_considered += 1
                
                # Check if entity is disabled OR has "deprecated" in unique_id OR is orphaned
                is_disabled = entity_entry.disabled
                has_deprecated = entity_entry.unique_id and "deprecated" in entity_entry.unique_id.lower()
                
                # Check for orphaned entities (no longer provided by integration)
                is_orphaned = False
                if entity_entry.unique_id:
                    # Extract peripheral_id from unique_id (format usually includes the peripheral_id)
                    # Try to find peripheral_id in the unique_id
                    unique_id_parts = entity_entry.unique_id.split('_')
                    for part in unique_id_parts:
                        if part.isdigit() and part not in current_peripheral_ids:
                            is_orphaned = True
                            break
                    
                    # Also check if the entity has no device_id (completely orphaned)
                    if not entity_entry.device_id:
                        is_orphaned = True
                
                if is_disabled or has_deprecated or is_orphaned:
                    reason = 'orphaned' if is_orphaned else ('deprecated' if has_deprecated else 'disabled')
                    entities_to_remove.append({
                        'entity_id': entity_entry.entity_id,
                        'unique_id': entity_entry.unique_id,
                        'disabled': is_disabled,
                        'has_deprecated': has_deprecated,
                        'is_orphaned': is_orphaned,
                        'reason': reason
                    })
        
        _LOGGER.info(f"Cleanup analysis complete: {entities_analyzed} entities analyzed, "
                   f"{entities_considered} eedomus entities considered, "
                   f"{len(entities_to_remove)} entities to be removed")
        
        # Remove the entities
        removed_count = 0
        for entity_info in entities_to_remove:
            try:
                _LOGGER.info(f"Removing entity {entity_info['entity_id']} (reason: {entity_info['reason']}, "
                           f"unique_id: {entity_info['unique_id']})")
                entity_registry.async_remove(entity_info['entity_id'])
                removed_count += 1
            except Exception as e:
                _LOGGER.error(f"Failed to remove entity {entity_info['entity_id']}: {e}")
        
        _LOGGER.info(f"Cleanup completed: {removed_count} entities removed out of {len(entities_to_remove)} identified")
        
        return {
            "success": True,
            "entities_analyzed": entities_analyzed,
            "entities_considered": entities_considered,
            "entities_identified": len(entities_to_remove),
            "entities_removed": removed_count
        }
        
    except Exception as e:
        _LOGGER.error(f"Cleanup service failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


