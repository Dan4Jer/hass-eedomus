"""The eedomus integration."""
import logging
import aiohttp
import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client
from .const import DOMAIN, PLATFORMS, COORDINATOR
from .coordinator import EedomusDataUpdateCoordinator
from .eedomus_client import EedomusClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eedomus from a config entry."""
    _LOGGER.debug("Setting up eedomus integration with entry: %s", entry.title)

    # Create an aiohttp session for the client
    session = aiohttp_client.async_get_clientsession(hass)

    client = EedomusClient(
        session=session,
        api_user=entry.data["api_user"],
        api_secret=entry.data["api_secret"],
        api_host=entry.data["api_host"],
    )

    coordinator = EedomusDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("eedomus integration setup completed for entry: %s", entry.title)
    return True
