"""Config flow for eedomus integration.

Detailed parameter documentation is available in docs/OPTIONS_DOCUMENTATION.md
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

# Import the options flow handler for the async_get_options_flow method
from .options_flow import EedomusOptionsFlow

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
    CONF_HTTP_REQUEST_TIMEOUT,
    CONF_PHP_FALLBACK_ENABLED,
    CONF_PHP_FALLBACK_SCRIPT_NAME,
    CONF_PHP_FALLBACK_TIMEOUT,
    CONF_REMOVE_ENTITIES,
    DEFAULT_API_HOST,
    DEFAULT_API_PROXY_DISABLE_SECURITY,
    DEFAULT_API_SECRET,
    DEFAULT_API_USER,
    DEFAULT_CONF_ENABLE_API_EEDOMUS,
    DEFAULT_CONF_ENABLE_API_PROXY,

    DEFAULT_ENABLE_SET_VALUE_RETRY,
    DEFAULT_ENABLE_WEBHOOK,
    DEFAULT_PHP_FALLBACK_ENABLED,
    DEFAULT_PHP_FALLBACK_SCRIPT_NAME,
    DEFAULT_PHP_FALLBACK_TIMEOUT,
    DEFAULT_HTTP_REQUEST_TIMEOUT,
    DEFAULT_REMOVE_ENTITIES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .eedomus_client import EedomusClient

# ASCII art and explanations
CONNECTION_MODES_EXPLANATION = """
🔄 CONNECTION MODES EXPLANATION 🔄

📋 API Eedomus Mode (Direct Connection - Pull):
      +----------------+     +----------------+
      | Home Assistant +--->+ Eedomus        |
      |                |     | (API)          |
      +----------------+     +----------------+
   • Home Assistant pulls data from Eedomus API
   • Requires API credentials (user/secret)
   • Enables full functionality including history
   • Uses coordinator for data synchronization
   • Recommended for most users

🔄 API Proxy Mode (Webhook - Push):
      +----------------+     +----------------+
      | Home Assistant +<---+ Eedomus        |
      |  (webhook)     |     | (HTTP)        |
      +----------------+     +----------------+
   • Eedomus pushes data to Home Assistant via webhooks
   • Only requires API host for webhook registration
   • No credentials needed for basic functionality
   • Limited functionality (no history)
   • Useful for restricted networks or real-time updates

💡 You can enable both modes for redundancy and optimal performance!
   - API Eedomus for full data access and history
   - API Proxy for real-time updates via webhooks

⚠️ SECURITY NOTE: API Proxy mode includes IP validation by default for security.
   This can be disabled in the configuration for debugging, but this is NOT RECOMMENDED
   for production environments as it exposes your webhook endpoints to potential abuse.

🔒 IMPORTANT SECURITY CONSIDERATION:
   The Eedomus box does NOT support HTTPS for local communications.
   All communications between Eedomus and Home Assistant are in PLAIN TEXT.
   Never expose your Eedomus box or Home Assistant directly to the internet!
