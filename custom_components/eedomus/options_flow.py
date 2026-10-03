"""Options flow for eedomus integration with UI/YAML toggle.

Detailed parameter documentation is available in docs/OPTIONS_DOCUMENTATION.md
"""

import logging

import voluptuous as vol
import yaml
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_API_HOST,
    CONF_API_PROXY_DISABLE_SECURITY,
    CONF_API_SECRET,
    CONF_API_USER,
    CONF_ENABLE_API_EEDOMUS,
    CONF_ENABLE_API_PROXY,
    CONF_ENABLE_HISTORY,
    CONF_ENABLE_SET_VALUE_RETRY,
    CONF_ENABLE_WEBHOOK,
    CONF_HISTORY_PERIPHERALS_PER_SCAN,
    CONF_HISTORY_RETRY_DELAY,
    CONF_HTTP_REQUEST_TIMEOUT,
    CONF_PHP_FALLBACK_ENABLED,
    CONF_PHP_FALLBACK_SCRIPT_NAME,
    CONF_PHP_FALLBACK_TIMEOUT,
    CONF_SCAN_INTERVAL,
    CONF_YAML_CONTENT,
    DEFAULT_HISTORY_PERIPHERALS_PER_SCAN,
    DEFAULT_HISTORY_RETRY_DELAY,
    DEFAULT_HTTP_REQUEST_TIMEOUT,
    DOMAIN,
)
from .storage_mapping import async_load_mapping, async_save_custom_mapping

_LOGGER = logging.getLogger(__name__)


