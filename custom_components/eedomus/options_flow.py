"""Options flow for eedomus integration."""

from __future__ import annotations

import logging
import os
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_API_PROXY_DISABLE_SECURITY,

    CONF_ENABLE_SET_VALUE_RETRY,
    CONF_ENABLE_WEBHOOK,
    CONF_REMOVE_ENTITIES,
    CONF_SCAN_INTERVAL,
    DEFAULT_API_PROXY_DISABLE_SECURITY,

    DEFAULT_ENABLE_SET_VALUE_RETRY,
    DEFAULT_ENABLE_WEBHOOK,
    DEFAULT_REMOVE_ENTITIES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    # YAML Mapping Configuration
    CONF_YAML_MAPPING,
    CONF_CUSTOM_MAPPING_FILE,
    CONF_RELOAD_MAPPING,
)

_LOGGER = logging.getLogger(__name__)

_LOGGER = logging.getLogger(__name__)


class EedomusOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle eedomus options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        # OptionsFlow handles config_entry automatically, no need to set it
        pass
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return EedomusOptionsFlowHandler(config_entry)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Add menu options for navigation
        menu_options = [
            "configure",  # Main configuration
            "yaml_mapping",  # YAML mapping configuration
            "edit_yaml",  # Edit YAML file directly
        ]

        return self.async_show_form(
            step_id="init",
            menu_options=menu_options,
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLE_SET_VALUE_RETRY,
                        default=self.config_entry.options.get(
                            CONF_ENABLE_SET_VALUE_RETRY,
                            self.config_entry.data.get(
                                CONF_ENABLE_SET_VALUE_RETRY,
                                DEFAULT_ENABLE_SET_VALUE_RETRY,
                            ),
                        ),
                    ): bool,

                    vol.Optional(
                        CONF_ENABLE_WEBHOOK,
                        default=self.config_entry.options.get(
                            CONF_ENABLE_WEBHOOK,
                            self.config_entry.data.get(
                                CONF_ENABLE_WEBHOOK,
                                DEFAULT_ENABLE_WEBHOOK,
                            ),
                        ),
                    ): bool,

                    vol.Optional(
                        CONF_API_PROXY_DISABLE_SECURITY,
                        default=self.config_entry.options.get(
                            CONF_API_PROXY_DISABLE_SECURITY,
                            self.config_entry.data.get(
                                CONF_API_PROXY_DISABLE_SECURITY,
                                DEFAULT_API_PROXY_DISABLE_SECURITY,
                            ),
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL,
                            self.config_entry.data.get(
                                CONF_SCAN_INTERVAL,
                                DEFAULT_SCAN_INTERVAL,
                            ),
                        ),
                    ): int,
                    vol.Optional(
                        CONF_REMOVE_ENTITIES,
                        default=self.config_entry.options.get(
                            CONF_REMOVE_ENTITIES,
                            self.config_entry.data.get(
                                CONF_REMOVE_ENTITIES,
                                DEFAULT_REMOVE_ENTITIES,
                            ),
                        ),
                    ): bool,
                }
            ),
            description_placeholders={
                "explanation": "📋 Configure advanced options for your eedomus integration. "
                "These options allow you to customize the behavior of the integration. "
                "Changes take effect immediately after saving.",
                "scan_interval_note": "Scan interval in seconds (minimum 30 seconds recommended)",
                "remove_entities_note": "⚠️ WARNING: This option will remove all entities associated with this integration when the integration is removed. "
                "This action cannot be undone. Make sure you have a backup of your configuration.",
            },
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage advanced options (future expansion)."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="advanced",
            data_schema=vol.Schema(
                {
                    vol.Optional("max_retries", default=3): int,
                }
            ),
        )

    async def async_step_yaml_mapping(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage YAML mapping configuration."""
        if user_input is not None:
            # Handle YAML mapping configuration
            return await self._handle_yaml_mapping(user_input)

        # Get current configuration
        current_config = self.config_entry.options.get(CONF_YAML_MAPPING, {})
        custom_file = current_config.get(CONF_CUSTOM_MAPPING_FILE, "config/custom_mapping.yaml")
        
        return self.async_show_form(
            step_id="yaml_mapping",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_CUSTOM_MAPPING_FILE,
                        default=custom_file,
                    ): str,
                    vol.Optional(
                        CONF_RELOAD_MAPPING,
                        default=False,
                    ): bool,
                }
            ),
            description_placeholders={
                "yaml_info": "📄 Configure YAML device mappings for custom device detection and entity creation. "
                "Changes to YAML mappings require a reload to take effect.",
                "custom_file_note": "Path to custom mapping file (relative to config directory)",
                "reload_note": "⚠️ Reload mapping will apply changes immediately without restarting Home Assistant",
            },
        )

    async def _handle_yaml_mapping(self, user_input: dict[str, Any]) -> FlowResult:
        """Handle YAML mapping configuration changes."""
        try:
            # Get current YAML configuration
            yaml_config = self.config_entry.options.get(CONF_YAML_MAPPING, {})
            
            # Update with new values
            yaml_config[CONF_CUSTOM_MAPPING_FILE] = user_input[CONF_CUSTOM_MAPPING_FILE]
            
            # Save configuration
            updated_options = {**self.config_entry.options, CONF_YAML_MAPPING: yaml_config}
            
            # Check if reload is requested
            if user_input.get(CONF_RELOAD_MAPPING, False):
                await self._reload_yaml_mappings(yaml_config)
                _LOGGER.info("YAML mappings reloaded successfully")
                return self.async_create_entry(title="", data=updated_options)
            else:
                _LOGGER.info("YAML mapping configuration updated (reload required)")
                return self.async_create_entry(title="", data=updated_options)
                
        except Exception as e:
            _LOGGER.error("Failed to update YAML mapping configuration: %s", e)
            return self.async_show_form(
                step_id="yaml_mapping",
                data_schema=vol.Schema(
                    {
                        vol.Optional(CONF_CUSTOM_MAPPING_FILE, default=user_input.get(CONF_CUSTOM_MAPPING_FILE)): str,
                        vol.Optional(CONF_RELOAD_MAPPING, default=False): bool,
                    }
                ),
                errors={"base": f"Failed to update configuration: {e}"},
            )

    async def _reload_yaml_mappings(self, yaml_config: dict[str, Any]) -> None:
        """Reload YAML mappings from configuration."""
        try:
            from .device_mapping import load_and_merge_yaml_mappings
            
            # Get the base path (config directory)
            base_path = self.hass.config.config_dir if hasattr(self.hass.config, 'config_dir') else ""
            
            # Extract custom mapping file path
            custom_file = yaml_config.get(CONF_CUSTOM_MAPPING_FILE, "config/custom_mapping.yaml")
            
            # Ensure the custom mapping file exists
            full_path = os.path.join(base_path, custom_file)
            if not os.path.exists(full_path):
                # Create empty custom mapping file if it doesn't exist
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write("# Custom Eedomus Device Mapping\nversion: 1.0\ncustom_rules: []\ncustom_usage_id_mappings: {}\ncustom_name_patterns: []\n")
                _LOGGER.info("Created new custom mapping file: %s", full_path)
            
            # Reload mappings
            load_and_merge_yaml_mappings(base_path)
            _LOGGER.info("YAML mappings reloaded from: %s", full_path)
            
        except Exception as e:
            _LOGGER.error("Failed to reload YAML mappings: %s", e)
            raise

    async def async_step_edit_yaml(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Allow editing YAML mapping file directly (advanced)."""
        # This would be implemented with a text editor interface
        # For now, just show information about the YAML file
        
        yaml_config = self.config_entry.options.get(CONF_YAML_MAPPING, {})
        custom_file = yaml_config.get(CONF_CUSTOM_MAPPING_FILE, "config/custom_mapping.yaml")
        
        base_path = self.hass.config.config_dir if hasattr(self.hass.config, 'config_dir') else ""
        full_path = os.path.join(base_path, custom_file)
        
        file_info = "File not found"
        if os.path.exists(full_path):
            file_size = os.path.getsize(full_path)
            file_info = f"File exists ({file_size} bytes)"
        
        return self.async_show_form(
            step_id="edit_yaml",
            data_schema=vol.Schema({}),
            description_placeholders={
                "file_path": full_path,
                "file_info": file_info,
                "edit_instruction": "📝 To edit the YAML file, use a file editor or the Home Assistant file editor add-on. "
                "The file follows the structure defined in config/device_mapping.yaml",
            },
        )
