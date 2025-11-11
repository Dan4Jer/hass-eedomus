"""Data update coordinator for eedomus."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .eedomus_client import EedomusClient

_LOGGER = logging.getLogger(__name__)

class EedomusDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching eedomus data."""

    def __init__(self, hass: HomeAssistant, client: EedomusClient) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="eedomus",
            update_interval=timedelta(seconds=30),
        )
        self.client = client
        self.peripherals = []

    async def _async_update_data(self):
        """Fetch data from eedomus API."""
        try:
            data = await self.client.get_periph_list()
            if data and data.get("success", 0) == 1:
                self.peripherals = data.get("body", [])
                return self.peripherals
            return []
        except Exception as err:
            raise UpdateFailed(f"Error communicating with eedomus API: {err}") from err
