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
        config_data = self._config_entry.data
        
        # Only copy if not already in options
        if CONF_ENABLE_API_EEDOMUS not in options:
            options[CONF_ENABLE_API_EEDOMUS] = config_data.get(CONF_ENABLE_API_EEDOMUS, True)
        if CONF_ENABLE_API_PROXY not in options:
            options[CONF_ENABLE_API_PROXY] = config_data.get(CONF_ENABLE_API_PROXY, False)
        if CONF_ENABLE_HISTORY not in options:
            options[CONF_ENABLE_HISTORY] = config_data.get(CONF_ENABLE_HISTORY, False)
        if CONF_HISTORY_PERIPHERALS_PER_SCAN not in options:
            options[CONF_HISTORY_PERIPHERALS_PER_SCAN] = config_data.get(CONF_HISTORY_PERIPHERALS_PER_SCAN, DEFAULT_HISTORY_PERIPHERALS_PER_SCAN)
        if CONF_SCAN_INTERVAL not in options:
            options[CONF_SCAN_INTERVAL] = config_data.get(CONF_SCAN_INTERVAL, 300)
        if CONF_HTTP_REQUEST_TIMEOUT not in options:
            options[CONF_HTTP_REQUEST_TIMEOUT] = config_data.get(CONF_HTTP_REQUEST_TIMEOUT, DEFAULT_HTTP_REQUEST_TIMEOUT)
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
        
        _LOGGER.debug("Copied config to options: %s", {k: v for k, v in options.items() if k not in ['api_user', 'api_secret']})
        return options

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return EedomusOptionsFlow(config_entry)

    async def async_step_init(self, user_input=None):
        """Manage the options with mode selection."""
        language = self.hass.config.language if self.hass else "en"
        translations = await async_get_translations(self.hass, language) if self.hass else {}
        
        if user_input is not None:
            self.use_yaml = user_input.get("mode") == "yaml"
            if self.use_yaml:
                return await self.async_step_yaml_editor(None)
            else:
                return await self.async_step_ui(None)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("mode", default="ui"): vol.In(["ui", "yaml"]),
            }),
            description_placeholders={
                "mode_selector": translations.get("mode_selector", "Mode de Configuration"),
                "mode_selector_help": translations.get("mode_selector_help", "Choisissez entre l'interface graphique ou l'éditeur YAML.")
            }
        )

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

    async def async_step_ui(self, user_input=None):
        """Handle UI-based device configuration."""
        errors = {}
        current_devices = []
        
        if user_input is not None:
            if user_input.get("action") == "preview":
                preview_yaml = yaml.dump(
                    {"custom_devices": user_input.get(CONF_CUSTOM_DEVICES, [])},
                    default_flow_style=False,
                    sort_keys=False
                )
                return self.async_show_form(
                    step_id="ui",
                    data_schema=vol.Schema({
                        vol.Optional(CONF_CUSTOM_DEVICES, default=current_devices): vol.All(
                            cv.ensure_list,
                            [vol.Schema({
                                vol.Required("eedomus_id"): str,
                                vol.Required("ha_entity"): str,
                                vol.Required("type"): vol.In(["light", "switch", "sensor", "climate", "cover", "binary_sensor", "text_sensor"]),
                                vol.Optional("ha_subtype"): str,
                                vol.Optional("icon"): str,
                                vol.Optional("room"): str,
                                vol.Optional("parent_periph_id"): str,
                                vol.Optional("attributes"): dict,
                            })]
                        ),
                    }),
                    description_placeholders={
                        "preview": f"```yaml\n{preview_yaml}\n```"
                    },
                )
            
            try:
                validated = YAML_MAPPING_SCHEMA({
                    "custom_devices": user_input.get(CONF_CUSTOM_DEVICES, [])
                })
                await async_save_custom_mapping(
                    self.hass,
                    self.hass.config.config_dir,
                    validated
                )
                return self.async_create_entry(
                    title="",
                    data={
                        CONF_USE_YAML: False,
                        CONF_CUSTOM_DEVICES: user_input.get(CONF_CUSTOM_DEVICES, [])
                    }
                )
            except vol.Invalid as e:
                errors["base"] = f"Erreur de validation: {e}"

        # Load current devices
        try:
            current_mapping = await async_load_mapping(
                self.hass,
                self.hass.config.config_dir
            )
            current_devices = current_mapping.get("custom_devices", [])
        except Exception as e:
            _LOGGER.error("Error loading mapping: %s", e)
            current_devices = []
        
        # Load current API configuration
        current_options = self._copy_config_to_options()
        
        # Load translations
        language = self.hass.config.language if self.hass else "en"
        translations = await async_get_translations(self.hass, language) if self.hass else {}
        
        return self.async_show_form(
            step_id="ui",
            data_schema=vol.Schema({
                vol.Required(CONF_CUSTOM_DEVICES, default=current_devices): vol.All(
                    cv.ensure_list,
                    [vol.Schema({
                        vol.Required("eedomus_id"): str,
                        vol.Required("ha_entity"): str,
                        vol.Required("type"): vol.In(["light", "switch", "sensor", "climate", "cover", "binary_sensor", "text_sensor"]),
                        vol.Optional("ha_subtype"): str,
                        vol.Optional("icon"): str,
                        vol.Optional("room"): str,
                        vol.Optional("parent_periph_id"): str,
                        vol.Optional("attributes"): dict,
                    })]
                ),
            }),
            description_placeholders={
                "intro": translations.get("ui_intro", "Configurez vos devices eedomus via l'interface graphique ou basculez en mode YAML pour une édition avancée.")
            }
        )

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