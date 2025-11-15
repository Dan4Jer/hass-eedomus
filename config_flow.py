"""Config flow for eedomus integration."""
from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_API_USER, CONF_API_SECRET, CONF_API_HOST, DEFAULT_API_HOST

_LOGGER = logging.getLogger(__name__)

class EedomusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for eedomus."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            # Use vol.Schema instead of the deprecated CONFIG_SCHEMA
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_API_HOST, default=DEFAULT_API_HOST): str,
                    vol.Required(CONF_API_USER): str,
                    vol.Required(CONF_API_SECRET): str,
                })
            )

        _LOGGER.debug("Config flow user input: %s", user_input)

        # Here you would typically validate the connection
        # For now we'll just create the entry
        return self.async_create_entry(
            title="eedomus",
            data=user_input,
        )
