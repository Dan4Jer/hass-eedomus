"""Eedomus Configuration Panel for Home Assistant 2026+."""

import logging
from homeassistant.core import HomeAssistant
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Track if panel is already registered to avoid duplicate registration
_PANEL_REGISTERED = False

async def async_setup_panel(hass: HomeAssistant):
    """Set up the Eedomus configuration panel."""
    global _PANEL_REGISTERED
    
    # Check if panel is already registered to avoid "Overwriting panel" error
    if _PANEL_REGISTERED:
        _LOGGER.debug("Eedomus panel already registered, skipping duplicate registration")
        return True
    
    try:
        # Register the panel using component approach
        # Check if frontend is available using try/except approach
        try:
            from homeassistant.components.frontend import async_register_built_in_panel
        except ImportError:
            _LOGGER.warning("Frontend component not available - panel registration skipped")
            return False
            
        async_register_built_in_panel(
            hass,
            "eedomus-config",
            "eedomus-config-panel",  # This should match the component name
            "mdi:cog",
            require_admin=True,
        )
        
        _PANEL_REGISTERED = True
        _LOGGER.info("✅ Eedomus configuration panel registered successfully")
        
    except Exception as e:
        _LOGGER.error("Error setting up Eedomus panel: %s", e)
        return False
    
    return True

async def async_unload_panel(hass: HomeAssistant):
    """Unload the Eedomus configuration panel."""
    return True
