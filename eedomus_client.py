import aiohttp
import async_timeout
import json
import logging

_LOGGER = logging.getLogger(__name__)

class EedomusClient:
    def __init__(self, api_user, api_secret, session):
        self.api_user = api_user
        self.api_secret = api_secret
        self.session = session
        self.base_url = "http://192.168.1.2/api/get"

    async def fetch_data(self, endpoint, params=None):
        """Fetch data from eedomus API."""
        if params is None:
            params = {}
        params['api_user'] = self.api_user
        params['api_secret'] = self.api_secret

        url = f"{self.base_url}?action={endpoint}"
        headers = {"Accept": "text/html"}

        try:
            with async_timeout.timeout(10):
                async with self.session.get(url, params=params, headers=headers) as resp:
                    if resp.status != 200:
                        _LOGGER.error("Error fetching data from eedomus API: %s", resp.status)
                        return None
                    data = await resp.text()
                    return json.loads(data)
        except Exception as e:
            _LOGGER.error("Exception while fetching data from eedomus API: %s", e)
            return None

    async def set_periph_value(self, periph_id, value):
        """Set the value of a peripheral."""
        params = {
            'periph_id': periph_id,
            'value': value
        }
        return await self.fetch_data('periph.value', params)

    async def get_periph_caract(self, periph_id):
        """Get characteristics of a peripheral."""
        params = {'periph_id': periph_id}
        return await self.fetch_data('periph.caract', params)

    async def get_periph_history(self, periph_id):
        """Get history of a peripheral."""
        params = {'periph_id': periph_id}
        return await self.fetch_data('periph.history', params)

    async def get_periph_value_list(self, periph_id):
        """Get possible values for a peripheral of type list."""
        params = {'periph_id': periph_id}
        return await self.fetch_data('periph.value_list', params)

    async def get_periph_list(self):
        """Get list of all peripherals."""
        return await self.fetch_data('periph.list')
