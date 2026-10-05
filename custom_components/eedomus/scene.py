"""Scene entity for eedomus integration."""

from __future__ import annotations

import logging

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, COORDINATOR
from .entity import EedomusEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up eedomus scene entities."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    scenes = []

    all_peripherals = coordinator.get_all_peripherals()

    # Second pass: create scene entities
    for periph_id, periph in all_peripherals.items():
        ha_entity = coordinator.data[periph_id].get("ha_entity")

        if ha_entity != "scene":
            continue

        _LOGGER.debug("Creating scene entity for %s (%s)", periph["name"], periph_id)
        scenes.append(EedomusScene(coordinator, periph_id))

    async_add_entities(scenes, True)


class EedomusScene(EedomusEntity, Scene):
    """Representation of an eedomus scene."""

    def __init__(self, coordinator, periph_id: str):
        """Initialize the scene."""
        super().__init__(coordinator, periph_id)
        # Route the name through the base's adoption path: a blank or
        # missing name must keep the translated fallback (entity.* keys),
        # not shadow it with an empty string.
        periph_name = self.coordinator.data.get(periph_id, {}).get("name")
        if periph_name is not None and str(periph_name).strip():
            self._attr_name = periph_name
            self._adopt_derived_name()
        self._attr_unique_id = f"{periph_id}_scene"
        _LOGGER.debug(
            "Initializing scene entity for %s (%s)",
            getattr(self, "_attr_name", self._periph_id),
            periph_id,
        )

    async def async_activate(self, **kwargs):
        """Activate the scene. Send the appropriate command to eedomus."""
        _LOGGER.info(
            "Activating scene %s (%s)",
            getattr(self, "_attr_name", self._periph_id),
            self._periph_id,
        )

        try:
            # For eedomus scenes, we typically send a "set" command with the appropriate value
            # The exact value depends on the scene type, but often it's "on" or a specific state
            result = await self._client.set_periph_value(self._periph_id, "on")

            if result.get("success", 0) == 1:
                _LOGGER.debug(
                    "Successfully activated scene %s",
                    getattr(self, "_attr_name", self._periph_id),
                )
                # Update the coordinator data to reflect the change
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error(
                    "Failed to activate scene %s: %s",
                    getattr(self, "_attr_name", self._periph_id),
                    result.get("error", "Unknown error"),
                )
        except Exception as e:
            _LOGGER.error(
                "Exception while activating scene %s: %s",
                getattr(self, "_attr_name", self._periph_id),
                str(e),
            )
            raise

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.data[self._periph_id].get("last_value", "") != ""

    async def async_update(self) -> None:
        """Update the scene state."""
        await super().async_update()
        # Scenes don't have a persistent state, so we just ensure the entity is available
        self._attr_available = True
