"""DataUpdateCoordinator for eedomus integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class EedomusDataUpdateCoordinator(DataUpdateCoordinator):
    """Eedomus data update coordinator with optimized refresh strategy."""

    def __init__(self, hass: HomeAssistant, client):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self._full_refresh_needed = True
        self._all_peripherals = {}
        self._dynamic_peripherals = {}

    async def _async_update_data(self):
        """Fetch data from eedomus API with improved error handling."""
        _LOGGER.info("Update eedomus data")
        try:
            if self._full_refresh_needed:
                return await self._async_full_refresh()
            else:
                return await self._async_partial_refresh()  # Cette méthode existe maintenant

        except Exception as err:
            _LOGGER.exception("Error updating eedomus data: %s", err)
            # Return last known good data if available
            if hasattr(self, 'data') and self.data:
                return self.data
            raise UpdateFailed(f"Error updating data: {err}") from err

    async def _async_full_refresh(self):
        """Perform a complete refresh of all peripherals."""
        _LOGGER.info("Performing full data refresh from eedomus API")

        peripherals_response = await self.client.get_periph_list()
        _LOGGER.debug("Raw API response: %s", peripherals_response)

        if not isinstance(peripherals_response, dict):
            _LOGGER.error("Invalid API response format: %s", peripherals_response)
            raise UpdateFailed("Invalid API response format")

        if peripherals_response.get("success", 0) != 1:
            error = peripherals_response.get("error", "Unknown API error")
            _LOGGER.error("API request failed: %s", error)
            _LOGGER.debug("API peripherals_response %s", peripherals_response)
            raise UpdateFailed(f"API request failed: {error}")

        peripherals = peripherals_response.get("body", [])
        if not isinstance(peripherals, list):
            _LOGGER.error("Invalid peripherals list: %s", peripherals)
            peripherals = []

        _LOGGER.info("Found %d peripherals in total", len(peripherals))

        data = {}
        self._all_peripherals = {}
        self._dynamic_peripherals = {}

        for periph in peripherals:
            if not isinstance(periph, dict) or "periph_id" not in periph:
                _LOGGER.warning("Skipping invalid peripheral: %s", periph)
                continue
            _LOGGER.debug("peripherals periph_id=%s data=%s", periph["periph_id"], periph)
            periph_id = periph["periph_id"]
            periph_type = periph.get("value_type", "")
            periph_name = periph.get("name", "N/A")

            data[periph_id] = {
                "info": periph,
                "current_value": None,
                "history": None,
                "value_list": None
            }

            self._all_peripherals[periph_id] = periph

            try:
                #current_value = await self.client.set_periph_value(periph_id, "get")
                current_value = await self.client.get_periph_caract(periph_id)
                if isinstance(current_value, dict):
                    data[periph_id]["current_value"] = current_value["body"].get("last_value")
                    data[periph_id]["last_value_change"] = current_value["body"].get("last_change")
                    data[periph_id]["lastest_caract_data"] = current_value
                if self._is_dynamic_peripheral(periph):
                    self._dynamic_peripherals[periph_id] = periph
            except Exception as e:
                _LOGGER.warning("Failed to get current value for %s: %s", periph_id, e)

            _LOGGER.debug("Processed peripheral %s (%s, type: %s)",
                         periph_id, periph_name, periph_type)

        self._full_refresh_needed = False
        return data

    async def _async_partial_refresh(self):
        """Update only dynamic peripherals that change frequently."""
        _LOGGER.debug("Performing partial refresh for %d dynamic peripherals",
                     len(self._dynamic_peripherals))

        # Start with all peripherals data
        data = {pid: self.data[pid] for pid in self.data}

        # Update only dynamic peripherals
        for periph_id in self._dynamic_peripherals:
            try:
                current_value = await self.client.get_periph_caract(periph_id)
                if isinstance(current_value, dict):
                    data[periph_id]["current_value"] = current_value["body"].get("last_value")
                    data[periph_id]["last_value_change"] = current_value["body"].get("last_change")
                    data[periph_id]["lastest_caract_data"] = current_value
                _LOGGER.debug("Performing partial refresh for %s %s", periph_id, current_value)
            except Exception as e:
                _LOGGER.warning("Failed to update peripheral %s: %s", periph_id, e)

        return data

    def _is_dynamic_peripheral(self, periph):
        """Determine if a peripheral needs regular updates."""
        value_type = periph.get("value_type", "")
        usage_name = periph.get("usage_name", "").lower()
        name = periph.get("name", "").lower()

        dynamic_types = ["float", "string"]
        dynamic_usages = [
            "température", "temperature", "humidité", "humidity",
            "luminosité", "luminosity", "consommation", "consumption",
            "puissance", "power", "débit", "flow", "niveau", "level"
        ]
        special_cases = ["decoration", "détection", "mouvement", "caméra"]
        if (value_type in dynamic_types or
            any(usage in usage_name for usage in dynamic_usages) or
            any(case in name for case in special_cases)):
            _LOGGER.info("Peripheral is dynamic ! %s", periph)
            return True
        return False

    def get_all_peripherals(self):
        """Return all peripherals (for entity setup)."""
        return self._all_peripherals

    async def request_full_refresh(self):
        """Request a full refresh of all peripherals."""
        _LOGGER.debug("Requesting full data refresh")
        self._full_refresh_needed = True
        await self.async_request_refresh()
