"""Eedomus integration services."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_platform as ep

from .const import DOMAIN, COORDINATOR

_LOGGER = logging.getLogger(__name__)


def _get_all_coordinators(hass: HomeAssistant) -> list:
    """Return every eedomus coordinator currently set up, one per configured box.

    hass.data[DOMAIN] holds a mix of per-config-entry dicts (keyed by
    entry_id, each with a COORDINATOR key) and a few shared service objects
    stored directly under their own string key (config_manager, data_service,
    etc.) - the isinstance/get check below skips those safely.
    """
    coordinators = []
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if isinstance(entry_data, dict):
            coordinator = entry_data.get(COORDINATOR)
            if coordinator is not None:
                coordinators.append(coordinator)
    return coordinators


def _find_coordinator_for_device(hass: HomeAssistant, device_id: str):
    """Find which box's coordinator currently knows about the given periph_id.

    On multi-box installs a device_id alone doesn't say which box it belongs
    to. Prior to this fix, every service handler here closed over a single
    coordinator - whichever box's config entry happened to finish setup last,
    since hass.services.async_register silently overwrites the previous
    registration when called again for the same service name (see GitHub
    issue #102 / bug #12). This looks the device up across every configured
    box's coordinator data instead.
    """
    for coordinator in _get_all_coordinators(hass):
        if coordinator.data and device_id in coordinator.data:
            return coordinator
    return None


def _find_live_climate_entity(hass: HomeAssistant, device_id: str):
    """Find the live EedomusClimate entity object for a given periph_id.

    entity_platform.async_get_platforms(hass, DOMAIN) returns every
    EntityPlatform Home Assistant's core has set up for this integration -
    across every entity domain (climate, sensor, switch...) and every
    config entry (every box) - each with an `.entities` mapping that HA
    itself keeps in sync whenever async_add_entities() runs. This replaces a
    prior lookup that searched hass.data[DOMAIN][entry_id]['entities'], a key
    nothing in this codebase ever populated, so it never found anything - on
    single-box installs too, not just multi-box.
    """
    for platform in ep.async_get_platforms(hass, DOMAIN):
        for entity in platform.entities.values():
            if getattr(entity, "_periph_id", None) == device_id:
                return entity
    return None


async def async_setup_services(hass: HomeAssistant, coordinator) -> None:
    """Set up eedomus services.

    Called once per configured box (once per config entry). The `coordinator`
    parameter is kept for backward compatibility with the call sites in
    __init__.py, but the handlers below no longer close over it directly -
    they look up the right coordinator for a given device_id dynamically at
    call time via _find_coordinator_for_device(), so that every box's
    devices are reachable regardless of which box's setup registered the
    services first. Home Assistant's service registry is global (one
    "eedomus.set_value" for the whole instance, not one per config entry), so
    only the FIRST call actually registers anything; later calls (from
    additional boxes) just join the pool of coordinators the already
    -registered handlers can dispatch to.
    """
    if hass.services.has_service(DOMAIN, "set_value"):
        _LOGGER.debug(
            "Eedomus services already registered - this box's coordinator is "
            "still reachable via hass.data[DOMAIN], nothing more to register"
        )
        return

    async def handle_refresh(call: ServiceCall) -> None:
        """Handle refresh service call - refreshes every configured eedomus box."""
        _LOGGER.info("🔄 Manual refresh requested via service call")
        coordinators = _get_all_coordinators(hass)
        if not coordinators:
            _LOGGER.warning("⚠️  No coordinator available for refresh")
            return
        errors = []
        for coord in coordinators:
            try:
                await coord.async_request_refresh()
            except Exception as err:
                box_title = getattr(getattr(coord, "config_entry", None), "title", "unknown box")
                _LOGGER.error("❌ Failed to refresh eedomus data for %s: %s", box_title, err)
                errors.append(err)
        _LOGGER.info("✅ Eedomus data refreshed (%d box(es), %d error(s))", len(coordinators), len(errors))
        if errors and len(errors) == len(coordinators):
            raise errors[0]

    async def handle_set_value(call: ServiceCall) -> None:
        """Handle set_value service call."""
        device_id = call.data.get("device_id")
        value = call.data.get("value")

        if not device_id or not value:
            _LOGGER.error("❌ Missing required parameters: device_id and value")
            raise ValueError("device_id and value are required")

        _LOGGER.info("📤 Setting value %s for device %s via service", value, device_id)

        target_coordinator = _find_coordinator_for_device(hass, device_id)
        if target_coordinator is None:
            _LOGGER.error("❌ Device %s not found on any configured eedomus box", device_id)
            raise ValueError(f"Device {device_id} not found on any configured eedomus box")

        try:
            # Send the command to eedomus using the owning box's coordinator
            # This ensures proper fallback and retry logic is applied
            result = await target_coordinator.async_set_periph_value(device_id, value)

            if result.get("success") == 1:
                _LOGGER.info("✅ Successfully set value for device %s", device_id)
                # Force refresh to get updated state
                await target_coordinator.async_request_refresh()
            else:
                _LOGGER.warning("⚠️ Set value returned non-success: %s", result)
                raise ValueError(f"Failed to set value: {result.get('error', 'Unknown error')}")

        except Exception as err:
            _LOGGER.error("❌ Failed to set value for device %s: %s", device_id, err)
            raise err

    async def handle_reload(call: ServiceCall) -> None:
        """Handle reload service call - reloads every configured eedomus box."""
        _LOGGER.info("🔄 Reload requested via service call")
        entries = hass.config_entries.async_entries(DOMAIN)
        if not entries:
            _LOGGER.error("❌ No eedomus config entry found")
            raise ValueError("No eedomus config entry found")

        errors = []
        for entry in entries:
            try:
                await hass.config_entries.async_reload(entry.entry_id)
                _LOGGER.info("✅ Eedomus integration reloaded successfully (%s)", entry.title)
            except Exception as err:
                _LOGGER.error("❌ Failed to reload eedomus integration (%s): %s", entry.title, err)
                errors.append(err)
        if errors and len(errors) == len(entries):
            raise errors[0]

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
        
        # Find which box owns this device, and validate it's a climate entity
        target_coordinator = _find_coordinator_for_device(hass, device_id)
        if target_coordinator is None:
            _LOGGER.error("❌ Device %s not found on any configured eedomus box", device_id)
            raise ValueError(f"Device {device_id} not found on any configured eedomus box")

        periph_data = target_coordinator.data.get(device_id)
        ha_entity = periph_data.get("ha_entity")
        if ha_entity != "climate":
            _LOGGER.error("❌ Device %s is not a climate entity (found: %s)", device_id, ha_entity)
            raise ValueError(f"Device {device_id} is not a climate entity")
        
        # Find the live climate entity object and set the temperature through it,
        # so its own eedomus-specific value translation (acceptable_values /
        # entity_specifics, see climate.py) is applied rather than sending a raw
        # number - this was previously broken for everyone (see docstring of
        # _find_live_climate_entity), not just on multi-box installs.
        climate_entity = _find_live_climate_entity(hass, device_id)
        
        if not climate_entity:
            _LOGGER.error("❌ No climate entity found for device %s", device_id)
            raise ValueError(f"No climate entity found for device {device_id}")
        
        # Set temperature through climate entity
        try:
            await climate_entity.async_set_temperature(temperature=rounded_temp)
            _LOGGER.info("✅ Successfully set climate temperature to %.1f°C for %s", rounded_temp, device_id)
            
            # Force refresh to get updated state
            await target_coordinator.async_request_refresh()
            
            return {
                "success": True,
                "device_id": device_id,
                "temperature": rounded_temp,
                "message": f"Temperature set to {rounded_temp}°C"
            }
            
        except Exception as err:
            _LOGGER.error("❌ Failed to set climate temperature for %s: %s", device_id, err)
            raise ValueError(f"Failed to set temperature: {str(err)}")

    async def handle_cleanup_unused_entities(call: ServiceCall) -> dict:
        """Handle cleanup of unused eedomus entities."""
        _LOGGER.info("🧹 Cleanup service called via eedomus.cleanup_unused_entities")
        
        try:
            # Import the cleanup function from __init__.py
            from . import async_cleanup_unused_entities
            
            # Call the cleanup function with explicit entity registry access
            # Use direct import to avoid hass.helpers issue
            from homeassistant.helpers import entity_registry as er
            
            # Get entity registry directly using the correct method
            # async_get returns EntityRegistry directly, not a coroutine
            entity_registry = er.async_get(hass)
            
            # Find entities to remove: eedomus domain, disabled, and have "deprecated" in unique_id
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
                    
                    # Check if entity is disabled OR has "deprecated" in unique_id OR is orphaned OR has no unique_id
                    is_disabled = entity_entry.disabled
                    has_deprecated = entity_entry.unique_id and "deprecated" in entity_entry.unique_id.lower()
                    has_no_unique_id = entity_entry.unique_id is None or entity_entry.unique_id == ""
                    
                    # Check for orphaned entities (no longer provided by integration)
                    is_orphaned = False
                    if entity_entry.unique_id:
                        # Extract peripheral_id from unique_id (format usually includes the peripheral_id)
                        unique_id_parts = entity_entry.unique_id.split('_')
                        for part in unique_id_parts:
                            if part.isdigit() and part not in current_peripheral_ids:
                                is_orphaned = True
                                break
                        
                        # Also check if the entity has no device_id (completely orphaned)
                        if not entity_entry.device_id:
                            is_orphaned = True
                    
                    if is_disabled or has_deprecated or is_orphaned or has_no_unique_id:
                        if has_no_unique_id:
                            reason = 'no_unique_id'
                        elif is_orphaned:
                            reason = 'orphaned'
                        else:
                            reason = 'deprecated' if has_deprecated else 'disabled'
                        entities_to_remove.append({
                            'entity_id': entity_entry.entity_id,
                            'unique_id': entity_entry.unique_id,
                            'disabled': is_disabled,
                            'has_deprecated': has_deprecated,
                            'is_orphaned': is_orphaned,
                            'has_no_unique_id': has_no_unique_id,
                            'reason': reason
                        })
            
            _LOGGER.info(f"Cleanup analysis complete: {entities_analyzed} entities analyzed, "
                       f"{entities_considered} eedomus entities considered, "
                       f"{len(entities_to_remove)} entities to be removed")
            
            # Remove the entities
            removed_count = 0
            for entity_info in entities_to_remove:
                try:
                    log_details = f"reason: {entity_info['reason']}"
                    if entity_info['unique_id']:
                        log_details += f", unique_id: {entity_info['unique_id']}"
                    if entity_info.get('is_orphaned'):
                        log_details += " (orphaned - no longer provided by integration)"
                    if entity_info.get('has_no_unique_id'):
                        log_details += " (no unique_id - cannot be managed from UI)"
                    _LOGGER.info(f"Removing entity {entity_info['entity_id']} ({log_details})")
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
            
        except Exception as err:
            _LOGGER.error("❌ Cleanup service failed: %s", err)
            return {
                "success": False,
                "error": str(err)
            }

    async def handle_cleanup_unused_devices(call: ServiceCall) -> dict:
        """Handle cleanup of unused eedomus devices."""
        _LOGGER.info("🗑️  Cleanup unused devices service called via eedomus.cleanup_unused_devices")
        
        try:
            # Import device registry
            from homeassistant.helpers import device_registry as dr
            
            # Get device registry (async_get returns DeviceRegistry directly, not a coroutine)
            device_registry = dr.async_get(hass)
            
            # Find devices to remove: eedomus devices that are disabled or have no entities
            devices_to_remove = []
            devices_analyzed = 0
            devices_considered = 0
            
            for device_entry in device_registry.devices.values():
                devices_analyzed += 1
                
                # Check if this device has eedomus in its identifiers
                is_eedomus_device = any(
                    identifier[0] == "eedomus" 
                    for identifier in device_entry.identifiers
                )
                
                if is_eedomus_device:
                    devices_considered += 1
                    
                    # Check if device is disabled OR has no entities
                    is_disabled = device_entry.disabled_by
                    # Check if device has no entities by looking at the device's entity associations
                    # We need to use the entity registry to find entities associated with this device
                    from homeassistant.helpers import entity_registry as er
                    entity_registry = er.async_get(hass)
                    device_entities = [entity_id for entity_id, entity in entity_registry.entities.items() 
                                     if entity.device_id == device_entry.id]
                    has_no_entities = len(device_entities) == 0
                    
                    if is_disabled or has_no_entities:
                        devices_to_remove.append({
                            'device_id': device_entry.id,
                            'name': device_entry.name,
                            'disabled': bool(is_disabled),
                            'has_no_entities': has_no_entities,
                            'reason': 'no_entities' if has_no_entities else 'disabled'
                        })
            
            _LOGGER.info(f"Device cleanup analysis complete: {devices_analyzed} devices analyzed, "
                       f"{devices_considered} eedomus devices considered, "
                       f"{len(devices_to_remove)} devices to be removed")
            
            # Remove the devices
            removed_count = 0
            for device_info in devices_to_remove:
                try:
                    _LOGGER.info(f"Removing device {device_info['name']} (id: {device_info['device_id']}, "
                               f"reason: {device_info['reason']})")
                    device_registry.async_remove_device(device_info['device_id'])
                    removed_count += 1
                except Exception as e:
                    _LOGGER.error(f"Failed to remove device {device_info['device_id']}: {e}")
            
            _LOGGER.info(f"Device cleanup completed: {removed_count} devices removed "
                       f"out of {len(devices_to_remove)} identified")
            
            return {
                "success": True,
                "devices_analyzed": devices_analyzed,
                "devices_considered": devices_considered,
                "devices_identified": len(devices_to_remove),
                "devices_removed": removed_count
            }
            
        except Exception as err:
            _LOGGER.error("❌ Device cleanup service failed: %s", err)
            return {
                "success": False,
                "error": str(err)
            }

    # Register services
    try:
        hass.services.async_register("eedomus", "refresh", handle_refresh)
        hass.services.async_register("eedomus", "set_value", handle_set_value)
        hass.services.async_register("eedomus", "reload", handle_reload)
        hass.services.async_register("eedomus", "set_climate_temperature", handle_set_climate_temperature)
        hass.services.async_register("eedomus", "cleanup_unused_entities", handle_cleanup_unused_entities)
        hass.services.async_register("eedomus", "cleanup_unused_devices", handle_cleanup_unused_devices)
        _LOGGER.info("🛠️  Eedomus services registered: refresh, set_value, reload, set_climate_temperature, cleanup_unused_entities, cleanup_unused_devices")
    except Exception as err:
        _LOGGER.error("❌ Failed to register eedomus services: %s", err)
        raise err
