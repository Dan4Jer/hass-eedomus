"""Base entity for eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, ATTR_PERIPH_ID, ATTR_CARACT_ID

_LOGGER = logging.getLogger(__name__)

class EedomusEntity(CoordinatorEntity):
    """Base class for eedomus entities."""

    def __init__(self, coordinator, periph_id, caract_id):
        """Initialize the entity."""
        super().__init__(coordinator)
        self._periph_id = periph_id
        self._caract_id = caract_id
        self._attr_unique_id = f"{periph_id}_{caract_id}"
        _LOGGER.debug("Initializing entity for periph_id=%s, caract_id=%s", periph_id, caract_id)
        _LOGGER.debug("Extra data for periph_id=%s, data=%s", periph_id, self.coordinator.data[periph_id]["info"])
        if self.coordinator.data[periph_id]["info"]["name"]:
            self._attr_name = self.coordinator.data[periph_id]["info"]["name"]
    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        periph_info = self.coordinator.data[self._periph_id]["info"]
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._periph_id))},
            name=periph_info.get("name"),
            manufacturer="eedomus",
            model=periph_info.get("model"),
        )

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {}
        if self.coordinator.data.get(self._periph_id):
            periph_data = self.coordinator.data[self._periph_id]
            attrs[ATTR_PERIPH_ID] = self._periph_id
            attrs[ATTR_CARACT_ID] = self._caract_id

            if "history" in periph_data:
                attrs["history"] = periph_data["history"]

            if "value_list" in periph_data:
                attrs["value_list"] = periph_data["value_list"]

            if "room_name" in periph_data:
                attrs["room"] = periph_data["room_name"]

            if "value_type" in periph_data["info"]:
                attrs["type"] = periph_data["info"]["value_type"]

            attrs["eedomus_id"] = self._periph_id

##Bug:cover with a false temperature sensor.
#if  periph_data["info"]["value_type"] == 'float' and periph_data["current_value"] == "":
#    periph_data["current_value"] = 0
#if  periph_data["info"]["value_type"] == ' ' and periph_data["current_value"] == "":
#    periph_data["current_value"] = 0
                
            if not "room" in attrs and "room_name" in periph_data["info"]:
                attrs["room"] = periph_data["info"]["room_name"]
        #_LOGGER.debug("Extra State Attributes for periph_id=%s, attrs=%s, periph_data=%s", self._periph_id, attrs, periph_data)
        return attrs

    @property
    def periph_id(self):
        """Return the periph ID."""
        return self._periph_id

    @property
    def caract_id(self):
        """Return the caract ID."""
        return self._caract_id
