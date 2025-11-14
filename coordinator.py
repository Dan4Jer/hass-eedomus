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
        self._all_peripherals = {}      # Tous les périphériques (statiques + dynamiques)
        self._dynamic_peripherals = {}  # Seuls les périphériques dynamiques

    async def _async_update_data(self):
        """Fetch data from eedomus API with optimized strategy."""
        try:
            if self._full_refresh_needed:
                return await self._async_full_refresh()
            else:
                return await self._async_partial_refresh()

        except Exception as err:
            _LOGGER.exception("Error updating eedomus data: %s", err)
            raise UpdateFailed(f"Error updating data: {err}") from err

    async def _async_full_refresh(self):
        """Perform a complete refresh of all peripherals."""
        _LOGGER.debug("Performing full data refresh from eedomus API")

        peripherals_response = await self.client.get_periph_list()
        _LOGGER.debug("Raw API response: %s", peripherals_response)

        if not peripherals_response or not isinstance(peripherals_response, dict):
            raise UpdateFailed("Invalid API response: not a dictionary")

        if peripherals_response.get("success") != 1:
            raise UpdateFailed(f"API request failed: {peripherals_response}")

        peripherals = peripherals_response.get("body", [])
        if not isinstance(peripherals, list):
            raise UpdateFailed(f"Invalid response body: {peripherals_response}")

        _LOGGER.debug("Found %d peripherals in total", len(peripherals))

        data = {}
        self._all_peripherals = {}    # Reset all peripherals list
        self._dynamic_peripherals = {}  # Reset dynamic peripherals list

        for periph in peripherals:
            if not isinstance(periph, dict) or "periph_id" not in periph:
                _LOGGER.warning("Skipping invalid peripheral: %s", periph)
                continue

            periph_id = periph["periph_id"]
            periph_type = periph.get("value_type")
            periph_name = periph.get("name", "N/A")

            # Store ALL peripherals in data
            data[periph_id] = {
                "info": periph,
                "current_value": None,
                "history": None,
                "value_list": None
            }

            # Store in all peripherals list
            self._all_peripherals[periph_id] = periph

            # Get current value for ALL peripherals (but only store dynamic ones for updates)
            try:
                current_value = await self.client.set_periph_value(periph_id, "get")
                if current_value and isinstance(current_value, dict):
                    data[periph_id]["current_value"] = current_value.get("value")

                # Classify as dynamic if needed
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
                current_value = await self.client.set_periph_value(periph_id, "get")
                if current_value and isinstance(current_value, dict):
                    data[periph_id]["current_value"] = current_value.get("value")
            except Exception as e:
                _LOGGER.warning("Failed to update peripheral %s: %s", periph_id, e)

        return data

    def _is_dynamic_peripheral(self, periph):
        """Determine if a peripheral needs regular updates."""
        value_type = periph.get("value_type")
        usage_name = periph.get("usage_name", "").lower()
        name = periph.get("name", "").lower()

        # Types that change frequently
        dynamic_types = ["float", "string"]

        # Usage names that indicate dynamic peripherals
        dynamic_usages = [
            "température", "temperature", "humidité", "humidity",
            "luminosité", "luminosity", "consommation", "consumption",
            "puissance", "power", "débit", "flow", "niveau", "level"
        ]

        # Special cases (like your Decorations)
        special_cases = ["decoration", "détection", "mouvement", "caméra"]

        return (value_type in dynamic_types or
                any(usage in usage_name for usage in dynamic_usages) or
                any(case in name for case in special_cases))

    def get_all_peripherals(self):
        """Return all peripherals (for entity setup)."""
        return self._all_peripherals

    async def request_full_refresh(self):
        """Request a full refresh of all peripherals."""
        _LOGGER.debug("Requesting full data refresh")
        self._full_refresh_needed = True
        await self.async_request_refresh()
