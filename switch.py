"""Switch entity for eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .entity import EedomusEntity, map_device_to_ha_entity
from .const import DOMAIN, CLASS_MAPPING

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    switches = []

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
        if parent_id and coordinator.data[parent_id]["ha_entity"] == "light":
            #les enfants sont gérés par le parent... est-ce une bonne idée ?
            eedomus_mapping = None
            if periph.get("usage_id") == "26":
                eedomus_mapping = {
                    "ha_entity": "sensor",
                    "ha_subtype": None,
                    "justification": "Parent is a switch - sensor - Consometre"
                }
            if not eedomus_mapping is None:
                coordinator.data[periph_id].update(eedomus_mapping)

    for periph_id, periph in all_peripherals.items():
        ha_entity = None
        if "ha_entity" in coordinator.data[periph_id]:
            ha_entity = coordinator.data[periph_id]["ha_entity"]

        if ha_entity is None or not ha_entity == "switch":
            continue
     
        _LOGGER.debug("Go for a switch !!! %s (%s) mapping=%s", periph["name"], periph_id,  ha_entity)

        switches.append(EedomusSwitch(coordinator, periph_id))

    async_add_entities(switches, True)


class EedomusSwitch(EedomusEntity, SwitchEntity):
    """Representation of an eedomus switch."""

    def __init__(self, coordinator, periph_id):
        """Initialize the switch."""
        super().__init__(coordinator, periph_id)
        _LOGGER.debug("Initializing switch entity for periph_id=%s", periph_id)

    @property
    def is_on(self):
        """Return true if the switch is on."""
        value = self.coordinator.data[self._periph_id].get("last_value")
        _LOGGER.debug("Switch %s is_on: %s name=%s", self._periph_id, self.coordinator.data[self._periph_id].get("last_value"), self.coordinator.data[self._periph_id].get("name"))
        return value == "100"

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Turning on switch %s", self._periph_id)
        try:
            response = await self.coordinator.client.set_periph_value(self._periph_id, "100")
            if isinstance(response, dict) and response.get("success") != 1:
                _LOGGER.error("Failed to turn on switch %s: %s", self._periph_id, response.get("error", "Unknown error"))
                raise Exception(f"Failed to turn on switch: {response.get('error', 'Unknown error')}")
            await self.coordinator.async_request_refresh()
        except Exception as e:
            _LOGGER.error("Failed to turn on switch %s: %s", self._periph_id, e)
            raise

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("Turning off switch %s", self._periph_id)
        try:
            response = await self.coordinator.client.set_periph_value(self._periph_id, "0")
            if isinstance(response, dict) and response.get("success") != 1:
                _LOGGER.error("Failed to turn off switch %s: %s", self._periph_id, response.get("error", "Unknown error"))
                raise Exception(f"Failed to turn off switch: {response.get('error', 'Unknown error')}")

            await self.coordinator.async_request_refresh()

        except Exception as e:
            _LOGGER.error("Failed to turn off switch %s: %s", self._periph_id, e)
            raise