class EedomusOptionsFlow(config_entries.OptionsFlow):
    """Handle eedomus options with UI/YAML toggle."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        super().__init__()
        self._config_entry = config_entry
        self.yaml_content = ""
        self.hass = None

    def _copy_config_to_options(self):
        """Copy configuration values from config_entry.data to options.

        This ensures that values set during config_flow are available in options_flow.
        Only copies values that haven't been explicitly set in options.
        """
        if not self._config_entry.options:
            options = {}
        else:
            options = dict(self._config_entry.options)

        config_data = self._config_entry.data

        # FIX : On injecte les identifiants directement dans le dictionnaire pour éviter le NameError
        options[CONF_API_HOST] = self._config_entry.options.get(
            CONF_API_HOST, config_data.get(CONF_API_HOST, "")
        )
        options[CONF_API_USER] = self._config_entry.options.get(
            CONF_API_USER, config_data.get(CONF_API_USER, "")
        )
        options[CONF_API_SECRET] = self._config_entry.options.get(
            CONF_API_SECRET, config_data.get(CONF_API_SECRET, "")
        )

        if CONF_ENABLE_API_EEDOMUS not in options:
            options[CONF_ENABLE_API_EEDOMUS] = config_data.get(
                CONF_ENABLE_API_EEDOMUS, True
            )
        if CONF_ENABLE_API_PROXY not in options:
            options[CONF_ENABLE_API_PROXY] = config_data.get(
                CONF_ENABLE_API_PROXY, False
            )
        if CONF_ENABLE_HISTORY not in options:
            options[CONF_ENABLE_HISTORY] = config_data.get(CONF_ENABLE_HISTORY, False)
        if CONF_HISTORY_PERIPHERALS_PER_SCAN not in options:
            options[CONF_HISTORY_PERIPHERALS_PER_SCAN] = config_data.get(
                CONF_HISTORY_PERIPHERALS_PER_SCAN, DEFAULT_HISTORY_PERIPHERALS_PER_SCAN
            )
        if CONF_SCAN_INTERVAL not in options:
            options[CONF_SCAN_INTERVAL] = config_data.get(CONF_SCAN_INTERVAL, 300)
        if CONF_HTTP_REQUEST_TIMEOUT not in options:
            options[CONF_HTTP_REQUEST_TIMEOUT] = config_data.get(
                CONF_HTTP_REQUEST_TIMEOUT, DEFAULT_HTTP_REQUEST_TIMEOUT
            )
        if CONF_ENABLE_SET_VALUE_RETRY not in options:
            options[CONF_ENABLE_SET_VALUE_RETRY] = config_data.get(
                CONF_ENABLE_SET_VALUE_RETRY, True
            )
        if CONF_ENABLE_WEBHOOK not in options:
            options[CONF_ENABLE_WEBHOOK] = config_data.get(CONF_ENABLE_WEBHOOK, True)
        if CONF_API_PROXY_DISABLE_SECURITY not in options:
            options[CONF_API_PROXY_DISABLE_SECURITY] = config_data.get(
                CONF_API_PROXY_DISABLE_SECURITY, False
            )
        if CONF_PHP_FALLBACK_ENABLED not in options:
            options[CONF_PHP_FALLBACK_ENABLED] = config_data.get(
                CONF_PHP_FALLBACK_ENABLED, False
            )
        if CONF_PHP_FALLBACK_SCRIPT_NAME not in options:
            options[CONF_PHP_FALLBACK_SCRIPT_NAME] = config_data.get(
                CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php"
            )
        if CONF_PHP_FALLBACK_TIMEOUT not in options:
            options[CONF_PHP_FALLBACK_TIMEOUT] = config_data.get(
                CONF_PHP_FALLBACK_TIMEOUT, 5
            )

        _LOGGER.debug(
            "Copied config to options: %s",
            {k: v for k, v in options.items() if k not in ["api_user", "api_secret"]},
        )
        return options

    async def async_step_init(self, user_input=None):
        """Manage the options with mode selection."""
        errors = {}

        if user_input is not None:
            # --- 🛡️ CONTRÔLE DE LA CONNEXION À LA BOX EEDOMUS ---
            if user_input.get(CONF_ENABLE_API_EEDOMUS, True):
                try:
                    from homeassistant.config_entries import ConfigEntry
                    from homeassistant.helpers.aiohttp_client import (
                        async_get_clientsession,
                    )

                    from .eedomus_client import EedomusClient

                    session = async_get_clientsession(self.hass)

                    # On simule un ConfigEntry temporaire pour tester les nouvelles saisies de l'utilisateur
                    test_client = EedomusClient(
                        session=session,
                        config_entry=ConfigEntry(
                            version=1,
                            domain=DOMAIN,
                            title=user_input[CONF_API_HOST],
                            data={
                                CONF_API_HOST: user_input[CONF_API_HOST],
                                CONF_API_USER: user_input[CONF_API_USER],
                                CONF_API_SECRET: user_input[CONF_API_SECRET],
                                CONF_ENABLE_HISTORY: user_input.get(
                                    CONF_ENABLE_HISTORY, False
                                ),
                                CONF_SCAN_INTERVAL: user_input.get(
                                    CONF_SCAN_INTERVAL, 300
                                ),
                                CONF_ENABLE_API_EEDOMUS: True,
                                CONF_ENABLE_API_PROXY: user_input.get(
                                    CONF_ENABLE_API_PROXY, False
                                ),
                                CONF_API_PROXY_DISABLE_SECURITY: user_input.get(
                                    CONF_API_PROXY_DISABLE_SECURITY, False
                                ),
                            },
                            source="user",
                            unique_id=f"eedomus_{user_input[CONF_API_HOST]}",
                            discovery_keys=None,
                            minor_version=None,
                            options={},
                            subentries_data=None,
                        ),
                    )

                    # Test effectif de communication
                    rdata = await test_client.auth_test()
                    if not rdata or rdata.get("success", 0) != 1:
                        errors["base"] = "cannot_connect"
                except Exception as e:
                    _LOGGER.error("Eedomus options validation failed: %s", e)
                    errors["base"] = "cannot_connect"

            if not errors:
                # Si aucune erreur, on procède à la sauvegarde des options
                options = {}
                options[CONF_API_HOST] = user_input[CONF_API_HOST]
                options[CONF_API_USER] = user_input[CONF_API_USER]
                options[CONF_API_SECRET] = user_input[CONF_API_SECRET]

                options[CONF_ENABLE_API_EEDOMUS] = user_input.get(
                    CONF_ENABLE_API_EEDOMUS, True
                )
                options[CONF_ENABLE_API_PROXY] = user_input.get(
                    CONF_ENABLE_API_PROXY, False
                )
                options[CONF_ENABLE_HISTORY] = user_input.get(
                    CONF_ENABLE_HISTORY, False
                )
                options[CONF_HISTORY_RETRY_DELAY] = user_input.get(
                    CONF_HISTORY_RETRY_DELAY, DEFAULT_HISTORY_RETRY_DELAY
                )
                options[CONF_HISTORY_PERIPHERALS_PER_SCAN] = user_input.get(
                    CONF_HISTORY_PERIPHERALS_PER_SCAN,
                    DEFAULT_HISTORY_PERIPHERALS_PER_SCAN,
                )
                options[CONF_SCAN_INTERVAL] = user_input.get(CONF_SCAN_INTERVAL, 300)
                options[CONF_ENABLE_SET_VALUE_RETRY] = user_input.get(
                    CONF_ENABLE_SET_VALUE_RETRY, True
                )
                options[CONF_ENABLE_WEBHOOK] = user_input.get(CONF_ENABLE_WEBHOOK, True)
                options[CONF_API_PROXY_DISABLE_SECURITY] = user_input.get(
                    CONF_API_PROXY_DISABLE_SECURITY, False
                )
                options[CONF_PHP_FALLBACK_ENABLED] = user_input.get(
                    CONF_PHP_FALLBACK_ENABLED, False
                )
                options[CONF_PHP_FALLBACK_SCRIPT_NAME] = user_input.get(
                    CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php"
                )
                options[CONF_PHP_FALLBACK_TIMEOUT] = user_input.get(
                    CONF_PHP_FALLBACK_TIMEOUT, 5
                )
                options[CONF_HTTP_REQUEST_TIMEOUT] = user_input.get(
                    CONF_HTTP_REQUEST_TIMEOUT, DEFAULT_HTTP_REQUEST_TIMEOUT
                )

                return self.async_create_entry(title="", data=options)

        # Récupération des options courantes (sécurisées par le FIX)
        current_options = self._copy_config_to_options()

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_HOST, default=current_options.get(CONF_API_HOST, "")
                    ): str,
                    vol.Required(
                        CONF_API_USER, default=current_options.get(CONF_API_USER, "")
                    ): str,
                    vol.Required(
                        CONF_API_SECRET,
                        default=current_options.get(CONF_API_SECRET, ""),
                    ): str,
                    vol.Optional(
                        CONF_ENABLE_API_EEDOMUS,
                        default=current_options.get(CONF_ENABLE_API_EEDOMUS, True),
                    ): bool,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current_options.get(CONF_SCAN_INTERVAL, 300),
                    ): int,
                    vol.Optional(
                        CONF_ENABLE_API_PROXY,
                        default=current_options.get(CONF_ENABLE_API_PROXY, False),
                    ): bool,
                    vol.Optional(
                        CONF_ENABLE_HISTORY,
                        default=current_options.get(CONF_ENABLE_HISTORY, False),
                    ): bool,
                    vol.Optional(
                        CONF_HTTP_REQUEST_TIMEOUT,
                        default=current_options.get(
                            CONF_HTTP_REQUEST_TIMEOUT, DEFAULT_HTTP_REQUEST_TIMEOUT
                        ),
                    ): int,
                    vol.Optional(
                        CONF_ENABLE_SET_VALUE_RETRY,
                        default=current_options.get(CONF_ENABLE_SET_VALUE_RETRY, True),
                    ): bool,
                    vol.Optional(
                        CONF_ENABLE_WEBHOOK,
                        default=current_options.get(CONF_ENABLE_WEBHOOK, True),
                    ): bool,
                    vol.Optional(
                        CONF_API_PROXY_DISABLE_SECURITY,
                        default=current_options.get(
                            CONF_API_PROXY_DISABLE_SECURITY, False
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_PHP_FALLBACK_ENABLED,
                        default=current_options.get(CONF_PHP_FALLBACK_ENABLED, False),
                    ): bool,
                    vol.Optional(
                        CONF_PHP_FALLBACK_SCRIPT_NAME,
                        default=current_options.get(
                            CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php"
                        ),
                    ): str,
                    vol.Optional(
                        CONF_PHP_FALLBACK_TIMEOUT,
                        default=current_options.get(CONF_PHP_FALLBACK_TIMEOUT, 5),
                    ): int,
                }
            ),
            errors=errors,
            description_placeholders={
                "docs_link": "https://github.com/Dan4Jer/hass-eedomus/blob/main/docs/README.md"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return EedomusOptionsFlow(config_entry)

    async def async_step_ui(self, user_input=None):
        """Handle UI-based device configuration."""
        errors = {}

        if user_input is not None:
            # Update options
            options = {}
            # Add API configuration options - ensure config values are preserved
            current_options = self._copy_config_to_options()
            options.update(
                {
                    CONF_ENABLE_API_EEDOMUS: current_options.get(
                        CONF_ENABLE_API_EEDOMUS, True
                    ),
                    CONF_ENABLE_API_PROXY: current_options.get(
                        CONF_ENABLE_API_PROXY, False
                    ),
                    CONF_ENABLE_HISTORY: current_options.get(
                        CONF_ENABLE_HISTORY, False
                    ),
                    CONF_HISTORY_RETRY_DELAY: current_options.get(
                        CONF_HISTORY_RETRY_DELAY, DEFAULT_HISTORY_RETRY_DELAY
                    ),
                    CONF_HISTORY_PERIPHERALS_PER_SCAN: current_options.get(
                        CONF_HISTORY_PERIPHERALS_PER_SCAN,
                        DEFAULT_HISTORY_PERIPHERALS_PER_SCAN,
                    ),
                    CONF_SCAN_INTERVAL: current_options.get(CONF_SCAN_INTERVAL, 300),
                    CONF_ENABLE_SET_VALUE_RETRY: current_options.get(
                        CONF_ENABLE_SET_VALUE_RETRY, True
                    ),
                    CONF_ENABLE_WEBHOOK: current_options.get(CONF_ENABLE_WEBHOOK, True),
                    CONF_API_PROXY_DISABLE_SECURITY: current_options.get(
                        CONF_API_PROXY_DISABLE_SECURITY, False
                    ),
                    CONF_PHP_FALLBACK_ENABLED: current_options.get(
                        CONF_PHP_FALLBACK_ENABLED, False
                    ),
                    CONF_PHP_FALLBACK_SCRIPT_NAME: current_options.get(
                        CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php"
                    ),
                    CONF_PHP_FALLBACK_TIMEOUT: current_options.get(
                        CONF_PHP_FALLBACK_TIMEOUT, 5
                    ),
                    CONF_HTTP_REQUEST_TIMEOUT: current_options.get(
                        CONF_HTTP_REQUEST_TIMEOUT, DEFAULT_HTTP_REQUEST_TIMEOUT
                    ),
                }
            )
            # Log the options being saved
            _LOGGER.debug("Saving options in UI mode: %s", options)
            return self.async_create_entry(title="", data=options)

        # Load current API configuration
        current_options = self._copy_config_to_options()

        return self.async_show_form(
            step_id="ui",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_ENABLE_API_EEDOMUS,
                        default=current_options.get(CONF_ENABLE_API_EEDOMUS, True),
                    ): bool,
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current_options.get(CONF_SCAN_INTERVAL, 300),
                    ): int,
                    vol.Optional(
                        CONF_ENABLE_API_PROXY,
                        default=current_options.get(CONF_ENABLE_API_PROXY, False),
                    ): bool,
                    vol.Optional(
                        CONF_ENABLE_HISTORY,
                        default=current_options.get(CONF_ENABLE_HISTORY, False),
                    ): bool,
                    vol.Optional(
                        CONF_HTTP_REQUEST_TIMEOUT,
                        default=current_options.get(
                            CONF_HTTP_REQUEST_TIMEOUT, DEFAULT_HTTP_REQUEST_TIMEOUT
                        ),
                    ): int,
                    vol.Optional(
                        CONF_ENABLE_SET_VALUE_RETRY,
                        default=current_options.get(CONF_ENABLE_SET_VALUE_RETRY, True),
                    ): bool,
                    vol.Optional(
                        CONF_ENABLE_WEBHOOK,
                        default=current_options.get(CONF_ENABLE_WEBHOOK, True),
                    ): bool,
                    vol.Optional(
                        CONF_API_PROXY_DISABLE_SECURITY,
                        default=current_options.get(
                            CONF_API_PROXY_DISABLE_SECURITY, False
                        ),
                    ): bool,
                    vol.Optional(
                        CONF_PHP_FALLBACK_ENABLED,
                        default=current_options.get(CONF_PHP_FALLBACK_ENABLED, False),
                    ): bool,
                    vol.Optional(
                        CONF_PHP_FALLBACK_SCRIPT_NAME,
                        default=current_options.get(
                            CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php"
                        ),
                    ): str,
                    vol.Optional(
                        CONF_PHP_FALLBACK_TIMEOUT,
                        default=current_options.get(CONF_PHP_FALLBACK_TIMEOUT, 5),
                    ): int,
                }
            ),
            errors=errors,
            description_placeholders={"current_mode": "UI"},
        )

    async def async_step_yaml(self, user_input=None):
        """Handle YAML-based configuration."""
        # Local imports to avoid circular dependency
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
                    self.hass, self.hass.config.config_dir, validated
                )

                if success:
                    # Update options
                    options = {CONF_YAML_CONTENT: yaml_content}  # Store for re-editing
                    # Add API configuration options - ensure config values are preserved
                    current_options = self._copy_config_to_options()
                    options.update(
                        {
                            CONF_ENABLE_API_EEDOMUS: current_options.get(
                                CONF_ENABLE_API_EEDOMUS, True
                            ),
                            CONF_ENABLE_API_PROXY: current_options.get(
                                CONF_ENABLE_API_PROXY, False
                            ),
                            CONF_ENABLE_HISTORY: current_options.get(
                                CONF_ENABLE_HISTORY, False
                            ),
                            CONF_HISTORY_RETRY_DELAY: current_options.get(
                                CONF_HISTORY_RETRY_DELAY, DEFAULT_HISTORY_RETRY_DELAY
                            ),
                            CONF_HISTORY_PERIPHERALS_PER_SCAN: current_options.get(
                                CONF_HISTORY_PERIPHERALS_PER_SCAN,
                                DEFAULT_HISTORY_PERIPHERALS_PER_SCAN,
                            ),
                            CONF_SCAN_INTERVAL: current_options.get(
                                CONF_SCAN_INTERVAL, 300
                            ),
                            CONF_ENABLE_SET_VALUE_RETRY: current_options.get(
                                CONF_ENABLE_SET_VALUE_RETRY, True
                            ),
                            CONF_ENABLE_WEBHOOK: current_options.get(
                                CONF_ENABLE_WEBHOOK, True
                            ),
                            CONF_API_PROXY_DISABLE_SECURITY: current_options.get(
                                CONF_API_PROXY_DISABLE_SECURITY, False
                            ),
                            CONF_PHP_FALLBACK_ENABLED: current_options.get(
                                CONF_PHP_FALLBACK_ENABLED, False
                            ),
                            CONF_PHP_FALLBACK_SCRIPT_NAME: current_options.get(
                                CONF_PHP_FALLBACK_SCRIPT_NAME, "fallback.php"
                            ),
                            CONF_PHP_FALLBACK_TIMEOUT: current_options.get(
                                CONF_PHP_FALLBACK_TIMEOUT, 5
                            ),
                            CONF_HTTP_REQUEST_TIMEOUT: current_options.get(
                                CONF_HTTP_REQUEST_TIMEOUT, DEFAULT_HTTP_REQUEST_TIMEOUT
                            ),
                        }
                    )
                    # Log the options being saved
                    _LOGGER.debug("Saving options in YAML mode: %s", options)
                    return self.async_create_entry(title="", data=options)
                else:
                    errors["base"] = "failed_to_save_yaml"

            except yaml.YAMLError as e:
                problem = getattr(e, "problem", None)

                _LOGGER.warning(
                    "YAML parse error: %s",
                    problem or "invalid YAML syntax",
                )

                _LOGGER.debug(
                    "Full YAML parsing error",
                    exc_info=True,
                )

                errors["base"] = "invalid_yaml"

            except vol.Invalid as e:
                _LOGGER.warning(
                    "YAML validation error: %s",
                    str(e),
                )

                _LOGGER.debug(
                    "Full YAML parsing error",
                    exc_info=True,
                )

                errors["base"] = "invalid_mapping"

        # Load current YAML content
        try:
            current_mapping = await async_load_mapping(
                self.hass, self.hass.config.config_dir
            )
            self.yaml_content = yaml.dump(
                current_mapping,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
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
            data_schema=vol.Schema(
                {vol.Required("yaml_content", default=self.yaml_content): str}
            ),
            errors=errors,
            description_placeholders={
                "example": "Edit YAML directly for advanced configuration"
            },
        )


"""
    async def async_step_cleanup(self, user_input=None):
        " ""Handle cleanup of unused eedomus entities."" "
        _LOGGER.info("Starting cleanup of unused eedomus entities")

        # Get entity registry
        entity_registry = await self.hass.helpers.entity_registry.async_get_registry()

        # Find entities to remove: eedomus domain, disabled, and have "deprecated" in unique_id
        entities_to_remove = []
        entities_analyzed = 0
        entities_considered = 0

        for entity_entry in entity_registry.entities.values():
            entities_analyzed += 1

            # Check if this is an eedomus entity
            if entity_entry.platform == "eedomus":
                entities_considered += 1

                # Check if entity is disabled OR has "deprecated" in unique_id
                is_disabled = entity_entry.disabled
                has_deprecated = (
                    entity_entry.unique_id
                    and "deprecated" in entity_entry.unique_id.lower()
                )

                if is_disabled or has_deprecated:
                    entities_to_remove.append(
                        {
                            "entity_id": entity_entry.entity_id,
                            "unique_id": entity_entry.unique_id,
                            "disabled": is_disabled,
                            "has_deprecated": has_deprecated,
                            "reason": "deprecated" if has_deprecated else "disabled",
                        }
                    )

        _LOGGER.info(
            f"Cleanup analysis complete: {entities_analyzed} entities analyzed, "
            f"{entities_considered} eedomus entities considered, "
            f"{len(entities_to_remove)} entities to be removed"
        )

        # Remove the entities
        removed_count = 0
        for entity_info in entities_to_remove:
            try:
                _LOGGER.info(
                    f"Removing entity {entity_info['entity_id']} (reason: {entity_info['reason']}, "
                    f"unique_id: {entity_info['unique_id']})"
                )
                entity_registry.async_remove(entity_info["entity_id"])
                removed_count += 1
            except Exception as e:
                _LOGGER.error(
                    f"Failed to remove entity {entity_info['entity_id']}: {e}"
                )

        _LOGGER.info(
            f"Cleanup completed: {removed_count} entities removed out of {len(entities_to_remove)} identified"
        )

        return self.async_create_entry(
            title="",
            data={
                "cleanup_completed": True,
                "entities_analyzed": entities_analyzed,
                "entities_considered": entities_considered,
                "entities_identified": len(entities_to_remove),
                "entities_removed": removed_count,
            },
        )
"""
