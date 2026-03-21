"""Eedomus Configuration Panel for Home Assistant 2026+."""

import logging
from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_panel(hass: HomeAssistant):
    """Set up the Eedomus configuration panel."""
    
    try:
        # Register the panel using iframe approach
        async_register_built_in_panel(
            hass,
            "eedomus-config",
            "eedomus-config-panel",  # This should match the HTML filename
            "mdi:cog",
            require_admin=True,
        )
        
        _LOGGER.info("✅ Eedomus configuration panel registered successfully")
        
    except Exception as e:
        _LOGGER.error("Error setting up Eedomus panel: %s", e)
        return False
    
    return True

async def async_unload_panel(hass: HomeAssistant):
    """Unload the Eedomus configuration panel."""
    return True
