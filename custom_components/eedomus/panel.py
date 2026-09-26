"""Eedomus Configuration Panel for Home Assistant 2026+."""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Track if panel is already registered to avoid duplicate registration
_PANEL_REGISTERED = False

async def async_setup_panel(hass: HomeAssistant, entry: ConfigEntry = None):
    """Set up the Eedomus configuration panel.
    
    Registers the configuration panel for both modern (frontend.yaml) and legacy HA versions.
    """
    global _PANEL_REGISTERED
    
    if _PANEL_REGISTERED:
        return False
    
    _PANEL_REGISTERED = True
    
    try:
        from homeassistant.components.panel_custom import (
            PanelCustomConfigEntry,
            async_register_panel,
        )
        # Register panel programmatically for legacy HA versions
        await async_register_panel(
            hass,
            PanelCustomConfigEntry(
                name="Eedomus Configuration",
                frontend_url_path="eedomus-config",
                config_entry=entry,
                require_admin=True,
                icon="mdi:cog",
            ),
        )
        _LOGGER.info("✅ Eedomus configuration panel registered (programmatic)")
        return True
    except ImportError:
        # Fall back: HA version doesn't support programmatic panel registration
        _LOGGER.debug("Panel registration via async_register_panel not available - relying on frontend.yaml")
        return False
    except Exception as e:
        _LOGGER.error("Failed to register Eedomus configuration panel: %s", e)
        return False

async def async_unload_panel(hass: HomeAssistant):
    """Unload the Eedomus configuration panel."""
    return True
