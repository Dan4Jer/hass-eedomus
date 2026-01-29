"""Base entity for eedomus integration."""

from __future__ import annotations
from datetime import datetime
import re
import logging
import os
import json

from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_PERIPH_ID, DOMAIN, EEDOMUS_TO_HA_ATTR_MAPPING
from .device_mapping import load_and_merge_yaml_mappings, load_yaml_mappings

# Get version from manifest.json
try:
    manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
    with open(manifest_path, "r") as f:
        manifest_data = json.load(f)
        VERSION = manifest_data.get("version", "unknown")
except Exception as e:
    VERSION = "unknown"
    _LOGGER.warning("Failed to read version from manifest.json: %s", e)

_LOGGER = logging.getLogger(__name__)

# Global variable to store loaded mappings
DEVICE_MAPPINGS = None

# Initialize YAML mappings when module is loaded
try:
    _LOGGER.info("🚀 Starting DEVICE_MAPPINGS initialization...")
    DEVICE_MAPPINGS = load_and_merge_yaml_mappings()
    
    if DEVICE_MAPPINGS:
        _LOGGER.info("✅ YAML device mappings initialized successfully")
        
        # Critical checks for dynamic properties
        dynamic_props = DEVICE_MAPPINGS.get('dynamic_entity_properties', {})
        specific_overrides = DEVICE_MAPPINGS.get('specific_device_dynamic_overrides', {})
        
        _LOGGER.info("📊 DEVICE_MAPPINGS summary:")
        _LOGGER.info("   📋 Usage ID mappings: %d", len(DEVICE_MAPPINGS.get('usage_id_mappings', {})))
        _LOGGER.info("   🤖 Advanced rules: %d", len(DEVICE_MAPPINGS.get('advanced_rules', [])))
        _LOGGER.info("   📝 Name patterns: %d", len(DEVICE_MAPPINGS.get('name_patterns', [])))
        _LOGGER.info("   ⚡ Dynamic entity properties: %s", dynamic_props)
        _LOGGER.info("   🎛️ Specific device overrides: %s", specific_overrides)
        
        # Critical error if dynamic properties are missing
        if not dynamic_props:
            _LOGGER.error("❌ CRITICAL ERROR: dynamic_entity_properties is empty!")
            _LOGGER.error("❌ This will cause ALL devices to be treated as static!")
            _LOGGER.error("❌ No partial refresh will work - performance will be severely impacted!")
            _LOGGER.error("❌ Check YAML file and loading process immediately!")
        else:
            _LOGGER.info("✅ Dynamic properties loaded: %s", dynamic_props)
            
        if not specific_overrides:
            _LOGGER.debug("⚠️  No specific device overrides (this is normal)")
        else:
            _LOGGER.info("✅ Specific device overrides loaded: %s", specific_overrides)
            
    else:
        _LOGGER.error("❌ CRITICAL ERROR: DEVICE_MAPPINGS is None or empty!")
        _LOGGER.error("❌ This will cause complete failure of device mapping!")
        raise Exception("DEVICE_MAPPINGS initialization failed - cannot continue")
        
except Exception as e:
    _LOGGER.error("❌ CRITICAL ERROR: Failed to initialize YAML mappings: %s", e)
    _LOGGER.error("❌ This is a fatal error - device mapping will not work!")
    import traceback
    _LOGGER.error("Exception details: %s", traceback.format_exc())
    _LOGGER.warning("⚠️  Using fallback mapping configuration - expect major issues!")
    
    # Fallback configuration with error tracking
    DEVICE_MAPPINGS = {
        'usage_id_mappings': {},
        'advanced_rules': [],
        'name_patterns': [],
        'dynamic_entity_properties': {},
        'specific_device_dynamic_overrides': {},
        'default_mapping': {
            'ha_entity': 'sensor',
            'ha_subtype': 'unknown',
            'justification': 'Fallback mapping - YAML loading failed!'
        },
        '_initialization_error': str(e)
    }
    
    _LOGGER.error("❌ DEVICE_MAPPINGS set to fallback: %s", DEVICE_MAPPINGS)

# Load name patterns for device name matching
try:
    yaml_config = load_yaml_mappings()
    NAME_PATTERNS = yaml_config.get('name_patterns', []) if yaml_config else []
    _LOGGER.info("Loaded %d name patterns from YAML configuration", len(NAME_PATTERNS))
except Exception as e:
    _LOGGER.error("Failed to load name patterns: %s", e)
    NAME_PATTERNS = []


# Timestamp formatting utilities

def _format_timestamp_value(timestamp_value: str) -> str:
    """Format various timestamp values from eedomus into ISO 8601 format.
    
    Handles multiple timestamp formats:
    - Unix timestamp (seconds since epoch)
    - Datetime string (e.g., "2026-01-10 16:21:14")
    - Invalid datetime (e.g., "0000-00-00 00:00:00")
    
    Args:
        timestamp_value: The raw timestamp value from eedomus
        
    Returns:
        str: ISO 8601 formatted timestamp or None if invalid
    """
    if not timestamp_value or timestamp_value == "None":
        return None
        
    try:
        # Handle Unix timestamp format (seconds since epoch)
        if isinstance(timestamp_value, (int, float)) or (isinstance(timestamp_value, str) and timestamp_value.isdigit()):
            timestamp = int(timestamp_value)
            dt = datetime.fromtimestamp(timestamp)
            return dt.isoformat()
            
        # Handle datetime string format (e.g., "2026-01-10 16:21:14")
        if isinstance(timestamp_value, str):
            timestamp_str = timestamp_value.strip()
            
            # Skip invalid datetime strings
            if timestamp_str == "0000-00-00 00:00:00":
                return None
                
            # Try common datetime formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
                    
    except (ValueError, TypeError, OverflowError) as e:
        _LOGGER.debug(
            "Failed to parse timestamp value '%s': %s",
            timestamp_value,
            e
        )
        return None
    
    return None


