"""Configuration panel for eedomus device mapping and dynamic properties."""

from __future__ import annotations
import logging
import os
import yaml
import asyncio
from typing import Dict, Any, List, Optional
from homeassistant.components import frontend
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device_mapping import (
    load_yaml_mappings,
    get_dynamic_entity_properties,
    get_specific_device_dynamic_overrides,
    load_and_merge_yaml_mappings
)

_LOGGER = logging.getLogger(__name__)

# Configuration file paths
CONFIG_DIR = "config"
DEFAULT_MAPPING_FILE = os.path.join(CONFIG_DIR, "device_mapping.yaml")
CUSTOM_MAPPING_FILE = os.path.join(CONFIG_DIR, "custom_mapping.yaml")

class EedomusConfigPanel:
    """Main configuration panel for eedomus device mapping and dynamic properties."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the configuration panel."""
        self.hass = hass
        self.current_config = "default"
        self.available_configs = ["default", "custom"]
        self.config_data = {
            "default": self._load_default_config(),
            "custom": self._load_custom_config()
        }
        
    def _load_default_config(self) -> Dict[str, Any]:
        """Load the default configuration from device_mapping.yaml."""
        try:
            config = load_yaml_mappings()
            if not config:
                config = {
                    "dynamic_entity_properties": {
                        "light": True,
                        "switch": True,
                        "binary_sensor": True,
                        "sensor": False,
                        "climate": False,
                        "cover": True,
                        "select": False,
                        "scene": False
                    },
                    "specific_device_dynamic_overrides": {}
                }
            return config
        except Exception as e:
            _LOGGER.error("Failed to load default config: %s", e)
            return {
                "dynamic_entity_properties": {
                    "light": True,
                    "switch": True,
                    "binary_sensor": True,
                    "sensor": False,
                    "climate": False,
                    "cover": True,
                    "select": False,
                    "scene": False
                },
                "specific_device_dynamic_overrides": {}
            }
    
    def _load_custom_config(self) -> Dict[str, Any]:
        """Load the custom configuration from custom_mapping.yaml."""
        try:
            # Load custom mappings
            custom_config = {}
            if os.path.exists(CUSTOM_MAPPING_FILE):
                with open(CUSTOM_MAPPING_FILE, 'r', encoding='utf-8') as file:
                    custom_config = yaml.safe_load(file) or {}
            
            # Merge with default to get complete structure
            default_config = self._load_default_config()
            merged_config = default_config.copy()
            
            # Apply custom overrides
            if 'custom_dynamic_entity_properties' in custom_config:
                merged_config['dynamic_entity_properties'].update(custom_config['custom_dynamic_entity_properties'])
            
            if 'custom_specific_device_dynamic_overrides' in custom_config:
                merged_config['specific_device_dynamic_overrides'].update(
                    custom_config['custom_specific_device_dynamic_overrides']
                )
            
            return merged_config
        except Exception as e:
            _LOGGER.error("Failed to load custom config: %s", e)
            return self._load_default_config()
    
    def switch_config(self, config_name: str) -> bool:
        """Switch to a different configuration."""
        if config_name in self.available_configs:
            self.current_config = config_name
            _LOGGER.info("Switched to %s configuration", config_name)
            return True
        return False
    
    def get_current_config(self) -> Dict[str, Any]:
        """Get the current active configuration."""
        return self.config_data[self.current_config]
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all available configurations."""
        return self.config_data
    
    def update_dynamic_entity_property(self, entity_type: str, is_dynamic: bool) -> bool:
        """Update dynamic property for an entity type."""
        try:
            config = self.get_current_config()
            config['dynamic_entity_properties'][entity_type] = is_dynamic
            
            # Save to appropriate file
            if self.current_config == "custom":
                self._save_custom_config(config)
            
            _LOGGER.info("Updated dynamic property for %s: %s", entity_type, is_dynamic)
            return True
        except Exception as e:
            _LOGGER.error("Failed to update dynamic property: %s", e)
            return False
    
    def update_specific_device_override(self, periph_id: str, is_dynamic: bool) -> bool:
        """Update dynamic override for a specific device."""
        try:
            config = self.get_current_config()
            config['specific_device_dynamic_overrides'][periph_id] = is_dynamic
            
            # Save to appropriate file
            if self.current_config == "custom":
                self._save_custom_config(config)
            
            _LOGGER.info("Updated dynamic override for device %s: %s", periph_id, is_dynamic)
            return True
        except Exception as e:
            _LOGGER.error("Failed to update device override: %s", e)
            return False
    
    def remove_specific_device_override(self, periph_id: str) -> bool:
        """Remove dynamic override for a specific device."""
        try:
            config = self.get_current_config()
            if periph_id in config['specific_device_dynamic_overrides']:
                del config['specific_device_dynamic_overrides'][periph_id]
                
                # Save to appropriate file
                if self.current_config == "custom":
                    self._save_custom_config(config)
                
                _LOGGER.info("Removed dynamic override for device %s", periph_id)
                return True
            return False
        except Exception as e:
            _LOGGER.error("Failed to remove device override: %s", e)
            return False
    
    def _save_custom_config(self, config: Dict[str, Any]) -> bool:
        """Save custom configuration to custom_mapping.yaml."""
        try:
            # Extract only custom parts
            custom_config = {
                "version": 1.0,
                "custom_rules": [],
                "custom_usage_id_mappings": {},
                "custom_name_patterns": [],
                "custom_dynamic_entity_properties": {},
                "custom_specific_device_dynamic_overrides": {}
            }
            
            # Compare with default to find customizations
            default_config = self._load_default_config()
            
            # Find custom dynamic entity properties
            for entity_type, is_dynamic in config['dynamic_entity_properties'].items():
                if entity_type in default_config['dynamic_entity_properties']:
                    if default_config['dynamic_entity_properties'][entity_type] != is_dynamic:
                        custom_config['custom_dynamic_entity_properties'][entity_type] = is_dynamic
                else:
                    custom_config['custom_dynamic_entity_properties'][entity_type] = is_dynamic
            
            # Add all specific device overrides
            custom_config['custom_specific_device_dynamic_overrides'] = config['specific_device_dynamic_overrides']
            
            # Save to file
            with open(CUSTOM_MAPPING_FILE, 'w', encoding='utf-8') as file:
                yaml.dump(custom_config, file, default_flow_style=False, sort_keys=False)
            
            _LOGGER.info("Saved custom configuration to %s", CUSTOM_MAPPING_FILE)
            return True
        except Exception as e:
            _LOGGER.error("Failed to save custom config: %s", e)
            return False
    
    def reload_configuration(self) -> bool:
        """Reload all configurations from files."""
        try:
            self.config_data = {
                "default": self._load_default_config(),
                "custom": self._load_custom_config()
            }
            _LOGGER.info("Reloaded configurations from files")
            return True
        except Exception as e:
            _LOGGER.error("Failed to reload configurations: %s", e)
            return False
    
    def get_device_dynamic_status(self, periph_id: str, ha_entity: str) -> Dict[str, Any]:
        """Get the dynamic status and reasoning for a specific device."""
        config = self.get_current_config()
        
        # Check specific overrides first
        if periph_id in config['specific_device_dynamic_overrides']:
            return {
                "is_dynamic": config['specific_device_dynamic_overrides'][periph_id],
                "reason": "specific_override",
                "source": "custom" if self.current_config == "custom" else "default"
            }
        
        # Check entity type properties
        if ha_entity in config['dynamic_entity_properties']:
            return {
                "is_dynamic": config['dynamic_entity_properties'][ha_entity],
                "reason": "entity_type",
                "source": "custom" if self.current_config == "custom" else "default"
            }
        
        # Fallback to default
        return {
            "is_dynamic": False,
            "reason": "fallback",
            "source": "default"
        }
    
    def get_all_devices_dynamic_status(self, coordinator_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get dynamic status for all devices."""
        devices_status = []
        config = self.get_current_config()
        
        for periph_id, periph_data in coordinator_data.items():
            if not isinstance(periph_data, dict) or "periph_id" not in periph_data:
                continue
                
            ha_entity = periph_data.get("ha_entity")
            device_status = self.get_device_dynamic_status(periph_id, ha_entity)
            device_status.update({
                "periph_id": periph_id,
                "name": periph_data.get("name", "Unknown"),
                "ha_entity": ha_entity,
                "usage_id": periph_data.get("usage_id")
            })
            devices_status.append(device_status)
        
        return devices_status

