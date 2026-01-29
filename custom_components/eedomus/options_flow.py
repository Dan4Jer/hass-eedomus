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
            
            if self.use_yaml:
                return await self.async_step_yaml()
            else:
                return await self.async_step_ui()

        # Get current options
        current_options = self._config_entry.options.copy()
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
                "current_mode": "YAML" if self.use_yaml else "UI"
            }
        )

    async def async_step_ui(self, user_input=None):
        """Handle UI-based device configuration."""
        # Local imports to avoid circular dependency
        from . import async_load_mapping, async_save_custom_mapping
        
        errors = {}

        if user_input is not None:
            try:
                # Validate input
                validated_input = UI_OPTIONS_SCHEMA(user_input)

                # Save devices to custom_mapping.yaml
                custom_mapping = {CONF_CUSTOM_DEVICES: validated_input.get(CONF_CUSTOM_DEVICES, [])}
                success = await async_save_custom_mapping(
                    self.hass,
                    self.hass.config.config_dir,
                    custom_mapping
                )

                if success:
                    # Update options
                    options = {
                        CONF_USE_YAML: False,
                        **validated_input
                    }
                    # Add API configuration options
                    options[CONF_ENABLE_API_EEDOMUS] = self._config_entry.options.get(CONF_ENABLE_API_EEDOMUS, True)
                    options[CONF_ENABLE_API_PROXY] = self._config_entry.options.get(CONF_ENABLE_API_PROXY, False)
                    options[CONF_ENABLE_HISTORY] = self._config_entry.options.get(CONF_ENABLE_HISTORY, False)
                    options[CONF_SCAN_INTERVAL] = self._config_entry.options.get(CONF_SCAN_INTERVAL, 300)
                    options[CONF_ENABLE_SET_VALUE_RETRY] = self._config_entry.options.get(CONF_ENABLE_SET_VALUE_RETRY, True)
                    options[CONF_ENABLE_WEBHOOK] = self._config_entry.options.get(CONF_ENABLE_WEBHOOK, True)
                    options[CONF_API_PROXY_DISABLE_SECURITY] = self._config_entry.options.get(CONF_API_PROXY_DISABLE_SECURITY, False)
                    options[CONF_PHP_FALLBACK_ENABLED] = self._config_entry.options.get(CONF_PHP_FALLBACK_ENABLED, False)
                    options[CONF_PHP_FALLBACK_SCRIPT_NAME] = self._config_entry.options.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php")
                    options[CONF_PHP_FALLBACK_TIMEOUT] = self._config_entry.options.get(CONF_PHP_FALLBACK_TIMEOUT, 5)
                    # Log the options being saved
                    _LOGGER.debug("Saving options in UI mode: %s", options)
                    return self.async_create_entry(title="", data=options)
                else:
                    errors["base"] = "failed_to_save_mapping"

            except vol.Invalid as e:
                _LOGGER.error("UI validation error: %s", e)
                errors["base"] = f"invalid_configuration: {e}"

        # Load current devices for pre-filling
        try:
            self.current_devices = await async_load_mapping(
                self.hass,
                self.hass.config.config_dir
            )
            self.current_devices = self.current_devices.get(CONF_CUSTOM_DEVICES, [])
        except Exception as e:
            _LOGGER.error("Failed to load devices for UI: %s", e)
            errors["base"] = "failed_to_load_devices"
            self.current_devices = []

        # Create dynamic schema for devices
        from homeassistant.helpers import config_validation as cv
        device_schema = vol.Schema({
            vol.Optional(CONF_CUSTOM_DEVICES, default=self.current_devices): cv.ensure_list(DEVICE_SCHEMA)
        })

        return self.async_show_form(
            step_id="ui",
            data_schema=device_schema,
            errors=errors,
            description_placeholders={
                "device_count": len(self.current_devices)
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
                    # Add API configuration options
                    options[CONF_ENABLE_API_EEDOMUS] = self._config_entry.options.get(CONF_ENABLE_API_EEDOMUS, True)
                    options[CONF_ENABLE_API_PROXY] = self._config_entry.options.get(CONF_ENABLE_API_PROXY, False)
                    options[CONF_ENABLE_HISTORY] = self._config_entry.options.get(CONF_ENABLE_HISTORY, False)
                    options[CONF_SCAN_INTERVAL] = self._config_entry.options.get(CONF_SCAN_INTERVAL, 300)
                    options[CONF_ENABLE_SET_VALUE_RETRY] = self._config_entry.options.get(CONF_ENABLE_SET_VALUE_RETRY, True)
                    options[CONF_ENABLE_WEBHOOK] = self._config_entry.options.get(CONF_ENABLE_WEBHOOK, True)
                    options[CONF_API_PROXY_DISABLE_SECURITY] = self._config_entry.options.get(CONF_API_PROXY_DISABLE_SECURITY, False)
                    options[CONF_PHP_FALLBACK_ENABLED] = self._config_entry.options.get(CONF_PHP_FALLBACK_ENABLED, False)
                    options[CONF_PHP_FALLBACK_SCRIPT_NAME] = self._config_entry.options.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php")
                    options[CONF_PHP_FALLBACK_TIMEOUT] = self._config_entry.options.get(CONF_PHP_FALLBACK_TIMEOUT, 5)
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