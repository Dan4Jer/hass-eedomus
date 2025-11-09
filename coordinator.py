from __future__ import annotations
import logging
import json
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant
import aiohttp
from .const import SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class EedomusClient:
    def __init__(self, host: str, user: str, secret: str, session: aiohttp.ClientSession):
        self._host = host
        self._user = user
        self._secret = secret
        self._session = session

    async def async_get_devices(self) -> list:
        url = f"http://{self._host}/api/get?api_user={self._user}&api_secret={self._secret}&action=devices"
        async with self._session.get(url, timeout=20) as resp:
            if resp.status != 200:
                raise Exception(f"eedomus API returns {resp.status}")
            text = await resp.text()
            try:
                # Parse manuellement le texte en JSON
                j = json.loads(text)
                return j.get("body", {}).get("devices", []) if isinstance(j.get("body"), dict) else j.get("body", [])
            except json.JSONDecodeError:
                # Si le texte n'est pas du JSON valide, retourne une liste vide
                return []

    async def async_set(self, action: str, device_id: str, value: str):
        url = f"http://{self._host}/api/set?api_user={self._user}&api_secret={self._secret}&action={action}&device_id={device_id}&value={value}"
        async with self._session.get(url, timeout=10) as resp:
            return await resp.text()

    async def get_lights(self) -> list[dict[str, Any]]:
        """Return a list of lights from eedomus."""
        # Appelle l'API eedomus pour récupérer les lumières
        # Exemple de retour attendu:
        # [
        #     {"id": "1", "name": "Salon", "state": "on"},
        #     {"id": "2", "name": "Cuisine", "state": "off"},
        # ]
        pass

    async def set_light_state(self, light_id: str, state: bool) -> None:
        """Set the state of a light."""
        # Appelle l'API eedomus pour allumer/éteindre la lumière
        pass

    async def get_data(self):
        """Fetch all data from Eedomus API."""
        # Exemple de retour :
        return {
            "lights": [
                {"id": "1", "name": "Salon", "state": "on"},
                {"id": "2", "name": "Cuisine", "state": "off"},
            ],
            # ... autres données
        }
    
class EedomusDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, host: str, user: str, secret: str):
        super().__init__(
            hass,
            _LOGGER,
            name="Eedomus Coordinator",
            update_interval=timedelta(seconds=SCAN_INTERVAL),
        )
        self._host = host
        self._user = user
        self._secret = secret
        self._session = async_get_clientsession(hass)
        self.client = EedomusClient(host, user, secret, self._session)
        self._device_map: dict[str, dict] = {}

    async def _async_update_data(self):
        try:
            devices = await self.client.async_get_devices()
            new_map = {str(d.get("id")): d for d in devices}
            removed_ids = set(self._device_map.keys()) - set(new_map.keys())
            if removed_ids:
                _LOGGER.info("Devices removed: %s", removed_ids)
            self._device_map = new_map
            return list(new_map.values())
        except Exception as err:
            raise UpdateFailed(f"Failed to update eedomus data: {err}")

    @property
    def lights(self):
        """Return the list of lights."""
        if self.data is None:
            return []
        return self.data

    async def get_lights(self):
        """Return the list of lights (alias pour compatibilité)."""
        return self.lights
