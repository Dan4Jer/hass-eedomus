"""DataUpdateCoordinator for eedomus integration."""
from datetime import timedelta
import logging
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

class EedomusDataUpdateCoordinator(DataUpdateCoordinator):
    """Eedomus data update coordinator."""

    def __init__(self, hass: HomeAssistant, client):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="eedomus",
            update_interval=timedelta(seconds=300),
        )
        self.client = client
        self._initial_load = True  # Flag for first deep data load

    async def _async_update_data(self):
        """Fetch data from eedomus API."""
        try:
            _LOGGER.debug("Starting data update from eedomus API")

            # 1. Fetch peripherals from API
            peripherals_response = await self.client.get_periph_list()
            _LOGGER.debug("Raw API response: %s", peripherals_response)

            # Validate response structure
            if not peripherals_response or not isinstance(peripherals_response, dict):
                raise UpdateFailed("Invalid API response: not a dictionary")

            if "success" not in peripherals_response or peripherals_response["success"] != 1:
                raise UpdateFailed(f"API request failed: {peripherals_response}")

            if "body" not in peripherals_response or not isinstance(peripherals_response["body"], list):
                raise UpdateFailed(f"Invalid response body: {peripherals_response}")

            peripherals = peripherals_response["body"]
            _LOGGER.debug("Found %d peripherals", len(peripherals))

            data = {}

            for periph in peripherals:
                if not isinstance(periph, dict) or "periph_id" not in periph:
                    _LOGGER.warning("Skipping invalid peripheral: %s", periph)
                    continue

                periph_id = periph["periph_id"]
                _LOGGER.debug("Processing peripheral %s (%s)", periph_id, periph.get("name", "N/A"))

                # Basic structure for this peripheral
                data[periph_id] = {
                    "info": periph,
                    # Note: We don't use "caracts" key anymore as periph info contains all characteristics
                    "current_value": None,  # Will be populated if needed
                    "history": None,        # Will be populated if needed
                    "value_list": None       # Will be populated if needed
                }

                # Fetch additional data only for relevant types
                if periph.get("value_type") in ["float", "list"]:
                    try:
                        # Current value
                        current_value = await self.client.set_periph_value(periph_id, "get")
                        if current_value and isinstance(current_value, dict):
                            data[periph_id]["current_value"] = current_value.get("value")
                            _LOGGER.debug("Current value for %s: %s", periph_id, data[periph_id]["current_value"])
                    except Exception as e:
                        _LOGGER.warning("Failed to fetch current value for %s: %s", periph_id, e)

                    # History (only on first load)
                    if self._initial_load:
                        try:
                            history = await self.client.get_periph_history(periph_id)
                            if history and isinstance(history, dict) and "body" in history:
                                data[periph_id]["history"] = history["body"]
                                _LOGGER.debug("Fetched history for %s (%d entries)", periph_id, len(history["body"]))
                        except Exception as e:
                            _LOGGER.warning("Failed to fetch history for %s: %s", periph_id, e)

                    # Value list (for "list" type)
                    if periph.get("value_type") == "list":
                        try:
                            value_list = await self.client.get_periph_value_list(periph_id)
                            if value_list and isinstance(value_list, dict) and "body" in value_list:
                                data[periph_id]["value_list"] = value_list["body"]
                                _LOGGER.debug("Fetched value list for %s", periph_id)
                        except Exception as e:
                            _LOGGER.warning("Failed to fetch value list for %s: %s", periph_id, e)

            if self._initial_load:
                self._initial_load = False
                _LOGGER.debug("Completed initial deep data load")

            _LOGGER.debug("Data update completed successfully")
            return data

        except Exception as err:
            _LOGGER.exception("Error updating eedomus data: %s", err)
            raise UpdateFailed(f"Error updating data: {err}") from err
