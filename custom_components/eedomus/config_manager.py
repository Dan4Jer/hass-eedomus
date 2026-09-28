"""Configuration Manager for Eedomus Integration with HA 2026 features."""

import logging
from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_time_interval, async_track_state_change_event
from homeassistant.helpers import config_validation as cv
from datetime import timedelta
import voluptuous as vol

from .const import (
    DOMAIN,
    YAML_MAPPING_SCHEMA,
    CONF_USE_YAML,
    CONF_CUSTOM_DEVICES,
)

_LOGGER = logging.getLogger(__name__)


class EedomusConfigManager:
    """Central configuration management with HA 2026 features."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the configuration manager."""
        self.hass = hass
        self.store = Store(hass, 1, f"{DOMAIN}.config")
        # Version archive for the panel Historique tab (CAP-5): the three
        # most recent custom mapping versions live in HA storage.
        self.versions_store = Store(hass, 1, f"{DOMAIN}.mapping_versions")
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
            
            self._unsubscribe_config_updated = async_track_state_change_event(
                self.hass,
                [f"{DOMAIN}.*"],
                _handle_config_updated
            )
            
            # Set up periodic auto-save (every 5 minutes)
            self._unsubscribe_periodic_save = async_track_time_interval(
                self.hass,
                self._async_auto_save,
                timedelta(minutes=5)
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
        try:
            await self.async_save_configuration()
        except Exception as e:
            _LOGGER.error(f"Failed to save configuration during shutdown: {e}")
        
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
            await self.store.async_save(config_to_save)
            
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
    async def async_get_custom_mapping(self) -> Dict[str, Any]:
        """Return the raw custom mapping the pipeline actually loads.

        This is the config-dir custom_mapping.yaml when it exists (the
        panel's save target), otherwise the file shipped with the
        integration. The merged config must never be exposed here: it
        mixes in the default mapping.
        """
        from .device_mapping import load_custom_yaml_mappings_async

        return await load_custom_yaml_mappings_async(self.hass) or {}

    async def async_save_custom_mapping(
        self, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Persist the custom mapping to the config-dir file.

        Validates against the mapping schema, archives the version being
        replaced in HA storage (three versions kept, oldest purged on the
        fourth save), then writes the new content outside the integration
        tree so a git-based deployment checkout stays clean.

        Returns:
            {"success": bool, "error": str | None, "path": str | None}
        """
        import os

        import yaml

        try:
            self._validate_configuration(config)
        except (vol.Invalid, cv.Invalid) as e:
            _LOGGER.error("Custom mapping validation failed: %s", e)
            return {"success": False, "error": str(e), "path": None}

        from .device_mapping import get_config_dir_custom_mapping_path

        path = get_config_dir_custom_mapping_path(self.hass)

        try:
            current = await self.async_get_custom_mapping()
            if current:
                await self.async_archive_mapping_version(current)

            def _write() -> None:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(
                        yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
                    )

            await self.hass.async_add_executor_job(_write)
        except Exception as e:
            _LOGGER.error("Failed to save custom mapping: %s", e)
            return {"success": False, "error": str(e), "path": path}

        _LOGGER.info("Custom mapping saved to %s", path)
        return {"success": True, "error": None, "path": path}

    async def async_archive_mapping_version(self, config: Dict[str, Any]) -> bool:
        """Archive a mapping version in HA storage (three kept).

        The fourth save purges the oldest. The panel Historique tab
        (P.1.6) reads these versions back.
        """
        from datetime import datetime

        data = await self.versions_store.async_load() or {}
        versions = list(data.get("versions") or [])
        versions.insert(
            0,
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "config": config,
            },
        )
        versions = versions[:3]
        await self.versions_store.async_save({"versions": versions})
        return True

    async def async_get_mapping_versions(self) -> list:
        """Return the archived mapping versions, newest first."""
        data = await self.versions_store.async_load() or {}
        return list(data.get("versions") or [])
