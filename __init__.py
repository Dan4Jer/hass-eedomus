"""The eedomus integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_API_HOST, CONF_API_USER, CONF_API_SECRET, PLATFORMS
from .coordinator import EedomusDataUpdateCoordinator
from .eedomus_client import EedomusClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up eedomus from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api_user = entry.data[CONF_API_USER]
    api_secret = entry.data[CONF_API_SECRET]
    api_host = entry.data[CONF_API_HOST]  # Récupérer l'hôte depuis la configuration

    session = async_get_clientsession(hass)
    client = EedomusClient(api_user, api_secret, session, api_host)

    coordinator = EedomusDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
