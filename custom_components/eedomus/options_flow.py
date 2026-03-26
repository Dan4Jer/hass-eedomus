"""Options flow for eedomus integration with UI/YAML toggle.

Detailed parameter documentation is available in docs/OPTIONS_DOCUMENTATION.md
"""

import voluptuous as vol
import logging
import yaml
import os
import json
import datetime
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers import config_validation as cv
from .const import (
    UI_OPTIONS_SCHEMA,
    DEVICE_SCHEMA,
    CONF_USE_YAML,
    CONF_CUSTOM_DEVICES,
    CONF_YAML_CONTENT,
    CONF_ENABLE_API_EEDOMUS,
    CONF_ENABLE_API_PROXY,
    CONF_ENABLE_HISTORY,
    CONF_HISTORY_RETRY_DELAY,
    CONF_HISTORY_PERIPHERALS_PER_SCAN,
    CONF_SCAN_INTERVAL,
    CONF_ENABLE_SET_VALUE_RETRY,
    CONF_ENABLE_WEBHOOK,
    CONF_API_PROXY_DISABLE_SECURITY,
    CONF_PHP_FALLBACK_ENABLED,
    CONF_PHP_FALLBACK_SCRIPT_NAME,
    CONF_PHP_FALLBACK_TIMEOUT,
    CONF_HTTP_REQUEST_TIMEOUT,
    DEFAULT_HISTORY_PERIPHERALS_PER_SCAN,
    CONF_ENABLE_HISTORY,
    CONF_SCAN_INTERVAL,
    CONF_ENABLE_SET_VALUE_RETRY,
    CONF_ENABLE_WEBHOOK,
    CONF_API_PROXY_DISABLE_SECURITY,
    CONF_PHP_FALLBACK_ENABLED,
    CONF_PHP_FALLBACK_SCRIPT_NAME,
    CONF_PHP_FALLBACK_TIMEOUT,
    CONF_HTTP_REQUEST_TIMEOUT,
    DEFAULT_HTTP_REQUEST_TIMEOUT,
    DEFAULT_HISTORY_RETRY_DELAY,
    YAML_MAPPING_SCHEMA,
)

_LOGGER = logging.getLogger(__name__)