# Frontend panel registration
async def async_setup_config_panel(hass: HomeAssistant):
    """Set up the configuration panel."""
    # Create config panel instance
    config_panel = EedomusConfigPanel(hass)
    
    # Store in hass data for access from other components
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["config_panel"] = config_panel
    
    _LOGGER.info("Eedomus configuration panel initialized")
    
    # Register frontend panel with robust error handling and retry mechanism
    async def try_register_panel():
        """Try to register the configuration panel with multiple fallback strategies."""
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            
            # Try direct frontend import (modern HA versions)
            try:
                from homeassistant.components import frontend as frontend_module
                if frontend_module is not None:
                    await frontend_module.async_register_built_in_panel(
                        hass,
                        "eedomus-config",
                        "Eedomus Configuration",
                        "mdi:cog-transfer",
                        require_admin=True,
                    )
                    _LOGGER.info("Configuration panel registered successfully (attempt %s)", attempt)
                    return True
            except Exception as e:
                _LOGGER.debug("Direct frontend registration failed (attempt %s): %s", attempt, e)
            
            # Try via hass.components.frontend (fallback)
            try:
                if hasattr(hass.components, 'frontend'):
                    await hass.components.frontend.async_register_built_in_panel(
                        "eedomus-config",
                        "Eedomus Configuration",
                        "mdi:cog-transfer",
                        require_admin=True,
                    )
                    _LOGGER.info("Configuration panel registered via components.frontend (attempt %s)", attempt)
                    return True
            except Exception as e:
                _LOGGER.debug("Components frontend registration failed (attempt %s): %s", attempt, e)
            
            # Wait before retry
            if attempt < max_attempts:
                await asyncio.sleep(1)
        
        return False
    
    # Try to register the panel
    registration_success = await try_register_panel()
    
    if not registration_success:
        _LOGGER.error("Failed to register configuration panel after %s attempts", max_attempts)
        _LOGGER.warning("Configuration panel will not be available in this session")
        _LOGGER.warning("Please restart Home Assistant to retry panel registration")
    
    # Add method to update from options flow
    async def update_from_options(options: dict) -> None:
        """Update configuration from options flow changes."""
        try:
            if "yaml_mapping" in options:
                yaml_config = options["yaml_mapping"]
                if "custom_mapping_file" in yaml_config:
                    # Update the custom mapping file path
                    config_panel._custom_mapping_file = yaml_config["custom_mapping_file"]
                    _LOGGER.info("Updated custom mapping file path from options: %s", 
                                config_panel._custom_mapping_file)
                    
                    # Reload configuration if needed
                    if yaml_config.get("reload_mapping", False):
                        await config_panel.reload_configuration()
                        _LOGGER.info("Configuration reloaded from options flow")
        except Exception as e:
            _LOGGER.error("Failed to update from options flow: %s", e)
    
    # Store update method for external access
    hass.data[DOMAIN]["update_config_from_options"] = update_from_options
    
    return True