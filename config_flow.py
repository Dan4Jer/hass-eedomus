"""Config flow for eedomus integration."""
from __future__ import annotations

import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DOMAIN, CONF_API_USER, CONF_API_SECRET, CONF_API_HOST, CONF_ENABLE_HISTORY, DEFAULT_API_HOST, DEFAULT_API_USER, DEFAULT_API_SECRET, DEFAULT_CONF_ENABLE_HISTORY
from .eedomus_client import EedomusClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_HOST, default=DEFAULT_API_HOST): str,
        vol.Required(CONF_API_USER, default=DEFAULT_API_USER): str,
        vol.Required(CONF_API_SECRET, default=DEFAULT_API_SECRET): str,
        vol.Required(CONF_ENABLE_HISTORY, default=DEFAULT_CONF_ENABLE_HISTORY): bool,
    }
)

class EedomusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for eedomus."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            # Use vol.Schema instead of the deprecated CONFIG_SCHEMA
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        _LOGGER.debug("Config flow user input: %s", user_input)

        # Here you would typically validate the connection

        errors = {}

        try:
            info = await self.validate_input(user_input)
        except vol.Invalid as err:
            errors["base"] = str(err)
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
    
    async def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate the user input allows us to connect."""
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
                    CONF_ENABLE_HISTORY: data[CONF_ENABLE_HISTORY]
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
        rdata = await client.auth_test()
        if not rdata or rdata.get("success", 0) != 1:
            raise vol.Invalid("Cannot connect to eedomus API - please check your credentials and host")

        return {"title": f"Eedomus ({data[CONF_API_HOST]})"}
