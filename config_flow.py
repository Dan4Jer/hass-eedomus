"""Config flow for eedomus integration."""
import logging
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, STEP_USER_DATA_SCHEMA
from .eedomus_client import EedomusClient

_LOGGER = logging.getLogger(__name__)

class EedomusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for eedomus."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=config_entries.CONFIG_SCHEMA(
                    STEP_USER_DATA_SCHEMA
                ),
            )

        _LOGGER.debug("Config flow user input: %s", user_input)

        client = EedomusClient(
            api_user=user_input["api_user"],
            api_secret=user_input["api_secret"],
            api_host=user_input["api_host"],
        )

        try:
            await self.hass.async_add_executor_job(client.get_periph_list)
            _LOGGER.debug("Successfully connected to eedomus API")
        except Exception as err:
            _LOGGER.exception("Error connecting to eedomus API: %s", err)
            return self.async_show_form(
                step_id="user",
                errors={"base": "auth"},
            )

        return self.async_create_entry(
            title="eedomus",
            data=user_input,
        )
