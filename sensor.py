from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]


    entities = []
    for d in (coordinator.data or []):
        dtype = d.get("type")
        if dtype in ("temperature", "value", "humidity", "energy"):
            entities.append(EedomusSensor(coordinator, d))


    async_add_entities(entities)


class EedomusSensor(CoordinatorEntity, Entity):
    def __init__(self, coordinator, device):
        super().__init__(coordinator)
        self._device_id = str(device.get("id"))
        self._attr_name = device.get("name")
        self._unique_id = f"eedomus_sensor_{self._device_id}"


        @property
        def unique_id(self):
            return self._unique_id


        @property
        def name(self):
            return self._attr_name


        @property
        def state(self):
            device = self.coordinator.device_map.get(self._device_id)
            if not device:
                return None
            return device.get("value")

        async def async_update(self):
            # Coordinator already refreshes; nothing special to do
            return
