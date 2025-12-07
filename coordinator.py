"""DataUpdateCoordinator for eedomus integration."""
from __future__ import annotations
import logging
from datetime import timedelta, datetime  
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, CONF_ENABLE_HISTORY

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
        self._history_progress = {}  # Format: {periph_id: {"last_timestamp": int, "completed": bool}}

 
    async def async_config_entry_first_refresh(self):
        """Effectue le premier rafraîchissement des données et charge la progression de l'historique."""
        
        await self._load_history_progress()
        await super().async_config_entry_first_refresh()

    async def _async_update_data(self):
        """Fetch data from eedomus API with improved error handling."""
        _LOGGER.info("Update eedomus data")
        try:
            if self._full_refresh_needed:
                return await self._async_full_refresh()
            else:
                return await self._async_partial_refresh()
        except Exception as err:
            _LOGGER.exception("Error updating eedomus data: %s", err) 
            # Return last known good data if available
            if hasattr(self, 'data') and self.data:
                return self.data
            raise UpdateFailed(f"Error updating data: {err}") from err


    async def _async_full_data_retreive(self):
        peripherals_response = await self.client.get_periph_list()
        peripherals_value_list_response = await self.client.get_periph_value_list("all")
        peripherals_caract_response = await self.client.get_periph_caract("all", True)
        #_LOGGER.debug("Raw API response: %s", peripherals_response)
        if not isinstance(peripherals_response, dict) or not isinstance(peripherals_value_list_response, dict) or not isinstance(peripherals_caract_response, dict):
            _LOGGER.error("Invalid API response format: %s", peripherals_response)
            raise UpdateFailed("Invalid API response format")
        if peripherals_response.get("success", 0) != 1 and peripherals_value_list_response.get("success",0) != 1 and peripherals_caract_response.get("success",0) != 1:
            error = peripherals_response.get("error", "Unknown API error")
            _LOGGER.error("API request failed: %s", error)
            _LOGGER.debug("API peripherals_response %s", peripherals_response)
            _LOGGER.debug("API peripherals_value_list_response %s", peripherals_value_list_response)
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
        _LOGGER.info("Found %d peripherals value list in total", len(peripherals_caract))
        return (peripherals, peripherals_value_list, peripherals_caract)

    async def _async_full_refresh(self):
        """Perform a complete refresh of all peripherals."""
        _LOGGER.info("Performing full data refresh from eedomus API")
        
        # Récupération des données
        peripherals, peripherals_value_list, peripherals_caract = await self._async_full_data_retreive()


        # Conversion des listes en dictionnaires
        peripherals_dict = {str(periph["periph_id"]): periph for periph in peripherals}
        peripherals_value_dict = {str(item["periph_id"]): item for item in peripherals_value_list}
        peripherals_caract_dict = {str(it["periph_id"]): it for it in peripherals_caract}

        # Initialisation du dictionnaire agrégé
        aggregated_data = {}

        # Agrégation des données pour chaque périphérique
        all_periph_ids = set(peripherals_dict.keys()) | set(peripherals_value_dict.keys()) | set(peripherals_caract_dict.keys())

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

        # Logs des tailles
        _LOGGER.info(
            "Data refresh summary - peripherals: %d, value_list: %d, caract: %d, total: %d",
            len(peripherals_dict),
            len(peripherals_value_dict),
            len(peripherals_caract_dict),
            len(aggregated_data)
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
                    periph_data
                )
                skipped += 1
                continue

            #_LOGGER.debug("Processing peripheral (ID: %s, data: %s)", periph_id, periph_data)

            if self._is_dynamic_peripheral(periph_data):
                self._dynamic_peripherals[periph_id] = periph_data
                dynamic += 1

        _LOGGER.warning("Skipped %d invalid peripherals", skipped)
        _LOGGER.warning("Found %d dynamic peripherals", dynamic)
        return aggregated_data
    
        
    async def _async_full_refresh_old(self):
        """Perform a complete refresh of all peripherals."""
        _LOGGER.info("Performing full data refresh from eedomus API")
        peripherals, peripherals_value_list = await self._async_full_data_retreive()
        data = {}
        value_list = {}
        self._all_peripherals = {}
        self._dynamic_peripherals = {}
        for periph in peripherals_value_list:
            if not isinstance(periph, dict) or "periph_id" not in periph:
                _LOGGER.warning("Skipping invalid peripheral: %s", periph)
                continue
            #_LOGGER.debug("peripherals_value_list periph_id=%s (type=%s) data=%s", periph["periph_id"], type(periph["periph_id"]), periph)
            periph_id = periph["periph_id"]
            value_list[periph["periph_id"]] = periph
        for periph in peripherals:
            if not isinstance(periph, dict) or "periph_id" not in periph:
                _LOGGER.warning("Skipping invalid peripheral: %s", periph)
                continue
            #_LOGGER.debug("peripherals periph_id=%s data=%s", periph["periph_id"], periph)
            periph_id = periph["periph_id"]
            periph_type = periph.get("value_type", "")
            periph_name = periph.get("name", "N/A")
            v_list = None
            if periph_id in value_list.keys():
                _LOGGER.info("Setting value_list for %s data=%s", periph_id, value_list[periph_id].get("values", None))
                v_list = value_list[periph_id].get("values", None)
                periph[periph_id]["value_list"] = value_list[periph_id].get("values", None)
            else:
                _LOGGER.debug("Error Setting value_list for %s (type:%s) in %s", periph_id, type(periph_id), value_list.keys())
            data[periph_id] = {
                "info": periph,
                "current_value": None,
                "history": None,
                "value_list": v_list
            }
            self._all_peripherals[periph_id] = periph
            
            try:
                caract_value = await self.client.get_periph_caract(periph_id)
                if isinstance(caract_value, dict):
                    #data[periph_id].update(caract_value.get("body"))
                    data[periph_id]["current_value"] = caract_value["body"].get("last_value")
                    data[periph_id]["last_value"] = caract_value["body"].get("last_value")
                    data[periph_id]["last_value_change"] = caract_value["body"].get("last_value_change")
                    data[periph_id]["lastest_caract_data"] = caract_value
                if self._is_dynamic_peripheral(periph):
                    self._dynamic_peripherals[periph_id] = periph
            except Exception as e:
                _LOGGER.warning("Failed to get current value for %s: %s", periph_id, e)
            _LOGGER.debug("Processed periperal %s (%s, type: %s)",
                         periph_id, periph_name, periph_type)

        self._full_refresh_needed = False
        return data

    async def _async_partial_refresh(self):
        """Update only dynamic peripherals that change frequently."""
        history_retrieval = self.client.config_entry.data.get(CONF_ENABLE_HISTORY, False)
        _LOGGER.info("Performing partial refresh for %d dynamic peripherals, history=%s",
                      len(self._dynamic_peripherals), history_retrieval)

        # Start with all peripherals data
        data = {pid: self.data[pid] for pid in self.data}

        # Update only dynamic peripherals
        for periph_id in self._dynamic_peripherals:
            try:
                current_value = await self.client.get_periph_caract(periph_id)
                if isinstance(current_value, dict):
                    #data[periph_id].update(current_value.get("body"))
                    data[periph_id]["last_value"] = current_value["body"].get("last_value")
                    data[periph_id]["last_value_change"] = current_value["body"].get("last_value_change")
                    data[periph_id]["lastest_caract_data"] = current_value
                #_LOGGER.debug("Performing partial refresh for %s %s", periph_id, current_value)
            except Exception as e:
                _LOGGER.warning("Failed to update peripheral %s: %s", periph_id, e)

            if history_retrieval:
                if not self._history_progress.get(periph_id, {}).get("completed"):
                    _LOGGER.info("Retrieving data history %s", periph_id)
                    chunk = await self.async_fetch_history_chunk(periph_id)
                    if chunk:
                        await self.async_import_history_chunk(periph_id, chunk)
                    history_retrieval=False 

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
            _LOGGER.debug("Peripheral is dynamic ! %s", periph)
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

    async def _load_history_progress(self):
        """Charge la progression depuis le stockage HA."""
        _LOGGER.debug("Starting to load history progress")
        if hasattr(self.hass, "components.recorder"):
            if (progress := await self.hass.async_add_executor_job(
                    lambda: self.hass.states.async_all(f"{DOMAIN}.history_progress_*")
            )):
                for state in progress:
                    periph_id = state.entity_id.split("_")[-1]
                    self._history_progress[periph_id] = {
                        "last_timestamp": int(float(state.state)),
                        "completed": state.attributes.get("completed", False),
                    }
                    _LOGGER.debug("Loaded progress for %s: %s", periph_id, self._history_progress[periph_id])
        else:
            _LOGGER.warning("Recorder component not available. Cannot load history progress.")

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
                        "periph_name": self.data[periph_id]["name"] if periph_id in self.data else "Unknown",
                    },
                )
                _LOGGER.debug("Saved progress for %s: %s", periph_id, progress)
        else:
            _LOGGER.warning("Recorder component not available. History progress will not be saved.")

    async def async_fetch_history_chunk(self, periph_id: str) -> list:
        """Récupère un chunk de 10 000 points d'historique."""
        if periph_id not in self._history_progress:
            self._history_progress[periph_id] = {"last_timestamp": 0, "completed": False}

        progress = self._history_progress[periph_id]
        if progress["completed"]:
            _LOGGER.debug("History already fully fetched for %s", periph_id)
            return []

        _LOGGER.info(
            "Fetching history for %s (from %s)",
            periph_id,
            datetime.fromtimestamp(progress["last_timestamp"]).isoformat() if progress["last_timestamp"] else "start",
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
            _LOGGER.info("History fully fetched for %s (%s) (received %d entries)",
                         periph_id,
                         self.data[periph_id]["name"] if periph_id in self.data else "Unknown",
                         len(chunk))


        if chunk:
            progress["last_timestamp"] = max(
                int(datetime.fromisoformat(entry["timestamp"]).timestamp())
                for entry in chunk
            )
            _LOGGER.debug("Updated last_timestamp for %s to %s", periph_id, progress["last_timestamp"])

        await self._save_history_progress()
        return chunk

    async def async_import_history_chunk(self, periph_id: str, chunk: list) -> None:
        """Importe un chunk d'historique dans la base de données de HA."""
        if not hasattr(self.hass, "components.recorder"):
            _LOGGER.warning("Recorder component not available. History will not be imported.")
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
                    _LOGGER.warning("Invalid timestamp format in entry %s: %s", entry, e)
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
            _LOGGER.info("Successfully imported %d historical states for %s", len(states), entity_id)
        except Exception as e:
            _LOGGER.exception("Failed to import history for %s: %s", entity_id, e)

    #Add method to set value for a specific peripheral
    async def async_set_periph_value(self, periph_id: str, value: str):
        """Set the value of a specific peripheral."""
        _LOGGER.debug("Setting value '%s' for peripheral '%s' (%s) ", value, periph_id, self.data[periph_id]["name"])
        #try:
        ret = await self.client.set_periph_value(periph_id, value)
        if ret.get("success") == 0 and ret.get("error_code") == "6":
            next_value = self.next_best_value(periph_id, value)
            _LOGGER.warn("Retry once with the next best value (%s => %s) for %s", value, next_value, periph_id)
            await self.client.set_periph_value(periph_id, next_value.get("value"))
        #except Exception as e:
        #    _LOGGER.error(
        #        "Failed to set value for peripheral '%s': %s\ndata=%s\n\nalldata=%s",
        #        periph_id,
        #        e,
        #        self.data[periph_id],
        #        self._all_peripherals[periph_id],
        #        )
        #    raise
        #await self.async_request_refresh()

    def next_best_value(self, periph_id: str, value: str):
        values_list = self.data.get(periph_id, {}).get("values", [])
        available_entries = []
        for item in values_list:
            try:
                available_entries.append((int(item["value"]), item))
            except (ValueError, KeyError):
                continue
        if not values_list:
            raise ValueError(f"Aucune valeur disponible pour le périphérique {periph_id}")

        try:
            target_value = int(value)
        except ValueError:
            raise ValueError(f"La valeur cible '{value}' n'est pas un nombre valide.")    
        if not available_entries:
            raise ValueError(f"Aucune valeur numérique valide trouvée pour le périphérique {periph_id}")
        
        return min(available_entries, key=lambda x: abs(x[0] - target_value))[1]