def _format_eedomus_timestamps(periph_data: dict) -> dict:
    """Format all eedomus timestamp fields into standardized ISO 8601 format.
    
    Processes common eedomus timestamp fields and creates standardized
    Home Assistant timestamp attributes.
    
    Args:
        periph_data: The peripheral data from eedomus
        
    Returns:
        dict: Dictionary with formatted timestamp attributes
    """
    timestamps = {}
    
    # Map eedomus timestamp fields to HA attribute names
    timestamp_mapping = {
        "last_value_change": ["last_changed", "last_reported"],  # Both attributes get same value
        "creation_date": ["created"],                           # Single attribute
    }
    
    for eedomus_field, ha_attributes in timestamp_mapping.items():
        if eedomus_field in periph_data:
            formatted_timestamp = _format_timestamp_value(periph_data[eedomus_field])
            if formatted_timestamp:
                for ha_attr in ha_attributes:
                    timestamps[ha_attr] = formatted_timestamp
    
    return timestamps


class EedomusEntity(CoordinatorEntity):
    """Base class for eedomus entities."""

    def __init__(self, coordinator, periph_id: str):
        """Initialize the entity."""
        super().__init__(coordinator)
        self._periph_id = periph_id
        
        # Safe access to coordinator data
        periph_data = self._get_periph_data(periph_id)
        if periph_data is None:
            _LOGGER.warning(f"Peripheral data not found for {periph_id}, using fallback")
            self._attr_name = f"Unknown Device ({periph_id})"
            self._parent_id = None
            self._attr_unique_id = f"{periph_id}"
            self._attr_available = False
            return
            
        self._parent_id = periph_data.get("parent_periph_id", None)
        if self.coordinator.client:
            self._client = self.coordinator.client
        if self._parent_id is None:
            self._attr_unique_id = f"{periph_id}"
        else:
            self._attr_unique_id = f"{self._parent_id}_{periph_id}"
        if periph_data["name"]:
            self._attr_name = periph_data["name"]
        _LOGGER.debug(
            "Initializing entity for %s (%s)", self._attr_name, self._periph_id
        )
        self._attr_available = True

    def _get_periph_data(self, periph_id: str = None):
        """Safely get peripheral data from coordinator."""
        target_id = periph_id or self._periph_id
        if self.coordinator.data is None:
            _LOGGER.warning(f"Coordinator data is None, cannot get data for {target_id}")
            return None
        return self.coordinator.data.get(target_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        periph_info = self._get_periph_data()
        if periph_info is None:
            return DeviceInfo(
                identifiers={(DOMAIN, str(self._periph_id))},
                name=f"Unknown Device {self._periph_id}",
                manufacturer="eedomus",
                model="unknown",
            )
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._periph_id))},
            name=periph_info.get("name"),
            manufacturer="eedomus",
            model=periph_info.get("model"),
        )

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {}
        if self.coordinator.data is not None and self.coordinator.data.get(self._periph_id):
            periph_data = self.coordinator.data[self._periph_id]
            attrs[ATTR_PERIPH_ID] = self._periph_id

            # Map standard eedomus attributes
            for eedomus_key, ha_key in EEDOMUS_TO_HA_ATTR_MAPPING.items():
                if eedomus_key in periph_data:
                    attrs[ha_key] = periph_data[eedomus_key]
            
            # Format all timestamp fields using the centralized utility
            timestamp_attrs = _format_eedomus_timestamps(periph_data)
            attrs.update(timestamp_attrs)
            
            # Add current timestamp for last_updated (when HA last updated this entity)
            attrs["last_updated"] = datetime.now().isoformat()
            
            # Ensure usage_id is always included in attributes
            if "usage_id" in periph_data:
                attrs["usage_id"] = periph_data["usage_id"]
            
        return attrs

    @property
    def available(self):
        """Return the periph ID."""
        return self._attr_available

    @property
    def periph_id(self):
        """Return the periph ID."""
        return self._periph_id

    def update(self) -> None:
        """Update entity state."""
        _LOGGER.warning(
            "Update for %s (%s) type=%s client=%s",
            self._attr_name,
            self._periph_id,
            type(self),
            type(self._client),
        )
        try:
            caract_value = self._client.get_periph_caract(self._periph_id)
            if isinstance(caract_value, dict):
                body = caract_value.get("body")
                if body is not None:
                    periph_data = self._get_periph_data()
                    if periph_data is not None:
                        periph_data.update(body)
                    else:
                        _LOGGER.warning(
                            "Cannot update characteristics: peripheral data not found for %s (%s)",
                            self._attr_name,
                            self._periph_id,
                        )
                else:
                    _LOGGER.warning(
                        "No body found in API response for %s (%s)",
                        self._attr_name,
                        self._periph_id,
                    )
        except Exception as e:
            if self.available:  # Read current state, no need to prefix with _attr_
                _LOGGER.warning(
                    "Update failed for %s (%s) : %s",
                    self._attr_name,
                    self._periph_id,
                    e,
                )
                self._attr_available = False  # Set property value
                return

        self._attr_available = True
        # We don't need to check if device available here
        if "last_value" in self.coordinator.data[self._periph_id]:
            self._attr_native_value = self.coordinator.data[self._periph_id]["last_value"]
        else:
            _LOGGER.warning(
                "No last_value found in data for %s (%s)",
                self._attr_name,
                self._periph_id,
            )
            self._attr_available = False

    async def async_update(self) -> None:
        """Update entity state."""
        _LOGGER.warn(
            "Async Update for %s (%s) type=%s client=%s",
            self._attr_name,
            self._periph_id,
            type(self),
            type(self._client),
        )
        try:
            caract_value = await self._client.get_periph_caract(self._periph_id)
            if isinstance(caract_value, dict):
                body = caract_value.get("body")
                if body is not None:
                    periph_data = self._get_periph_data()
                    if periph_data is not None:
                        periph_data.update(body)
                    else:
                        _LOGGER.warning(
                            "Cannot update characteristics: peripheral data not found for %s (%s)",
                            self._attr_name,
                            self._periph_id,
                        )
                else:
                    _LOGGER.warning(
                        "No body found in API response for %s (%s)",
                        self._attr_name,
                        self._periph_id,
                    )
        except Exception as e:
            if self.available:  # Read current state, no need to prefix with _attr_
                _LOGGER.warning(
                    "Update failed for %s (%s) : %s",
                    self._attr_name,
                    self._periph_id,
                    e,
                )
                self._attr_available = False  # Set property value
                return

        self._attr_available = True
        # We don't need to check if device available here
        periph_data = self._get_periph_data()
        if periph_data is not None:
            self._attr_native_value = periph_data["last_value"]
            periph_data["last_updated"] = datetime.now().isoformat()
        else:
            _LOGGER.warning(f"Cannot update native value: peripheral data not found for {self._periph_id}")
            self._attr_native_value = None

    async def async_set_value(self, value: str):
        """Set device value with full eedomus logic including fallback and retry.
        
        This method centralizes all value-setting logic including:
        - PHP fallback for rejected values
        - Next best value selection
        - Immediate state updates
        - Coordinator refresh
        
        Args:
            value: The value to set (e.g., "100", "0", "50")
            
        Returns:
            dict: API response from eedomus
            
        Raises:
            Exception: If the value cannot be set after all retry attempts
        """
        _LOGGER.debug(
            "Setting value '%s' for %s (%s)",
            value,
            self._attr_name,
            self._periph_id
        )
        

        
        try:
            # Verify periph_id is not None before calling set_value
            if self._periph_id is None:
                _LOGGER.error("Cannot set value: periph_id is None for entity %s", self._attr_name)
                return {"success": 0, "error": "periph_id is None"}
                
            # Call coordinator method to set the value
            response = await self.coordinator.async_set_periph_value(
                self._periph_id, str(value)
            )
            
            # Check if we need to handle retry/fallback
            if isinstance(response, dict):
                if response.get("success") == 1:
                    # Success! Force immediate state update
                    await self.async_force_state_update(value)
                    await self.coordinator.async_request_refresh()
                    return response
                elif response.get("error_code") == "6":  # Value refused
                    _LOGGER.warning(
                        "Value '%s' refused for %s (%s), checking fallback/next best value",
                        value,
                        self._attr_name,
                        self._periph_id
                    )
                    # The coordinator already handled retry/fallback, just update state
                    await self.async_force_state_update(value)
                    await self.coordinator.async_request_refresh()
                    return response
            
            # If we get here, something went wrong
            error_msg = "Unknown error"
            if response is None:
                error_msg = "API returned None response"
            elif isinstance(response, dict):
                error_msg = response.get("error", "Unknown error")
            else:
                error_msg = str(response)
            
            _LOGGER.error(
                "Failed to set value '%s' for %s (%s): %s",
                value,
                self._attr_name,
                self._periph_id,
                error_msg
            )
            raise Exception(f"Failed to set value: {error_msg}")
            
        except Exception as e:
            _LOGGER.error(
                "Failed to set value for %s (%s): %s",
                self._attr_name,
                self._periph_id,
                e
            )
            raise

    async def async_force_state_update(self, new_value):
        """Force an immediate state update with the given value.
        
        This method should be called after successfully setting a device value
        to ensure the UI updates immediately without waiting for coordinator refresh.
        """
        _LOGGER.debug(
            "Forcing state update for %s (%s) to value: %s",
            self._attr_name,
            self._periph_id,
            new_value
        )
        
        # Update the coordinator's data
        periph_data = self._get_periph_data()
        if periph_data is not None:
            periph_data["last_value"] = str(new_value)
            # Update last_value_change timestamp to current time
            # This is crucial for covers and other entities that track when values were last changed
            from datetime import datetime
            current_timestamp = datetime.now().isoformat()
            periph_data["last_value_change"] = current_timestamp
            _LOGGER.debug(
                "Updated last_value_change for %s (%s) to: %s",
                self._attr_name,
                self._periph_id,
                current_timestamp
            )
        else:
            _LOGGER.warning(f"Cannot force state update: peripheral data not found for {self._periph_id}")
        
        # Force immediate state update in Home Assistant using explicit state machine
        # This ensures we control the timestamp precisely
        try:
            # Get the timestamp from last_value_change
            periph_data = self._get_periph_data()
            if periph_data is None:
                _LOGGER.warning(f"Cannot get last_value_change: peripheral data not found for {self._periph_id}")
                return
                
            last_value_change = periph_data.get("last_value_change")
            if last_value_change:
                # Convert ISO format timestamp to datetime object
                desired_dt = datetime.fromisoformat(last_value_change)
                desired_ts = desired_dt.timestamp()
                
                _LOGGER.debug(
                    "Setting explicit state for %s (%s) with timestamp %s",
                    self._attr_name,
                    self._periph_id,
                    desired_ts
                )
                
                # Use state machine to set state with precise timestamp
                if hasattr(self, 'hass') and hasattr(self, 'entity_id'):
                    self.hass.states.async_set(
                        self.entity_id,
                        str(self._attr_native_value) if hasattr(self, '_attr_native_value') else str(new_value),
                        self.extra_state_attributes,
                        force_update=True,
                        timestamp=desired_ts,
                    )
                else:
                    _LOGGER.warning(
                        "Cannot set explicit state - missing hass or entity_id for %s (%s)",
                        self._attr_name,
                        self._periph_id
                    )
                    # Fallback to standard method
                    self.async_write_ha_state()
            else:
                _LOGGER.warning(
                    "No last_value_change timestamp available for %s (%s)",
                    self._attr_name,
                    self._periph_id
                )
                # Fallback to standard method
                self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(
                "Failed to set explicit state for %s (%s): %s",
                self._attr_name,
                self._periph_id,
                e
            )
            # Fallback to standard method
            self.async_write_ha_state()
        
        # Schedule a regular update to ensure consistency
        self.async_schedule_update_ha_state()


