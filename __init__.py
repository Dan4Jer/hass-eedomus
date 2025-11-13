"""The eedomus integration."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, PLATFORMS, COORDINATOR
from .coordinator import EedomusDataUpdateCoordinator
from .eedomus_client import EedomusClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eedomus from a config entry."""
    _LOGGER.debug("Setting up eedomus integration with entry: %s", entry.title)

    client = EedomusClient(
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

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("eedomus integration unloaded for entry: %s", entry.title)
    return unload_ok
