from __future__ import annotations
import logging
import aiohttp
import async_timeout
import asyncio
import json
import voluptuous as vol
from homeassistant import config_entries
from homeassistant import exceptions
from homeassistant.data_entry_flow import FlowResult
from .const import DOMAIN, CONF_API_HOST, CONF_API_USER, CONF_API_SECRET

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_API_HOST): str,
    vol.Required(CONF_API_USER): str,
    vol.Required(CONF_API_SECRET): str,
})

async def _test_credentials(host: str, user: str, secret: str) -> bool:
    """Test connection to eedomus API."""
    url = f"http://{host}/api/get?action=auth.test&api_user={user}&api_secret={secret}&format=json"
    _LOGGER.warning(
        "try to connect to %s", url
    )
    try:
        async with async_timeout.timeout(5):
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={"Accept": "text/html"}) as resp:
                    _LOGGER.warning("Response status: %s", resp.status)
                    _LOGGER.warning("Response headers: %s", resp.headers)
                    text = await resp.text()
                    _LOGGER.warning("Response text: %s", text)
                    if resp.status != 200:
                        raise CannotConnect(f"HTTP status {resp.status}")
                    try:
                        # Parse manuellement le texte en JSON
                        data = json.loads(text)
                        _LOGGER.warning("Response JSON: %s", data)
                        if data.get("success") == 1:
                            return True
                        raise InvalidAuth("API credentials rejected by eedomus")
                    except aiohttp.ContentTypeError as err:
                        _LOGGER.warning("Response is not JSON, but server returned status 200")
                        raise CannotConnect("API did not return JSON")
    except asyncio.TimeoutError as err:
        raise CannotConnect("Timeout contacting eedomus") from err
    except aiohttp.ClientError as err:
        raise CannotConnect(f"Network error: {err}") from err
    except Exception as err:
        raise CannotConnect(f"Unexpected error: {err}") from err


 

class EedomusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    _attr_icon = "eedomus:eedomus"
    
    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        _LOGGER.warning(
        "début du flow %s", user_input
        )
    
        errors = {}

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA)

        host = user_input[CONF_API_HOST]
        user = user_input[CONF_API_USER]
        secret = user_input[CONF_API_SECRET]

        _LOGGER.warning(
            "host %s, user %s, secret %s", host, user, secret
        )
    
        try:
            await _test_credentials(host, user, secret)

            return self.async_create_entry(
                title=f"Eedomus ({host})",
                data=user_input
            )

        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception as exc:
            _LOGGER.exception("Unexpected error validating eedomus: %s", exc)
            errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate credentials are invalid."""