async def async_get_translations(hass, language="en"):
    """Load translations for the given language."""
    try:
        if language == "en-GB":
            language = "en"
        translations_path = os.path.join(
            os.path.dirname(__file__), "translations", f"{language}.json"
        )
        if os.path.exists(translations_path):
            return await hass.async_add_executor_job(
                lambda: json.load(open(translations_path, "r"))
            )
        else:
            _LOGGER.warning(f"Translations for language {language} not found. Using English as fallback.")
            translations_path = os.path.join(
                os.path.dirname(__file__), "translations", "en.json"
            )
            return await hass.async_add_executor_job(
                lambda: json.load(open(translations_path, "r"))
            )
    except Exception as e:
        _LOGGER.error(f"Failed to load translations: {e}")
        return {}

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
        Only copies values that haven't been explicitly set in options.
        """
        # Start with existing options or empty dict
        if not self._config_entry.options:
            options = {}
        else:
            options = dict(self._config_entry.options)
        
        # Copy values from config_entry.data (config_flow values)
        # Only copy if the option hasn't been explicitly set yet
        # Use the same logic as _get_current_config() to ensure consistency
        
        # Only copy if not already in options
        if CONF_ENABLE_API_EEDOMUS not in options:
            options[CONF_ENABLE_API_EEDOMUS] = self._config_entry.data.get(CONF_ENABLE_API_EEDOMUS, True)
        if CONF_ENABLE_API_PROXY not in options:
            options[CONF_ENABLE_API_PROXY] = self._config_entry.data.get(CONF_ENABLE_API_PROXY, False)
        if CONF_ENABLE_HISTORY not in options:
            options[CONF_ENABLE_HISTORY] = self._config_entry.data.get(CONF_ENABLE_HISTORY, False)
        if CONF_HISTORY_PERIPHERALS_PER_SCAN not in options:
            options[CONF_HISTORY_PERIPHERALS_PER_SCAN] = self._config_entry.data.get(CONF_HISTORY_PERIPHERALS_PER_SCAN, DEFAULT_HISTORY_PERIPHERALS_PER_SCAN)
        if CONF_SCAN_INTERVAL not in options:
            options[CONF_SCAN_INTERVAL] = self._config_entry.data.get(CONF_SCAN_INTERVAL, 300)
        if CONF_HTTP_REQUEST_TIMEOUT not in options:
            options[CONF_HTTP_REQUEST_TIMEOUT] = self._config_entry.data.get(CONF_HTTP_REQUEST_TIMEOUT, DEFAULT_HTTP_REQUEST_TIMEOUT)
        if CONF_ENABLE_SET_VALUE_RETRY not in options:
            options[CONF_ENABLE_SET_VALUE_RETRY] = self._config_entry.data.get(CONF_ENABLE_SET_VALUE_RETRY, True)
        if CONF_ENABLE_WEBHOOK not in options:
            options[CONF_ENABLE_WEBHOOK] = self._config_entry.data.get(CONF_ENABLE_WEBHOOK, True)
        if CONF_API_PROXY_DISABLE_SECURITY not in options:
            options[CONF_API_PROXY_DISABLE_SECURITY] = self._config_entry.data.get(CONF_API_PROXY_DISABLE_SECURITY, False)
        if CONF_PHP_FALLBACK_ENABLED not in options:
            options[CONF_PHP_FALLBACK_ENABLED] = self._config_entry.data.get(CONF_PHP_FALLBACK_ENABLED, False)
        if CONF_PHP_FALLBACK_SCRIPT_NAME not in options:
            options[CONF_PHP_FALLBACK_SCRIPT_NAME] = self._config_entry.data.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php")
        if CONF_PHP_FALLBACK_TIMEOUT not in options:
            options[CONF_PHP_FALLBACK_TIMEOUT] = self._config_entry.data.get(CONF_PHP_FALLBACK_TIMEOUT, 5)
        
        _LOGGER.debug("Copied config to options: %s", {k: v for k, v in options.items() if k not in ['api_user', 'api_secret']})
        return options

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return EedomusOptionsFlow(config_entry)

    async def async_step_init(self, user_input=None):
        """Manage the options - comprehensive configuration interface."""
        # Get current configuration first (needed for both display and submission)
        current_config = self._get_current_config()
        
        # Handle form submission
        if user_input is not None:
            # Check if user wants to use rich editor
            if user_input.get("use_rich_editor", False):
                # Save options first
                options = {
                    CONF_ENABLE_API_EEDOMUS: user_input.get(CONF_ENABLE_API_EEDOMUS, current_config.get(CONF_ENABLE_API_EEDOMUS, True)),
                    CONF_ENABLE_API_PROXY: user_input.get(CONF_ENABLE_API_PROXY, current_config.get(CONF_ENABLE_API_PROXY, False)),
                    CONF_ENABLE_HISTORY: user_input.get(CONF_ENABLE_HISTORY, current_config.get(CONF_ENABLE_HISTORY, False)),
                    CONF_HISTORY_PERIPHERALS_PER_SCAN: user_input.get(CONF_HISTORY_PERIPHERALS_PER_SCAN, current_config.get(CONF_HISTORY_PERIPHERALS_PER_SCAN, 5)),
                    CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, current_config.get(CONF_SCAN_INTERVAL, 300)),
                    CONF_ENABLE_SET_VALUE_RETRY: user_input.get(CONF_ENABLE_SET_VALUE_RETRY, current_config.get(CONF_ENABLE_SET_VALUE_RETRY, True)),
                    CONF_ENABLE_WEBHOOK: user_input.get(CONF_ENABLE_WEBHOOK, current_config.get(CONF_ENABLE_WEBHOOK, True)),
                    CONF_API_PROXY_DISABLE_SECURITY: user_input.get(CONF_API_PROXY_DISABLE_SECURITY, current_config.get(CONF_API_PROXY_DISABLE_SECURITY, False)),
                    CONF_PHP_FALLBACK_ENABLED: user_input.get(CONF_PHP_FALLBACK_ENABLED, current_config.get(CONF_PHP_FALLBACK_ENABLED, False)),
                    CONF_PHP_FALLBACK_SCRIPT_NAME: user_input.get(CONF_PHP_FALLBACK_SCRIPT_NAME, current_config.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php")),
                    CONF_PHP_FALLBACK_TIMEOUT: user_input.get(CONF_PHP_FALLBACK_TIMEOUT, current_config.get(CONF_PHP_FALLBACK_TIMEOUT, 5)),
                    CONF_HTTP_REQUEST_TIMEOUT: user_input.get(CONF_HTTP_REQUEST_TIMEOUT, current_config.get(CONF_HTTP_REQUEST_TIMEOUT, 30)),
                }
                
                # Update config entry
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    options=options
                )
                
                # Show message about using the panel
                return self.async_show_form(
                    step_id="init",
                    data_schema=vol.Schema({}),
                    description_placeholders={
                        "message": "✅ Configuration saved! You can now use the Eedomus Config panel from the sidebar for advanced YAML editing."
                    }
                )
            
            # Debug: Log user_input to see what's actually submitted
            _LOGGER.debug("User input received in async_step_init: %s", user_input)
            _LOGGER.debug("CONF_ENABLE_API_PROXY in user_input: %s", CONF_ENABLE_API_PROXY in user_input)
            if CONF_ENABLE_API_PROXY in user_input:
                _LOGGER.debug("CONF_ENABLE_API_PROXY value: %s", user_input[CONF_ENABLE_API_PROXY])
            
            # Save all options with proper key names
            options = {
                CONF_ENABLE_API_EEDOMUS: user_input.get(CONF_ENABLE_API_EEDOMUS, current_config.get(CONF_ENABLE_API_EEDOMUS, True)),
                CONF_ENABLE_API_PROXY: user_input.get(CONF_ENABLE_API_PROXY, current_config.get(CONF_ENABLE_API_PROXY, False)),
                CONF_ENABLE_HISTORY: user_input.get(CONF_ENABLE_HISTORY, current_config.get(CONF_ENABLE_HISTORY, False)),
                CONF_HISTORY_PERIPHERALS_PER_SCAN: user_input.get(CONF_HISTORY_PERIPHERALS_PER_SCAN, current_config.get(CONF_HISTORY_PERIPHERALS_PER_SCAN, 5)),
                CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, current_config.get(CONF_SCAN_INTERVAL, 300)),
                CONF_ENABLE_SET_VALUE_RETRY: user_input.get(CONF_ENABLE_SET_VALUE_RETRY, current_config.get(CONF_ENABLE_SET_VALUE_RETRY, True)),
                CONF_ENABLE_WEBHOOK: user_input.get(CONF_ENABLE_WEBHOOK, current_config.get(CONF_ENABLE_WEBHOOK, True)),
                CONF_API_PROXY_DISABLE_SECURITY: user_input.get(CONF_API_PROXY_DISABLE_SECURITY, current_config.get(CONF_API_PROXY_DISABLE_SECURITY, False)),
                CONF_PHP_FALLBACK_ENABLED: user_input.get(CONF_PHP_FALLBACK_ENABLED, current_config.get(CONF_PHP_FALLBACK_ENABLED, False)),
                CONF_PHP_FALLBACK_SCRIPT_NAME: user_input.get(CONF_PHP_FALLBACK_SCRIPT_NAME, current_config.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php")),
                CONF_PHP_FALLBACK_TIMEOUT: user_input.get(CONF_PHP_FALLBACK_TIMEOUT, current_config.get(CONF_PHP_FALLBACK_TIMEOUT, 5)),
                CONF_HTTP_REQUEST_TIMEOUT: user_input.get(CONF_HTTP_REQUEST_TIMEOUT, current_config.get(CONF_HTTP_REQUEST_TIMEOUT, 30)),
            }
            
            # Debug: Log the options being saved
            _LOGGER.debug("Options to be saved: %s", options)
            
            # Update config entry
            _LOGGER.debug("Calling async_update_entry with options: %s", options)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options=options
            )
            _LOGGER.debug("async_update_entry called successfully")
            
            return self.async_create_entry(title="", data={})
        
        # Get current configuration
        current_config = self._get_current_config()
        
        # Show comprehensive options form
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_ENABLE_API_EEDOMUS, default=current_config.get(CONF_ENABLE_API_EEDOMUS, True)): bool,
                vol.Required(CONF_ENABLE_API_PROXY, default=current_config.get(CONF_ENABLE_API_PROXY, False)): bool,
                vol.Optional(CONF_ENABLE_HISTORY, default=current_config.get(CONF_ENABLE_HISTORY, False)): bool,
                vol.Optional(CONF_HISTORY_PERIPHERALS_PER_SCAN, default=current_config.get(CONF_HISTORY_PERIPHERALS_PER_SCAN, 5)): int,
                vol.Optional(CONF_SCAN_INTERVAL, default=current_config.get(CONF_SCAN_INTERVAL, 300)): int,
                vol.Optional(CONF_ENABLE_SET_VALUE_RETRY, default=current_config.get(CONF_ENABLE_SET_VALUE_RETRY, True)): bool,
                vol.Optional(CONF_ENABLE_WEBHOOK, default=current_config.get(CONF_ENABLE_WEBHOOK, True)): bool,
                vol.Optional(CONF_API_PROXY_DISABLE_SECURITY, default=current_config.get(CONF_API_PROXY_DISABLE_SECURITY, False)): bool,
                vol.Optional(CONF_PHP_FALLBACK_ENABLED, default=current_config.get(CONF_PHP_FALLBACK_ENABLED, False)): bool,
                vol.Optional(CONF_PHP_FALLBACK_SCRIPT_NAME, default=current_config.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php")): str,
                vol.Optional(CONF_PHP_FALLBACK_TIMEOUT, default=current_config.get(CONF_PHP_FALLBACK_TIMEOUT, 5)): int,
                vol.Optional(CONF_HTTP_REQUEST_TIMEOUT, default=current_config.get(CONF_HTTP_REQUEST_TIMEOUT, 30)): int,
                vol.Optional("use_rich_editor", default=False): bool,
            }),
            description_placeholders={
                "content": "Configure Eedomus integration settings. Check 'Use Rich Editor' for advanced YAML configuration."
            }
        )
    
    async def async_step_yaml_editor(self, user_input=None):
        """Handle YAML configuration editing - fallback for compatibility."""
        errors = {}
        
        # Check if user wants to preview YAML
        if user_input is not None and user_input.get("action") == "preview":
            yaml_content = user_input.get("yaml_content", "")
            try:
                # Parse and validate
                parsed_yaml = yaml.safe_load(yaml_content) or {}
                from .const import YAML_MAPPING_SCHEMA
                YAML_MAPPING_SCHEMA(parsed_yaml)
                
                # Return preview
                return self.async_show_form(
                    step_id="yaml_editor",
                    data_schema=vol.Schema({
                        vol.Optional("yaml_content", default=yaml_content): str,
                        vol.Optional("preview_mode"): bool,
                    }),
                    description_placeholders={
                        "preview_title": "YAML Preview",
                        "preview_content": f"```yaml\n{yaml_content}\n```",
                        "preview_valid": "✅ YAML is valid",
                    },
                    errors=errors
                )
            except (yaml.YAMLError, vol.Invalid) as e:
                errors["base"] = f"Invalid YAML: {e}"
                return self.async_show_form(
                    step_id="yaml_editor",
                    data_schema=vol.Schema({
                        vol.Optional("yaml_content", default=yaml_content): str,
                    }),
                    description_placeholders={
                        "preview_title": "YAML Preview",
                        "preview_content": f"```yaml\n{yaml_content}\n```",
                        "preview_error": f"❌ Error: {e}",
                    },
                    errors=errors
                )
        
        # Save YAML configuration
        if user_input is not None and user_input.get("yaml_content"):
            yaml_content = user_input.get("yaml_content", "")
            
            try:
                # Parse and validate
                parsed_yaml = yaml.safe_load(yaml_content) or {}
                from .const import YAML_MAPPING_SCHEMA
                validated = YAML_MAPPING_SCHEMA(parsed_yaml)
                
                # Save to custom_mapping.yaml
                custom_mapping_path = os.path.join(
                    os.path.dirname(__file__), "config", "custom_mapping.yaml"
                )
                
                # Use async_add_executor_job to avoid blocking calls
                await self.hass.async_add_executor_job(
                    lambda: open(custom_mapping_path, "w").write(yaml_content)
                )
                
                _LOGGER.info("YAML configuration saved successfully")
                
                # Update options
                options = {
                    CONF_USE_YAML: True,
                    "yaml_content": yaml_content
                }
                
                # Preserve API configuration options
                current_options = self._copy_config_to_options()
                options.update(current_options)
                
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    options=options
                )
                
                return self.async_create_entry(title="", data={})
                
            except Exception as err:
                _LOGGER.error("Failed to save YAML configuration: %s", err)
                return self.async_show_form(
                    step_id="yaml_editor",
                    data_schema=vol.Schema({
                        vol.Optional("yaml_content", default=yaml_content): str,
                    }),
                    description_placeholders={
                        "error": f"Failed to save configuration: {err}"
                    },
                    errors={"base": str(err)}
                )
        
        # Initial YAML editor view
        try:
            # Load current YAML configuration
            yaml_content = self._load_current_yaml()
        except Exception as e:
            _LOGGER.warning("Could not load current YAML: %s", e)
            yaml_content = ""
        
        return self.async_show_form(
            step_id="yaml_editor",
            data_schema=vol.Schema({
                vol.Optional("yaml_content", default=yaml_content): str,
            }),
            description_placeholders={
                "content": "Edit YAML configuration directly. Use the panel for rich editing."
            }
        )
    
    def _get_current_config(self):
        """Get current configuration from options or defaults."""
        return {
            CONF_ENABLE_API_EEDOMUS: self.config_entry.options.get(
                CONF_ENABLE_API_EEDOMUS,
                self.config_entry.data.get(CONF_ENABLE_API_EEDOMUS, True)
            ),
            CONF_ENABLE_API_PROXY: self.config_entry.options.get(
                CONF_ENABLE_API_PROXY,
                self.config_entry.data.get(CONF_ENABLE_API_PROXY, False)
            ),
            CONF_ENABLE_HISTORY: self.config_entry.options.get(
                CONF_ENABLE_HISTORY,
                self.config_entry.data.get(CONF_ENABLE_HISTORY, False)
            ),
            CONF_HISTORY_PERIPHERALS_PER_SCAN: self.config_entry.options.get(
                CONF_HISTORY_PERIPHERALS_PER_SCAN,
                self.config_entry.data.get(CONF_HISTORY_PERIPHERALS_PER_SCAN, 5)
            ),
            CONF_SCAN_INTERVAL: self.config_entry.options.get(
                CONF_SCAN_INTERVAL,
                self.config_entry.data.get(CONF_SCAN_INTERVAL, 300)
            ),
            CONF_ENABLE_SET_VALUE_RETRY: self.config_entry.options.get(
                CONF_ENABLE_SET_VALUE_RETRY,
                self.config_entry.data.get(CONF_ENABLE_SET_VALUE_RETRY, True)
            ),
            CONF_ENABLE_WEBHOOK: self.config_entry.options.get(
                CONF_ENABLE_WEBHOOK,
                self.config_entry.data.get(CONF_ENABLE_WEBHOOK, True)
            ),
            CONF_API_PROXY_DISABLE_SECURITY: self.config_entry.options.get(
                CONF_API_PROXY_DISABLE_SECURITY,
                self.config_entry.data.get(CONF_API_PROXY_DISABLE_SECURITY, False)
            ),
            CONF_PHP_FALLBACK_ENABLED: self.config_entry.options.get(
                CONF_PHP_FALLBACK_ENABLED,
                self.config_entry.data.get(CONF_PHP_FALLBACK_ENABLED, False)
            ),
            CONF_PHP_FALLBACK_SCRIPT_NAME: self.config_entry.options.get(
                CONF_PHP_FALLBACK_SCRIPT_NAME,
                self.config_entry.data.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php")
            ),
            CONF_PHP_FALLBACK_TIMEOUT: self.config_entry.options.get(
                CONF_PHP_FALLBACK_TIMEOUT,
                self.config_entry.data.get(CONF_PHP_FALLBACK_TIMEOUT, 5)
            ),
            CONF_HTTP_REQUEST_TIMEOUT: self.config_entry.options.get(
                CONF_HTTP_REQUEST_TIMEOUT,
                self.config_entry.data.get(CONF_HTTP_REQUEST_TIMEOUT, 30)
            ),
        }
    
    def _copy_config_to_options(self):
        """Copy configuration values from config_entry.data to options.
        
        This ensures that values set during config_flow are available in options_flow.
        Only copies values that haven't been explicitly set in options.
        """
        # Start with existing options or empty dict
        if not self.config_entry.options:
            options = {}
        else:
            options = dict(self.config_entry.options)
        
        # Copy values from config_entry.data (config_flow values)
        # Only copy if the option hasn't been explicitly set yet
        config_data = self.config_entry.data
        
        # Only copy if not already in options
        if CONF_ENABLE_API_EEDOMUS not in options:
            options[CONF_ENABLE_API_EEDOMUS] = config_data.get(CONF_ENABLE_API_EEDOMUS, True)
        if CONF_ENABLE_API_PROXY not in options:
            options[CONF_ENABLE_API_PROXY] = config_data.get(CONF_ENABLE_API_PROXY, False)
        if CONF_ENABLE_HISTORY not in options:
            options[CONF_ENABLE_HISTORY] = config_data.get(CONF_ENABLE_HISTORY, False)
        if CONF_HISTORY_PERIPHERALS_PER_SCAN not in options:
            options[CONF_HISTORY_PERIPHERALS_PER_SCAN] = config_data.get(CONF_HISTORY_PERIPHERALS_PER_SCAN, 5)
        if CONF_SCAN_INTERVAL not in options:
            options[CONF_SCAN_INTERVAL] = config_data.get(CONF_SCAN_INTERVAL, 300)
        if CONF_ENABLE_SET_VALUE_RETRY not in options:
            options[CONF_ENABLE_SET_VALUE_RETRY] = config_data.get(CONF_ENABLE_SET_VALUE_RETRY, True)
        if CONF_ENABLE_WEBHOOK not in options:
            options[CONF_ENABLE_WEBHOOK] = config_data.get(CONF_ENABLE_WEBHOOK, True)
        if CONF_API_PROXY_DISABLE_SECURITY not in options:
            options[CONF_API_PROXY_DISABLE_SECURITY] = config_data.get(CONF_API_PROXY_DISABLE_SECURITY, False)
        if CONF_PHP_FALLBACK_ENABLED not in options:
            options[CONF_PHP_FALLBACK_ENABLED] = config_data.get(CONF_PHP_FALLBACK_ENABLED, False)
        if CONF_PHP_FALLBACK_SCRIPT_NAME not in options:
            options[CONF_PHP_FALLBACK_SCRIPT_NAME] = config_data.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php")
        if CONF_PHP_FALLBACK_TIMEOUT not in options:
            options[CONF_PHP_FALLBACK_TIMEOUT] = config_data.get(CONF_PHP_FALLBACK_TIMEOUT, 5)
        if CONF_HTTP_REQUEST_TIMEOUT not in options:
            options[CONF_HTTP_REQUEST_TIMEOUT] = config_data.get(CONF_HTTP_REQUEST_TIMEOUT, 30)
        
        _LOGGER.debug("Copied config to options: %s", {k: v for k, v in options.items() if k not in ['api_user', 'api_secret']})
        return options
    
    def _load_current_yaml(self):
        """Load current YAML configuration."""
        try:
            custom_mapping_path = os.path.join(
                os.path.dirname(__file__), "config", "custom_mapping.yaml"
            )
            with open(custom_mapping_path, "r") as f:
                return f.read()
        except FileNotFoundError:
            return "# Eedomus Configuration\n# Add your custom device mappings here\n"
        except Exception as e:
            _LOGGER.error("Failed to load YAML: %s", e)
            return "# Error loading configuration"

    async def async_step_yaml_editor(self, user_input=None):
        """Handle YAML configuration editing with rich editor interface."""
        errors = {}
        
        # Check if user wants to preview YAML
        if user_input is not None and user_input.get("action") == "preview":
            yaml_content = user_input.get("yaml_content", "")
            try:
                # Parse and validate
                parsed_yaml = yaml.safe_load(yaml_content) or {}
                from .const import YAML_MAPPING_SCHEMA
                YAML_MAPPING_SCHEMA(parsed_yaml)
                
                # Return preview
                return self.async_show_form(
                    step_id="yaml_editor",
                    data_schema=vol.Schema({
                        vol.Optional("yaml_content", default=yaml_content): str,
                        vol.Optional("preview_mode"): bool,
                    }),
                    description_placeholders={
                        "preview_title": "YAML Preview",
                        "preview_content": f"```yaml\n{yaml_content}\n```",
                        "preview_valid": "✅ YAML is valid",
                    },
                    errors=errors
                )
            except (yaml.YAMLError, vol.Invalid) as e:
                errors["base"] = f"Invalid YAML: {e}"
                return self.async_show_form(
                    step_id="yaml_editor",
                    data_schema=vol.Schema({
                        vol.Optional("yaml_content", default=yaml_content): str,
                    }),
                    description_placeholders={
                        "preview_title": "YAML Preview",
                        "preview_content": f"```yaml\n{yaml_content}\n```",
                        "preview_error": f"❌ Error: {e}",
                    },
                    errors=errors
                )
        
        # Save YAML configuration
        if user_input is not None and user_input.get("yaml_content"):
            yaml_content = user_input.get("yaml_content", "")
            
            try:
                # Parse and validate
                parsed_yaml = yaml.safe_load(yaml_content) or {}
                from .const import YAML_MAPPING_SCHEMA
                validated = YAML_MAPPING_SCHEMA(parsed_yaml)
                
                # Save to custom_mapping.yaml
                custom_mapping_path = os.path.join(
                    os.path.dirname(__file__), "config", "custom_mapping.yaml"
                )
                
                # Use async_add_executor_job to avoid blocking calls
                await self.hass.async_add_executor_job(
                    lambda: open(custom_mapping_path, "w").write(yaml_content)
                )
                
                _LOGGER.info("YAML configuration saved successfully")
                
                # Update options
                options = {
                    CONF_USE_YAML: True,
                    "yaml_content": yaml_content
                }
                
                # Preserve API configuration options
                current_options = self._copy_config_to_options()
                options.update({
                    CONF_ENABLE_API_EEDOMUS: current_options.get(CONF_ENABLE_API_EEDOMUS, True),
                    CONF_ENABLE_API_PROXY: current_options.get(CONF_ENABLE_API_PROXY, False),
                    CONF_ENABLE_HISTORY: current_options.get(CONF_ENABLE_HISTORY, False),
                    CONF_HISTORY_RETRY_DELAY: current_options.get(CONF_HISTORY_RETRY_DELAY, DEFAULT_HISTORY_RETRY_DELAY),
                    CONF_HISTORY_PERIPHERALS_PER_SCAN: current_options.get(CONF_HISTORY_PERIPHERALS_PER_SCAN, DEFAULT_HISTORY_PERIPHERALS_PER_SCAN),
                    CONF_SCAN_INTERVAL: current_options.get(CONF_SCAN_INTERVAL, 300),
                    CONF_ENABLE_SET_VALUE_RETRY: current_options.get(CONF_ENABLE_SET_VALUE_RETRY, True),
                    CONF_ENABLE_WEBHOOK: current_options.get(CONF_ENABLE_WEBHOOK, True),
                    CONF_API_PROXY_DISABLE_SECURITY: current_options.get(CONF_API_PROXY_DISABLE_SECURITY, False),
                    CONF_PHP_FALLBACK_ENABLED: current_options.get(CONF_PHP_FALLBACK_ENABLED, False),
                    CONF_PHP_FALLBACK_SCRIPT_NAME: current_options.get(CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php"),
                    CONF_PHP_FALLBACK_TIMEOUT: current_options.get(CONF_PHP_FALLBACK_TIMEOUT, 5),
                    CONF_HTTP_REQUEST_TIMEOUT: current_options.get(CONF_HTTP_REQUEST_TIMEOUT, DEFAULT_HTTP_REQUEST_TIMEOUT)
                })
                
                _LOGGER.debug("Saving YAML configuration")
                return self.async_create_entry(title="", data=options)
            except (yaml.YAMLError, vol.Invalid) as e:
                errors["base"] = f"Invalid YAML: {e}"
                _LOGGER.error(f"Failed to save YAML configuration: {e}")
        
        # Load current YAML configuration
        try:
            custom_mapping_path = os.path.join(
                os.path.dirname(__file__), "config", "custom_mapping.yaml"
            )
            
            # Use async_add_executor_job to avoid blocking calls
            if os.path.exists(custom_mapping_path):
                yaml_content = await self.hass.async_add_executor_job(
                    lambda: open(custom_mapping_path, "r").read()
                )
            else:
                # Provide template
                yaml_content = """# Eedomus Custom Mapping Configuration
