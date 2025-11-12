import aiohttp
import asyncio
import json
import logging
from typing import Optional, Dict, Any

from async_timeout import timeout as async_timeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

class EedomusClient:
    def __init__(self, api_user: str, api_secret: str, session: aiohttp.ClientSession, api_host: str):
        self.api_user = api_user
        self.api_secret = api_secret
        self.session = session
        self.api_host = api_host
        self.base_url = f"http://{self.api_host}/api/get"

    async def fetch_data(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Fetch data from eedomus API."""
        if params is None:
            params = {}
        params['api_user'] = self.api_user
        params['api_secret'] = self.api_secret

        url = f"{self.base_url}?action={endpoint}"
        headers = {"Accept": "text/html"}

        try:
            async with async_timeout(10):
                async with self.session.get(url, params=params, headers=headers) as resp:
                    if resp.status != 200:
                        _LOGGER.error("Error fetching data from eedomus API: %s", resp.status)
                        return None

                    #data = await resp.text() pb utf8

                    # Lire les données brutes
                    raw_data = await resp.read()
                    
                    _LOGGER.debug("Request URL: %s", url)
                    _LOGGER.debug("Request params: %s", params)
                    
                    # Essayer de décoder avec UTF-8 d'abord
                    try:
                        text_data = raw_data.decode('utf-8')
                    except UnicodeDecodeError:
                        # Si UTF-8 échoue, essayer avec ISO-8859-1 (Latin-1)
                        try:
                            text_data = raw_data.decode('iso-8859-1')
                        except Exception as e:
                            _LOGGER.error("Error decoding response: %s", e)
                            return None

                    try:
                        _LOGGER.debug("Raw response: %s", text_data)  # Avant le json.loads
                        return json.loads(text_data)
                    except json.JSONDecodeError as e:
                        _LOGGER.error("Error decoding JSON response from eedomus API: %s", e)
                        _LOGGER.debug("Raw response: %s", text_data)  # Pour le débogage
                        return None
                    #return json.loads(data) pb utf8
                    
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout while fetching data from eedomus API")
            return None
        except aiohttp.ClientError as e:
            _LOGGER.error("Client error while fetching data from eedomus API: %s", e)
            return None
        except json.JSONDecodeError as e:
            _LOGGER.error("Error decoding JSON response from eedomus API: %s", e)
            return None
        except Exception as e:
            _LOGGER.error("Unexpected error while fetching data from eedomus API: %s", e)
            return None

    async def set_periph_value(self, periph_id: str, value: str) -> Optional[Dict]:
        """Set the value of a peripheral."""
        params = {
            'periph_id': periph_id,
            'value': value
        }
        return await self.fetch_data('periph.value', params)

    async def get_periph_caract(self, periph_id: str) -> Optional[Dict]:
        """Get characteristics of a peripheral."""
        params = {'periph_id': periph_id}
        return await self.fetch_data('periph.caract', params)

    async def get_periph_history(self, periph_id: str) -> Optional[Dict]:
        """Get history of a peripheral."""
        params = {'periph_id': periph_id}
        return await self.fetch_data('periph.history', params)

    async def get_periph_value_list(self, periph_id: str) -> Optional[Dict]:
        """Get possible values for a peripheral of type list."""
        params = {'periph_id': periph_id}
        return await self.fetch_data('periph.value_list', params)

    async def get_periph_list(self) -> Optional[Dict]:
        """Get list of all peripherals."""
        return await self.fetch_data('periph.list')

    async def auth_test(self) -> Optional[Dict]:
        """Authorization check"""
        return await self.fetch_data('auth.test')
