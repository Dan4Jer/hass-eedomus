"""Cover entity for eedomus integration."""

from __future__ import annotations

import logging

from homeassistant.components.cover import CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .entity import EedomusEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up eedomus cover entities from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []

    # Get all peripherals and build parent-to-children mapping
    all_peripherals = coordinator.get_all_peripherals()
    parent_to_children = {}

    for periph_id, periph in all_peripherals.items():
        if periph.get("parent_periph_id"):
            parent_id = periph["parent_periph_id"]
            if parent_id not in parent_to_children:
                parent_to_children[parent_id] = []
            parent_to_children[parent_id].append(periph)
        if not "ha_entity" in coordinator.data[periph_id]:
            eedomus_mapping = map_device_to_ha_entity(periph)
            coordinator.data[periph_id].update(eedomus_mapping)

    for periph_id, periph in all_peripherals.items():
        ha_entity = None
        if "ha_entity" in coordinator.data[periph_id]:
            ha_entity = coordinator.data[periph_id]["ha_entity"]

        parent_id = periph.get("parent_periph_id", None)
        if parent_id and coordinator.data[parent_id]["ha_entity"] == "cover":
            # Children are managed by parent... similar to light logic
            eedomus_mapping = None
            if periph.get("usage_id") == "26":  # Energy meter
                eedomus_mapping = {
                    "ha_entity": "sensor",
                    "ha_subtype": "energy",
                    "justification": "Parent is a cover - energy consumption meter",
                }
            if periph.get("usage_id") == "48":  # Slats
                eedomus_mapping = {
                    "ha_entity": "cover",
                    "ha_subtype": "shutter",
                    "justification": "Parent is a cover - slats",
                }
            if not eedomus_mapping is None:
                coordinator.data[periph_id].update(eedomus_mapping)
                _LOGGER.info(
                    "Created energy sensor for cover %s (%s) - consumption monitoring",
                    periph["name"],
                    periph_id,
                )

    for periph_id, periph in all_peripherals.items():
        ha_entity = None
        if "ha_entity" in coordinator.data[periph_id]:
            ha_entity = coordinator.data[periph_id]["ha_entity"]

        if ha_entity is None or not ha_entity == "cover":
            continue

        _LOGGER.debug(
            "Creating cover entity for %s (periph_id=%s)", periph["name"], periph_id
        )

        # Check if this cover has children that should be aggregated
        if periph_id in parent_to_children and len(parent_to_children[periph_id]) > 0:
            # Create aggregated cover entity (similar to RGBW light)
            entities.append(
                EedomusAggregatedCover(
                    coordinator,
                    periph_id,
                    parent_to_children[periph_id],
                )
            )
        else:
            # Create regular cover entity
            entities.append(EedomusCover(coordinator, periph_id))

    async_add_entities(entities)


class EedomusCover(EedomusEntity, CoverEntity):
    """Representation of an eedomus cover entity (shutter/blind)."""

    def __init__(self, coordinator, periph_id):
        """Initialize the cover."""
        super().__init__(coordinator, periph_id)
        _LOGGER.debug(
            "Initializing cover entity for %s (periph_id=%s)",
            self.coordinator.data[periph_id].get("name", "unknown"),
            periph_id,
        )

        # Set cover-specific attributes
        self._attr_device_class = "shutter"  # Use "shutter" for shutters
        self._attr_supported_features = (
            CoverEntityFeature.SET_POSITION
        )  # Only position setting is supported

    @property
    def is_closed(self):
        """Return if the cover is closed (position = 0)."""
        position = self.coordinator.data[self._periph_id].get("last_value")
        return position == "0" or position == 0

    @property
    def current_cover_position(self):
        """Return the current position of the cover (0-100)."""
        position = self.coordinator.data[self._periph_id].get("last_value")
        try:
            return int(position)
        except (ValueError, TypeError):
            return 0

    async def async_open_cover(self, **kwargs):
        """Open the cover to 100%."""
        await self.async_set_cover_position(position=100)

    async def async_close_cover(self, **kwargs):
        """Close the cover to 0%."""
        await self.async_set_cover_position(position=0)

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position (0-100)."""
        position = kwargs.get("position")
        if position is None:
            _LOGGER.error(
                "Position is None for cover %s (periph_id=%s)",
                self.coordinator.data[self._periph_id].get("name", "unknown"),
                self._periph_id,
            )
            return

        # Ensure position is within valid range
        position = max(0, min(100, position))
        _LOGGER.debug(
            "Setting cover position to %s for %s (periph_id=%s)",
            position,
            self.coordinator.data[self._periph_id].get("name", "unknown"),
            self._periph_id,
        )

        # Use coordinator method to set position
        await self.coordinator.async_set_periph_value(self._periph_id, str(position))
        
        # Force refresh to update attributes immediately
        await self.coordinator.async_request_refresh()

    async def async_stop_cover(self, **kwargs):
        """Stop the cover (not supported by eedomus shutters)."""
        _LOGGER.warning(
            "Stopping cover is not supported by eedomus shutters for %s (periph_id=%s)",
            self.coordinator.data[self._periph_id].get("name", "unknown"),
            self._periph_id,
        )


class EedomusAggregatedCover(EedomusCover):
    """Representation of an eedomus aggregated cover, combining parent and child devices."""

    def __init__(self, coordinator, periph_id, child_devices):
        """Initialize the aggregated cover with parent and child devices."""
        super().__init__(coordinator, periph_id)
        self._parent_id = periph_id
        self._parent_device = self.coordinator.data[periph_id]
        self._child_devices = {child["periph_id"]: child for child in child_devices}

        _LOGGER.debug(
            "Initializing aggregated cover %s (periph_id=%s) with children: %s",
            self._parent_device["name"],
            self._parent_id,
            ", ".join(
                f"{child['name']} (periph_id={child['periph_id']})"
                for child in child_devices
            ),
        )

    @property
    def current_cover_position(self):
        """Return the current position of the cover (0-100)."""
        position = self.coordinator.data[self._parent_id].get("last_value")
        try:
            return int(position)
        except (ValueError, TypeError):
            return 0

    @property
    def extra_state_attributes(self):
        """Return extended state attributes including child values."""
        # Get parent's extra state attributes (which is a dict, not a method)
        attrs = super().extra_state_attributes

        # Create a new dict to avoid modifying the parent's attributes
        result_attrs = dict(attrs) if attrs else {}

        # Add child device values
        child_attrs = {}
        for child_id, child in self._child_devices.items():
            child_data = self.coordinator.data.get(child_id, {})
            child_attrs[child_id] = {
                "name": child_data.get("name"),
                "value": child_data.get("last_value"),
                "unit": child_data.get("unit"),
                "type": child_data.get("ha_subtype"),
            }

        result_attrs["child_devices"] = child_attrs
        return result_attrs
