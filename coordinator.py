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
        self._history_progress = {}  # Format: {periph_id: {"last_timestamp": int, "completed": bool}}

        # Charger la progression depuis le stockage (si elle existe)
        self._load_history_progress()

        
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
            if (current_value["body"].get("unit") == "°C" and current_value["body"].get("last_value") == ""):
                _LOGGER.info("Unit null for %s current_value=%s", periph_id, current_value)
            if periph_id == "3445482":
                _LOGGER.info("log to delete !!! null for %s current_value=%s", periph_id, current_value) 
        
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


    async def _load_history_progress(self):
        """Charge la progression depuis le stockage HA."""
        if (progress := await self.hass.async_add_executor_job(
                lambda: self.hass.states.async_all(f"{DOMAIN}.history_progress")
        )):
            for state in progress:
                self._history_progress[state.entity_id.split("_")[-1]] = {
                    "last_timestamp": int(state.state),
                    "completed": state.attributes.get("completed", False),
                }

    async def _save_history_progress(self):
        """Sauvegarde la progression dans le stockage HA."""
        for periph_id, progress in self._history_progress.items():
            entity_id = f"{DOMAIN}.history_progress_{periph_id}"
            self.hass.states.async_set(
                entity_id,
                progress["last_timestamp"],
                {
                    "completed": progress["completed"],
                    "periph_name": next(
                        (d["name"] for d in self.data if d["id"] == periph_id),
                        "Unknown",
                    ),
                },
            )
            
    async def async_fetch_history_chunk(self, periph_id):
        """Récupère un chunk de 10 000 points d'historique."""
        if periph_id not in self._history_progress:
            self._history_progress[periph_id] = {"last_timestamp": 0, "completed": False}

        progress = self._history_progress[periph_id]
        if progress["completed"]:
            return []

        _LOGGER.info(
            "Fetching history for %s (from %s, limit=10000)",
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

        if len(chunk) < 10000:
            progress["completed"] = True
            _LOGGER.info("History fully fetched for %s", periph_id)

        # Mettre à jour le dernier timestamp
        progress["last_timestamp"] = max(
            int(datetime.fromisoformat(entry["timestamp"]).timestamp())
            for entry in chunk
        )

        await self._save_history_progress()
        return chunk

    async def async_import_history_chunk(self, periph_id, chunk):
        """Importe un chunk d'historique dans la base de données de HA."""
        if not hasattr(self.hass, "components.recorder"):
            _LOGGER.warning("Recorder component not available. History will not be imported.")
            return

        entity_id = f"sensor.eedomus_{periph_id}"
        states = [
            State(
                entity_id,
                entry["value"],
                last_changed=datetime.fromisoformat(entry["timestamp"]),
            )
            for entry in chunk
        ]

        try:
            await self.hass.components.recorder.async_add_executor_job(
                lambda: self.hass.components.recorder.history.async_add_states(states)
            )
            _LOGGER.info("Imported %d historical states for %s", len(states), entity_id)
        except Exception as e:
            _LOGGER.error("Failed to import history: %s", e)

    async def async_update_data(self):
        """Met à jour les données et récupère l'historique si activé."""
        data = await self.client.get_devices()

        if self.config_entry.data.get(CONF_ENABLE_HISTORY):
            # Traiter 1 périphérique par cycle
            for device in data:
                if not self._history_progress.get(device["id"], {}).get("completed"):
                    chunk = await self.async_fetch_history_chunk(device["id"])
                    if chunk:
                        await self.async_import_history_chunk(device["id"], chunk)
                    break  # 1 périphérique par cycle

        return data
