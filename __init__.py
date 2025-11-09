import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, PLATFORMS, CONF_API_HOST, CONF_API_USER, CONF_API_SECRET, SCAN_INTERVAL
from .coordinator import EedomusDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    config = entry.data
    host = config[CONF_API_HOST]
    user = config[CONF_API_USER]
    secret = config[CONF_API_SECRET]

    coordinator = EedomusDataUpdateCoordinator(hass, host, user, secret)
    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Charge les plateformes
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = True
    if hasattr(PLATFORMS, "__iter__") and len(PLATFORMS) > 0:
        unload_ok = all(
            await asyncio.gather(
                *[hass.config_entries.async_forward_entry_unload(entry, platform) for platform in PLATFORMS]
            )
        )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
