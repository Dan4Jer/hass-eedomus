"""Eedomus Configuration Panel for Home Assistant 2026+."""

import logging
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Track if panel is already registered to avoid duplicate registration
_PANEL_REGISTERED = False

async def async_setup_panel(hass: HomeAssistant):
    """Set up the Eedomus configuration panel.
    
    Note: Panel registration is now handled via frontend.yaml for modern HA approach.
    This function is kept for backward compatibility but won't be called.
    """
    global _PANEL_REGISTERED
    
    _LOGGER.debug("Panel registration via async_setup_panel is disabled - using frontend.yaml instead")
    return False

async def async_unload_panel(hass: HomeAssistant):
    """Unload the Eedomus configuration panel."""
    return True
