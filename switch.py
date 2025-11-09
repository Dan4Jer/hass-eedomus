from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EedomusSwitch(coordinator, device) for device in coordinator.data if device.get("type") == "switch"])

class EedomusSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, device):
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"{DOMAIN}_{device['id']}"
        self._attr_name = device.get("name", f"Eedomus Switch {device['id']}")

    @property
    def is_on(self):
        return self._device.get("state") == "on"

    async def async_turn_on(self):
        await self.coordinator.client.async_set("turn_on", self._device["id"], "1")
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self):
        await self.coordinator.client.async_set("turn_off", self._device["id"], "0")
        await self.coordinator.async_request_refresh()