def map_device_to_ha_entity(device_data, all_devices=None, default_ha_entity: str = "sensor"):
    """Mappe un périphérique eedomus vers une entité Home Assistant.
    
    Logique de mapping simplifiée et optimisée :
    1. Règles avancées (relations parent-enfant)
    2. Cas spécifiques prioritaires (usage_id)
    3. Mapping basé sur usage_id
    4. Détection par nom (dernier recours)
    5. Mapping par défaut
    
    Args:
        device_data (dict): Données du périphérique.
        all_devices (dict): Tous les périphériques pour les règles avancées.
        default_ha_entity (str): Entité HA par défaut.
    
    Returns:
        dict: {"ha_entity": str, "ha_subtype": str, "justification": str}
    """
    # Utiliser les mappings chargés globalement
    # from .device_mapping import ADVANCED_MAPPING_RULES
    
    periph_id = device_data["periph_id"]
    periph_name = device_data["name"]
    usage_id = device_data.get("usage_id")
    
    _LOGGER.debug("Mapping device: %s (%s, usage_id=%s)", periph_name, periph_id, usage_id)
    
    # FORCED DEBUG FOR DEVICE 1269454
    if periph_id == "1269454":
        _LOGGER.error("🚨 FORCED DEBUG: Device 1269454 is being mapped!")
        _LOGGER.error("🚨 FORCED DEBUG: Device data: %s", device_data)
        _LOGGER.error("🚨 FORCED DEBUG: all_devices available: %s", bool(all_devices))
        if all_devices:
            children = [
                child for child_id, child in all_devices.items()
                if child.get("parent_periph_id") == periph_id
            ]
            _LOGGER.error("🚨 FORCED DEBUG: Found %d children: %s", 
                         len(children), [c["name"] for c in children])
    
    # Debug: Log the number of advanced rules loaded
    _LOGGER.debug("Number of advanced rules loaded: %d", len(DEVICE_MAPPINGS.get('advanced_rules', [])))
    
    # Priorité 1: Règles avancées (nécessite all_devices)
    _LOGGER.info("🔍 Starting mapping process for %s (%s)", periph_name, periph_id)
    _LOGGER.debug("   all_devices available: %s", bool(all_devices))
    _LOGGER.debug("   all_devices type: %s", type(all_devices))
    
    # Fix: Ensure all_devices is never None or empty - create empty dict if needed
    if all_devices is None or not all_devices:
        _LOGGER.warning("⚠️  all_devices is None or empty, creating empty dict to allow advanced rules evaluation")
        all_devices = {}
    
    # FORCED DEBUG: Log before all_devices check
    _LOGGER.error("🚨 FORCED DEBUG (v%s): Before all_devices check - periph_id=%s (type: %s)", VERSION, periph_id, type(periph_id))
    if periph_id == "1269454":
        _LOGGER.error("🚨 FORCED DEBUG (v%s): Before all_devices check", VERSION)
        _LOGGER.error("🚨 FORCED DEBUG (v%s): all_devices value: %s", VERSION, all_devices)
        _LOGGER.error("🚨 FORCED DEBUG (v%s): all_devices keys: %s", VERSION, list(all_devices.keys()) if all_devices else None)
        _LOGGER.error("🚨 FORCED DEBUG (v%s): Device data: %s", VERSION, device_data)
    
    # Always evaluate advanced rules - never skip this section
    _LOGGER.debug("   all_devices keys count: %d", len(all_devices))
    _LOGGER.info("✅ Checking advanced rules for %s (%s)", periph_name, periph_id)
        
        # Debug spécifique pour le device 1269454 (RGBW connu)
        if periph_id == "1269454":
            _LOGGER.info("🔍 SPECIAL DEBUG: Analyzing RGBW device 1269454")
            _LOGGER.info("🔍 Device data: name=%s, usage_id=%s, parent_periph_id=%s, PRODUCT_TYPE_ID=%s",
                        device_data.get("name"), device_data.get("usage_id"), device_data.get("parent_periph_id"), device_data.get("PRODUCT_TYPE_ID"))
            
            # Find all children of this device
            children = [
                child for child_id, child in all_devices.items()
                if child.get("parent_periph_id") == periph_id
            ]
            _LOGGER.info("🔍 Found %d children for device 1269454: %s", 
                        len(children), [c["name"] for c in children])
            
            # Count children with usage_id=1
            usage_id_1_children = [
                child for child_id, child in all_devices.items()
                if child.get("parent_periph_id") == periph_id and child.get("usage_id") == "1"
            ]
            _LOGGER.info("🔍 Found %d children with usage_id=1: %s", 
                        len(usage_id_1_children), [c["name"] for c in usage_id_1_children])
            
            # Log the RGBW children names specifically
            rgbw_names = [c["name"] for c in usage_id_1_children if "Rouge" in c["name"] or "Vert" in c["name"] or "Bleu" in c["name"] or "Blanc" in c["name"]]
            _LOGGER.info("🔍 RGBW component names: %s", rgbw_names)
            
            # FORCED DEBUG: Confirm we're about to exit the if all_devices block
            if periph_id == "1269454":
                _LOGGER.error("🚨 FORCED DEBUG (v%s): About to exit if all_devices block - continuing to rule evaluation", VERSION)
                _LOGGER.error("🚨 FORCED DEBUG: Advanced rules evaluation completed for device 1269454")
    else:
        _LOGGER.error("❌ CRITICAL: all_devices is None or empty for %s (%s)", periph_name, periph_id)
        _LOGGER.error("❌ Advanced rules will NOT be executed - using fallback mapping")
        
        # Debug: List all advanced rule names
        advanced_rules = DEVICE_MAPPINGS.get('advanced_rules', [])
        
        # General debug for RGBW devices
        if device_data.get("usage_id") == "1":
            _LOGGER.info("🔍 DEBUG: Processing light device %s (%s) with usage_id=1", 
                        device_data.get("name"), periph_id)
        
        # Special debug for device 1269454
        if periph_id == "1269454":
            _LOGGER.info("🔍 SPECIAL DEBUG: Device 1269454 - Starting advanced rules analysis")
            _LOGGER.info("🔍 Device data: name=%s, usage_id=%s, parent_periph_id=%s",
                        device_data.get("name"), device_data.get("usage_id"), device_data.get("parent_periph_id"))
            
            # Find all children of this device
            if all_devices:
                children = [
                    child for child_id, child in all_devices.items()
                    if child.get("parent_periph_id") == periph_id
                ]
                _LOGGER.info("🔍 Found %d children for device 1269454", len(children))
                for child in children:
                    _LOGGER.info("🔍   Child: %s (usage_id=%s)", child.get("name"), child.get("usage_id"))
                
                # Count children with usage_id=1
                usage_id_1_children = [
                    child for child_id, child in all_devices.items()
                    if child.get("parent_periph_id") == periph_id and child.get("usage_id") == "1"
                ]
                _LOGGER.info("🔍 Found %d children with usage_id=1", len(usage_id_1_children))
                
                # Check for RGBW component names
                rgbw_names = ["Rouge", "Vert", "Bleu", "Blanc"]
                found_rgbw = []
                for name in rgbw_names:
                    if any(name.lower() in child.get("name", "").lower() for child in children):
                        found_rgbw.append(name)
                _LOGGER.info("🔍 Found RGBW components: %s", found_rgbw)
                _LOGGER.info("🔍 Missing RGBW components: %s", [name for name in rgbw_names if name not in found_rgbw])
        
        # Handle both list and dict formats
        if isinstance(advanced_rules, list):
            rule_names = [rule.get('name', 'unnamed') for rule in advanced_rules if isinstance(rule, dict)]
            _LOGGER.info("📋 Found %d advanced rules (list format): %s", len(advanced_rules), rule_names)
            if periph_id == "1269454":
                _LOGGER.info("🔍 RGBW RULES LOADED: %s", rule_names)
        elif isinstance(advanced_rules, dict):
            rule_names = list(advanced_rules.keys())
            _LOGGER.info("📋 Found %d advanced rules (dict format): %s", len(advanced_rules), rule_names)
            if periph_id == "1269454":
                _LOGGER.info("🔍 RGBW RULES LOADED: %s", rule_names)
        else:
            _LOGGER.error("❌ CRITICAL: advanced_rules has unexpected type: %s", type(advanced_rules))
            rule_names = []
        
        # Special check for device 1269454
        if periph_id == "1269454":
            _LOGGER.info("🔍 SPECIAL DEBUG: Device 1269454 mapping process started")
            _LOGGER.info("🔍 Available rules: %s", rule_names)
            
            # Check if our RGBW rules are present (handle both formats)
            if isinstance(advanced_rules, list):
                has_rgbw_rule = any(rule.get('name') == 'rgbw_lamp_with_children' for rule in advanced_rules if isinstance(rule, dict))
                has_flexible_rule = any(rule.get('name') == 'rgbw_lamp_flexible' for rule in advanced_rules if isinstance(rule, dict))
            elif isinstance(advanced_rules, dict):
                has_rgbw_rule = 'rgbw_lamp_with_children' in advanced_rules
                has_flexible_rule = 'rgbw_lamp_flexible' in advanced_rules
            else:
                has_rgbw_rule = False
                has_flexible_rule = False
            
            _LOGGER.info("🔍 Has rgbw_lamp_with_children: %s", has_rgbw_rule)
            _LOGGER.info("🔍 Has rgbw_lamp_flexible: %s", has_flexible_rule)
        
        # Debug logging for device 1269454 specifically
    # if periph_id == "1269454":
    #     _LOGGER.info("🔍 SPECIAL DEBUG: Analyzing device 1269454")
    #     _LOGGER.info("🔍 Device data: %s", device_data)
    #     
    #     # Find all children of this device
    #     children = [
    #         child for child_id, child in all_devices.items()
    #         if child.get("parent_periph_id") == periph_id
    #     ]
    #     _LOGGER.info("🔍 Found %d children for device 1269454: %s", 
    #                 len(children), [c["name"] for c in children])
    #     
    #     # Count children with usage_id=1
    #     usage_id_1_children = [
    #         child for child_id, child in all_devices.items()
    #         if child.get("parent_periph_id") == periph_id and child.get("usage_id") == "1"
    #     ]
    #     _LOGGER.info("🔍 Found %d children with usage_id=1: %s", 
    #                 len(usage_id_1_children), [c["name"] for c in usage_id_1_children])
        
        # Handle both list and dict formats for advanced_rules
        _LOGGER.error("🚨 FORCED DEBUG (v%s): About to handle advanced rules - periph_id=%s", VERSION, periph_id)
        # FORCED DEBUG: Log before rule conversion
        if periph_id == "1269454":
            _LOGGER.error("🚨 FORCED DEBUG (v%s): Before rule conversion", VERSION)
            _LOGGER.error("🚨 FORCED DEBUG (v%s): DEVICE_MAPPINGS.get('advanced_rules') type: %s", 
                         VERSION, type(DEVICE_MAPPINGS.get('advanced_rules')))
            _LOGGER.error("🚨 FORCED DEBUG (v%s): DEVICE_MAPPINGS.get('advanced_rules') value: %s", 
                         VERSION, DEVICE_MAPPINGS.get('advanced_rules'))
            _LOGGER.error("🚨 FORCED DEBUG: DEVICE_MAPPINGS keys: %s", list(DEVICE_MAPPINGS.keys()))
        
        advanced_rules_dict = {}
        if isinstance(DEVICE_MAPPINGS.get('advanced_rules'), list):
            # Convert list of rules to dict format for compatibility
            for rule in DEVICE_MAPPINGS.get('advanced_rules', []):
                if isinstance(rule, dict) and 'name' in rule:
                    advanced_rules_dict[rule['name']] = rule
        else:
            advanced_rules_dict = DEVICE_MAPPINGS.get('advanced_rules', {})
        
        # Debug: Log if advanced_rules_dict is empty
        if not advanced_rules_dict:
            _LOGGER.error("❌ CRITICAL: advanced_rules_dict is empty for device %s (%s)", 
                         periph_name, periph_id)
            _LOGGER.error("❌ This means no advanced rules will be evaluated!")
        else:
            _LOGGER.debug("✅ advanced_rules_dict has %d rules for device %s (%s)", 
                         len(advanced_rules_dict), periph_name, periph_id)
            _LOGGER.debug("✅ Rule names: %s", list(advanced_rules_dict.keys()))
        
        # FORCED DEBUG: Log before rule evaluation
        if periph_id == "1269454":
            _LOGGER.error("🚨 FORCED DEBUG: About to evaluate %d rules", len(advanced_rules_dict))
            _LOGGER.error("🚨 FORCED DEBUG: Rule names: %s", list(advanced_rules_dict.keys()))
            
            # FORCED DEBUG: Check if rgbw_lamp_with_children rule exists
            if 'rgbw_lamp_with_children' in advanced_rules_dict:
                _LOGGER.error("🚨 FORCED DEBUG (v%s): rgbw_lamp_with_children rule found!", VERSION)
                _LOGGER.error("🚨 FORCED DEBUG (v%s): Rule config: %s", VERSION, advanced_rules_dict['rgbw_lamp_with_children'])
            else:
                _LOGGER.error("🚨 FORCED DEBUG (v%s): rgbw_lamp_with_children rule NOT FOUND!", VERSION)
        
        # FORCED DEBUG: Confirm we're entering the advanced rules loop
        if periph_id == "1269454":
            _LOGGER.error("🚨 FORCED DEBUG (v%s): Entering advanced rules loop with %d rules", VERSION, len(advanced_rules_dict))
            _LOGGER.error("🚨 FORCED DEBUG (v%s): Rules to evaluate: %s", VERSION, list(advanced_rules_dict.keys()))
        
        for rule_name, rule_config in advanced_rules_dict.items():
            # Debug: Log which rule is being evaluated
            _LOGGER.debug("🔍 Evaluating rule '%s' for device %s (%s)", 
                         rule_name, periph_name, periph_id)
            
            # Special debug for RGBW rules
            if periph_id == "1269454" and rule_name in ["rgbw_lamp_with_children", "rgbw_lamp_flexible"]:
                _LOGGER.error("🚨 FORCED DEBUG: Evaluating RGBW rule '%s' for device 1269454", rule_name)
            
            # Check if we have a condition function or conditions list
            if "condition" in rule_config:
                # Use the condition function if provided
                _LOGGER.debug("🔍 Using condition function for rule '%s'", rule_name)
                condition_result = rule_config["condition"](device_data, all_devices)
            elif "conditions" in rule_config:
                # Evaluate conditions list from YAML
                _LOGGER.debug("🔍 Using conditions list for rule '%s'", rule_name)
                condition_result = True
                for condition in rule_config["conditions"]:
                    for cond_key, cond_value in condition.items():
                        if cond_key == "usage_id":
                            if device_data.get("usage_id") != cond_value:
                                condition_result = False
                                break
                        elif cond_key == "min_children":
                            if not all_devices:
                                condition_result = False
                                break
                            children = [
                                child for child_id, child in all_devices.items()
                                if child.get("parent_periph_id") == periph_id
                            ]
                            if len(children) < int(cond_value):
                                condition_result = False
                                break


                        elif cond_key == "child_usage_id":
                            if not all_devices:
                                condition_result = False
                                break
                            children = [
                                child for child_id, child in all_devices.items()
                                if child.get("parent_periph_id") == periph_id and child.get("usage_id") == cond_value
                            ]
                            if len(children) < 1:
                                condition_result = False
                                break
                        elif cond_key == "PRODUCT_TYPE_ID":
                            if device_data.get("PRODUCT_TYPE_ID") != cond_value:
                                condition_result = False
                                break
                        elif cond_key == "has_parent":
                            if not device_data.get("parent_periph_id"):
                                condition_result = False
                                break
                        elif cond_key == "parent_usage_id":
                            if not device_data.get("parent_periph_id"):
                                condition_result = False
                                break
                            parent_id = device_data.get("parent_periph_id")
                            parent = all_devices.get(parent_id, {})
                            if parent.get("usage_id") != cond_value:
                                condition_result = False
                                break
                        elif cond_key == "parent_has_min_children":
                            if not device_data.get("parent_periph_id"):
                                condition_result = False
                                break
                            parent_id = device_data.get("parent_periph_id")
                            parent_children = [
                                child for child_id, child in all_devices.items()
                                if child.get("parent_periph_id") == parent_id
                            ]
                            if len(parent_children) < int(cond_value):
                                condition_result = False
                                break
                        elif cond_key == "has_children_with_names":
                            if not all_devices:
                                condition_result = False
                                break
                            # Check if device has children with specific names
                            required_names = cond_value if isinstance(cond_value, list) else [cond_value]
                            children = [
                                child for child_id, child in all_devices.items()
                                if child.get("parent_periph_id") == periph_id
                            ]
                            child_names = [child.get("name", "").lower() for child in children]
                            
                            # Special debug for device 1269454
                            if periph_id == "1269454":
                                _LOGGER.error("🚨 FORCED DEBUG: has_children_with_names condition")
                                _LOGGER.error("🚨 FORCED DEBUG:   Required names: %s", required_names)
                                _LOGGER.error("🚨 FORCED DEBUG:   Child names: %s", child_names)
                                _LOGGER.error("🚨 FORCED DEBUG:   Checking each required name:")
                                for required_name in required_names:
                                    found = any(required_name.lower() in child_name for child_name in child_names)
                                    _LOGGER.error("🚨 FORCED DEBUG:     '%s' found: %s", required_name, found)
                                    if found:
                                        matching_children = [name for name in child_names if required_name.lower() in name]
                                        _LOGGER.error("🚨 FORCED DEBUG:       Matching children: %s", matching_children)
                            
                            # Check if all required names are present in children
                            all_found = all(
                                any(required_name.lower() in child_name for child_name in child_names)
                                for required_name in required_names
                            )
                            
                            if not all_found:
                                condition_result = False
                                # Special debug for device 1269454
                                if periph_id == "1269454":
                                    _LOGGER.error("🚨 FORCED DEBUG: has_children_with_names FAILED")
                                    missing_names = [name for name in required_names if not any(name.lower() in child_name for child_name in child_names)]
                                    _LOGGER.error("🚨 FORCED DEBUG:   Missing names: %s", missing_names)
                                break
                        else:
                            _LOGGER.warning("Unknown condition key: %s", cond_key)
                            condition_result = False
                            break
                    if not condition_result:
                        break
            else:
                _LOGGER.warning("No condition or conditions found in rule: %s", rule_name)
                condition_result = False
            
            _LOGGER.debug("Advanced rule '%s' for %s (%s): condition_result=%s",
                         rule_name, periph_name, periph_id, condition_result)
            
            # Special debug for device 1269454
            if periph_id == "1269454":
                _LOGGER.error("🚨 FORCED DEBUG: Rule '%s' condition result: %s", rule_name, condition_result)
                if rule_name == "rgbw_lamp_with_children":
                    _LOGGER.error("🚨 FORCED DEBUG: RGBW rule condition breakdown:")
                    _LOGGER.error("🚨 FORCED DEBUG:   - usage_id check: %s (expected: 1, actual: %s)", 
                                device_data.get("usage_id") == "1", device_data.get("usage_id"))
                    _LOGGER.error("🚨 FORCED DEBUG:   - PRODUCT_TYPE_ID check: %s (expected: 2304, actual: %s)", 
                                device_data.get("PRODUCT_TYPE_ID") == "2304", device_data.get("PRODUCT_TYPE_ID"))
                    child_count = sum(1 for child_id, child in all_devices.items()
                                     if child.get("parent_periph_id") == periph_id)
                    _LOGGER.error("🚨 FORCED DEBUG:   - child count check: %s (expected: >=1, actual: %d)", 
                                child_count >= 1, child_count)
                elif rule_name == "rgbw_lamp_flexible":
                    _LOGGER.error("🚨 FORCED DEBUG: Flexible RGBW rule condition breakdown:")
                    _LOGGER.error("🚨 FORCED DEBUG:   - usage_id check: %s (expected: 1, actual: %s)", 
                                device_data.get("usage_id") == "1", device_data.get("usage_id"))
                    total_children = len([child for child_id, child in all_devices.items()
                                        if child.get("parent_periph_id") == periph_id])
                    _LOGGER.error("🚨 FORCED DEBUG:   - min_children check: %s (expected: >=4, actual: %d)", 
                                total_children >= 4, total_children)
                    _LOGGER.error("🚨 FORCED DEBUG:   - SUPPORTED_CLASSES: %s", device_data.get("SUPPORTED_CLASSES", "N/A"))
                    _LOGGER.error("🚨 FORCED DEBUG:   - PRODUCT_TYPE_ID: %s", device_data.get("PRODUCT_TYPE_ID", "N/A"))
                    _LOGGER.error("🚨 FORCED DEBUG:   - Device name: %s", device_data.get("name", "N/A"))
                    
                    # Check children names
                    children = [child for child_id, child in all_devices.items()
                               if child.get("parent_periph_id") == periph_id]
                    _LOGGER.error("🚨 FORCED DEBUG:   - Children: %s", [c.get("name") for c in children])
            
            if condition_result:
                # Log spécifique pour le débogage RGBW
                if rule_name == "rgbw_lamp_with_children":
                    rgbw_children = [
                        child for child_id, child in all_devices.items()
                        if child.get("parent_periph_id") == periph_id and child.get("usage_id") == "1"
                    ]
                    _LOGGER.debug("RGBW detection for %s (%s): found %d children with usage_id=1: %s",
                                periph_name, periph_id, len(rgbw_children),
                                [c["name"] for c in rgbw_children])
                
                # Special debug for device 1269454
                if periph_id == "1269454":
                    _LOGGER.error("🚨 FORCED DEBUG: RGBW RULE APPLIED for device 1269454!")
                    _LOGGER.error("🚨 FORCED DEBUG: Mapping result: %s:%s", 
                                rule_config["ha_entity"], rule_config["ha_subtype"])
                    _LOGGER.error("🚨 FORCED DEBUG: Justification: %s", rule_config["justification"])
                
                return _create_mapping(rule_config, periph_name, periph_id, rule_name, "🎯 Advanced rule")
    
    # Priorité 2: Cas spécifiques critiques (usage_id)
    specific_cases = {
        "27": ("binary_sensor", "smoke", "🔥 Smoke detector", "fire"),
        "23": ("sensor", "cpu_usage", "💻 CPU monitor", "info"),
        "37": ("binary_sensor", "motion", "🚶 Motion sensor", "walking"),
    }
    
    if usage_id in specific_cases:
        ha_entity, ha_subtype, log_msg, emoji = specific_cases[usage_id]
        return _create_mapping(
            {"ha_entity": ha_entity, "ha_subtype": ha_subtype, "justification": f"{log_msg}: usage_id={usage_id}"},
            periph_name, periph_id, usage_id, emoji
        )
    
    # Priorité 3: Mapping basé sur usage_id
    if usage_id and DEVICE_MAPPINGS and usage_id in DEVICE_MAPPINGS['usage_id_mappings']:
        mapping = DEVICE_MAPPINGS['usage_id_mappings'][usage_id].copy()
        
        # Special debug for device 1269454
        if periph_id == "1269454":
            _LOGGER.error("🚨 FORCED DEBUG: Usage ID mapping for device 1269454: usage_id=%s → %s:%s",
                        usage_id, mapping["ha_entity"], mapping["ha_subtype"])
            _LOGGER.error("🚨 FORCED DEBUG: This means advanced rules were NOT applied!")
        
        # Appliquer les règles avancées si définies
        if "advanced_rules" in mapping:
            for rule_name in mapping["advanced_rules"]:
                if DEVICE_MAPPINGS and rule_name in DEVICE_MAPPINGS['advanced_rules']:
                    rule_config = DEVICE_MAPPINGS['advanced_rules'][rule_name]
                    advanced_rule_result = rule_config["condition"](device_data, all_devices or {})
                    
                    # Special debug for device 1269454
                    if periph_id == "1269454":
                        _LOGGER.info("🔍 Advanced rule '%s' for usage_id mapping: %s", 
                                    rule_name, advanced_rule_result)
                    
                    if advanced_rule_result:
                        mapping.update({
                            "ha_entity": rule_config["ha_entity"],
                            "ha_subtype": rule_config["ha_subtype"],
                            "justification": f"Advanced rule {rule_name}: {rule_config['justification']}",
                        })
                        _LOGGER.info("🎯 Advanced rule applied: %s (%s) → %s:%s", 
                                   periph_name, periph_id, mapping["ha_entity"], mapping["ha_subtype"])
                        break
        
        _LOGGER.debug("Usage ID mapping: %s (%s) → %s:%s", 
                     periph_name, periph_id, mapping["ha_entity"], mapping["ha_subtype"])
        
        # Special debug for device 1269454
        if periph_id == "1269454":
            _LOGGER.info("🔍 FINAL mapping decision for device 1269454: %s:%s",
                        mapping["ha_entity"], mapping["ha_subtype"])
            _LOGGER.info("🔍 Justification: %s", mapping["justification"])
        
        return mapping
    
    # Priorité 4: Détection par nom (YAML patterns)
    name_lower = device_data["name"].lower()
    
    # Check YAML name patterns first
    for pattern in NAME_PATTERNS:
        if re.search(pattern['pattern'], name_lower, re.IGNORECASE):
            mapping = {
                "ha_entity": pattern['ha_entity'],
                "ha_subtype": pattern['ha_subtype'],
                "justification": f"Name pattern match: {pattern['pattern']}",
                "device_class": pattern.get('device_class'),
                "icon": pattern.get('icon')
            }
            _LOGGER.info("🎯 Name pattern matched: %s (%s) → %s:%s (pattern: %s)",
                        periph_name, periph_id, mapping["ha_entity"], mapping["ha_subtype"], pattern['pattern'])
            return mapping
    
    # Legacy name detection (can be removed in future)
    if "message" in name_lower and "box" in name_lower:
        return _create_mapping(
            {"ha_entity": "sensor", "ha_subtype": "text", 
             "justification": f"Message box: {device_data['name']}"},
            periph_name, periph_id, "message", "📝"
        )
    
    # Priorité 5: Mapping par défaut (YAML fallback)
    try:
        yaml_config = load_yaml_mappings()
        if yaml_config and 'default_mapping' in yaml_config:
            default_config = yaml_config['default_mapping']
            mapping = {
                "ha_entity": default_config['ha_entity'],
                "ha_subtype": default_config['ha_subtype'],
                "justification": default_config['justification'],
                "device_class": default_config.get('device_class'),
                "icon": default_config.get('icon')
            }
        else:
            mapping = {
                "ha_entity": default_ha_entity,
                "ha_subtype": "unknown",
                "justification": "No matching rule found"
            }
    except Exception as e:
        _LOGGER.error("Failed to load default mapping from YAML: %s", e)
        mapping = {
            "ha_entity": default_ha_entity,
            "ha_subtype": "unknown",
            "justification": "No matching rule found"
        }
    
    # Special debug for device 1269454 if it reaches default mapping
    if periph_id == "1269454":
        _LOGGER.error("❌ CRITICAL: Device 1269454 reached default mapping!")
        _LOGGER.error("❌ This means RGBW detection failed - device will be wrongly mapped")
        _LOGGER.error("❌ Final mapping: %s:%s", mapping["ha_entity"], mapping["ha_subtype"])
        _LOGGER.error("❌ Device data: %s", device_data)
    
    _LOGGER.warning("❓ Unknown device: %s (%s) → %s:%s. Data: %s",
                    periph_name, periph_id, mapping["ha_entity"], mapping["ha_subtype"], device_data)
    return mapping

def _create_mapping(mapping_config, periph_name, periph_id, context, emoji="🎯"):
    """Crée un mapping standardisé avec logging approprié."""
    mapping = {
        "ha_entity": mapping_config["ha_entity"],
        "ha_subtype": mapping_config["ha_subtype"],
        "justification": mapping_config["justification"]
    }
    
    log_method = _LOGGER.info if emoji != "❓" else _LOGGER.warning
    log_method("%s %s mapping: %s (%s) → %s:%s", 
               emoji, context, periph_name, periph_id, mapping["ha_entity"], mapping["ha_subtype"])
    
    # Debug logging pour le suivi du processus de mapping
    _LOGGER.debug("Mapping decision details for %s (%s): method=%s, result=%s:%s, justification=%s",
                  periph_name, periph_id, context, mapping["ha_entity"], mapping["ha_subtype"],
                  mapping["justification"])
    
    return mapping
