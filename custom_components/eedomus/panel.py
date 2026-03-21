"""Eedomus Configuration Panel for Home Assistant 2026+."""

import voluptuous as vol
import logging
from homeassistant.components.frontend import (
    async_register_built_in_panel,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_flow
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_panel(hass: HomeAssistant):
    """Set up the Eedomus configuration panel."""
    
    try:
        # Register the panel with proper configuration
        # Note: async_register_built_in_panel doesn't return a value, it's a fire-and-forget function
        async_register_built_in_panel(
            hass,
            "eedomus-config",
            "eedomus-config",
            "mdi:cog",
            require_admin=True,
            config={
                "component": "eedomus-config-panel",  # Use our panel component
                "title": "Eedomus Configuration",
                "icon": "mdi:cog",
                "require_admin": True,
                "url_path": "eedomus-config",
            },
        )
        
        _LOGGER.info("✅ Eedomus configuration panel registered successfully")
        
        # Also register as a custom panel for compatibility
        try:
            from homeassistant.components.panel_custom import async_register_panel
            async_register_panel(
                hass,
                "eedomus-config",
                "eedomus-config",
                "mdi:cog",
                config={
                    "component": "eedomus-config-panel",
                    "title": "Eedomus Configuration",
                    "icon": "mdi:cog",
                },
                require_admin=True,
            )
            _LOGGER.info("✅ Eedomus custom panel registered successfully")
        except ImportError as e:
            _LOGGER.debug("Custom panel registration not available: %s", e)
            
    except Exception as e:
        _LOGGER.error("Error setting up Eedomus panel: %s", e)
        return False
    
    return True

async def async_unload_panel(hass: HomeAssistant):
    """Unload the Eedomus configuration panel."""
    # Panel unregistration if needed
    return True

# Panel configuration schema
PANEL_SCHEMA = vol.Schema({
    vol.Optional("component"): str,
    vol.Optional("title"): str,
    vol.Optional("icon"): str,
    vol.Optional("require_admin"): bool,
})

# Panel content configuration
PANEL_CONTENT = {
    "component": "eedomus-rich-editor",
    "config": {
        "entry_id": "CURRENT_ENTRY_ID",  # Will be replaced at runtime
        "mode": "ui",  # Default to UI mode
    },
    "title": "Eedomus Configuration Editor",
    "icon": "mdi:cog",
    "require_admin": True,
}