"""DataUpdateCoordinator for eedomus integration."""
from datetime import timedelta
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

class EedomusDataUpdateCoordinator(DataUpdateCoordinator):
    """Eedomus data update coordinator."""

    def __init__(self, hass: HomeAssistant, client):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self._initial_load = True  # Flag for first deep data load

    async def _async_update_data(self):
        """Fetch data from eedomus API."""
        try:
            _LOGGER.debug("Starting data update from eedomus API")

            # Fetch all peripherals
            peripherals = await self.hass.async_add_executor_job(
                self.client.get_periph_list
            )
            data = {}

            for periph in peripherals:
                periph_id = periph["id"]
                _LOGGER.debug("Processing peripheral: %s", periph_id)

                # Fetch characteristics for the peripheral
                caracts = await self.hass.async_add_executor_job(
                    self.client.get_periph_caract, periph_id
                )
                data[periph_id] = {
                    "info": periph,
                    "caracts": {},
                }

                for caract in caracts:
                    caract_id = caract["id"]
                    _LOGGER.debug("Processing characteristic: %s for peripheral: %s", caract_id, periph_id)

                    # Fetch current value
                    current_value = await self.hass.async_add_executor_job(
                        self.client.get_periph_value, periph_id, caract_id
                    )

                    # Fetch value list if type is 'list'
                    value_list = None
                    if caract.get("type") == "list":
                        value_list = await self.hass.async_add_executor_job(
                            self.client.get_periph_value_list, periph_id, caract_id
                        )
                        _LOGGER.debug("Fetched value list for %s: %s", caract_id, value_list)

                    # Fetch history (deep load on first run, incremental afterwards)
                    history = []
                    if self._initial_load:
                        history = await self.hass.async_add_executor_job(
                            self.client.get_periph_history, periph_id, caract_id
                        )
                        _LOGGER.debug("Fetched full history for %s: %s entries", caract_id, len(history))
                    else:
                        # Incremental update: fetch only the latest value
                        latest_history = await self.hass.async_add_executor_job(
                            self.client.get_periph_history, periph_id, caract_id, limit=1
                        )
                        if latest_history:
                            history = latest_history
                            _LOGGER.debug("Fetched incremental history for %s: 1 entry", caract_id)

                    data[periph_id]["caracts"][caract_id] = {
                        "info": caract,
                        "current_value": current_value,
                        "value_list": value_list,
                        "history": history,
                    }

            if self._initial_load:
                self._initial_load = False
                _LOGGER.debug("Completed initial deep data load")

            _LOGGER.debug("Data update completed successfully")
            return data

        except Exception as err:
            _LOGGER.exception("Error updating eedomus data: %s", err)
            raise UpdateFailed(f"Error updating eedomus data: {err}") from err
