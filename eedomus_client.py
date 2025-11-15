"""Eedomus API client with proper encoding handling."""
from __future__ import annotations

import aiohttp
import asyncio
import json
import logging
from typing import Optional, Dict, Any
from async_timeout import timeout as async_timeout

_LOGGER = logging.getLogger(__name__)

# Dictionnaire des codes d'erreur eedomus connus
EEDOMUS_ERROR_CODES = {
    '1': 'Invalid API credentials',
    '2': 'Invalid action',
    '3': 'Missing parameter',
    '4': 'Invalid parameter value',
    '5': 'Unknown peripheral',
    '6': 'Unknown peripheral value',
    '7': 'Invalid peripheral type',
    '8': 'Database error',
    '9': 'Permission denied',
    '10': 'Value not decimal',
    '11': 'Value out of range',
    '12': 'Invalid date format',
    '13': 'Invalid time format',
    '14': 'Invalid cron format',
    '15': 'Invalid script',
    '16': 'Invalid condition',
    '17': 'Invalid scenario',
    '18': 'Invalid camera',
    '19': 'Invalid user',
    '20': 'Invalid notification'
}

class EedomusClient:
    """Client for interacting with eedomus API with proper encoding handling."""

    def __init__(self, session: aiohttp.ClientSession, api_user: str, api_secret: str, api_host: str):
        """Initialize the client."""
        self.session = session
        self.api_user = api_user
        self.api_secret = api_secret
        self.api_host = api_host
        self.base_url_get = f"http://{self.api_host}/api/get"
        self.base_url_set = f"http://{self.api_host}/api/set"

    async def fetch_data(self, endpoint: str, params: Optional[Dict] = None, use_set: bool = False) -> Dict:
        """Fetch data from eedomus API with proper encoding handling."""
        if params is None:
            params = {}

        params['api_user'] = self.api_user
        params['api_secret'] = self.api_secret

        url = self.base_url_set if use_set else self.base_url_get
        url = f"{url}?action={endpoint}"
        self.url = url
        self.params = params
        try:
            async with async_timeout(10):
                async with self.session.get(url, params=params) as resp:
                    # Lire les données brutes
                    raw_data = await resp.read()

                    # Gestion des statuts HTTP
                    if resp.status != 200:
                        try:
                            error_text = raw_data.decode('utf-8', errors='replace')
                        except UnicodeDecodeError:
                            error_text = raw_data.decode('iso-8859-1', errors='replace')

                        _LOGGER.error("HTTP %s error for %s: %s", resp.status, endpoint, error_text)
                        return self._format_error_response(
                            f"HTTP {resp.status} error",
                            error_text,
                            resp.status
                        )

                    # Essayer plusieurs encodages pour la réponse
                    response_text = self._decode_response(raw_data)

                    # Parsing de la réponse
                    try:
                        response_data = json.loads(response_text)

                        # Normalisation de la structure de réponse
                        if not isinstance(response_data, dict):
                            return self._format_error_response(
                                "Invalid response format",
                                response_text
                            )

                        # Gestion des réponses d'erreur eedomus
                        success = response_data.get('success')
                        if success == '0' or success == 0:
                            return self._handle_eedomus_error(response_data)

                        # Normalisation du champ success
                        response_data['success'] = 1
                        return response_data

                    except json.JSONDecodeError:
                        _LOGGER.error("Invalid JSON response for %s: %s", endpoint, response_text)
                        return self._format_error_response(
                            "Invalid JSON response",
                            response_text
                        )

        except asyncio.TimeoutError:
            _LOGGER.error("Request timed out for %s", endpoint)
            return self._format_error_response("Request timed out")
        except aiohttp.ClientError as e:
            _LOGGER.error("Client error for %s: %s", endpoint, str(e))
            return self._format_error_response(str(e))
        except Exception as e:
            _LOGGER.error("Unexpected error for %s: %s", endpoint, str(e))
            return self._format_error_response(str(e))

    def _decode_response(self, raw_data: bytes) -> str:
        """Try multiple encodings to decode the response."""
        encodings = ['utf-8', 'iso-8859-1', 'latin-1', 'windows-1252']

        for encoding in encodings:
            try:
                return raw_data.decode(encoding)
            except UnicodeDecodeError:
                continue

        # Si tout échoue, utiliser un remplacement de caractères
        return raw_data.decode('utf-8', errors='replace')

    def _format_error_response(self, error: str, raw_response: Optional[str] = None,
                              http_status: Optional[int] = None) -> Dict:
        """Format a consistent error response."""
        response = {
            "success": 0,
            "error": error,
        }

        if http_status:
            response["http_status"] = http_status
        if raw_response:
            response["raw_response"] = raw_response

        return response

    def _handle_eedomus_error(self, response: Dict) -> Dict:
        """Handle eedomus-specific error responses."""
        error_code = None
        error_msg = "Unknown eedomus error"

        if isinstance(response, dict):
            body = response.get('body', {})
            if isinstance(body, dict):
                error_code = body.get('error_code')
                error_msg = body.get('error_msg', error_msg)

        if error_code and str(error_code) in EEDOMUS_ERROR_CODES:
            error_msg = f"{EEDOMUS_ERROR_CODES[str(error_code)]} (code: {error_code})"

        _LOGGER.error("Eedomus API error: %s (code: %s). Full response: %s",
                     error_msg, error_code, response)
        
        _LOGGER.debug("Eedomus API error request url %s params %s", self.url, self.params)
        return {
            "success": 0,
            "error": error_msg,
            "error_code": error_code,
            "original_response": response
        }

    async def set_periph_value(self, periph_id: str, value: str) -> Dict:
        """Set or get the value of a peripheral."""
        _LOGGER.debug("set_periph_value called with periph_id=%s, value=%s", periph_id, value)

        params = {
            'periph_id': periph_id,
            'value': value
        }

        result = await self.fetch_data('periph.value', params, use_set=True)
        _LOGGER.debug("set_periph_value response: %s", result)

        if isinstance(result, dict):
            if result.get('success') == 0:
                error = result.get('error', 'Unknown error')
                _LOGGER.error("Failed to set peripheral value: %s", error)
                return result

            # Normalisation de la réponse pour les commandes réussies
            if 'body' in result and 'result' in result['body']:
                result['success'] = 1
                result['message'] = result['body']['result']

        return result

    async def get_periph_value(self, periph_id: str) -> Dict:
        """Get the current value of a peripheral."""
        _LOGGER.debug("get_periph_value called with periph_id=%s", periph_id)
        params = {'periph_id': periph_id, 'action': 'get'}
        result = await self.fetch_data('periph.value', params)

        if isinstance(result, dict):
            if result.get('success') == 0:
                return result

            if 'body' in result and isinstance(result['body'], dict):
                if 'value' not in result:
                    result['value'] = result['body'].get('value')

        return result

    async def get_periph_list(self) -> Dict:
        """Get list of all peripherals."""
        result = await self.fetch_data('periph.list')

        # Normalisation de la réponse
        if not isinstance(result, dict):
            return self._format_error_response("Invalid response format", str(result))

        if result.get('success') == 0:
            return result

        # Assure que body est une liste
        if 'body' not in result or not isinstance(result['body'], list):
            result['body'] = []

        return result

    async def get_periph_caract(self, periph_id: str) -> Dict:
        """Get characteristics of a peripheral."""
        params = {'periph_id': periph_id}
        result = await self.fetch_data('periph.caract', params)

        if isinstance(result, dict) and result.get('success') == 0:
            return result

        if 'body' not in result:
            result['body'] = {}

        return result

    async def get_periph_history(self, periph_id: str) -> Dict:
        """Get history of a peripheral."""
        params = {'periph_id': periph_id}
        result = await self.fetch_data('periph.history', params)

        if isinstance(result, dict):
            if result.get('success') == 0:
                return result

            if 'body' not in result or not isinstance(result['body'], list):
                result['body'] = []

        return result

    async def get_periph_value_list(self, periph_id: str) -> Dict: #API inexistante
        """Get possible values for a peripheral of type list."""
        params = {'periph_id': periph_id}
        result = await self.fetch_data('periph.value_list', params)

        if isinstance(result, dict):
            if result.get('success') == 0:
                return result

            if 'body' not in result or not isinstance(result['body'], list):
                result['body'] = []

        return result

    async def auth_test(self) -> Dict:
        """Authorization check."""
        return await self.fetch_data('auth.test')
