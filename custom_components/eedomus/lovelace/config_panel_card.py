"""
Eedomus Configuration Panel - Lovelace Card for HA 2026.1+

This card provides a modern interface for configuring eedomus device mapping
and dynamic properties, compatible with Home Assistant 2026.1 and later.

Note: For HA 2026.02+, the built-in panel (www/config_panel.js) is preferred.
This Lovelace card is kept for backward compatibility.
"""

from __future__ import annotations

import logging
from typing import Any

# For HA 2026.02+, we use the modern frontend API instead of Lovelace card
# Keep this import for backward compatibility, but handle ImportError gracefully
try:
    from homeassistant.components.lovelace.card import LovelaceCard
    from homeassistant.components.lovelace.const import CardType
except ImportError:
    # Fallback for newer HA versions where lovelace.card is deprecated
    LovelaceCard = object  # Type hint fallback
    CardType = str  # Type hint fallback

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_entry_flow

from ..const import DOMAIN
from ..device_mapping import get_dynamic_entity_properties, get_specific_device_dynamic_overrides

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: config_entry_flow.ConfigEntry) -> bool:
    """Set up the eedomus configuration panel card."""
    _LOGGER.info("Setting up Eedomus Configuration Panel card")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: config_entry_flow.ConfigEntry) -> bool:
    """Unload the eedomus configuration panel card."""
    _LOGGER.info("Unloading Eedomus Configuration Panel card")
    return True


class EedomusConfigPanelCard(LovelaceCard):
    """Lovelace card for eedomus configuration panel."""
    
    def __init__(self, config: dict[str, Any], hass: HomeAssistant):
        """Initialize the card."""
        super().__init__(config, hass)
        self._hass = hass
        self._config = config
        self._card_type = CardType.CUSTOM
        self._name = "Eedomus Configuration Panel"
        self._icon = "mdi:cog-transfer"
        
    @property
    def card_type(self) -> CardType:
        """Return the card type."""
        return self._card_type
    
    @property
    def name(self) -> str:
        """Return the card name."""
        return self._name
    
    @property
    def icon(self) -> str:
        """Return the card icon."""
        return self._icon
    
    @property
    def extra_styles(self) -> str:
        """Return extra styles for the card."""
        return "--ha-card-border-radius: 12px;"
    
    async def async_get_config(self) -> dict[str, Any]:
        """Get the current configuration."""
        config_panel = self._hass.data.get(DOMAIN, {}).get("config_panel")
        
        if config_panel:
            return {
                "current_config": config_panel.currentConfig,
                "dynamic_entity_properties": get_dynamic_entity_properties(),
                "specific_device_overrides": get_specific_device_dynamic_overrides(),
                "devices": await self._get_devices_data()
            }
        
        return {
            "current_config": "default",
            "dynamic_entity_properties": {
                "light": True, "switch": True, "binary_sensor": True,
                "sensor": False, "climate": False, "cover": True,
                "select": False, "scene": False
            },
            "specific_device_overrides": {},
            "devices": []
        }
    
    async def _get_devices_data(self) -> list[dict[str, Any]]:
        """Get devices data from coordinator."""
        coordinator = self._hass.data.get(DOMAIN, {}).get("coordinator")
        
        if coordinator and hasattr(coordinator, 'data'):
            devices_data = []
            for periph_id, periph_data in coordinator.data.items():
                if isinstance(periph_data, dict) and "periph_id" in periph_data:
                    devices_data.append({
                        "periph_id": periph_id,
                        "name": periph_data.get("name", "Unknown"),
                        "ha_entity": periph_data.get("ha_entity"),
                        "usage_id": periph_data.get("usage_id"),
                        "is_dynamic": periph_data.get("is_dynamic", False)
                    })
            return devices_data
        
        return []
    
    async def async_update_config(self, entity_type: str, is_dynamic: bool) -> bool:
        """Update dynamic property for an entity type."""
        config_panel = self._hass.data.get(DOMAIN, {}).get("config_panel")
        
        if config_panel:
            return config_panel.update_dynamic_entity_property(entity_type, is_dynamic)
        
        return False
    
    async def async_update_device_override(self, periph_id: str, is_dynamic: bool) -> bool:
        """Update dynamic override for a specific device."""
        config_panel = self._hass.data.get(DOMAIN, {}).get("config_panel")
        
        if config_panel:
            return config_panel.update_specific_device_override(periph_id, is_dynamic)
        
        return False
    
    async def async_remove_device_override(self, periph_id: str) -> bool:
        """Remove dynamic override for a specific device."""
        config_panel = self._hass.data.get(DOMAIN, {}).get("config_panel")
        
        if config_panel:
            return config_panel.remove_specific_device_override(periph_id)
        
        return False
    
    async def async_switch_config(self, config_name: str) -> bool:
        """Switch to a different configuration."""
        config_panel = self._hass.data.get(DOMAIN, {}).get("config_panel")
        
        if config_panel:
            return config_panel.switch_config(config_name)
        
        return False
    
    async def async_reload_config(self) -> bool:
        """Reload configuration from files."""
        config_panel = self._hass.data.get(DOMAIN, {}).get("config_panel")
        
        if config_panel:
            return config_panel.reload_configuration()
        
        return False