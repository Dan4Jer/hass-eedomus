"""Configuration Manager for Eedomus Integration with HA 2026 features."""

import logging
import asyncio
from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN,
    YAML_MAPPING_SCHEMA,
    CONF_USE_YAML,
    CONF_CUSTOM_DEVICES,
    CONF_YAML_CONTENT,
)

_LOGGER = logging.getLogger(__name__)


class EedomusConfigManager:
    """Central configuration management with HA 2026 features."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the configuration manager."""
        self.hass = hass
        self.store = Store(hass, 1, f"{DOMAIN}.config")
        self._unsubscribe_config_updated = None
        self._unsubscribe_periodic_save = None
        self._config_cache: Dict[str, Any] = {}
        self._initialized = False
    
    async def async_init(self) -> None:
        """Initialize the configuration manager."""
        try:
            # Load existing configuration
            await self.store.async_load()
            
            # Cache current configuration
            # Note: Store doesn't have .data attribute, we need to use .async_load() result
            stored_data = await self.hass.async_add_executor_job(
                lambda: self.store._data  # Access internal data
            )
            
            if stored_data:
                self._config_cache = dict(stored_data)
            else:
                # Initialize with default structure
                self._config_cache = {
                    "metadata": {"version": "1.0"},
                    CONF_CUSTOM_DEVICES: [],
                    "custom_dynamic_entity_properties": {},
                    "custom_specific_device_dynamic_overrides": {}
                }
            
            # Register event listener for config updates
            @callback
            def _handle_config_updated(event):
                """Handle configuration updated events."""
                self.hass.async_create_task(self._async_handle_config_updated(event))
            
            self._unsubscribe_config_updated = self.hass.helpers.event.async_track_state_change(
                self.hass.states.all(),
                _handle_config_updated
            )
            
            # Set up periodic auto-save (every 5 minutes)
            self._unsubscribe_periodic_save = async_track_time_interval(
                self.hass,
                self._async_auto_save,
                asyncio.timedelta(minutes=5)
            )
            
            self._initialized = True
            _LOGGER.info("Eedomus ConfigManager initialized successfully")
            
        except Exception as e:
            _LOGGER.error(f"Failed to initialize ConfigManager: {e}")
            raise
    
    async def async_shutdown(self) -> None:
        """Clean up resources."""
        # Unsubscribe from events
        if self._unsubscribe_config_updated:
            self._unsubscribe_config_updated()
        if self._unsubscribe_periodic_save:
            self._unsubscribe_periodic_save()
        
        # Final save before shutdown
        await self.async_save_configuration()
        
        _LOGGER.debug("Eedomus ConfigManager shutdown complete")
    
    async def _async_handle_config_updated(self, event) -> None:
        """Handle configuration updated events."""
        # Check if this is a configuration-related event
        if event.data.get("entity_id") and event.data["entity_id"].startswith(f"{DOMAIN}."):
            _LOGGER.debug(f"Configuration-related event detected: {event.data['entity_id']}")
            # Add logic here to handle specific configuration changes
    
    async def _async_auto_save(self, now) -> None:
        """Periodic auto-save of configuration."""
        if self._config_cache:
            await self.async_save_configuration()
            _LOGGER.debug("Periodic auto-save completed")
    
    async def async_get_configuration(self) -> Dict[str, Any]:
        """Get current configuration with HA 2026 storage."""
        if not self._initialized:
            await self.async_init()
        
        return dict(self._config_cache)
    
    async def async_save_configuration(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """Save configuration using HA 2026 storage."""
        try:
            # Use provided config or cached config
            config_to_save = config if config is not None else self._config_cache
            
            # Validate against schema
            self._validate_configuration(config_to_save)
            
            # Update cache
            self._config_cache = dict(config_to_save)
            
            # Use HA 2026 storage
            await self.hass.async_add_executor_job(
                lambda: setattr(self.store, '_data', config_to_save)
            )
            await self.store.async_save()
            
            # Fire config updated event
            self.hass.bus.async_fire(
                f"{DOMAIN}_config_updated",
                {"config": config_to_save}
            )
            
            _LOGGER.info("Configuration saved successfully")
            return True
            
        except (vol.Invalid, cv.Invalid) as e:
            _LOGGER.error(f"Configuration validation failed: {e}")
            return False
        except Exception as e:
            _LOGGER.error(f"Failed to save configuration: {e}")
            return False
    
    def _validate_configuration(self, config: Dict[str, Any]) -> None:
        """Validate configuration against schema."""
        try:
            # Validate against the main YAML schema
            YAML_MAPPING_SCHEMA(config)
            _LOGGER.debug("Configuration validation successful")
        except (vol.Invalid, cv.Invalid) as e:
            _LOGGER.error(f"Configuration validation error: {e}")
            raise
    
    async def async_update_configuration(self, updates: Dict[str, Any]) -> bool:
        """Update specific configuration values."""
        try:
            # Get current config
            current_config = await self.async_get_configuration()
            
            # Apply updates
            current_config.update(updates)
            
            # Save updated config
            return await self.async_save_configuration(current_config)
            
        except Exception as e:
            _LOGGER.error(f"Failed to update configuration: {e}")
            return False
    
    async def async_get_yaml_content(self) -> str:
        """Get YAML content from configuration."""
        import yaml
        
        config = await self.async_get_configuration()
        try:
            return yaml.dump(
                config,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )
        except Exception as e:
            _LOGGER.error(f"Failed to generate YAML content: {e}")
            return ""
    
    async def async_load_yaml_content(self, yaml_content: str) -> bool:
        """Load configuration from YAML content."""
        import yaml
        
        try:
            # Parse YAML
            config = yaml.safe_load(yaml_content) or {}
            
            # Validate
            self._validate_configuration(config)
            
            # Save
            return await self.async_save_configuration(config)
            
        except yaml.YAMLError as e:
            _LOGGER.error(f"YAML parsing error: {e}")
            return False
        except Exception as e:
            _LOGGER.error(f"Failed to load YAML configuration: {e}")
            return False
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration value."""
        return self._config_cache.get(key, default)
    
    def set_config_value(self, key: str, value: Any) -> None:
        """Set a specific configuration value (not persisted until save)."""
        self._config_cache[key] = value
    
    async def async_reset_to_defaults(self) -> bool:
        """Reset configuration to defaults."""
        try:
            default_config = {
                "metadata": {"version": "1.0"},
                CONF_CUSTOM_DEVICES: [],
                "custom_dynamic_entity_properties": {},
                "custom_specific_device_dynamic_overrides": {}
            }
            
            return await self.async_save_configuration(default_config)
            
        except Exception as e:
            _LOGGER.error(f"Failed to reset configuration: {e}")
            return False
    
    async def async_backup_configuration(self) -> Dict[str, Any]:
        """Create a backup of current configuration."""
        import copy
        return copy.deepcopy(self._config_cache)
    
    async def async_restore_configuration(self, backup: Dict[str, Any]) -> bool:
        """Restore configuration from backup."""
        try:
            # Validate backup
            self._validate_configuration(backup)
            
            # Restore
            self._config_cache = dict(backup)
            await self.store.async_save()
            
            _LOGGER.info("Configuration restored from backup")
            return True
            
        except Exception as e:
            _LOGGER.error(f"Failed to restore configuration: {e}")
            return False