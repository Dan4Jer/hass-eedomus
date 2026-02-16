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
from .mapping_registry import register_device_mapping, get_mapping_registry, print_mapping_table, print_mapping_summary
from .mapping_rules import evaluate_conditions

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
        else:
            self._attr_name = periph_data.get("name", f"Unknown Device ({periph_id})")
            self._parent_id = periph_data.get("parent_periph_id", None)
            self._attr_unique_id = f"{periph_id}"

    def _get_periph_data(self, periph_id: str = None):
        """Get peripheral data from coordinator."""
        if not hasattr(self.coordinator, 'data') or not self.coordinator.data:
            return None
        # Use self._periph_id if no periph_id is provided
        periph_id = periph_id or self._periph_id
        return self.coordinator.data.get(periph_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        periph_data = self._get_periph_data(self._periph_id)
        if not periph_data:
            return DeviceInfo(
                identifiers={(DOMAIN, self._periph_id)},
                name=f"Unknown Device ({self._periph_id})",
                manufacturer="Eedomus",
            )
        
        device_name = periph_data.get("name", f"Unknown Device ({self._periph_id})")
        parent_id = periph_data.get("parent_periph_id")
        
        # If this device has a parent, use the parent's info
        if parent_id and hasattr(self.coordinator, 'data') and parent_id in self.coordinator.data:
            parent_data = self.coordinator.data[parent_id]
            parent_name = parent_data.get("name", f"Unknown Parent ({parent_id})")
            
            return DeviceInfo(
                identifiers={(DOMAIN, parent_id)},
                name=parent_name,
                manufacturer="Eedomus",
                model=parent_data.get("usage_name", "Unknown"),
                via_device=(DOMAIN, "eedomus_box_main"),
            )
        
        # Otherwise, use this device's info
        return DeviceInfo(
            identifiers={(DOMAIN, self._periph_id)},
            name=device_name,
            manufacturer="Eedomus",
            model=periph_data.get("usage_name", "Unknown"),
            via_device=(DOMAIN, "eedomus_box_main"),
        )

    async def async_update(self):
        """Update the entity state."""
        await self.coordinator.async_request_refresh()

    async def async_added_to_hass(self):
        """Call when the entity is added to Home Assistant."""
        await super().async_added_to_hass()
        # Schedule a regular update to ensure consistency
        self.async_schedule_update_ha_state()


    async def async_set_value(self, value: str) -> dict | None:
        """Set the value of the peripheral using the eedomus service.
        
        Args:
            value: The value to set (string representation)
            
        Returns:
            The response from the service call, or None if service not available
        """
        try:
            # Call the eedomus.set_value service
            # Note: return_response=False because the service doesn't return responses
            return await self.hass.services.async_call(
                DOMAIN,
                "set_value",
                {
                    "device_id": self._periph_id,
                    "value": value,
                },
                blocking=True,
                return_response=False,
            )
        except Exception as e:
            _LOGGER.error(
                "Failed to set value for %s (periph_id=%s) to %s: %s",
                self._attr_name,
                self._periph_id,
                value,
                e,
            )
            return None

def map_device_to_ha_entity(device_data, all_devices=None, default_ha_entity: str = "sensor"):
    """Mappe un périphérique eedomus vers une entité Home Assistant.
    
    Logique de mapping simplifiée et optimisée :
    1. Règles avancées (relations parent-enfant)
    2. Cas spécifiques prioritaires (usage_id)
    3. Mapping basé sur usage_id
    4. Détection par nom (dernier recours)
    5. Mapping par défaut
    """
    periph_id = device_data["periph_id"]
    periph_name = device_data["name"]
    usage_id = device_data.get("usage_id")
    
    _LOGGER.debug("Mapping device: %s (%s, usage_id=%s)", periph_name, periph_id, usage_id)
    
    # Debug spécifique pour le device 1269454 (RGBW connu)
    if periph_id == "1269454":
        _LOGGER.debug("🔍 SPECIAL DEBUG: Starting advanced rules evaluation for RGBW device 1269454")
    
    # Fix: Ensure all_devices is never None or empty - create empty dict if needed
    if all_devices is None or not all_devices:
        _LOGGER.warning("⚠️  all_devices is None or empty, creating empty dict to allow advanced rules evaluation")
        all_devices = {}
    
    # Priorité 1: Règles avancées (nécessite all_devices)
    # Use the pre-converted dict format from device_mapping.py
    if periph_id == "1269454":
        _LOGGER.debug("SPECIAL DEBUG (v%s): Device 1269454 - advanced_rules type: %s", 
                     VERSION, type(DEVICE_MAPPINGS.get('advanced_rules')))
        _LOGGER.debug("SPECIAL DEBUG (v%s): Device 1269454 - advanced_rules_dict type: %s", 
                     VERSION, type(DEVICE_MAPPINGS.get('advanced_rules_dict')))
        _LOGGER.debug("SPECIAL DEBUG (v%s): Device 1269454 - advanced_rules_dict content: %s", 
                     VERSION, DEVICE_MAPPINGS.get('advanced_rules_dict'))
    
    # Use the pre-converted dict format if available, otherwise fall back to old conversion
    if 'advanced_rules_dict' in DEVICE_MAPPINGS and isinstance(DEVICE_MAPPINGS['advanced_rules_dict'], dict):
        advanced_rules_dict = DEVICE_MAPPINGS['advanced_rules_dict']
        _LOGGER.debug("✅ Using pre-converted advanced_rules_dict with %d rules", len(advanced_rules_dict))
    else:
        # Fallback to old conversion method for backward compatibility
        advanced_rules_dict = {}
        if isinstance(DEVICE_MAPPINGS.get('advanced_rules'), list):
            # Convert list of rules to dict format for compatibility
            for rule in DEVICE_MAPPINGS.get('advanced_rules', []):
                if isinstance(rule, dict) and 'name' in rule:
                    advanced_rules_dict[rule['name']] = rule
        else:
            advanced_rules_dict = DEVICE_MAPPINGS.get('advanced_rules', {})
        _LOGGER.debug("⚠️  Using fallback conversion method for advanced rules")
    
    # Debug: Log if advanced_rules_dict is empty
    if not advanced_rules_dict:
        _LOGGER.error("❌ CRITICAL: advanced_rules_dict is empty for device %s (%s)", 
                     periph_name, periph_id)
        _LOGGER.error("❌ This means no advanced rules will be evaluated!")
    else:
        _LOGGER.debug("✅ advanced_rules_dict has %d rules for device %s (%s)", 
                     len(advanced_rules_dict), periph_name, periph_id)
        _LOGGER.debug("✅ Rule names: %s", list(advanced_rules_dict.keys()))
    
    if periph_id == "1269454":
        _LOGGER.debug("SPECIAL DEBUG: Device 1269454 - checking rgbw_lamp_by_children rule")
        
        if 'rgbw_lamp_by_children' in advanced_rules_dict:
            _LOGGER.debug("SPECIAL DEBUG: rgbw_lamp_by_children rule found")
        else:
            _LOGGER.debug("SPECIAL DEBUG: rgbw_lamp_by_children rule NOT found")
    
    if periph_id == "1269454":
        _LOGGER.debug("SPECIAL DEBUG: Device 1269454 - analyzing children")
    
    for rule_name, rule_config in advanced_rules_dict.items():
        # Debug: Log which rule is being evaluated
        _LOGGER.debug("🔍 Evaluating rule '%s' for device %s (%s)", 
                     rule_name, periph_name, periph_id)
        
        # Special debug for RGBW rules
        if periph_id == "1269454" and rule_name in ["rgbw_lamp_by_children", "rgbw_lamp_flexible"]:
            _LOGGER.debug("SPECIAL DEBUG: Evaluating RGBW rule '%s' for device 1269454", rule_name)
        
        # Check if we have a condition function or conditions list
        if "condition" in rule_config:
            # Use the condition function if provided
            _LOGGER.debug("🔍 Using condition function for rule '%s'", rule_name)
            condition_result = rule_config["condition"](device_data, all_devices)
        elif "conditions" in rule_config:
            # Evaluate conditions list from YAML
            _LOGGER.debug("🔍 Using conditions list for rule '%s'", rule_name)
            condition_result = evaluate_conditions(rule_config["conditions"], device_data, all_devices, periph_id, rule_name)
        else:
            _LOGGER.warning("No condition or conditions found in rule: %s", rule_name)
            condition_result = False
        
        _LOGGER.debug("Advanced rule '%s' for %s (%s): condition_result=%s",
                     rule_name, periph_name, periph_id, condition_result)
        
        # Special debug for device 1269454
        if periph_id == "1269454":
            if rule_name == "rgbw_lamp_by_children":
                _LOGGER.debug("SPECIAL DEBUG: rgbw_lamp_by_children - usage_id check: %s == %s", 
                             device_data.get("usage_id") == "1", device_data.get("usage_id"))
                _LOGGER.debug("SPECIAL DEBUG: rgbw_lamp_by_children - PRODUCT_TYPE_ID check: %s == %s", 
                             device_data.get("PRODUCT_TYPE_ID") == "2304", device_data.get("PRODUCT_TYPE_ID"))
                child_count = sum(1 for child_id, child in all_devices.items()
                                 if child.get("parent_periph_id") == periph_id)
                _LOGGER.debug("SPECIAL DEBUG: rgbw_lamp_by_children - child_count check: %s >= 4", 
                             child_count)
            elif rule_name == "rgbw_lamp_flexible":
                _LOGGER.debug("SPECIAL DEBUG: rgbw_lamp_flexible - usage_id check: %s == %s", 
                             device_data.get("usage_id") == "1", device_data.get("usage_id"))
                total_children = len([child for child_id, child in all_devices.items()
                                    if child.get("parent_periph_id") == periph_id])
                _LOGGER.debug("SPECIAL DEBUG: rgbw_lamp_flexible - total_children check: %s >= 4", 
                             total_children)
                
                # Check children names
                children = [child for child_id, child in all_devices.items()
                           if child.get("parent_periph_id") == periph_id]

        if condition_result:
            # Log spécifique pour le débogage RGBW
            if rule_name == "rgbw_lamp_by_children":
                rgbw_children = [
                    child for child_id, child in all_devices.items()
                    if child.get("parent_periph_id") == periph_id and child.get("usage_id") == "1"
                ]
                _LOGGER.debug("RGBW detection for %s (%s): found %d children with usage_id=1: %s",
                            periph_name, periph_id, len(rgbw_children),
                            [c["name"] for c in rgbw_children])
            
            # Special debug for device 1269454
            if periph_id == "1269454":
                _LOGGER.debug("SPECIAL DEBUG: Device 1269454 - rule mapping: %s/%s", 
                             rule_config["mapping"]["ha_entity"], rule_config["mapping"]["ha_subtype"])
                _LOGGER.debug("✅ rgbw_lamp_by_children rule APPLIED for device 1269454!")
                _LOGGER.debug("✅ Mapping: %s:%s", 
                            rule_config["mapping"]["ha_entity"], rule_config["mapping"]["ha_subtype"])
            
            # Special debug for RGBW children (1269455-1269458)
            if periph_id in ["1269455", "1269456", "1269457", "1269458"]:
                _LOGGER.debug("✅ rgbw_child_brightness rule APPLIED for device %s!", periph_id)
                _LOGGER.debug("✅ Mapping: %s:%s", 
                            rule_config["mapping"]["ha_entity"], rule_config["mapping"]["ha_subtype"])
            
            return _create_mapping(rule_config["mapping"], periph_name, periph_id, rule_name, "🎯 Advanced rule", device_data)
    
    # Priorité 2: Cas spécifiques critiques (usage_id)
    specific_cases = {
        "27": ("binary_sensor", "smoke", "🔥 Smoke detector", "fire"),
        "23": ("sensor", "usage", "📊 Usage monitor", "info"),
        "37": ("binary_sensor", "motion", "🚶 Motion sensor", "walking"),
    }
    
    if usage_id in specific_cases:
        ha_entity, ha_subtype, log_msg, emoji = specific_cases[usage_id]
        return _create_mapping(
            {"ha_entity": ha_entity, "ha_subtype": ha_subtype, "justification": f"{log_msg}: usage_id={usage_id}"},
            periph_name, periph_id, usage_id, emoji, device_data
        )
    
    # Priorité 3: Mapping basé sur usage_id
    if usage_id and DEVICE_MAPPINGS and usage_id in DEVICE_MAPPINGS['usage_id_mappings']:
        mapping = DEVICE_MAPPINGS['usage_id_mappings'][usage_id].copy()
        
        # Special debug for device 1269454
        if periph_id == "1269454":
            _LOGGER.debug("SPECIAL DEBUG: Device 1269454 - final mapping: usage_id=%s, ha_entity=%s, ha_subtype=%s", 
                         usage_id, mapping["ha_entity"], mapping["ha_subtype"])
        
        # Special debug for RGBW children (1269455-1269458)
        if periph_id in ["1269455", "1269456", "1269457", "1269458"]:
            _LOGGER.debug("🔍 SPECIAL DEBUG: RGBW child device %s - usage_id=%s, ha_entity=%s, ha_subtype=%s", 
                        periph_id, usage_id, mapping["ha_entity"], mapping["ha_subtype"])
            _LOGGER.debug("🔍 Device data: %s", device_data)
            
            # Check if parent is RGBW device
            parent_id = device_data.get("parent_periph_id")
            if parent_id and all_devices and parent_id in all_devices:
                parent = all_devices[parent_id]
                _LOGGER.debug("🔍 Parent device %s: name=%s, usage_id=%s", 
                            parent_id, parent.get("name"), parent.get("usage_id"))
                
                # Check if parent is mapped as RGBW
                parent_mapping = map_device_to_ha_entity(parent, all_devices)
                _LOGGER.debug("🔍 Parent mapping: %s:%s", 
                            parent_mapping["ha_entity"], parent_mapping["ha_subtype"])
        
        # Appliquer les règles avancées si définies
        if "advanced_rules" in mapping:
            for rule_name in mapping["advanced_rules"]:
                if DEVICE_MAPPINGS and rule_name in DEVICE_MAPPINGS['advanced_rules']:
                    rule_config = DEVICE_MAPPINGS['advanced_rules'][rule_name]
                    advanced_rule_result = rule_config["condition"](device_data, all_devices or {})
                    
                    # Special debug for device 1269454
                    if periph_id == "1269454":
                        _LOGGER.debug("🔍 Advanced rule '%s' for usage_id mapping: %s", 
                                    rule_name, advanced_rule_result)
                    
                    if advanced_rule_result:
                        mapping.update({
                            "ha_entity": rule_config["mapping"]["ha_entity"],
                            "ha_subtype": rule_config["mapping"]["ha_subtype"],
                            "justification": f"Advanced rule {rule_name}: {rule_config['mapping']['justification']}",
                        })
                        _LOGGER.debug("🎯 Advanced rule applied: %s (%s) → %s:%s", 
                                   periph_name, periph_id, mapping["ha_entity"], mapping["ha_subtype"])
                        break
        
        _LOGGER.debug("Usage ID mapping: %s (%s) → %s:%s", 
                     periph_name, periph_id, mapping["ha_entity"], mapping["ha_subtype"])
        
        # Special debug for device 1269454
        if periph_id == "1269454":
            _LOGGER.debug("🔍 FINAL mapping decision for device 1269454: %s:%s",
                        mapping["ha_entity"], mapping["ha_subtype"])
            _LOGGER.debug("🔍 Justification: %s", mapping["justification"])
        
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
            _LOGGER.debug("🎯 Name pattern matched: %s (%s) → %s:%s (pattern: %s)",
                        periph_name, periph_id, mapping["ha_entity"], mapping["ha_subtype"], pattern['pattern'])
            return mapping
    
    # Legacy name detection (can be removed in future)
    if "message" in name_lower and "box" in name_lower:
        return _create_mapping(
            {"ha_entity": "sensor", "ha_subtype": "text", 
             "justification": f"Message box: {device_data['name']}"},
            periph_name, periph_id, "message", "📝", device_data
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


    """Crée un mapping standardisé avec logging approprié."""
    # mapping_config peut être soit la section 'mapping' directement, soit la règle complète
    # avec une section 'mapping' imbriquée
    if "ha_entity" in mapping_config:
        # Cas 1: mapping_config est la section 'mapping' directement
        mapping = {
            "ha_entity": mapping_config["ha_entity"],
            "ha_subtype": mapping_config["ha_subtype"],
            "justification": mapping_config["justification"]
        }
    elif "mapping" in mapping_config:
        # Cas 2: mapping_config est la règle complète avec une section 'mapping' imbriquée
        mapping = {
            "ha_entity": mapping_config["mapping"]["ha_entity"],
            "ha_subtype": mapping_config["mapping"]["ha_subtype"],
            "justification": mapping_config["mapping"]["justification"]
        }
    else:
        raise ValueError(f"Invalid mapping_config structure: {mapping_config}")
    
    log_method = _LOGGER.info if emoji != "❓" else _LOGGER.warning
    log_method("%s %s mapping: %s (%s) → %s:%s", 
               emoji, context, periph_name, periph_id, mapping["ha_entity"], mapping["ha_subtype"])
    
    # Debug logging pour le suivi du processus de mapping
    _LOGGER.debug("Mapping decision details for %s (%s): method=%s, result=%s:%s, justification=%s",
                  periph_name, periph_id, context, mapping["ha_entity"], mapping["ha_subtype"],
                  mapping["justification"])
    
    # Stocker le mapping dans le registre global
    register_device_mapping(mapping, periph_name, periph_id, device_data)
    async def async_set_value(self, value: str) -> dict | None:
        """Set the value of the peripheral using the eedomus service.
        
        Args:
            value: The value to set (string representation)
            
        Returns:
            The response from the service call, or None if service not available
        """
        try:
            # Call the eedomus.set_value service
            # Note: return_response=False because the service doesn't return responses
            return await self.hass.services.async_call(
                DOMAIN,
                "set_value",
                {
                    "device_id": self._periph_id,
                    "value": value,
                },
                blocking=True,
                return_response=False,
            )
        except Exception as e:
            _LOGGER.error(
                "Failed to set value for %s (periph_id=%s) to %s: %s",
                self._attr_name,
                self._periph_id,
                value,
                e,
            )
            return None

def _create_mapping(mapping_config, periph_name, periph_id, context, emoji="🎯", device_data=None):
    """Crée un mapping standardisé avec logging approprié."""
    # mapping_config peut être soit la section 'mapping' directement, soit la règle complète
    if isinstance(mapping_config, dict) and "mapping" in mapping_config:
        mapping = mapping_config["mapping"]
        justification = mapping_config.get("justification", "No justification provided")
    else:
        mapping = mapping_config
        justification = "No justification provided"
    
    # Ajouter la justification au mapping
    if "justification" not in mapping:
        mapping["justification"] = justification
    
    # Log the mapping decision
    log_method = _LOGGER.info if emoji != "❓" else _LOGGER.warning
    log_method("%s %s mapping: %s (%s) → %s:%s", 
               emoji, context, periph_name, periph_id, mapping["ha_entity"], mapping["ha_subtype"])
    
    # Debug logging pour le suivi du processus de mapping
    _LOGGER.debug("Mapping decision details for %s (%s): method=%s, result=%s:%s, justification=%s",
                  periph_name, periph_id, context, mapping["ha_entity"], mapping["ha_subtype"],
                  mapping["justification"])
    
    # Stocker le mapping dans le registre global
    register_device_mapping(mapping, periph_name, periph_id, device_data)
    
    return mapping
