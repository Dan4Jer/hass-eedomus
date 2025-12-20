"""Config flow for eedomus integration."""
from __future__ import annotations

import logging
import voluptuous as vol
from typing import Any
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DOMAIN, CONF_API_USER, CONF_API_SECRET, CONF_API_HOST, 
    CONF_ENABLE_HISTORY, DEFAULT_API_HOST, DEFAULT_API_USER, 
    DEFAULT_API_SECRET, DEFAULT_CONF_ENABLE_HISTORY, DEFAULT_SCAN_INTERVAL,
    CONF_ENABLE_API_EEDOMUS, CONF_ENABLE_API_PROXY, DEFAULT_CONF_ENABLE_API_EEDOMUS,
    DEFAULT_CONF_ENABLE_API_PROXY, CONF_API_PROXY_DISABLE_SECURITY, DEFAULT_API_PROXY_DISABLE_SECURITY,
    CONF_ENABLE_SET_VALUE_RETRY, DEFAULT_ENABLE_SET_VALUE_RETRY
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
   This can be disabled in advanced options for debugging, but this is NOT RECOMMENDED
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
        vol.Required(CONF_ENABLE_API_EEDOMUS, default=DEFAULT_CONF_ENABLE_API_EEDOMUS): bool,
        vol.Required(CONF_ENABLE_API_PROXY, default=DEFAULT_CONF_ENABLE_API_PROXY): bool,
        vol.Optional(CONF_API_USER, default=DEFAULT_API_USER or ""): str,
        vol.Optional(CONF_API_SECRET, default=DEFAULT_API_SECRET or ""): str,
        vol.Optional(CONF_ENABLE_HISTORY, default=DEFAULT_CONF_ENABLE_HISTORY): bool,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
        vol.Optional("show_advanced_options", default=False): bool,
    }
)

STEP_ADVANCED_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional("enable_extended_attributes", default=False): bool,
        vol.Optional(CONF_ENABLE_SET_VALUE_RETRY, default=DEFAULT_ENABLE_SET_VALUE_RETRY): bool,
        vol.Optional("max_retries", default=3): int,
        vol.Optional(CONF_API_PROXY_DISABLE_SECURITY, default=DEFAULT_API_PROXY_DISABLE_SECURITY): bool,
    }
)

class EedomusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for eedomus."""

    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        self._user_input = {}
        self._advanced_options = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            _LOGGER.info("Starting eedomus config flow - showing initial form")
            return self.async_show_form(
                step_id="user", 
                data_schema=STEP_USER_DATA_SCHEMA,
                description_placeholders={"explanation": CONNECTION_MODES_EXPLANATION}
            )

        _LOGGER.info("Config flow received user input: %s", user_input)
        _LOGGER.debug("Full user input details: %s", user_input)
        
        # Store user input
        self._user_input = user_input
        
        # Log which modes are selected
        api_eedomus_enabled = user_input.get(CONF_ENABLE_API_EEDOMUS, DEFAULT_CONF_ENABLE_API_EEDOMUS)
        api_proxy_enabled = user_input.get(CONF_ENABLE_API_PROXY, DEFAULT_CONF_ENABLE_API_PROXY)
        _LOGGER.info("Selected modes - API Eedomus: %s, API Proxy: %s", api_eedomus_enabled, api_proxy_enabled)
        
        # Log if advanced options are being shown
        show_advanced = user_input.get("show_advanced_options", False)
        if show_advanced:
            _LOGGER.info("Advanced options are enabled in the form")
        
        # Check if user wants to see advanced options
        if user_input.get("show_advanced_options", False):
            _LOGGER.info("🔧 User requested advanced options - showing advanced configuration form")
            return await self.async_step_advanced()
        
        # Validate the input (only if not coming back from advanced options)
        # If we have advanced options stored, we're coming back from advanced form
        if self._advanced_options:
            _LOGGER.info("Finalizing configuration with advanced options")
            # Combine user input and advanced options for final validation
            final_user_input = {**user_input, **self._advanced_options}
            
            try:
                info = await self.validate_input(final_user_input)
            except vol.Invalid as err:
                errors["base"] = str(err)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during final validation")
                errors["base"] = "unknown"
            else:
                # Create entry with combined data
                return self.async_create_entry(title=info["title"], data=final_user_input)
        else:
            # Normal validation for first submission
            try:
                info = await self.validate_input(user_input)
            except vol.Invalid as err:
                errors["base"] = str(err)
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Combine user input and advanced options (if any)
                final_data = {**user_input, **self._advanced_options}
                return self.async_create_entry(title=info["title"], data=final_data)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
    
    async def async_step_advanced(self, user_input=None):
        """Handle the advanced options step."""
        if user_input is None:
            _LOGGER.info("Showing advanced options form")
            return self.async_show_form(
                step_id="advanced", data_schema=STEP_ADVANCED_DATA_SCHEMA
            )
        
        _LOGGER.info("Advanced options submitted: %s", user_input)
        
        _LOGGER.debug("Advanced options: %s", user_input)
        self._advanced_options = user_input
        
        # Go back to user step to finalize, but keep show_advanced_options=True to show the button as active
        # Don't validate again, just show the form with the advanced options
        user_input_with_advanced = {**self._user_input, "show_advanced_options": True}
        
        # Log the combined data for debugging
        _LOGGER.info("✅ Advanced options saved - returning to main configuration form")
        _LOGGER.info("💡 User can now review all settings and click Submit to finalize configuration")
        _LOGGER.debug("Combined data: %s", user_input_with_advanced)
        
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            description_placeholders={"explanation": CONNECTION_MODES_EXPLANATION}
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
        
        # Check which modes are enabled
        api_eedomus_enabled = data.get(CONF_ENABLE_API_EEDOMUS, DEFAULT_CONF_ENABLE_API_EEDOMUS)
        api_proxy_enabled = data.get(CONF_ENABLE_API_PROXY, DEFAULT_CONF_ENABLE_API_PROXY)
        
        _LOGGER.info("Validating configuration - API Eedomus: %s, API Proxy: %s", 
                    api_eedomus_enabled, api_proxy_enabled)
        
        # Validate API Eedomus mode requirements
        if api_eedomus_enabled:
            # API Eedomus mode requires credentials
            if not data.get(CONF_API_USER) or not data[CONF_API_USER].strip():
                raise vol.Invalid("API user is required when API Eedomus mode is enabled")
                
            if not data.get(CONF_API_SECRET) or not data[CONF_API_SECRET].strip():
                raise vol.Invalid("API secret is required when API Eedomus mode is enabled")
            
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
                        CONF_ENABLE_HISTORY: data.get(CONF_ENABLE_HISTORY, DEFAULT_CONF_ENABLE_HISTORY),
                        CONF_SCAN_INTERVAL: scan_interval,
                        CONF_ENABLE_API_EEDOMUS: api_eedomus_enabled,
                        CONF_ENABLE_API_PROXY: api_proxy_enabled,
                        CONF_ENABLE_SET_VALUE_RETRY: data.get(CONF_ENABLE_SET_VALUE_RETRY, DEFAULT_ENABLE_SET_VALUE_RETRY),
                        CONF_API_PROXY_DISABLE_SECURITY: data.get(CONF_API_PROXY_DISABLE_SECURITY, DEFAULT_API_PROXY_DISABLE_SECURITY)
                    },
                    source="user",
                    unique_id=f"eedomus_{data[CONF_API_HOST]}",
                    discovery_keys = None,
                    minor_version = None,
                    options= None,
                    subentries_data = None
                ),
            )
            _LOGGER.debug("Config flow validate input: %s", client)
            
            # Test the connection by trying to fetch peripheral list
            try:
                rdata = await client.auth_test()
                if not rdata or rdata.get("success", 0) != 1:
                    raise vol.Invalid("Cannot connect to eedomus API - please check your credentials and host")
                _LOGGER.info("API Eedomus connection test successful")
            except Exception as e:
                _LOGGER.error("API Eedomus connection test failed: %s", str(e))
                raise vol.Invalid(f"API Eedomus connection test failed: {str(e)}")
        
        # API Proxy mode validation
        if api_proxy_enabled:
            _LOGGER.info("API Proxy mode enabled - webhook registration will be attempted")
            # For proxy mode, we just need to ensure the host is valid
            # No connection test needed as webhooks are passive
        
        # Check if at least one mode is enabled
        if not api_eedomus_enabled and not api_proxy_enabled:
            raise vol.Invalid("At least one connection mode (API Eedomus or API Proxy) must be enabled")
        
        # Generate appropriate title based on enabled modes
        modes = []
        if api_eedomus_enabled:
            modes.append("Eedomus API")
        if api_proxy_enabled:
            modes.append("Proxy")
        
        return {"title": f"Eedomus ({data[CONF_API_HOST]}) - {' + '.join(modes)} Mode"}