# Edit this file to override default device mappings

metadata:
  version: \"1.0\"
  last_modified: \""" + str(datetime.datetime.now().strftime('%Y-%m-%d')) + "\"
  changes: []

custom_rules: []
custom_usage_id_mappings: {}
temperature_setpoint_mappings: {}
custom_name_patterns: []

custom_devices:
  # Example:
  # - eedomus_id: \"12345\"
  #   ha_entity: \"light.my_light\"
  #   type: \"light\"
  #   ha_subtype: \"rgbw\"
  #   icon: \"mdi:lightbulb\"
  #   room: \"Living Room\"
"""
        except Exception as e:
            _LOGGER.error(f"Failed to load YAML configuration: {e}")
            yaml_content = """# Eedomus Custom Mapping Configuration
# Add your custom device mappings here
"""
        
        # Load translations
        language = self.hass.config.language if self.hass else "en"
        translations = await async_get_translations(self.hass, language) if self.hass else {}
        
        return self.async_show_form(
            step_id="yaml_editor",
            data_schema=vol.Schema({
                vol.Optional("yaml_content", default=yaml_content): str,
            }),
            description_placeholders={
                "title": translations.get("title", "Eedomus"),
                "description": translations.get("description", "Edit YAML configuration"),
                "helper": "Modify the YAML below. Click 'Preview' to validate before saving.",
            },
            errors=errors
        )

    # async_step_ui method removed - using YAML editor only

# Fonctions utilitaires pour charger/sauvegarder les mappings
async def async_load_mapping(hass, config_dir):
    """Load custom mapping from file."""
    mapping_path = os.path.join(
        os.path.dirname(__file__),
        "config",
        "custom_mapping.yaml"
    )
    if os.path.exists(mapping_path):
        try:
            with open(mapping_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            _LOGGER.error(f"Failed to load mapping: {e}")
    return {}

async def async_save_custom_mapping(hass, config_dir, mapping):
    """Save custom mapping to file."""
    mapping_path = os.path.join(
        os.path.dirname(__file__),
        "config",
        "custom_mapping.yaml"
    )
    try:
        with open(mapping_path, "w") as f:
            yaml.dump(
                mapping,
                f,
                default_flow_style=False,
                sort_keys=False
            )
        return True
    except Exception as e:
        _LOGGER.error(f"Failed to save mapping: {e}")
        return False