"""

_LOGGER = logging.getLogger(__name__)

# Configuration constants
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ADVANCED_OPTIONS = "advanced_options"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_HOST, default=DEFAULT_API_HOST): str,
        vol.Required(
            CONF_ENABLE_API_EEDOMUS, default=DEFAULT_CONF_ENABLE_API_EEDOMUS
        ): bool,
        vol.Required(
            CONF_ENABLE_API_PROXY, default=DEFAULT_CONF_ENABLE_API_PROXY
        ): bool,
        vol.Optional(CONF_API_USER, default=DEFAULT_API_USER or ""): str,
        vol.Optional(CONF_API_SECRET, default=DEFAULT_API_SECRET or ""): str,
        vol.Optional(CONF_ENABLE_HISTORY, default=False): bool,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
        vol.Optional(CONF_HTTP_REQUEST_TIMEOUT, default=DEFAULT_HTTP_REQUEST_TIMEOUT): int,
        vol.Optional(
            CONF_ENABLE_SET_VALUE_RETRY, default=DEFAULT_ENABLE_SET_VALUE_RETRY
        ): bool,
        vol.Optional("max_retries", default=3): int,
        vol.Optional(
            CONF_ENABLE_WEBHOOK, default=DEFAULT_ENABLE_WEBHOOK
        ): bool,
        vol.Optional(
            CONF_API_PROXY_DISABLE_SECURITY, default=DEFAULT_API_PROXY_DISABLE_SECURITY
        ): bool,
        vol.Optional(
            CONF_PHP_FALLBACK_ENABLED, default=DEFAULT_PHP_FALLBACK_ENABLED
        ): bool,
        vol.Optional(
            CONF_PHP_FALLBACK_SCRIPT_NAME, default=DEFAULT_PHP_FALLBACK_SCRIPT_NAME
        ): str,
        vol.Optional(
            CONF_PHP_FALLBACK_TIMEOUT, default=DEFAULT_PHP_FALLBACK_TIMEOUT
        ): int,
    }
)


class EedomusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for eedomus."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        pass

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            _LOGGER.info(
                "Starting eedomus config flow - showing simplified single-screen form"
            )
            return self.async_show_form(
                step_id="user",
                data_schema=STEP_USER_DATA_SCHEMA,
                description_placeholders={"explanation": CONNECTION_MODES_EXPLANATION},
            )

        user_show = user_input.copy()
        user_show['api_secret'] = "********"
        _LOGGER.info("Config flow received user input: %s", user_show)
        _LOGGER.debug("Full user input details: %s", user_show)

        # Log which modes are selected
        api_eedomus_enabled = user_input.get(
            CONF_ENABLE_API_EEDOMUS, DEFAULT_CONF_ENABLE_API_EEDOMUS
        )
        api_proxy_enabled = user_input.get(
            CONF_ENABLE_API_PROXY, DEFAULT_CONF_ENABLE_API_PROXY
        )
        _LOGGER.info(
            "Selected modes - API Eedomus: %s, API Proxy: %s",
            api_eedomus_enabled,
            api_proxy_enabled,
        )

        # Validate the input
        try:
            info = await self.validate_input(user_input)
        except vol.Invalid as err:
            errors = {"base": str(err)}
            _LOGGER.error("Validation error: %s", str(err))
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception during validation")
            errors = {"base": "unknown"}
        else:
            _LOGGER.info("Configuration validation successful, creating entry")
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"explanation": CONNECTION_MODES_EXPLANATION},
        )

    async def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate the user input allows us to connect."""
        _LOGGER.info("Starting input validation for eedomus configuration")

        # Basic validation - API host is always required
        if not data[CONF_API_HOST] or not data[CONF_API_HOST].strip():
            _LOGGER.error("Validation failed: API host is empty")
            raise vol.Invalid("API host cannot be empty")

        # Validate scan interval (only relevant for API Eedomus mode, but validate anyway)
        scan_interval = data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        if scan_interval < 30:
            raise vol.Invalid("Scan interval must be at least 30 seconds")

        # Validate HTTP request timeout
        http_request_timeout = data.get(CONF_HTTP_REQUEST_TIMEOUT, DEFAULT_HTTP_REQUEST_TIMEOUT)
        if http_request_timeout < 5 or http_request_timeout > 120:
            raise vol.Invalid("HTTP request timeout must be between 5 and 120 seconds")

        # Check which modes are enabled
        api_eedomus_enabled = data.get(
            CONF_ENABLE_API_EEDOMUS, DEFAULT_CONF_ENABLE_API_EEDOMUS
        )
        api_proxy_enabled = data.get(
            CONF_ENABLE_API_PROXY, DEFAULT_CONF_ENABLE_API_PROXY
        )

        _LOGGER.info(
            "Validating configuration - API Eedomus: %s, API Proxy: %s",
            api_eedomus_enabled,
            api_proxy_enabled,
        )

        # Validate API Eedomus mode requirements
        if api_eedomus_enabled:
            # API Eedomus mode requires credentials
            if not data.get(CONF_API_USER) or not data[CONF_API_USER].strip():
                raise vol.Invalid(
                    "API user is required when API Eedomus mode is enabled"
                )

            if not data.get(CONF_API_SECRET) or not data[CONF_API_SECRET].strip():
                raise vol.Invalid(
                    "API secret is required when API Eedomus mode is enabled"
                )

            # History option is only available with API Eedomus mode
            if data.get(CONF_ENABLE_HISTORY) and not api_eedomus_enabled:
                raise vol.Invalid("History can only be enabled with API Eedomus mode")

            # Test the connection for API Eedomus mode
            session = async_get_clientsession(self.hass)

            client = EedomusClient(
                session=session,
                config_entry=ConfigEntry(
                    version=1,
                    domain=DOMAIN,
                    title=data[CONF_API_HOST],
                    data={
                        "api_host": data[CONF_API_HOST],
                        "api_user": data[CONF_API_USER],
                        "api_secret": data[CONF_API_SECRET],
                        CONF_ENABLE_HISTORY: data.get(CONF_ENABLE_HISTORY, False),
                        CONF_SCAN_INTERVAL: scan_interval,
                        CONF_ENABLE_API_EEDOMUS: api_eedomus_enabled,
                        CONF_ENABLE_API_PROXY: api_proxy_enabled,
                        CONF_ENABLE_SET_VALUE_RETRY: data.get(
                            CONF_ENABLE_SET_VALUE_RETRY, DEFAULT_ENABLE_SET_VALUE_RETRY
                        ),
                        CONF_API_PROXY_DISABLE_SECURITY: data.get(
                            CONF_API_PROXY_DISABLE_SECURITY,
                            DEFAULT_API_PROXY_DISABLE_SECURITY,
                        ),
                    },
                    source="user",
                    unique_id=f"eedomus_{data[CONF_API_HOST]}",
                    discovery_keys=None,
                    minor_version=None,
                    options={
                        CONF_PHP_FALLBACK_ENABLED: data.get(
                            CONF_PHP_FALLBACK_ENABLED, DEFAULT_PHP_FALLBACK_ENABLED
                        ),
                        CONF_PHP_FALLBACK_SCRIPT_NAME: data.get(
                            CONF_PHP_FALLBACK_SCRIPT_NAME,
                            DEFAULT_PHP_FALLBACK_SCRIPT_NAME,
                        ),
                        CONF_PHP_FALLBACK_TIMEOUT: data.get(
                            CONF_PHP_FALLBACK_TIMEOUT, DEFAULT_PHP_FALLBACK_TIMEOUT
                        ),
                    },
                    subentries_data=None,
                ),
            )
            _LOGGER.debug("Config flow validate input: %s", client)

            # Test the connection by trying to fetch peripheral list
            try:
                rdata = await client.auth_test()
                if not rdata or rdata.get("success", 0) != 1:
                    raise vol.Invalid(
                        "Cannot connect to eedomus API - please check your credentials and host"
                    )
                _LOGGER.info("API Eedomus connection test successful")
            except Exception as e:
                _LOGGER.error("API Eedomus connection test failed: %s", str(e))
                raise vol.Invalid(f"API Eedomus connection test failed: {str(e)}")

        # API Proxy mode validation
        if api_proxy_enabled:
            _LOGGER.info(
                "API Proxy mode enabled - webhook registration will be attempted"
            )
            # For proxy mode, we just need to ensure the host is valid
            # No connection test needed as webhooks are passive

        # Check if at least one mode is enabled
        if not api_eedomus_enabled and not api_proxy_enabled:
            raise vol.Invalid(
                "At least one connection mode (API Eedomus or API Proxy) must be enabled"
            )

        # Generate appropriate title based on enabled modes
        modes = []
        if api_eedomus_enabled:
            modes.append("Eedomus API")
        if api_proxy_enabled:
            modes.append("Proxy")

        return {"title": f"Eedomus ({data[CONF_API_HOST]}) - {' + '.join(modes)} Mode"}

    async def async_step_uninstall(self, user_input=None):
        """Handle the uninstall step."""
        if user_input is None:
            return self.async_show_form(
                step_id="uninstall",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_REMOVE_ENTITIES,
                            default=DEFAULT_REMOVE_ENTITIES
                        ): bool,
                    }
                ),
                description_placeholders={
                    "explanation": "⚠️ WARNING: This will remove the eedomus integration and optionally delete all associated entities. "
                    "This action cannot be undone. Make sure you have a backup of your configuration."
                },
            )

        # If user confirms uninstallation
        remove_entities = user_input.get(CONF_REMOVE_ENTITIES, DEFAULT_REMOVE_ENTITIES)
        
        # Store the uninstallation options in the config entry
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            options={**self.config_entry.options, CONF_REMOVE_ENTITIES: remove_entities}
        )

        # Proceed with uninstallation
        return await self.async_step_remove()

    async def async_step_remove(self, user_input=None):
        """Handle the removal of the config entry."""
        # Get the remove_entities option from the config entry
        remove_entities = self.config_entry.options.get(
            CONF_REMOVE_ENTITIES, DEFAULT_REMOVE_ENTITIES
        )

        if remove_entities:
            # Remove all entities associated with this integration
            await self._async_remove_entities()

        # Remove the config entry
        return await super().async_step_remove(user_input)

    async def _async_remove_entities(self):
        """Remove all entities associated with this integration."""
        _LOGGER.info("Removing all entities associated with eedomus integration")

        # Get all entities from the entity registry
        entity_registry = await self.hass.helpers.entity_registry.async_get_registry()

        # Find all entities that belong to this integration
        entities_to_remove = []
        for entity_entry in entity_registry.entities.values():
            if entity_entry.platform == DOMAIN:
                entities_to_remove.append(entity_entry.entity_id)

        # Remove the entities
        for entity_id in entities_to_remove:
            _LOGGER.info(f"Removing entity: {entity_id}")
            entity_registry.async_remove(entity_id)

        _LOGGER.info(f"Removed {len(entities_to_remove)} entities")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Get the options flow for this handler."""
        return EedomusOptionsFlow(config_entry)
