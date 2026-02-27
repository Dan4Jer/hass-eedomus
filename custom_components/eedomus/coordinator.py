"""DataUpdateCoordinator for eedomus integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import service

from .const import (
    CONF_ENABLE_HISTORY,
    CONF_HISTORY_RETRY_DELAY,
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
        self._retry_queue = {}  # {periph_id: {"error_time": timestamp, "retry_after": timestamp, "error_message": str, "attempts": int}}
        self._error_count = {}   # {periph_id: int}
        self._scan_interval = scan_interval
        
        # Timing metrics for performance monitoring
        self._last_api_time = 0.0
        self._last_processing_time = 0.0
        self._last_refresh_time = 0.0
        self._last_processed_devices = 0
        self._refresh_timing_history = []  # Store last 10 refresh times for analysis
        
        # Endpoint-specific timing metrics
        self._endpoint_timings = {
            'get_periph_list': 0.0,
            'get_periph_value_list': 0.0,
            'get_periph_caract': 0.0,
            'set_periph_value': 0.0,
            'partial_refresh': 0.0
        }
        self._endpoint_call_counts = {
            'get_periph_list': 0,
            'get_periph_value_list': 0,
            'get_periph_caract': 0,
            'set_periph_value': 0,
            'partial_refresh': 0
        }
        self._yaml_config_cache = None  # Cache for YAML configuration

    async def async_config_entry_first_refresh(self):
        """Effectue le premier rafraîchissement des données et charge la progression de l'historique.
        
        Performs the initial data refresh when the integration is first set up.
        Loads historical progress data and retrieves full device information from the eedomus API.
        """

        # Pre-load YAML configuration asynchronously to cache it for later synchronous access
        await self._load_yaml_config_async()
        
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

        # Phase 1: Construction complète des données SANS mapping
        # Cela résout le problème de temporalité où les enfants peuvent ne pas être encore dans aggregated_data
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

        # Phase 2: Détection des relations parent-enfant pour résoudre les dépendances circulaires
        # Cela permet d'avoir une vue complète des relations avant d'appliquer le mapping
        parent_child_relations = {}
        for periph_id, device_data in aggregated_data.items():
            parent_id = device_data.get("parent_periph_id")
            if parent_id:
                if parent_id not in parent_child_relations:
                    parent_child_relations[parent_id] = []
                parent_child_relations[parent_id].append(periph_id)

        # Phase 3: Application du mapping avec gestion explicite des dépendances
        # Maintenant que toutes les relations sont établies, nous pouvons appliquer le mapping de manière fiable
        for periph_id, device_data in aggregated_data.items():
            # Passer les relations parent-enfant complètes au mapping pour éviter les problèmes de timing
            eedomus_mapping = map_device_to_ha_entity(
                device_data, 
                aggregated_data, 
                coordinator=self,
                parent_child_relations=parent_child_relations
            )
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

        # Log final timing summary for initial refresh (consistent with other refresh types)
        endpoint_details = []
        for endpoint, time in self._endpoint_timings.items():
            if time > 0:
                endpoint_details.append(f"{endpoint}: {time:.3f}s")
        endpoint_log = ", ".join(endpoint_details) if endpoint_details else "no endpoints"
        total_time = sum(self._endpoint_timings.values())
        _LOGGER.info("🔄 INITIAL REFRESH: %d total, %.3fs total (Endpoints: %s)", len(aggregated_data), total_time, endpoint_log)

        # Display enhanced mapping table only on initial startup (not on subsequent refreshes)
        if not hasattr(self, '_mapping_table_displayed'):
            _LOGGER.info("🗺️ Enhanced Device Mapping Table:")
            _LOGGER.info("=" * 150)
            _LOGGER.info("| Periph ID   | Device Name                          | Parent ID     | Type       | Subtype         | usage_id | PRODUCT_TYPE_ID | Justification                                  |")
            _LOGGER.info("=" * 150)
            
            for periph_id in sorted(aggregated_data.keys(), key=lambda x: aggregated_data[x].get('name', '').lower()):
                periph_data = aggregated_data[periph_id]
                parent_id = periph_data.get('parent_periph_id', 'None')
                ha_entity = periph_data.get('ha_entity', '?')
                ha_subtype = periph_data.get('ha_subtype', '?')
                usage_id = periph_data.get('usage_id', '?')
                product_type_id = periph_data.get('PRODUCT_TYPE_ID', '?')
                device_name = periph_data.get('name', '?')
                usage_name = periph_data.get('usage_name', '?')
                
                # Determine justification
                is_rgbw_parent = (ha_entity == 'light' and ha_subtype == 'rgbw')
                is_rgbw_child = (parent_id != 'None' and 
                                aggregated_data.get(parent_id, {}).get('ha_subtype') == 'rgbw')
                
                justification = ""
                if is_rgbw_parent:
                    children = [child_id for child_id, child in aggregated_data.items() 
                              if child.get('parent_periph_id') == periph_id]
                    justification = f"🎨 RGBW lamp detected ({len(children)} children)"
                elif is_rgbw_child:
                    justification = f"🎨 RGBW child brightness channel (parent: {parent_id})"
                else:
                    justification = f"{ha_entity}:{ha_subtype} mapping"
                
                # Format the table row
                _LOGGER.info("| %-12s | %-35s | %-12s | %-10s | %-14s | %-8s | %-15s | %-45s |",
                            periph_id,
                            f"{device_name}",
                            parent_id,
                            ha_entity,
                            ha_subtype,
                            usage_id,
                            product_type_id,
                            justification)
            
            _LOGGER.info("=" * 150)
            _LOGGER.info(f"Total devices mapped: {len(aggregated_data)}")
            _LOGGER.info("⚠️  Note: This table shows all devices with complete coordinator data")
            _LOGGER.info("")
            self._mapping_table_displayed = True
        
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
        
        # Reset endpoint timings before each refresh to avoid cumulative errors
        self._endpoint_timings = {
            'get_periph_list': 0.0,
            'get_periph_value_list': 0.0,
            'get_periph_caract': 0.0,
            'set_periph_value': 0.0,
            'partial_refresh': 0.0
        }
        
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
                    
                    # Calculate actual API time as sum of all endpoint timings
                    actual_api_time = sum(self._endpoint_timings.values())
                    
                    # Store timing metrics for sensors
                    self._last_api_time = actual_api_time
                    self._last_processing_time = processing_time
                    self._last_refresh_time = total_time
                    self._last_processed_devices = stats['total_peripherals']
                    
                    # Log detailed endpoint timings
                    endpoint_details = []
                    for endpoint, time in self._endpoint_timings.items():
                        if time > 0:
                            endpoint_details.append(f"{endpoint}: {time:.3f}s")
                    endpoint_log = ", ".join(endpoint_details) if endpoint_details else "no endpoints"
                    
                    _LOGGER.info("🔄 FULL REFRESH: %d total, %d dynamic, %.3fs total (API: %.3fs, Processing: %.3fs, Endpoints: %s)",
                                 stats['total_peripherals'], stats['dynamic_peripherals'], total_time, actual_api_time, processing_time, endpoint_log)
                else:
                    # Fallback for old format
                    aggregated_data = result
                    processing_time = (datetime.now() - processing_start).total_seconds()
                    total_time = (datetime.now() - start_time).total_seconds()
                    
                    # Calculate actual API time as sum of all endpoint timings
                    actual_api_time = sum(self._endpoint_timings.values())
                    
                    # Log detailed endpoint timings
                    endpoint_details = []
                    for endpoint, time in self._endpoint_timings.items():
                        if time > 0:
                            endpoint_details.append(f"{endpoint}: {time:.3f}s")
                    endpoint_log = ", ".join(endpoint_details) if endpoint_details else "no endpoints"
                    
                    # Store timing metrics for sensors
                    self._last_api_time = actual_api_time
                    self._last_processing_time = processing_time
                    self._last_refresh_time = total_time
                    self._last_processed_devices = len(aggregated_data) if isinstance(aggregated_data, dict) else 0
                    
                    _LOGGER.info("🔄 FULL REFRESH: %d total, %.3fs total (API: %.3fs, Endpoints: %s)",
                                 len(aggregated_data), total_time, actual_api_time, endpoint_log)
                
                return aggregated_data
            else:
                # Track detailed timing for partial refresh
                api_start = datetime.now()
                ret = await self._async_partial_refresh()
                # Calculate actual API time as sum of relevant endpoint timings for partial refresh
                actual_api_time = sum(time for endpoint, time in self._endpoint_timings.items() if endpoint in ['get_periph_caract', 'set_periph_value'])
                
                processing_start = datetime.now()
                # Minimal processing time for partial refresh
                processing_time = (datetime.now() - processing_start).total_seconds()
                total_time = (datetime.now() - start_time).total_seconds()
                
                # Store timing metrics for sensors
                self._last_api_time = actual_api_time
                self._last_processing_time = processing_time
                self._last_refresh_time = total_time
                # For partial refresh, processed devices is the number of dynamic peripherals
                self._last_processed_devices = len(self._dynamic_peripherals) if hasattr(self, '_dynamic_peripherals') else 0
                
                # Log detailed endpoint timings for partial refresh
                endpoint_details = []
                for endpoint, time in self._endpoint_timings.items():
                    if time > 0:
                        endpoint_details.append(f"{endpoint}: {time:.3f}s")
                endpoint_log = ", ".join(endpoint_details) if endpoint_details else "no endpoints"
                
                # Count dynamic peripherals using the same logic as full refresh for consistency
                partial_dynamic_count = sum(1 for periph_data in self._dynamic_peripherals.values() 
                                          if self._is_dynamic_peripheral(periph_data))
                _LOGGER.info("🔄 PARTIAL REFRESH: %d dynamic, %.3fs total (Endpoints: %s)", 
                             partial_dynamic_count, total_time, endpoint_log)
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

    async def _load_yaml_config_async(self):
        """Load YAML configuration asynchronously using device_mapping async functions."""
        if self._yaml_config_cache is not None:
            return self._yaml_config_cache
        
        try:
            # Use the new async function from device_mapping
            from .device_mapping import load_yaml_mappings_async
            
            # Load and merge mappings asynchronously
            merged_config = await load_yaml_mappings_async(self.hass)
            
            self._yaml_config_cache = merged_config
            return self._yaml_config_cache
        except Exception as e:
            _LOGGER.error("❌ Failed to load YAML config asynchronously: %s", e)
            _LOGGER.error("❌ This is a critical error - YAML configuration could not be loaded")
            # No fallback - we require async loading to avoid blocking warnings
            raise e

    def get_yaml_config_sync(self):
        """Get cached YAML configuration synchronously.
        
        This method provides synchronous access to the YAML config cache
        for use in synchronous contexts like map_device_to_ha_entity().
        The config MUST have been pre-loaded during coordinator initialization.
        
        Raises:
            Exception: If YAML config has not been loaded yet (this indicates a bug)
        """
        if self._yaml_config_cache is not None:
            return self._yaml_config_cache
        
        # This should never happen - YAML config should be pre-loaded during initialization
        _LOGGER.error("❌ CRITICAL BUG: YAML config requested but not loaded!")
        _LOGGER.error("❌ This indicates get_yaml_config_sync() was called before initialization completed")
        raise Exception("YAML configuration not loaded - this is a bug in the initialization sequence")

    async def _async_full_data_retreive(self):
        """Retrieve full data including peripherals list, value list, and characteristics."""
        from datetime import datetime
        
        # Track timing for each endpoint
        start_time = datetime.now()
        peripherals_response = await self.client.get_periph_list()
        self._endpoint_timings['get_periph_list'] = (datetime.now() - start_time).total_seconds()
        self._endpoint_call_counts['get_periph_list'] += 1
        
        start_time = datetime.now()
        peripherals_value_list_response = await self.client.get_periph_value_list("all")
        self._endpoint_timings['get_periph_value_list'] = (datetime.now() - start_time).total_seconds()
        self._endpoint_call_counts['get_periph_value_list'] += 1
        
        start_time = datetime.now()
        peripherals_caract_response = await self.client.get_periph_caract("all", True)
        self._endpoint_timings['get_periph_caract'] = (datetime.now() - start_time).total_seconds()
        self._endpoint_call_counts['get_periph_caract'] += 1
        
        _LOGGER.debug("📊 Endpoint timings - get_periph_list: %.3fs, get_periph_value_list: %.3fs, get_periph_caract: %.3fs",
                     self._endpoint_timings['get_periph_list'],
                     self._endpoint_timings['get_periph_value_list'],
                     self._endpoint_timings['get_periph_caract'])
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
        _LOGGER.debug(
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

        # Récupération des données - CORRECTED: now calls full data retrieve with all endpoints
        peripherals_caract = await self._async_full_data_retreive()
        
        # SAFE: Ensure peripherals_caract contains dictionaries with periph_id
        # URGENT FIX FOR CRITICAL BUG - 2026-02-23 16:50
        # Handle both flat and nested list structures
        peripherals_caract_dict = {}
        nested_structure_count = 0
        
        for it in peripherals_caract:
            if isinstance(it, dict) and 'periph_id' in it:
                # Normal case: flat list of dicts
                peripherals_caract_dict[str(it["periph_id"])] = it
            elif isinstance(it, list):
                # Nested case: list of lists - flatten it
                nested_structure_count += 1
                for sub_item in it:
                    if isinstance(sub_item, dict) and 'periph_id' in sub_item:
                        peripherals_caract_dict[str(sub_item["periph_id"])] = sub_item
                    else:
                        _LOGGER.error("❌ Invalid sub-item in nested structure: %s (type: %s)", sub_item, type(sub_item))
            else:
                _LOGGER.error("❌ CRITICAL BUG FIXED: Invalid peripheral data format: %s (type: %s)", it, type(it))
        
        # Log nested structure count once instead of multiple times
        if nested_structure_count > 0:
            _LOGGER.debug("🔍 Found %d nested structure(s) in peripherals_caract, flattened successfully", nested_structure_count)

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

        # Mapping table only displayed on initial startup, not on subsequent refreshes
        # This reduces log volume while maintaining useful startup information
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

        concat_text_periph_id = ",".join(peripherals_for_history)
        try:
            # Track timing for get_periph_caract (partial refresh)
            api_start_time = datetime.now()
            peripherals_caract = await self.client.get_periph_caract(
                concat_text_periph_id
            )
            self._endpoint_timings['get_periph_caract'] = (datetime.now() - api_start_time).total_seconds()
            self._endpoint_call_counts['get_periph_caract'] += 1
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

            # Try to retrieve history if enabled and this peripheral needs it
            if history_retrieval and periph_id in peripherals_for_history:
                if not self._history_progress.get(periph_id, {}).get("completed"):
                    _LOGGER.debug("Retrieving data history %s", periph_id)
                    chunk = await self.async_fetch_history_chunk(periph_id)
                    if chunk:
                        _LOGGER.debug("Retrieved %d history data points for %s", len(chunk), periph_id)
                        # Import the historical data using the optimized Recorder API method
                        await self.async_import_history_chunk(periph_id, chunk)

        # Create/update error sensors
        await self._create_error_sensors()

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
        entity_specifics = periph.get("entity_specifics", {})

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

        # Check if it's a sensor with dynamic value mapping
        if ha_entity == "sensor" and entity_specifics.get("value_mapping") == "dynamic_from_values":
            _LOGGER.debug(
                "Sensor is dynamic (value_mapping) ! %s (%s)",
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
        """Charge la progression depuis les states Home Assistant.
        
        Cette méthode charge la progression depuis les states existants.
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
            _LOGGER.warning(
                "Warning loading history progress (this is normal if no history data exists): %s",
                e
            )

    async def _save_history_progress(self):
        """Sauvegarde la progression dans les states Home Assistant.
        
        Cette méthode utilise uniquement les states de Home Assistant.
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
                            self.data[periph_id]["name"]
                            if periph_id in self.data
                            else "Unknown"
                        ),
                        "device_class": "timestamp",
                        "state_class": "measurement",
                    },
                )
                _LOGGER.debug("Saved progress for %s: %s", periph_id, progress)
        except Exception as e:
            _LOGGER.error("Error saving history progress: %s", e)

    def _validate_history_data(self, chunk: list) -> bool:
        """Valider les données historiques reçues."""
        if not isinstance(chunk, list):
            return False

        for entry in chunk:
            if not isinstance(entry, dict):
                return False
            if "timestamp" not in entry or "value" not in entry:
                return False
            # Vérifier que le timestamp est valide
            try:
                datetime.fromisoformat(entry["timestamp"])
            except ValueError:
                return False

        return True

    def _handle_fetch_error(self, periph_id, error_message):
        """Gérer les erreurs de récupération d'historique."""
        now = datetime.now().timestamp()

        # Initialiser si première erreur
        if periph_id not in self._error_count:
            self._error_count[periph_id] = 0

        self._error_count[periph_id] += 1

        # Si première erreur, mettre en pause pour la durée configurée
        if self._error_count[periph_id] == 1:
            # Obtenir la durée de réessai depuis la configuration
            retry_delay_hours = self.config_entry.options.get(
                CONF_HISTORY_RETRY_DELAY,
                DEFAULT_HISTORY_RETRY_DELAY
            )
            retry_delay = retry_delay_hours * 3600
            retry_after = now + retry_delay
            self._retry_queue[periph_id] = {
                "error_time": now,
                "retry_after": retry_after,
                "error_message": error_message,
                "attempts": 1
            }
            _LOGGER.error(f"❌ Erreur lors de la récupération de l'historique pour {periph_id}: {error_message}")
            _LOGGER.error(f"   Réessai dans {retry_delay_hours} heures")
        else:
            # Mettre à jour le compteur d'erreurs
            if periph_id in self._retry_queue:
                self._retry_queue[periph_id]["attempts"] += 1

    async def async_fetch_history_chunk(self, periph_id: str) -> list:
        """Récupère un chunk de 10 000 points d'historique."""
        # Vérifier si le périphérique est en queue de réessai
        if periph_id in self._retry_queue:
            retry_info = self._retry_queue[periph_id]
            if datetime.now().timestamp() < retry_info["retry_after"]:
                _LOGGER.debug(f"Skipping {periph_id} - in retry queue until {retry_info['retry_after']}")
                return []

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

        try:
            chunk = await self.client.get_device_history(
                periph_id,
                start_timestamp=progress["last_timestamp"],
            )

            if not chunk:
                _LOGGER.error("No history data received for %s", periph_id)
                self._handle_fetch_error(periph_id, "No data received")
                return []

            # Valider les données reçues
            if not self._validate_history_data(chunk):
                _LOGGER.error(f"❌ Données historiques invalides pour {periph_id}")
                self._handle_fetch_error(periph_id, "Invalid data format")
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
                # Import the history data into Home Assistant states
                _LOGGER.info(
                    "Importing %d historical states for %s (%s)",
                    len(chunk),
                    self.data[periph_id]["name"] if periph_id in self.data else "Unknown",
                    periph_id
                )
                
                # Create states for each historical data point
                for entry in chunk:
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                    state_value = entry["value"]
                    
                    # Create a state with the historical data
                    self.hass.states.async_set(
                        f"sensor.eedomus_{periph_id}",
                        str(state_value),
                        {
                            "last_updated": timestamp.isoformat(),
                            "friendly_name": self.data[periph_id]["name"] if periph_id in self.data else "Unknown",
                            "device_class": "timestamp",
                            "state_class": "measurement",
                        },
                        timestamp
                    )
                
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
            # History sensors are now proper entities, no need to recreate them here
            await self._create_error_sensors()
            return chunk
            
        except Exception as e:
            _LOGGER.error(f"❌ Erreur lors de la récupération de l'historique pour {periph_id}: {e}")
            self._handle_fetch_error(periph_id, str(e))
            return []

    async def _create_error_sensors(self):
        """Créer des capteurs pour visualiser les erreurs et la queue de réessais."""
        if not self.hass:
            return
        
        try:
            # Capteur pour le nombre total de périphériques en erreur
            self.hass.states.async_set(
                "sensor.eedomus_history_errors_total",
                str(len(self._retry_queue)),
                {
                    "device_class": "problem",
                    "state_class": "measurement",
                    "unit_of_measurement": "devices",
                    "friendly_name": "Eedomus History Errors Total",
                    "icon": "mdi:alert-circle",
                    "last_updated": datetime.now().isoformat(),
                },
            )

            # Capteur pour le nombre de périphériques complétés
            completed_count = sum(1 for p in self._history_progress.values() if p.get("completed", False))
            self.hass.states.async_set(
                "sensor.eedomus_history_completed",
                str(completed_count),
                {
                    "device_class": "problem",
                    "state_class": "measurement",
                    "unit_of_measurement": "devices",
                    "friendly_name": "Eedomus History Completed",
                    "icon": "mdi:check-circle",
                    "last_updated": datetime.now().isoformat(),
                },
            )

            # Capteur pour chaque périphérique en erreur
            for periph_id, error_info in self._retry_queue.items():
                periph_name = self.data.get(periph_id, {}).get("name", "Unknown")
                retry_in_hours = max(0, (error_info["retry_after"] - datetime.now().timestamp()) / 3600)

                self.hass.states.async_set(
                    f"sensor.eedomus_history_error_{periph_id}",
                    str(retry_in_hours),
                    {
                        "device_class": "duration",
                        "state_class": "measurement",
                        "unit_of_measurement": "hours",
                        "friendly_name": f"History Error: {periph_name}",
                        "icon": "mdi:clock-alert",
                        "periph_id": periph_id,
                        "periph_name": periph_name,
                        "error_message": error_info["error_message"],
                        "attempts": error_info["attempts"],
                        "last_updated": datetime.now().isoformat(),
                    },
                )

            _LOGGER.info(
                "✅ Error sensors created: %d devices in retry queue",
                len(self._retry_queue)
            )
            
        except Exception as e:
            _LOGGER.error("Error creating error sensors: %s", e)



    async def async_import_history_chunk(self, periph_id: str, chunk: list, main_entity_id: str = None) -> None:
        """Import historical data using the most reliable method available.
        
        This method attempts to use the Recorder API for optimal performance,
        but falls back to async_set if the Recorder API is not available or fails.
        """
        if not chunk:
            _LOGGER.debug("No history data to import for %s", periph_id)
            return
        
        # For HA 2026.2+, the Recorder API models have changed significantly
        # and direct insertion is complex. Use the reliable async_set method
        # which has been proven to work correctly.
        
        try:
            await self._fallback_import_history_chunk(periph_id, chunk, main_entity_id)
            _LOGGER.info("Successfully imported %d historical data points for %s", len(chunk), periph_id)
            
        except Exception as err:
            _LOGGER.error("Failed to import history chunk for %s: %s", periph_id, err)
            raise


        

    async def _fallback_import_history_chunk(self, periph_id: str, chunk: list, main_entity_id: str = None) -> None:
        """Import historical data using Statistics API for HA 2026.2+."""
        periph_data = self.data.get(periph_id, {})
        periph_name = periph_data.get("name", f"Device {periph_id}")
        # Use the provided main entity ID if available, otherwise use the default
        entity_id = main_entity_id if main_entity_id else f"sensor.eedomus_{periph_id}"
        
        _LOGGER.info("Importing historical data using Statistics API for %s", entity_id)
        
        try:
            # Try the Statistics API approach first (HA 2026.2+ recommended method)
            await self._import_via_statistics(entity_id, chunk, periph_name)
            return
        except Exception as err:
            _LOGGER.warning("Statistics API import failed, falling back to async_set: %s", err)
            
            # Fallback to async_set if Statistics API fails
            for entry in chunk:
                timestamp = datetime.fromisoformat(entry["timestamp"])
                state_value = entry["value"]
                
                # Create a state with the historical data
                self.hass.states.async_set(
                    entity_id,
                    str(state_value),
                    {
                        "last_updated": timestamp.isoformat(),
                        "friendly_name": periph_name,
                        "device_class": "temperature",
                        "state_class": "measurement",
                        "unit_of_measurement": "°C"
                    },
                    timestamp
                )

    async def _import_via_statistics(self, entity_id: str, chunk: list, periph_name: str) -> None:
        """Import historical data using the Statistics API (HA 2026.2+ recommended method)."""
        try:
            # Prepare statistics data in the format expected by Home Assistant
            statistics_data = []
            for entry in chunk:
                try:
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                    state_value = float(entry["value"])
                    
                    statistics_data.append({
                        "statistic_id": entity_id,
                        "start": timestamp.isoformat(),
                        "mean": state_value,
                        "min": state_value,
                        "max": state_value,
                        "state": state_value,
                        "sum": None  # Not applicable for temperature
                    })
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Skipping invalid data point: %s", e)
                    continue
            
            if not statistics_data:
                _LOGGER.warning("No valid statistics data to import for %s", entity_id)
                return
            
            # Import using the Statistics API
            _LOGGER.info("Calling recorder.import_statistics for %d data points", len(statistics_data))
            
            # Call the service to import statistics
            await self.hass.services.async_call(
                domain="recorder",
                service="import_statistics",
                service_data={
                    "statistic_id": entity_id,
                    "data": statistics_data
                },
                blocking=True
            )
            
            _LOGGER.info("Successfully imported %d statistics points for %s using Statistics API", 
                       len(statistics_data), entity_id)
            
        except Exception as e:
            if "service not found" in str(e).lower() or "import_statistics" in str(e).lower():
                _LOGGER.warning("recorder.import_statistics service not available: %s", e)
            else:
                _LOGGER.error("Failed to import statistics for %s: %s", entity_id, e)
            raise
        except Exception as e:
            _LOGGER.error("Failed to import statistics for %s: %s", entity_id, e)
            raise

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

        # Store original value for tracking
        original_value = value
        _LOGGER.debug("📋 Original set_value call: %s (%s) = %s", 
                     self.data[periph_id]["name"], periph_id, original_value)
        
        # try:
        ret = await self.client.set_periph_value(periph_id, value)

        # Log API response details
        _LOGGER.debug("📋 API response for %s (%s): success=%s, error_code=%s",
                     self.data[periph_id]["name"], periph_id, 
                     ret.get("success"), ret.get("error_code"))

        # Only retry if enabled and we get error_code 6 (value refused)
        if enable_retry and ret.get("success") == 0 and ret.get("error_code") == "6":
            # Try PHP fallback first if enabled
            if php_fallback_enabled:
                _LOGGER.info(
                    "🔄 Trying PHP fallback for %s (%s) with original value: %s",
                    self.data[periph_id]["name"],
                    periph_id,
                    value
                )
                fallback_result = await self.client.php_fallback_set_value(
                    periph_id, value
                )
                if fallback_result.get("success") == 1:
                    _LOGGER.info(
                        "✅ PHP fallback succeeded for %s (%s) - original value %s preserved",
                        self.data[periph_id]["name"],
                        periph_id,
                        value
                    )
                    # Return success response when PHP fallback succeeds
                    return {"success": 1, "fallback_used": True, "value_used": value}
                else:
                    _LOGGER.warning(
                        "⚠️ PHP fallback failed for %s (%s): %s",
                        self.data[periph_id]["name"],
                        periph_id,
                        fallback_result.get("error", "Unknown error"),
                    )
                    # Try next best value if PHP fallback fails
                    next_value = self.next_best_value(periph_id, value)
                    original_value = value
                    modified_value = next_value.get("value")
                    _LOGGER.warning(
                        "🔄 VALUE MODIFICATION DETECTED: %s (%s) - original=%s, modified=%s",
                        self.data[periph_id]["name"],
                        periph_id,
                        original_value,
                        modified_value
                    )
                    _LOGGER.warning(
                        "🔄 Retry enabled - trying next best value (%s => %s) for %s (%s)",
                        original_value,
                        modified_value,
                        self.data[periph_id]["name"],
                        periph_id,
                    )
                    await self.client.set_periph_value(
                        periph_id, modified_value
                    )
                    # Return success response when next best value is used
                    return {"success": 1, "fallback_used": True, "value_used": modified_value, "original_value": original_value}
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
                "✅ Set value successful for %s (%s) - value %s applied without modification",
                self.data[periph_id]["name"],
                periph_id,
                value
            )
            
            # Immediately update local state to reflect the change
            # This ensures UI updates instantly without waiting for coordinator refresh
            self.data[periph_id]["last_value"] = value
            return {"success": 1, "value_used": value, "original_value": value}

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
