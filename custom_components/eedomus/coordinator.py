"""DataUpdateCoordinator for eedomus integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ENABLE_HISTORY,
    CONF_ENABLE_SET_VALUE_RETRY,
    CONF_PHP_FALLBACK_ENABLED,
    CONF_PHP_FALLBACK_SCRIPT_NAME,
    CONF_PHP_FALLBACK_TIMEOUT,
    DEFAULT_ENABLE_SET_VALUE_RETRY,
    DEFAULT_PHP_FALLBACK_ENABLED,
    DEFAULT_PHP_FALLBACK_SCRIPT_NAME,
    DEFAULT_PHP_FALLBACK_TIMEOUT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .entity import EedomusEntity, map_device_to_ha_entity

_LOGGER = logging.getLogger(__name__)


class EedomusDataUpdateCoordinator(DataUpdateCoordinator):
    """Eedomus data update coordinator with optimized refresh strategy."""

    def __init__(
        self, hass: HomeAssistant, client, scan_interval=DEFAULT_SCAN_INTERVAL
    ):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._last_update_start_time = datetime.now()
        self._full_refresh_needed = True
        self._all_peripherals = {}
        self._dynamic_peripherals = {}
        self._history_progress = (
            {}
        )  # Format: {periph_id: {"last_timestamp": int, "completed": bool}}
        self._scan_interval = scan_interval
        
        # Timing metrics for performance monitoring
        self._last_api_time = 0.0
        self._last_processing_time = 0.0
        self._last_refresh_time = 0.0
        self._last_processed_devices = 0
        self._refresh_timing_history = []  # Store last 10 refresh times for analysis

    async def async_config_entry_first_refresh(self):
        """Effectue le premier rafraîchissement des données et charge la progression de l'historique.
        
        Performs the initial data refresh when the integration is first set up.
        Loads historical progress data and retrieves full device information from the eedomus API.
        """

        await self._load_history_progress()
        
        # Perform initial full data retrieval including peripherals list and value list
        peripherals, peripherals_value_list, peripherals_caract = (
            await self._async_full_data_retreive()
        )
        
        # Conversion des listes en dictionnaires
        peripherals_dict = {str(periph["periph_id"]): periph for periph in peripherals}
        peripherals_value_dict = {
            str(item["periph_id"]): item for item in peripherals_value_list
        }
        peripherals_caract_dict = {
            str(it["periph_id"]): it for it in peripherals_caract
        }

        # Initialisation du dictionnaire agrégé
        aggregated_data = {}

        # Agrégation des données pour chaque périphérique
        all_periph_ids = (
            set(peripherals_dict.keys())
            | set(peripherals_value_dict.keys())
            | set(peripherals_caract_dict.keys())
        )

        for periph_id in all_periph_ids:
            aggregated_data[periph_id] = {}

            # Ajout des données de peripherals_dict (si existantes)
            if periph_id in peripherals_dict:
                aggregated_data[periph_id].update(peripherals_dict[periph_id])

            # Ajout des données de peripherals_value_dict (si existantes)
            if periph_id in peripherals_value_dict:
                aggregated_data[periph_id].update(peripherals_value_dict[periph_id])

            # Ajout des données de peripherals_caract_dict (si existantes)
            if periph_id in peripherals_caract_dict:
                aggregated_data[periph_id].update(peripherals_caract_dict[periph_id])

            # Mapping des périphériques vers une entité HA : la bonne ? quid des enfants vis à vis de parent ?
            if not "ha_entity" in aggregated_data[periph_id]:
                eedomus_mapping = map_device_to_ha_entity(aggregated_data[periph_id], aggregated_data)
                aggregated_data[periph_id].update(eedomus_mapping)

        # Logs des tailles
        _LOGGER.info(
            "Initial data load summary - peripherals: %d, value_list: %d, caract: %d, total: %d",
            len(peripherals_dict),
            len(peripherals_value_dict),
            len(peripherals_caract_dict),
            len(aggregated_data),
        )

        # Initialisation des attributs
        self._all_peripherals = aggregated_data
        self._dynamic_peripherals = {}
        self._full_refresh_needed = False

        # Traitement des périphériques
        skipped = 0
        dynamic = 0
        for periph_id, periph_data in aggregated_data.items():
            if not isinstance(periph_data, dict) or "periph_id" not in periph_data:
                _LOGGER.warning(
                    "Skipping invalid peripheral (ID: %s, type: %s, data: %s)",
                    periph_id,
                    type(periph_data),
                    periph_data,
                )
                skipped += 1
                continue

            # _LOGGER.debug("Processing peripheral (ID: %s, data: %s)", periph_id, periph_data)

            if self._is_dynamic_peripheral(periph_data):
                self._dynamic_peripherals[periph_id] = periph_data
                dynamic += 1

        _LOGGER.info("📊 Device processing summary: %d total peripherals, %d dynamic, %d skipped, %d processed", len(aggregated_data), dynamic, skipped, len(aggregated_data))

        _LOGGER.debug(
            "Initial Mapping Table %s",
            "\n".join(
                "Map: "
                f"{aggregated_data[id].get('ha_entity', '?')}/"
                f"{aggregated_data[id].get('ha_subtype', '?')} "
                f"usage_id={aggregated_data[id].get('usage_id', '?')} "
                f"PRODUCT_TYPE_ID={aggregated_data[id].get('PRODUCT_TYPE_ID', '?')} "
                f"{aggregated_data[id].get('name', '?')}/{aggregated_data[id].get('usage_name', '?')}({id})"
                for id in aggregated_data.keys()
            ),
        )
        
        # Set the data for the coordinator
        self.data = aggregated_data
        
        # No need to call super().async_config_entry_first_refresh() as we've already loaded the data

    async def _async_update_data(self):
        """Fetch data from eedomus API with improved error handling.
        
        Main update method that decides between full or partial refresh based on timing.
        Implements error handling and fallback to last known good data.
        """
        start_time = datetime.now()

        _LOGGER.debug("Update eedomus data")
        if (
            start_time - self._last_update_start_time
        ).total_seconds() > self._scan_interval:
            self._full_refresh_needed = True
        self._last_update_start_time = start_time
        try:
            if self._full_refresh_needed:
                # Track detailed timing for full refresh
                api_start = datetime.now()
                result = await self._async_full_refresh()
                api_time = (datetime.now() - api_start).total_seconds()
                
                processing_start = datetime.now()
                # Handle both old and new return formats for compatibility
                if isinstance(result, tuple) and len(result) == 2:
                    aggregated_data, stats = result
                    processing_time = (datetime.now() - processing_start).total_seconds()
                    total_time = (datetime.now() - start_time).total_seconds()
                    
                    # Store timing metrics for sensors
                    self._last_api_time = api_time
                    self._last_processing_time = processing_time
                    self._last_refresh_time = total_time
                    self._last_processed_devices = stats['total_peripherals']
                    
                    _LOGGER.info("🔄 FULL REFRESH: %d total, %d dynamic, %.3fs total (API: %.3fs, Processing: %.3fs)",
                                 stats['total_peripherals'], stats['dynamic_peripherals'], total_time, api_time, processing_time)
                else:
                    # Fallback for old format
                    aggregated_data = result
                    processing_time = (datetime.now() - processing_start).total_seconds()
                    total_time = (datetime.now() - start_time).total_seconds()
                    
                    # Store timing metrics for sensors
                    self._last_api_time = api_time
                    self._last_processing_time = processing_time
                    self._last_refresh_time = total_time
                    self._last_processed_devices = len(aggregated_data) if isinstance(aggregated_data, dict) else 0
                    
                    _LOGGER.info("🔄 FULL REFRESH: %d total, %.3fs total (API: %.3fs, Processing: %.3fs)",
                                 len(aggregated_data), total_time, api_time, processing_time)
                
                return aggregated_data
            else:
                # Track detailed timing for partial refresh
                api_start = datetime.now()
                ret = await self._async_partial_refresh()
                api_time = (datetime.now() - api_start).total_seconds()
                
                processing_start = datetime.now()
                # Minimal processing time for partial refresh
                processing_time = (datetime.now() - processing_start).total_seconds()
                total_time = (datetime.now() - start_time).total_seconds()
                
                # Store timing metrics for sensors
                self._last_api_time = api_time
                self._last_processing_time = processing_time
                self._last_refresh_time = total_time
                # For partial refresh, processed devices is the number of dynamic peripherals
                self._last_processed_devices = len(self._dynamic_peripherals) if hasattr(self, '_dynamic_peripherals') else 0
                
                _LOGGER.info("🔄 PARTIAL REFRESH: %d dynamic, %.3fs total (API: %.3fs, Processing: %.3fs)", 
                             len(self._dynamic_peripherals), total_time, api_time, processing_time)
                return ret
        except Exception as err:
            elapsed = (datetime.now() - start_time).total_seconds()
            _LOGGER.exception(
                "Error updating eedomus after %.3f seconds data: %s", elapsed, err
            )
            # Return last known good data if available
            if hasattr(self, "data") and self.data:
                return self.data
            raise UpdateFailed(f"Error updating data: {err}") from err

    async def _async_partial_data_retreive(self, concat_text_periph_id: str):
        peripherals_caract_response = await self.client.get_periph_caract(
            concat_text_periph_id, False
        )
        if not isinstance(peripherals_caract_response, dict):
            _LOGGER.error(
                "Invalid API response format: %s", peripherals_caract_response
            )
            raise UpdateFailed("Invalid API response format")
        if peripherals_caract_response.get("success", 0) != 1:
            error = peripherals_caract_response.get("error", "Unknown API error")
            _LOGGER.error("API request failed: %s", error)
            _LOGGER.debug("API peripherals_response %s", peripherals_caract_response)
            raise UpdateFailed(f"API request failed: {error}")
        if not isinstance(peripherals_caract, list):
            _LOGGER.error("Invalid peripherals list: %s", peripherals_caract)
            peripherals_caract = []
        return peripherals_caract

    async def _async_full_data_retreive(self):
        """Retrieve full data including peripherals list, value list, and characteristics."""
        peripherals_response = await self.client.get_periph_list()
        peripherals_value_list_response = await self.client.get_periph_value_list("all")
        peripherals_caract_response = await self.client.get_periph_caract("all", True)
        # _LOGGER.debug("Raw API response: %s", peripherals_response)
        if (
            not isinstance(peripherals_response, dict)
            or not isinstance(peripherals_value_list_response, dict)
            or not isinstance(peripherals_caract_response, dict)
        ):
            _LOGGER.error("Invalid API response format: %s", peripherals_response)
            raise UpdateFailed("Invalid API response format")
        if (
            peripherals_response.get("success", 0) != 1
            and peripherals_value_list_response.get("success", 0) != 1
            and peripherals_caract_response.get("success", 0) != 1
        ):
            error = peripherals_response.get("error", "Unknown API error")
            _LOGGER.error("API request failed: %s", error)
            _LOGGER.debug("API peripherals_response %s", peripherals_response)
            _LOGGER.debug(
                "API peripherals_value_list_response %s",
                peripherals_value_list_response,
            )
            raise UpdateFailed(f"API request failed: {error}")
        peripherals = peripherals_response.get("body", [])
        peripherals_value_list = peripherals_value_list_response.get("body", [])
        peripherals_caract = peripherals_caract_response.get("body", [])
        if not isinstance(peripherals, list):
            _LOGGER.error("Invalid peripherals list: %s", peripherals)
            peripherals = []
        _LOGGER.info("Found %d peripherals in total", len(peripherals))
        if not isinstance(peripherals_value_list, list):
            _LOGGER.error("Invalid peripherals list: %s", peripherals_value_list)
            peripherals_value_list = []
        if not isinstance(peripherals_caract, list):
            _LOGGER.error("Invalid peripherals list: %s", peripherals_caract)
            peripherals_caract = []
        _LOGGER.info(
            "Found %d peripherals value list in total", len(peripherals_caract)
        )
        return (peripherals, peripherals_value_list, peripherals_caract)

    async def _async_full_refresh_data_retreive(self):
        """Retrieve only characteristics data for full refresh."""
        peripherals_caract_response = await self.client.get_periph_caract("all", True)
        if not isinstance(peripherals_caract_response, dict):
            _LOGGER.error("Invalid API response format: %s", peripherals_caract_response)
            raise UpdateFailed("Invalid API response format")
        if peripherals_caract_response.get("success", 0) != 1:
            error = peripherals_caract_response.get("error", "Unknown API error")
            _LOGGER.error("API request failed: %s", error)
            _LOGGER.debug("API peripherals_response %s", peripherals_caract_response)
            raise UpdateFailed(f"API request failed: {error}")
        peripherals_caract = peripherals_caract_response.get("body", [])
        if not isinstance(peripherals_caract, list):
            _LOGGER.error("Invalid peripherals list: %s", peripherals_caract)
            peripherals_caract = []
        _LOGGER.debug("Found %d peripherals characteristics in total", len(peripherals_caract))
        return peripherals_caract

    async def _async_full_refresh(self):
        """Perform a complete refresh of all peripherals."""
        _LOGGER.debug("Performing full data refresh from eedomus API")

        # Récupération des données
        peripherals_caract = await self._async_full_refresh_data_retreive()
        peripherals_caract_dict = {
            str(it["periph_id"]): it for it in peripherals_caract
        }

        # Initialisation du dictionnaire agrégé
        aggregated_data = self.data

        # Agrégation des données pour chaque périphérique
        all_periph_ids = set(peripherals_caract_dict.keys())

        for periph_id in all_periph_ids:
            if not periph_id in aggregated_data:
                _LOGGER.warn("This periph_id is unknown %d, please do a reload", periph_id)
                aggregated_data[periph_id] = {}

            # Ajout des données de peripherals_caract_dict (si existantes)
            if periph_id in peripherals_caract_dict:
                aggregated_data[periph_id].update(peripherals_caract_dict[periph_id])


        # Logs des tailles
        _LOGGER.debug(
            "Data refresh summary - caract: %d, total: %d",
            len(peripherals_caract_dict),
            len(aggregated_data),
        )

        # Initialisation des attributs
        self._all_peripherals = aggregated_data
        self._dynamic_peripherals = {}
        self._full_refresh_needed = False

        # Traitement des périphériques
        skipped = 0
        dynamic = 0
        for periph_id, periph_data in aggregated_data.items():
            if not isinstance(periph_data, dict) or "periph_id" not in periph_data:
                _LOGGER.warning(
                    "Skipping invalid peripheral (ID: %s, type: %s, data: %s)",
                    periph_id,
                    type(periph_data),
                    periph_data,
                )
                skipped += 1
                continue

            # _LOGGER.debug("Processing peripheral (ID: %s, data: %s)", periph_id, periph_data)

            if self._is_dynamic_peripheral(periph_data):
                self._dynamic_peripherals[periph_id] = periph_data
                dynamic += 1

        _LOGGER.info("📊 Device processing summary: %d total peripherals, %d dynamic, %d skipped, %d processed", len(aggregated_data), dynamic, skipped, len(aggregated_data))

        _LOGGER.debug(
            "Mapping Table %s",
            "\n".join(
                "Map: "
                f"{aggregated_data[id].get('ha_entity', '?')}/"
                f"{aggregated_data[id].get('ha_subtype', '?')} "
                f"usage_id={aggregated_data[id].get('usage_id', '?')} "
                f"PRODUCT_TYPE_ID={aggregated_data[id].get('PRODUCT_TYPE_ID', '?')} "
                f"{aggregated_data[id].get('name', '?')}/{aggregated_data[id].get('usage_name', '?')}({id})"
                for id in aggregated_data.keys()
            ),
        )
        self.data = aggregated_data
        return aggregated_data

    async def _async_partial_refresh(self):
        """Perform a partial refresh of dynamic peripherals only.
        
        Updates only devices marked as dynamic (lights, switches, sensors that change frequently).
        More efficient than full refresh as it targets only devices that need frequent updates.
        """
        history_retrieval = self.client.config_entry.data.get(
            CONF_ENABLE_HISTORY, False
        )
        _LOGGER.debug(
            "Performing partial refresh for %d dynamic peripherals, history=%s",
            len(self._dynamic_peripherals),
            history_retrieval,
        )
        
        # Start API timing
        api_start_time = datetime.now()
        
        # Skip API call if no dynamic peripherals to refresh
        if not self._dynamic_peripherals:
            _LOGGER.warning("No dynamic peripherals to refresh, skipping partial refresh")
            # Return current data to preserve state instead of empty dict
            if hasattr(self, 'data') and self.data:
                _LOGGER.info("Returning current data to preserve state during partial refresh")
                return self.data
            else:
                _LOGGER.error("No data available to return during partial refresh")
                return {"success": 1, "body": []}

        concat_text_periph_id = ",".join(self._dynamic_peripherals.keys())
        try:
            peripherals_caract = await self.client.get_periph_caract(
                concat_text_periph_id
            )
        except Exception as e:
            _LOGGER.warning(
                "Failed to partial refresh peripheral %s: %s", concat_text_periph_id, e
            )

        if not isinstance(peripherals_caract, dict):
            _LOGGER.warning(
                "Failed to partial refresh %s: %s", concat_text_periph_id, e
            )
            raise

        # Ensure peripherals_caract.get("body") is a list before iterating
        peripherals_body = peripherals_caract.get("body")
        if not isinstance(peripherals_body, list):
            _LOGGER.error("peripherals_caract body is not a list: %s", type(peripherals_body))
            if peripherals_body is None:
                _LOGGER.error("peripherals_caract body is None, API may have returned empty response")
            return
        
        # End API timing, start processing timing
        api_time = (datetime.now() - api_start_time).total_seconds()
        processing_start_time = datetime.now()
        
        processed_devices = 0
        for periph_data in peripherals_body:
            periph_id = periph_data.get("periph_id")
            # Ajout des données de peripherals_caract_dict (si existantes)
            if self.data and periph_id in self.data:
                self.data[periph_id].update(periph_data)
                processed_devices += 1
            else:
                _LOGGER.warning("Cannot update peripheral data: data not available for %s", periph_id)

            if history_retrieval:
                if not self._history_progress.get(periph_id, {}).get("completed"):
                    _LOGGER.debug("Retrieving data history %s", periph_id)
                    chunk = await self.async_fetch_history_chunk(periph_id)
                    if chunk:
                        await self.async_import_history_chunk(periph_id, chunk)
                    history_retrieval = False

        # End processing timing
        processing_time = (datetime.now() - processing_start_time).total_seconds()
        
        # Store timing metrics for sensors
        self._last_api_time = api_time
        self._last_processing_time = processing_time
        self._last_refresh_time = api_time + processing_time
        self._last_processed_devices = processed_devices
        
        return self.data

    def _is_dynamic_peripheral(self, periph):
        """Determine if a peripheral needs regular updates."""
        ha_entity = periph.get("ha_entity")

        dynamic_types = [
            "light",
            "switch",
            "binary_sensor",
        ]

        if ha_entity in dynamic_types:
            _LOGGER.debug(
                "Peripheral is dynamic ! %s (%s)",
                periph.get("name"),
                periph.get("periph_id"),
            )
            return True

        _LOGGER.debug(
            "Peripheral is NOT dynamic ! %s (%s)",
            periph.get("name"),
            periph.get("periph_id"),
        )
        return False

    def get_all_peripherals(self):
        """Return all peripherals (for entity setup)."""
        return self._all_peripherals

    async def request_full_refresh(self):
        """Request a full refresh of all peripherals."""
        _LOGGER.debug("Requesting full data refresh")
        self._full_refresh_needed = True
        await self.async_request_refresh()

    async def _load_history_progress(self):
        """Charge la progression depuis le stockage HA."""
        _LOGGER.debug("Starting to load history progress")
        if hasattr(self.hass, "components.recorder"):
            if progress := await self.hass.async_add_executor_job(
                lambda: self.hass.states.async_all(f"{DOMAIN}.history_progress_*")
            ):
                for state in progress:
                    periph_id = state.entity_id.split("_")[-1]
                    self._history_progress[periph_id] = {
                        "last_timestamp": int(float(state.state)),
                        "completed": state.attributes.get("completed", False),
                    }
                    _LOGGER.debug(
                        "Loaded progress for %s: %s",
                        periph_id,
                        self._history_progress[periph_id],
                    )
        else:
            _LOGGER.warning(
                "Recorder component not available. Cannot load history progress."
            )

    async def _save_history_progress(self):
        """Sauvegarde la progression dans le stockage HA."""
        _LOGGER.debug("Saving history progress...")
        if hasattr(self.hass, "components.recorder"):
            for periph_id, progress in self._history_progress.items():
                entity_id = f"{DOMAIN}.history_progress_{periph_id}"
                self.hass.states.async_set(
                    entity_id,
                    str(progress["last_timestamp"]),
                    {
                        "completed": progress["completed"],
                        "periph_name": (
                            self.data[periph_id]["name"]
                            if periph_id in self.data
                            else "Unknown"
                        ),
                    },
                )
                _LOGGER.debug("Saved progress for %s: %s", periph_id, progress)
        else:
            _LOGGER.warning(
                "Recorder component not available. History progress will not be saved."
            )

    async def async_fetch_history_chunk(self, periph_id: str) -> list:
        """Récupère un chunk de 10 000 points d'historique."""
        if periph_id not in self._history_progress:
            self._history_progress[periph_id] = {
                "last_timestamp": 0,
                "completed": False,
            }

        progress = self._history_progress[periph_id]
        if progress["completed"]:
            _LOGGER.debug("History already fully fetched for %s", periph_id)
            return []

        _LOGGER.info(
            "Fetching history for %s (from %s)",
            periph_id,
            (
                datetime.fromtimestamp(progress["last_timestamp"]).isoformat()
                if progress["last_timestamp"]
                else "start"
            ),
        )

        chunk = await self.client.get_device_history(
            periph_id,
            start_timestamp=progress["last_timestamp"],
        )

        if not chunk:
            _LOGGER.error("No history data received for %s", periph_id)
            return []

        if len(chunk) < 10000:  # ⚠️ À adapter selon la réponse réelle de l'API eedomus
            progress["completed"] = True
            _LOGGER.info(
                "History fully fetched for %s (%s) (received %d entries)",
                periph_id,
                self.data[periph_id]["name"] if periph_id in self.data else "Unknown",
                len(chunk),
            )

        if chunk:
            progress["last_timestamp"] = max(
                int(datetime.fromisoformat(entry["timestamp"]).timestamp())
                for entry in chunk
            )
            _LOGGER.debug(
                "Updated last_timestamp for %s to %s",
                periph_id,
                progress["last_timestamp"],
            )

        await self._save_history_progress()
        return chunk

    async def async_import_history_chunk(self, periph_id: str, chunk: list) -> None:
        """Importe un chunk d'historique dans la base de données de HA."""
        if not hasattr(self.hass, "components.recorder"):
            _LOGGER.warning(
                "Recorder component not available. History will not be imported."
            )
            return

        entity_id = f"sensor.eedomus_{periph_id}"

        if not isinstance(chunk, list) or not chunk:
            _LOGGER.warning("Invalid history chunk for %s: %s", periph_id, chunk)
            return

        states = []
        for entry in chunk:
            try:
                if not isinstance(entry, dict):
                    _LOGGER.warning("Invalid history entry (not a dict): %s", entry)
                    continue

                value = entry.get("value")
                timestamp_str = entry.get("timestamp")

                if value is None or timestamp_str is None:
                    _LOGGER.warning("History entry missing data: %s", entry)
                    continue

                try:
                    last_changed = datetime.fromisoformat(timestamp_str)
                except ValueError as e:
                    _LOGGER.warning(
                        "Invalid timestamp format in entry %s: %s", entry, e
                    )
                    continue

                states.append(
                    State(
                        entity_id,
                        str(value),
                        last_changed=last_changed,
                    )
                )
            except Exception as e:

                _LOGGER.warning("Failed to create state for entry %s: %s", entry, e)

        if not states:
            _LOGGER.warning("No valid states to import for %s", periph_id)
            return

        try:
            await self.hass.components.recorder.async_add_executor_job(
                lambda: self.hass.components.recorder.history.async_add_states(states)
            )
            _LOGGER.info(
                "Successfully imported %d historical states for %s",
                len(states),
                entity_id,
            )
        except Exception as e:
            _LOGGER.exception("Failed to import history for %s: %s", entity_id, e)

    # Add method to set value for a specific peripheral
    async def async_set_periph_value(self, periph_id: str, value: str):
        """Set the value of a specific peripheral."""
        _LOGGER.debug(
            "Setting value '%s' for peripheral '%s' (%s) ",
            value,
            periph_id,
            self.data[periph_id]["name"],
        )

        # Check if retry is enabled in config
        entry_data = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id, {})
        # Get the config entry data - handle both old and new formats
        config_entry_data = (
            entry_data.get("config_entry")
            if isinstance(entry_data.get("config_entry"), dict)
            else self.config_entry.data
        )
        enable_retry = (
            config_entry_data.get(
                CONF_ENABLE_SET_VALUE_RETRY, DEFAULT_ENABLE_SET_VALUE_RETRY
            )
            if config_entry_data
            else DEFAULT_ENABLE_SET_VALUE_RETRY
        )
        php_fallback_enabled = (
            config_entry_data.get(
                CONF_PHP_FALLBACK_ENABLED, DEFAULT_PHP_FALLBACK_ENABLED
            )
            if config_entry_data
            else DEFAULT_PHP_FALLBACK_ENABLED
        )

        if not enable_retry:
            _LOGGER.info(
                "⏭️ Set value retry disabled - attempting single set_value for %s (%s)",
                self.data[periph_id]["name"],
                periph_id,
            )
            _LOGGER.info(
                "💡 If this fails, enable 'Set Value Retry' in advanced configuration options"
            )

        # try:
        ret = await self.client.set_periph_value(periph_id, value)

        # Only retry if enabled and we get error_code 6 (value refused)
        if enable_retry and ret.get("success") == 0 and ret.get("error_code") == "6":
            # Try PHP fallback first if enabled
            if php_fallback_enabled:
                _LOGGER.info(
                    "🔄 Trying PHP fallback for %s (%s)",
                    self.data[periph_id]["name"],
                    periph_id,
                )
                fallback_result = await self.client.php_fallback_set_value(
                    periph_id, value
                )
                if fallback_result.get("success") == 1:
                    _LOGGER.info(
                        "✅ PHP fallback succeeded for %s (%s)",
                        self.data[periph_id]["name"],
                        periph_id,
                    )
                    # Return success response when PHP fallback succeeds
                    return {"success": 1, "fallback_used": True}
                else:
                    _LOGGER.warning(
                        "⚠️ PHP fallback failed for %s (%s): %s",
                        self.data[periph_id]["name"],
                        periph_id,
                        fallback_result.get("error", "Unknown error"),
                    )
                    # Try next best value if PHP fallback fails
                    next_value = self.next_best_value(periph_id, value)
                    _LOGGER.warn(
                        "🔄 Retry enabled - trying next best value (%s => %s) for %s (%s)",
                        value,
                        next_value,
                        self.data[periph_id]["name"],
                        periph_id,
                    )
                    await self.client.set_periph_value(
                        periph_id, next_value.get("value")
                    )
                    # Return success response when next best value is used
                    return {"success": 1, "fallback_used": True, "value_used": next_value.get("value")}
            else:
                # Try next best value if PHP fallback is not enabled
                next_value = self.next_best_value(periph_id, value)
                _LOGGER.warn(
                    "🔄 Retry enabled - trying next best value (%s => %s) for %s (%s)",
                    value,
                    next_value,
                    self.data[periph_id]["name"],
                    periph_id,
                )
                await self.client.set_periph_value(periph_id, next_value.get("value"))
        elif ret.get("success") == 0:
            _LOGGER.error(
                "❌ Set value failed for %s (%s): %s - retry disabled or not applicable",
                self.data[periph_id]["name"],
                periph_id,
                ret.get("error", "Unknown error"),
            )
            _LOGGER.error(
                "💡 Check the documentation for value constraints and consider enabling 'Set Value Retry' in advanced options"
            )
            _LOGGER.error(
                "📖 Documentation: https://github.com/Dan4Jer/hass-eedomus#value-constraints"
            )
        else:
            _LOGGER.info(
                "✅ Set value successful for %s (%s)",
                self.data[periph_id]["name"],
                periph_id,
            )
            
            # Immediately update local state to reflect the change
            # This ensures UI updates instantly without waiting for coordinator refresh
            self.data[periph_id]["last_value"] = value
            return ret

        # except Exception as e:
        #    _LOGGER.error(
        #        "Failed to set value for peripheral '%s': %s\ndata=%s\n\nalldata=%s",
        #        periph_id,
        #        e,
        #        self.data[periph_id],
        #        self._all_peripherals[periph_id],
        #        )
        #    raise
        # await self.async_request_refresh()

    def next_best_value(self, periph_id: str, value: str):
        values_list = self.data.get(periph_id, {}).get("values", [])
        available_entries = []
        for item in values_list:
            try:
                available_entries.append((int(item["value"]), item))
            except (ValueError, KeyError):
                continue
        if not values_list:
            raise ValueError(
                f"Aucune valeur disponible pour le périphérique {periph_id}"
            )

        try:
            target_value = int(value)
        except ValueError:
            raise ValueError(f"La valeur cible '{value}' n'est pas un nombre valide.")
        if not available_entries:
            raise ValueError(
                f"Aucune valeur numérique valide trouvée pour le périphérique {periph_id}"
            )

        return min(available_entries, key=lambda x: abs(x[0] - target_value))[1]
