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

    async def async_config_entry_first_refresh(self):
        """Effectue le premier rafraîchissement des données et charge la progression de l'historique."""

        await self._load_history_progress()
        
        # Perform initial full data retrieval including peripherals list and value list
        start_time = datetime.now()
        peripherals, peripherals_value_list, peripherals_caract = (
            await self._async_full_data_retrieve()
        )
        elapsed_time = (datetime.now() - start_time).total_seconds()
        _LOGGER.debug("Initial data retrieval completed in %.3f seconds", elapsed_time)
        
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

        # Première passe : Ajouter tous les devices à aggregated_data
        # Cela permet aux règles avancées d'avoir accès à tous les devices, y compris les enfants
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

        # Deuxième passe : Appliquer le mapping pour chaque device
        # Maintenant tous les devices sont disponibles dans aggregated_data
        for periph_id in all_periph_ids:
            # Mapping des périphériques vers une entité HA : la bonne ? quid des enfants vis à vis de parent ?
            if not "ha_entity" in aggregated_data[periph_id]:
                eedomus_mapping = map_device_to_ha_entity(aggregated_data[periph_id], aggregated_data)
                aggregated_data[periph_id].update(eedomus_mapping)
                
                # Add dynamic property based on entity type
                try:
                    from .entity import DEVICE_MAPPINGS
                    ha_entity = aggregated_data[periph_id].get("ha_entity")
                    if ha_entity and DEVICE_MAPPINGS:
                        dynamic_properties = DEVICE_MAPPINGS.get('dynamic_entity_properties', {})
                        aggregated_data[periph_id]["is_dynamic"] = dynamic_properties.get(ha_entity, False)
                        _LOGGER.debug(
                            "Set is_dynamic=%s for %s (%s) based on entity type %s",
                            aggregated_data[periph_id]["is_dynamic"],
                            aggregated_data[periph_id].get("name"),
                            periph_id,
                            ha_entity
                        )
                except Exception as e:
                    _LOGGER.warning(
                        "Failed to set dynamic property for %s (%s): %s",
                        aggregated_data[periph_id].get("name"),
                        periph_id,
                        e
                    )
                    # Set default dynamic property
                    ha_entity = aggregated_data[periph_id].get("ha_entity")
                    if ha_entity in ["light", "switch", "binary_sensor"]:
                        aggregated_data[periph_id]["is_dynamic"] = True
                    else:
                        aggregated_data[periph_id]["is_dynamic"] = False

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
        disabled = 0
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

            # Check if entity is disabled


            # _LOGGER.debug("Processing peripheral (ID: %s, data: %s)", periph_id, periph_data)

            # Ensure is_dynamic property is set for all peripherals
            if "ha_entity" in periph_data and "is_dynamic" not in periph_data:
                try:
                    from .entity import DEVICE_MAPPINGS
                    ha_entity = periph_data.get("ha_entity")
                    if ha_entity and DEVICE_MAPPINGS:
                        dynamic_properties = DEVICE_MAPPINGS.get('dynamic_entity_properties', {})
                        periph_data["is_dynamic"] = dynamic_properties.get(ha_entity, False)
                        _LOGGER.debug(
                            "Set is_dynamic=%s for %s (%s) based on entity type %s",
                            periph_data["is_dynamic"],
                            periph_data.get("name"),
                            periph_id,
                            ha_entity
                        )
                except Exception as e:
                    _LOGGER.warning(
                        "Failed to set dynamic property for %s (%s): %s",
                        periph_data.get("name"),
                        periph_id,
                        e
                    )
                    # Set default dynamic property
                    ha_entity = periph_data.get("ha_entity")
                    if ha_entity in ["light", "switch", "binary_sensor"]:
                        periph_data["is_dynamic"] = True
                    else:
                        periph_data["is_dynamic"] = False

            if self._is_dynamic_peripheral(periph_data):
                self._dynamic_peripherals[periph_id] = periph_data
                dynamic += 1

        _LOGGER.info("Skipped %d invalid peripherals", skipped)
        _LOGGER.info("Found %d dynamic peripherals", dynamic)
        _LOGGER.info("Skipped %d disabled peripherals", disabled)

        # Set the data for the coordinator
        self.data = aggregated_data
        
        # Afficher un résumé des devices
        _LOGGER.info("\n" + "="*120)
        _LOGGER.info("EEDOMUS INTEGRATION SUMMARY")
        _LOGGER.info("="*120)
        _LOGGER.info("Total peripherals from eedomus API: %d", len(aggregated_data))
        _LOGGER.info("Total dynamic peripherals: %d", dynamic)
        _LOGGER.info("Total skipped peripherals: %d (invalid: %d, disabled: %d)", skipped + disabled, skipped, disabled)
        _LOGGER.info("="*120 + "\n")
        
        # Afficher le tableau de mapping global après le premier rafraîchissement
        try:
            from .mapping_registry import print_mapping_table as _print_global_mapping_table, print_mapping_summary, get_mapping_registry
            _print_global_mapping_table()
            print_mapping_summary()
            
            # Vérifier si tous les devices sont mappés
            mapped_ids = {m["periph_id"] for m in get_mapping_registry()}
            # aggregated_data est un dictionnaire, donc nous devons itérer sur ses valeurs
            all_ids = {str(periph_data["periph_id"]) for periph_data in aggregated_data.values() if isinstance(periph_data, dict)}
            
            if len(mapped_ids) < len(all_ids):
                _LOGGER.info("\n" + "="*120)
                _LOGGER.info("ℹ️  INFO: Not all devices were mapped (this is normal)")
                _LOGGER.info("="*120)
                _LOGGER.info("Total devices from API: %d", len(all_ids))
                _LOGGER.info("Total devices mapped: %d", len(mapped_ids))
                _LOGGER.info("Devices not mapped: %d (virtual/system devices)", len(all_ids) - len(mapped_ids))
                
                # Afficher les devices non mappés
                missing_ids = all_ids - mapped_ids
                _LOGGER.info("\nFirst 10 unmapped devices (example):")
                for periph_id in sorted(missing_ids)[:10]:  # Afficher seulement les 10 premiers
                    periph_data = aggregated_data.get(periph_id)
                    if periph_data and isinstance(periph_data, dict):
                        _LOGGER.info("  - %s (ID: %s, usage_id: %s)", 
                                     periph_data.get("name", "Unknown"), periph_id, periph_data.get("usage_id", "Unknown"))
                    else:
                        _LOGGER.info("  - Unknown device (ID: %s)", periph_id)
                
                if len(missing_ids) > 10:
                    _LOGGER.info("  ... and %d more devices (mostly virtual/system)", len(missing_ids) - 10)
                
                _LOGGER.info("="*120 + "\n")
                _LOGGER.info("ℹ️  This is normal behavior - virtual and system devices are intentionally not mapped")
                
        except Exception as e:
            _LOGGER.warning("Failed to print global mapping table: %s", e)
            _LOGGER.warning("Exception type: %s", type(e).__name__)
            _LOGGER.warning("Exception details: %s", str(e))
            _LOGGER.warning("Traceback:")
            import traceback
            _LOGGER.warning(traceback.format_exc())
        
        # No need to call super().async_config_entry_first_refresh() as we've already loaded the data

    async def _async_update_data(self):
        """Fetch data from eedomus API with improved error handling."""
        start_time = datetime.now()

        _LOGGER.info("Update eedomus data")
        if (
            start_time - self._last_update_start_time
        ).total_seconds() > self._scan_interval:
            self._full_refresh_needed = True
        self._last_update_start_time = start_time
        try:
            if self._full_refresh_needed:
                ret = await self._async_full_refresh()
                elapsed = (datetime.now() - start_time).total_seconds()
                _LOGGER.info("Full refresh done in %.3f seconds", elapsed)
                return ret
            else:
                ret = await self._async_partial_refresh()
                elapsed = (datetime.now() - start_time).total_seconds()
                _LOGGER.info("Partial refresh done in %.3f seconds", elapsed)
                return ret
        except Exception as err:
            elapsed = (datetime.now() - start_time).total_seconds()
            _LOGGER.exception(
                "Error updating eedomus after %.3f seconds data: %s", elapsed, err
            )
            # Return last known good data if available
            if hasattr(self, "data") and self.data:
                _LOGGER.warning("Returning last known good data after API error, data size: %d", len(self.data))
                return self.data
            _LOGGER.error("No last known good data available, coordinator.data is None or empty")
            raise UpdateFailed(f"Error updating data: {err}") from err

    async def _async_partial_data_retrieve(self, concat_text_periph_id: str):
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

    async def _async_full_data_retrieve(self):
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
        _LOGGER.debug("Found %d peripherals in total", len(peripherals))
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

    async def _async_full_refresh_data_retrieve(self):
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
        peripherals_caract = await self._async_full_refresh_data_retrieve()
        peripherals_caract_dict = {
            str(it["periph_id"]): it for it in peripherals_caract
        }

        # Initialisation du dictionnaire agrégé
        aggregated_data = self.data

        # Agrégation des données pour chaque périphérique
        all_periph_ids = set(peripherals_caract_dict.keys())

        for periph_id in all_periph_ids:
            if aggregated_data is None:
                _LOGGER.error("aggregated_data is None, cannot process peripheral data")
                continue
                
            if not periph_id in aggregated_data:
                _LOGGER.warning("This periph_id is unknown %d, please do a reload", periph_id)
                aggregated_data[periph_id] = {}

            # Ajout des données de peripherals_caract_dict (si existantes)
            if periph_id in peripherals_caract_dict:
                aggregated_data[periph_id].update(peripherals_caract_dict[periph_id])


        # Logs des tailles
        _LOGGER.info(
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
        disabled = 0
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

        _LOGGER.info("Skipped %d invalid peripherals", skipped)
        _LOGGER.info("Found %d dynamic peripherals", dynamic)
        _LOGGER.info("Skipped %d disabled peripherals", disabled)

        _LOGGER.debug(
            "Mapping Table %s",
            "\n".join(
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
        # Check history option from both config_entry.data and options
        history_from_config = self.client.config_entry.data.get(CONF_ENABLE_HISTORY, False)
        
        # Check if history option is explicitly set in options
        if CONF_ENABLE_HISTORY in self.config_entry.options:
            history_from_options = self.config_entry.options[CONF_ENABLE_HISTORY]
        else:
            history_from_options = None
        
        # Use options if explicitly set, otherwise use config
        history_retrieval = history_from_options if history_from_options is not None else history_from_config
        
        _LOGGER.info(
            "Performing partial refresh for %d dynamic peripherals, history=%s",
            len(self._dynamic_peripherals),
            history_retrieval,
        )

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
        
        for periph_data in peripherals_body:
            periph_id = periph_data.get("periph_id")
            # Ajout des données de peripherals_caract_dict (si existantes)
            if self.data and periph_id in self.data:
                self.data[periph_id].update(periph_data)
            else:
                _LOGGER.warning("Cannot update peripheral data: data not available for %s", periph_id)

            if history_retrieval:
                if not self._history_progress.get(periph_id, {}).get("completed"):
                    _LOGGER.debug("Retrieving data history %s", periph_id)
                    chunk = await self.async_fetch_history_chunk(periph_id)
                    if chunk:
                        await self.async_import_history_chunk(periph_id, chunk)
                    history_retrieval = False

        return self.data

    def _is_dynamic_peripheral(self, periph):
        """Determine if a peripheral needs regular updates based on mapping configuration."""
        periph_id = periph.get("periph_id")
        ha_entity = periph.get("ha_entity")
        
        # Debug: Log the peripheral being checked
        _LOGGER.debug("Checking dynamic status for peripheral %s (%s) with ha_entity=%s", 
                    periph.get("name"), periph_id, ha_entity)
        
        # Special debug for RGBW devices
        if periph_id in ["1269454", "1269455", "1269456", "1269457", "1269458"]:
            _LOGGER.debug("🔍 SPECIAL DEBUG: Checking dynamic status for RGBW device %s (%s)", 
                        periph.get("name"), periph_id)
        
        # Debug: Log DEVICE_MAPPINGS content
        try:
            from .entity import DEVICE_MAPPINGS
            _LOGGER.debug("DEVICE_MAPPINGS loaded: %s", bool(DEVICE_MAPPINGS))
            if DEVICE_MAPPINGS:
                _LOGGER.debug("DEVICE_MAPPINGS keys: %s", list(DEVICE_MAPPINGS.keys()))
                _LOGGER.debug("dynamic_entity_properties: %s", DEVICE_MAPPINGS.get('dynamic_entity_properties', {}))
                _LOGGER.debug("specific_device_dynamic_overrides: %s", DEVICE_MAPPINGS.get('specific_device_dynamic_overrides', {}))
            else:
                _LOGGER.error("DEVICE_MAPPINGS is None or empty!")
        except Exception as e:
            _LOGGER.error("Failed to import DEVICE_MAPPINGS: %s", e)
            DEVICE_MAPPINGS = None
        
        # Check for specific device overrides first (highest priority)
        try:
            if periph_id and DEVICE_MAPPINGS and str(periph_id) in DEVICE_MAPPINGS.get('specific_device_dynamic_overrides', {}):
                is_dynamic = DEVICE_MAPPINGS['specific_device_dynamic_overrides'][str(periph_id)]
                _LOGGER.debug(
                    "Peripheral is %s (specific override) ! %s (%s)",
                    "dynamic" if is_dynamic else "NOT dynamic",
                    periph.get("name"),
                    periph_id,
                )
                return is_dynamic
        except Exception as e:
            _LOGGER.warning(
                "Failed to check specific device overrides for %s (%s): %s",
                periph.get("name"),
                periph_id,
                e
            )
        
        # Check if the peripheral has explicit is_dynamic property from mapping
        if "is_dynamic" in periph:
            is_dynamic = periph.get("is_dynamic", False)
            if is_dynamic:
                _LOGGER.debug(
                    "Peripheral is dynamic (explicit) ! %s (%s)",
                    periph.get("name"),
                    periph_id,
                )
            else:
                _LOGGER.debug(
                    "Peripheral is NOT dynamic (explicit) ! %s (%s)",
                    periph.get("name"),
                    periph_id,
                )
            return is_dynamic
        
        # Fallback to entity type-based dynamic properties
        try:
            from .entity import DEVICE_MAPPINGS
            dynamic_properties = DEVICE_MAPPINGS.get('dynamic_entity_properties', {}) if DEVICE_MAPPINGS else {}
            is_dynamic = dynamic_properties.get(ha_entity, False)
            
            _LOGGER.debug(
                "Peripheral dynamic check (entity type) ! %s (%s) - entity: %s, is_dynamic: %s, properties: %s",
                periph.get("name"),
                periph_id,
                ha_entity,
                is_dynamic,
                dynamic_properties,
            )
            
            if is_dynamic:
                _LOGGER.debug(
                    "Peripheral is dynamic (entity type) ! %s (%s) - entity: %s",
                    periph.get("name"),
                    periph_id,
                    ha_entity,
                )
                
                # Special debug for RGBW devices
                if periph_id in ["1269454", "1269455", "1269456", "1269457", "1269458"]:
                    _LOGGER.debug("🔍 SPECIAL DEBUG: RGBW device %s (%s) is_dynamic=%s (entity type)", 
                                periph.get("name"), periph_id, is_dynamic)
            else:
                _LOGGER.debug(
                    "Peripheral is NOT dynamic (entity type) ! %s (%s) - entity: %s",
                    periph.get("name"),
                    periph_id,
                    ha_entity,
                )
                
                # Special debug for RGBW devices
                if periph_id in ["1269454", "1269455", "1269456", "1269457", "1269458"]:
                    _LOGGER.debug("🔍 SPECIAL DEBUG: RGBW device %s (%s) is_dynamic=%s (entity type)", 
                                periph.get("name"), periph_id, is_dynamic)
            return is_dynamic
        except Exception as e:
            _LOGGER.warning(
                "Failed to determine dynamic status for %s (%s): %s. Falling back to default logic.",
                periph.get("name"),
                periph_id,
                e
            )
            # Fallback to old logic
            dynamic_types = ["light", "switch", "binary_sensor", "cover"]
            is_dynamic = ha_entity in dynamic_types
            
            # Special debug for RGBW devices
            if periph_id in ["1269454", "1269455", "1269456", "1269457", "1269458"]:
                _LOGGER.debug("🔍 SPECIAL DEBUG: RGBW device %s (%s) is_dynamic=%s (fallback)", 
                            periph.get("name"), periph_id, is_dynamic)
            
            return is_dynamic

    def get_all_peripherals(self):
        """Return all peripherals (for entity setup)."""
        return self._all_peripherals

    async def request_full_refresh(self):
        """Request a full refresh of all peripherals."""
        _LOGGER.debug("Requesting full data refresh")
        self._full_refresh_needed = True
        await self.async_request_refresh()

    async def _load_history_progress(self):
        """Charge la progression depuis les states Home Assistant.
        
        Cette méthode charge la progression depuis les states existants.
        Elle ne dépend pas du Recorder component.
        """
        _LOGGER.debug("Loading history progress from Home Assistant states")
        
        try:
            # Charger la progression depuis les states existants
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
        except Exception as e:
            _LOGGER.error(
                "Error loading history progress: %s",
                e
            )

    async def _save_history_progress(self):
        """Sauvegarde la progression dans les states Home Assistant.
        
        Cette méthode utilise uniquement les states de Home Assistant.
        Aucune dépendance au Recorder component.
        """
        _LOGGER.debug("Saving history progress to Home Assistant states")
        
        try:
            for periph_id, progress in self._history_progress.items():
                entity_id = f"{DOMAIN}.history_progress_{periph_id}"
                self.hass.states.async_set(
                    entity_id,
                    str(progress["last_timestamp"]),
                    {
                        "completed": progress["completed"],
                        "periph_name": (
                            self.data.get(periph_id, {}).get("name", "Unknown")
                            if self.data and periph_id in self.data
                            else "Unknown"
                        ),
                        "device_class": "timestamp",
                        "state_class": "measurement",
                    },
                )
                _LOGGER.debug("Saved progress for %s: %s", periph_id, progress)
        except Exception as e:
            _LOGGER.error("Error saving history progress: %s", e)

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
        # Create/update virtual history sensors
        await self._create_virtual_history_sensors()
        return chunk

    async def _create_virtual_history_sensors(self) -> None:
        """Crée des capteurs virtuels pour suivre la progression de l'historique.
        
        Ces capteurs sont indépendants du Recorder component et utilisent
        uniquement les states de Home Assistant pour le stockage.
        """
        if not self.hass:
            return
        
        try:
            from datetime import datetime
            
            # 1. Créer des capteurs de progression par device
            for periph_id, progress in self._history_progress.items():
                periph_name = (
                    self.data.get(periph_id, {}).get("name", "Unknown")
                    if self.data and periph_id in self.data
                    else "Unknown"
                )
                
                # Estimer le nombre total de points
                total_points = await self.client.get_device_history_count(periph_id)
                retrieved_points = 0
                
                if progress.get("last_timestamp", 0) > 0:
                    retrieved_points = max(0, min(10000, (progress["last_timestamp"] / 86400) * 100))
                
                progress_percent = min(100, (retrieved_points / max(1, total_points)) * 100) if total_points > 0 else 0
                
                # Créer le capteur de progression par device
                entity_id = f"sensor.eedomus_history_progress_{periph_id}"
                self.hass.states.async_set(
                    entity_id,
                    str(progress_percent),
                    {
                        "device_class": "progress",
                        "state_class": "measurement",
                        "unit_of_measurement": "%",
                        "friendly_name": f"History Progress: {periph_name}",
                        "icon": "mdi:progress-clock",
                        "periph_id": periph_id,
                        "periph_name": periph_name,
                        "data_points_retrieved": retrieved_points,
                        "data_points_estimated": total_points,
                        "last_timestamp": progress.get("last_timestamp", 0),
                        "completed": progress.get("completed", False),
                        "last_updated": datetime.now().isoformat(),
                    },
                )
            
            # 2. Calculer la progression globale
            total_devices = len(self._history_progress)
            completed_devices = sum(1 for p in self._history_progress.values() if p.get("completed", False))
            total_retrieved = sum(
                max(0, min(10000, (p.get("last_timestamp", 0) / 86400) * 100))
                for p in self._history_progress.values()
            )
            total_estimated = sum(
                await self.client.get_device_history_count(periph_id)
                for periph_id in self._history_progress.keys()
            )
            
            global_progress = (total_retrieved / max(1, total_estimated)) * 100 if total_estimated > 0 else 0
            
            # Créer le capteur de progression globale
            self.hass.states.async_set(
                "sensor.eedomus_history_progress",
                str(global_progress),
                {
                    "device_class": "progress",
                    "state_class": "measurement",
                    "unit_of_measurement": "%",
                    "friendly_name": "Eedomus History Progress",
                    "icon": "mdi:progress-wrench",
                    "devices_total": total_devices,
                    "devices_completed": completed_devices,
                    "data_points_retrieved": total_retrieved,
                    "data_points_estimated": total_estimated,
                    "last_updated": datetime.now().isoformat(),
                },
            )
            
            # 3. Créer le capteur de statistiques
            downloaded_mb = (total_retrieved * 100) / 1024  # Estimation en Mo
            total_mb = (total_estimated * 100) / 1024  # Estimation en Mo
            
            self.hass.states.async_set(
                "sensor.eedomus_history_stats",
                str(downloaded_mb),
                {
                    "device_class": "data_size",
                    "state_class": "measurement",
                    "unit_of_measurement": "MB",
                    "friendly_name": "Eedomus History Stats",
                    "icon": "mdi:database-clock",
                    "total_size": str(total_mb),
                    "downloaded_size": str(downloaded_mb),
                    "devices_with_history": completed_devices,
                    "devices_without_history": total_devices - completed_devices,
                    "last_updated": datetime.now().isoformat(),
                },
            )
            
            _LOGGER.info(
                "✅ Virtual history sensors created: %d device sensors, 1 global progress, 1 stats",
                len(self._history_progress)
            )
            
        except Exception as e:
            _LOGGER.error("Error creating virtual history sensors: %s", e)

    async def async_import_history_chunk(self, periph_id: str, chunk: list) -> None:
        """Importe un chunk d'historique dans la base de données de HA.
        
        Note: Cette méthode est conservée pour compatibilité mais n'est plus
        utilisée lorsque l'option des capteurs virtuels est activée.
        Elle n'a aucune dépendance au Recorder component.
        """
        # Cette méthode est maintenant un stub - elle ne fait plus rien
        # car nous utilisons les capteurs virtuels pour le suivi de progression
        _LOGGER.debug(
            "History chunk import skipped. Using virtual sensors instead."
        )

    # Add method to set value for a specific peripheral
    async def async_set_periph_value(self, periph_id: str, value: str):
        """Set the value of a specific peripheral."""
        _LOGGER.debug(
            "Setting value '%s' for peripheral '%s' (%s) ",
            value,
            periph_id,
            self.data.get(periph_id, {}).get("name", "unknown") if self.data else "unknown",
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
                self.data.get(periph_id, {}).get("name", "unknown") if self.data else "unknown",
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
                    self.data.get(periph_id, {}).get("name", "unknown") if self.data else "unknown",
                    periph_id,
                )
                fallback_result = await self.client.php_fallback_set_value(
                    periph_id, value
                )
                if fallback_result.get("success") == 1:
                    _LOGGER.info(
                        "✅ PHP fallback succeeded for %s (%s)",
                        self.data.get(periph_id, {}).get("name", "unknown") if self.data else "unknown",
                        periph_id,
                    )
                    # Return success response when PHP fallback succeeds
                    return {"success": 1, "fallback_used": True}
                else:
                    _LOGGER.warning(
                        "⚠️ PHP fallback failed for %s (%s): %s",
                        self.data.get(periph_id, {}).get("name", "unknown") if self.data else "unknown",
                        periph_id,
                        fallback_result.get("error", "Unknown error"),
                    )
                    # Try next best value if PHP fallback fails
                    next_value = self.next_best_value(periph_id, value)
                    _LOGGER.warning(
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
                _LOGGER.warning(
                    "🔄 Retry enabled - trying next best value (%s => %s) for %s (%s)",
                    value,
                    next_value,
                    self.data[periph_id]["name"],
                    periph_id,
                )
                await self.client.set_periph_value(periph_id, next_value.get("value"))
                # Return success response when next best value is used
                return {"success": 1, "fallback_used": True, "value_used": next_value.get("value")}
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
                self.data.get(periph_id, {}).get("name", "unknown") if self.data else "unknown",
                periph_id,
            )
            
            # Immediately update local state to reflect the change
            # This ensures UI updates instantly without waiting for coordinator refresh
            if self.data and periph_id in self.data:
                self.data[periph_id]["last_value"] = value
                self.data[periph_id]["last_updated"] = datetime.now().isoformat()
            else:
                _LOGGER.warning("Cannot update local state: data not available for %s", periph_id)
            # Return success response for normal successful case
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
