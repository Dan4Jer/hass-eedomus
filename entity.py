"""Base entity for eedomus integration."""
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    ATTR_PERIPH_ID,
    ATTR_CARACT_ID,
    ATTR_VALUE_LIST,
    ATTR_HISTORY,
    ATTR_LAST_UPDATED,
)

class EedomusEntity(CoordinatorEntity):
    """Base class for eedomus entities."""

    def __init__(self, coordinator, periph_id, caract_id):
        """Initialize the entity."""
        super().__init__(coordinator)
        self._periph_id = periph_id
        self._caract_id = caract_id
        self._attr_unique_id = f"{periph_id}_{caract_id}"
        _LOGGER = logging.getLogger(__name__)
        _LOGGER.debug("Initializing entity for periph_id=%s, caract_id=%s", periph_id, caract_id)

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
        if self.coordinator.data.get(self._periph_id, {}).get("caracts", {}).get(self._caract_id):
            caract_data = self.coordinator.data[self._periph_id]["caracts"][self._caract_id]
            attrs[ATTR_PERIPH_ID] = self._periph_id
            attrs[ATTR_CARACT_ID] = self._caract_id
            attrs[ATTR_LAST_UPDATED] = self.coordinator.data.last_updated

            if caract_data.get("value_list"):
                attrs[ATTR_VALUE_LIST] = caract_data["value_list"]

            if caract_data.get("history"):
                attrs[ATTR_HISTORY] = caract_data["history"]

        return attrs

    @property
    def periph_id(self):
        """Return the periph ID."""
        return self._periph_id

    @property
    def caract_id(self):
        """Return the caract ID."""
        return self._caract_id
