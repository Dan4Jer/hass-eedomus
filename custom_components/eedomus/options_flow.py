"""Options flow for eedomus integration with UI/YAML toggle."""

import voluptuous as vol
import logging
import yaml
import os
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from .const import (
    UI_OPTIONS_SCHEMA,
    DEVICE_SCHEMA,
    CONF_USE_YAML,
    CONF_CUSTOM_DEVICES,
    CONF_YAML_CONTENT,
    CONF_ENABLE_API_EEDOMUS,
    CONF_ENABLE_API_PROXY,
    CONF_ENABLE_HISTORY,
    CONF_SCAN_INTERVAL,
    CONF_ENABLE_SET_VALUE_RETRY,
    CONF_ENABLE_WEBHOOK,
    CONF_API_PROXY_DISABLE_SECURITY,
    CONF_PHP_FALLBACK_ENABLED,
    CONF_PHP_FALLBACK_SCRIPT_NAME,
    CONF_PHP_FALLBACK_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


class EedomusOptionsFlow(config_entries.OptionsFlow):
    """Handle eedomus options with UI/YAML toggle."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        super().__init__()
        self._config_entry = config_entry
        self.current_devices = []
        self.use_yaml = False
        self.yaml_content = ""
        self.hass = None

    def _copy_config_to_options(self):
        """Copy configuration values from config_entry.data to options.
        
        This ensures that values set during config_flow are available in options_flow.
        """
        # Start with existing options or empty dict
        if not self._config_entry.options:
            options = {}
        else:
            options = dict(self._config_entry.options)
        
        # Copy values from config_entry.data (config_flow values)
        config_data = self._config_entry.data
        options[CONF_ENABLE_API_EEDOMUS] = config_data.get(CONF_ENABLE_API_EEDOMUS, True)
        options[CONF_ENABLE_API_PROXY] = config_data.get(CONF_ENABLE_API_PROXY, False)
        options[CONF_ENABLE_HISTORY] = config_data.get(CONF_ENABLE_HISTORY, False)
        options[CONF_SCAN_INTERVAL] = config_data.get(CONF_SCAN_INTERVAL, 300)
        options[CONF_ENABLE_SET_VALUE_RETRY] = config_data.get(CONF_ENABLE_SET_VALUE_RETRY, True)
        options[CONF_ENABLE_WEBHOOK] = config_data.get(CONF_ENABLE_WEBHOOK, True)
        options[CONF_API_PROXY_DISABLE_SECURITY] = config_data.get(CONF_API_PROXY_DISABLE_SECURITY, False)
        options[CONF_PHP_FALLBACK_ENABLED] = config_data.get(CONF_PHP_FALLBACK_ENABLED, False)
        options[CONF_PHP_FALLBACK_SCRIPT_NAME] = config_data.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php")
        options[CONF_PHP_FALLBACK_TIMEOUT] = config_data.get(CONF_PHP_FALLBACK_TIMEOUT, 5)
        
        _LOGGER.debug("Copied config to options: %s", {k: v for k, v in options.items() if k not in ['api_user', 'api_secret']})
        return options

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return EedomusOptionsFlow(config_entry)

    async def async_step_init(self, user_input=None):
        """Manage the options with mode selection."""
        if user_input is not None:
            # Save all configuration options
            options = {}
            
            # Debug: Log the user input
            _LOGGER.debug("User input received: %s", {k: v for k, v in user_input.items() if k != CONF_YAML_CONTENT})
            _LOGGER.debug("API Proxy Disable Security: %s", user_input.get(CONF_API_PROXY_DISABLE_SECURITY, False))
            
            # Save mode selection
            self.use_yaml = user_input.get(CONF_USE_YAML, False)
            options[CONF_USE_YAML] = self.use_yaml
            
            # Save API configuration options
            options[CONF_ENABLE_API_EEDOMUS] = user_input.get(CONF_ENABLE_API_EEDOMUS, True)
            options[CONF_ENABLE_API_PROXY] = user_input.get(CONF_ENABLE_API_PROXY, False)
            options[CONF_ENABLE_HISTORY] = user_input.get(CONF_ENABLE_HISTORY, False)
            options[CONF_SCAN_INTERVAL] = user_input.get(CONF_SCAN_INTERVAL, 300)
            options[CONF_ENABLE_SET_VALUE_RETRY] = user_input.get(CONF_ENABLE_SET_VALUE_RETRY, True)
            options[CONF_ENABLE_WEBHOOK] = user_input.get(CONF_ENABLE_WEBHOOK, True)
            options[CONF_API_PROXY_DISABLE_SECURITY] = user_input.get(CONF_API_PROXY_DISABLE_SECURITY, False)
            options[CONF_PHP_FALLBACK_ENABLED] = user_input.get(CONF_PHP_FALLBACK_ENABLED, False)
            options[CONF_PHP_FALLBACK_SCRIPT_NAME] = user_input.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php")
            options[CONF_PHP_FALLBACK_TIMEOUT] = user_input.get(CONF_PHP_FALLBACK_TIMEOUT, 5)
            
            # Store options for use in other steps
            # Convert mappingproxy to dict if needed
            if hasattr(self._config_entry.options, 'update'):
                self._config_entry.options.update(options)
            else:
                # Handle the case where options is a mappingproxy
                _LOGGER.debug("Options is a mappingproxy, creating new dict")
                new_options = dict(self._config_entry.options)
                new_options.update(options)
                # Note: We can't actually update the mappingproxy, so we'll use it in the next step
            
            # Debug: Log the options being saved
            _LOGGER.debug("Options to be saved: %s", {k: v for k, v in options.items() if k != CONF_YAML_CONTENT})
            _LOGGER.debug("API Proxy Disable Security to be saved: %s", options.get(CONF_API_PROXY_DISABLE_SECURITY, False))
            
            # Create entry with only the options that are allowed
            return self.async_create_entry(title="", data=options)

        # Get current options - ensure config values are copied to options
        current_options = self._copy_config_to_options()
        self.use_yaml = current_options.get(CONF_USE_YAML, False)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_USE_YAML, default=self.use_yaml): bool,
                vol.Optional(CONF_ENABLE_API_EEDOMUS, default=current_options.get(CONF_ENABLE_API_EEDOMUS, True)): bool,
                vol.Optional(CONF_ENABLE_API_PROXY, default=current_options.get(CONF_ENABLE_API_PROXY, False)): bool,
                vol.Optional(CONF_ENABLE_HISTORY, default=current_options.get(CONF_ENABLE_HISTORY, False)): bool,
                vol.Optional(CONF_SCAN_INTERVAL, default=current_options.get(CONF_SCAN_INTERVAL, 300)): int,
                vol.Optional(CONF_ENABLE_SET_VALUE_RETRY, default=current_options.get(CONF_ENABLE_SET_VALUE_RETRY, True)): bool,
                vol.Optional(CONF_ENABLE_WEBHOOK, default=current_options.get(CONF_ENABLE_WEBHOOK, True)): bool,
                vol.Optional(CONF_API_PROXY_DISABLE_SECURITY, default=current_options.get(CONF_API_PROXY_DISABLE_SECURITY, False)): bool,
                vol.Optional(CONF_PHP_FALLBACK_ENABLED, default=current_options.get(CONF_PHP_FALLBACK_ENABLED, False)): bool,
                vol.Optional(CONF_PHP_FALLBACK_SCRIPT_NAME, default=current_options.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php")): str,
                vol.Optional(CONF_PHP_FALLBACK_TIMEOUT, default=current_options.get(CONF_PHP_FALLBACK_TIMEOUT, 5)): int,
            }),
            description_placeholders={
                "current_mode": "YAML" if self.use_yaml else "UI (DISABLED)"
            }
        )

    async def async_step_ui(self, user_input=None):
        """Handle UI-based device configuration."""
        errors = {}
        
        if user_input is not None:
            # Save device configuration
            devices = user_input.get(CONF_CUSTOM_DEVICES, [])
            
            # Save to custom_mapping.yaml
            success = await async_save_custom_mapping(
                self.hass,
                self.hass.config.config_dir,
                {"custom_devices": devices}
            )
            
            if success:
                # Update options
                options = {
                    CONF_USE_YAML: False,  # UI mode
                    CONF_CUSTOM_DEVICES: devices
                }
                # Add API configuration options - ensure config values are preserved
                current_options = self._copy_config_to_options()
                options.update({
                    CONF_ENABLE_API_EEDOMUS: current_options.get(CONF_ENABLE_API_EEDOMUS, True),
                    CONF_ENABLE_API_PROXY: current_options.get(CONF_ENABLE_API_PROXY, False),
                    CONF_ENABLE_HISTORY: current_options.get(CONF_ENABLE_HISTORY, False),
                    CONF_SCAN_INTERVAL: current_options.get(CONF_SCAN_INTERVAL, 300),
                    CONF_ENABLE_SET_VALUE_RETRY: current_options.get(CONF_ENABLE_SET_VALUE_RETRY, True),
                    CONF_ENABLE_WEBHOOK: current_options.get(CONF_ENABLE_WEBHOOK, True),
                    CONF_API_PROXY_DISABLE_SECURITY: current_options.get(CONF_API_PROXY_DISABLE_SECURITY, False),
                    CONF_PHP_FALLBACK_ENABLED: current_options.get(CONF_PHP_FALLBACK_ENABLED, False),
                    CONF_PHP_FALLBACK_SCRIPT_NAME: current_options.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php"),
                    CONF_PHP_FALLBACK_TIMEOUT: current_options.get(CONF_PHP_FALLBACK_TIMEOUT, 5)
                })
                # Log the options being saved
                _LOGGER.debug("Saving options in UI mode: %s", options)
                return self.async_create_entry(title="", data=options)
            else:
                errors["base"] = "failed_to_save_yaml"
        
        # Load current device configuration
        try:
            current_mapping = await async_load_mapping(
                self.hass,
                self.hass.config.config_dir
            )
            current_devices = current_mapping.get("custom_devices", []) if current_mapping else []
        except Exception as e:
            _LOGGER.error("Error loading mapping: %s", e)
            current_devices = []
        
        return self.async_show_form(
            step_id="ui",
            data_schema=UI_OPTIONS_SCHEMA({
                vol.Required(CONF_USE_YAML, default=False): False,
                vol.Optional(CONF_CUSTOM_DEVICES, default=current_devices): current_devices,
            }),
            errors=errors,
            description_placeholders={
                "current_mode": "UI"
            }
        )

    async def async_step_yaml(self, user_input=None):
        """Handle YAML-based configuration."""
        # Local imports to avoid circular dependency
        from . import async_load_mapping, async_save_custom_mapping
        from .const import YAML_MAPPING_SCHEMA
        
        errors = {}

        if user_input is not None:
            yaml_content = user_input.get("yaml_content", "")

            try:
                # Parse and validate YAML
                parsed_yaml = yaml.safe_load(yaml_content) or {}
                validated = YAML_MAPPING_SCHEMA(parsed_yaml)

                # Save to custom_mapping.yaml
                success = await async_save_custom_mapping(
                    self.hass,
                    self.hass.config.config_dir,
                    validated
                )

                if success:
                    # Update options
                    options = {
                        CONF_USE_YAML: True,
                        CONF_YAML_CONTENT: yaml_content  # Store for re-editing
                    }
                    # Add API configuration options - ensure config values are preserved
                    current_options = self._copy_config_to_options()
                    options.update({
                        CONF_ENABLE_API_EEDOMUS: current_options.get(CONF_ENABLE_API_EEDOMUS, True),
                        CONF_ENABLE_API_PROXY: current_options.get(CONF_ENABLE_API_PROXY, False),
                        CONF_ENABLE_HISTORY: current_options.get(CONF_ENABLE_HISTORY, False),
                        CONF_SCAN_INTERVAL: current_options.get(CONF_SCAN_INTERVAL, 300),
                        CONF_ENABLE_SET_VALUE_RETRY: current_options.get(CONF_ENABLE_SET_VALUE_RETRY, True),
                        CONF_ENABLE_WEBHOOK: current_options.get(CONF_ENABLE_WEBHOOK, True),
                        CONF_API_PROXY_DISABLE_SECURITY: current_options.get(CONF_API_PROXY_DISABLE_SECURITY, False),
                        CONF_PHP_FALLBACK_ENABLED: current_options.get(CONF_PHP_FALLBACK_ENABLED, False),
                        CONF_PHP_FALLBACK_SCRIPT_NAME: current_options.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php"),
                        CONF_PHP_FALLBACK_TIMEOUT: current_options.get(CONF_PHP_FALLBACK_TIMEOUT, 5)
                    })
                    # Log the options being saved
                    _LOGGER.debug("Saving options in YAML mode: %s", options)
                    return self.async_create_entry(title="", data=options)
                else:
                    errors["base"] = "failed_to_save_yaml"

            except yaml.YAMLError as e:
                _LOGGER.error("YAML parse error: %s", e)
                errors["base"] = f"invalid_yaml: {e}"
            except vol.Invalid as e:
                _LOGGER.error("YAML validation error: %s", e)
                errors["base"] = f"invalid_mapping: {e}"

        # Load current YAML content
        try:
            current_mapping = await async_load_mapping(
                self.hass,
                self.hass.config.config_dir
            )
            self.yaml_content = yaml.dump(
                current_mapping,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True
            )
        except Exception as e:
            _LOGGER.error("Failed to load YAML for editing: %s", e)
            errors["base"] = "failed_to_load_yaml"
            # Provide template if loading fails
            self.yaml_content = """# Eedomus Custom Mapping
# Edit this file to override default device mappings

custom_devices:
  # Example:
  # - eedomus_id: "12345"
  #   ha_entity: "light.my_light"
  #   type: "light"
  #   name: "My Custom Light"
  #   ha_subtype: "dimmable"
  #   icon: "mdi:lightbulb"
  #   room: "Living Room"

"""

        return self.async_show_form(
            step_id="yaml",
            data_schema=vol.Schema({
                vol.Required("yaml_content", default=self.yaml_content): str
            }),
            errors=errors,
            description_placeholders={
                "example": "Edit YAML directly for advanced configuration"
            }
        )