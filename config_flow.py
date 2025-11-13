"""Config flow for eedomus integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .eedomus_client import EedomusClient
from .const import DOMAIN, CONF_API_HOST, CONF_API_USER, CONF_API_SECRET

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_HOST): str,  # Champ obligatoire sans valeur par défaut
        vol.Required(CONF_API_USER): str,
        vol.Required(CONF_API_SECRET): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    client = EedomusClient(
        data[CONF_API_USER],
        data[CONF_API_SECRET],
        session,
        data[CONF_API_HOST]  # Passer l'hôte au client
    )

    # Test the connection by trying to fetch peripheral list
    rdata = await client.auth_test()
    if not rdata or rdata.get("success", 0) != 1:
        raise vol.Invalid("Cannot connect to eedomus API - please check your credentials and host")

    return {"title": f"Eedomus ({data[CONF_API_HOST]})"}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for eedomus."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
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
