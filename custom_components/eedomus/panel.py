"""Eedomus Configuration Panel for Home Assistant 2026+."""

import voluptuous as vol
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.components.frontend import (
    async_register_built_in_panel,
)
from homeassistant.core import HomeAssistant
from .const import DOMAIN

async def async_setup_panel(hass: HomeAssistant):
    """Set up the Eedomus configuration panel."""
    
    # Register as a built-in panel
    await async_register_built_in_panel(
        hass,
        "eedomus-config",
        "eedomus-config",
        "mdi:cog",
        require_admin=True,
        config={
            "component": "eedomus-rich-editor",
            "title": "Eedomus Configuration",
            "icon": "mdi:cog",
            "require_admin": True,
        },
    )
    
    # Alternative registration method for HA 2026+
    try:
        from homeassistant.components.lovelace import async_register_panel
        await async_register_panel(hass, "eedomus-config", "eedomus-config", "mdi:cog")
    except ImportError:
        # Fallback for older versions
        pass
    
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