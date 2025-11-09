"""Base entity for Eedomus integration."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN

class EedomusEntity(Entity):
    """Base class for all Eedomus entities."""

    _attr_has_entity_name = True

    def __init__(self, device_info: dict, client: any) -> None:
        """Initialize the Eedomus entity."""
        self._device_info = device_info
        self._client = client
        self._attr_unique_id = f"{device_info['id']}"
        self._attr_name = device_info.get("name", "")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._attr_name,
            manufacturer="Eedomus",
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Ajoute ici une logique pour vérifier si l'entité est disponible
        # (par exemple, si le client est connecté)
        return self._client.available
