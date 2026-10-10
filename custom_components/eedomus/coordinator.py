"""DataUpdateCoordinator for eedomus integration."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ENABLE_HISTORY,
    CONF_ENABLE_SET_VALUE_RETRY,
    CONF_HISTORY_PERIPHERALS_PER_SCAN,
    CONF_HISTORY_RETRY_DELAY,
    CONF_PHP_FALLBACK_ENABLED,
    DEFAULT_ENABLE_SET_VALUE_RETRY,
    DEFAULT_HISTORY_PERIPHERALS_PER_SCAN,
    DEFAULT_HISTORY_RETRY_DELAY,
    DEFAULT_PHP_FALLBACK_ENABLED,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .entity import _get_config_value, get_entry_prefix, map_device_to_ha_entity

_LOGGER = logging.getLogger(__name__)

# CAP-5: schema version of the persisted backfill document (ignored /
# paused periphs, global pause, and since v2 the per-periph history
# progress + retry queue). Calqued on the mapping store of
# config_manager: bump this and add a migration to _BACKFILL_MIGRATIONS
# when the stored grammar evolves. The progress entries are keyed
# "<config_entry_id>_<periph_id>" (spec-eedomus-history constraint).
BACKFILL_CONFIG_SCHEMA_VERSION = 2

# Ordered schema migrations: target_version -> pure transform (dict) -> dict.
# A migration for target N upgrades the stored document from N-1 to N.
def _migrate_backfill_v1_to_v2(data: dict) -> dict:
    """v1 (control state only) -> v2 (progress + retry ride along)."""
    return {
        **data,
        "progress": data.get("progress") or {},
        "retry": data.get("retry") or {},
    }


_BACKFILL_MIGRATIONS: dict[int, Any] = {2: _migrate_backfill_v1_to_v2}

# AD-2: seconds between two drain passes of the background worker. The
# pass drains at most history_peripherals_per_scan peripherals - the
# real-time refresh never hosts the history segment again.
BACKFILL_WORKER_INTERVAL = 60

# Websocket error codes surfaced by the backfill control API (CAP-5):
# a refused action carries a stable, branchable code instead of a generic
# exception swallowed by the ui_service handlers.
BACKFILL_ERROR_INVALID = "invalid_format"
BACKFILL_ERROR_BUSY = "error"

# CAP-9 (Supervision tab): number of refresh cycles kept in the box
# metrics circular buffer - the panel's chart horizon.
METRICS_BUFFER_SIZE = 30


class EedomusBackfillError(Exception):
    """A refused backfill control action (CAP-5).

    error_type is the websocket error code sent to the panel:
    invalid_format (unknown periph, inconsistent payload) or error
    (mono-importer lock already held).
    """

    def __init__(self, error_type: str, message: str) -> None:
        """Initialize with a websocket error code and message."""
        super().__init__(message)
        self.error_type = error_type


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
        # AD-3: backfill-eligible peripherals (sensor entity with a
        # numerically resolvable value). The queue is derived from this
        # set, not from _dynamic_peripherals.
        self._backfill_eligible_peripherals = {}
        self._history_progress = (
            {}
        )  # Format: {periph_id: {"last_timestamp": int, "completed": bool}}
        self._retry_queue = (
            {}
        )  # {periph_id: {"error_time": timestamp, "retry_after": timestamp, "error_message": str, "attempts": int}}
        self._error_count = {}  # {periph_id: int}
        # Bug 1.11: consecutive registry-resolution misses per periph —
        # an eligible sensor that never resolves has no importable
        # target and must leave the queue instead of silently burning
        # every fetched chunk.
        self._import_miss_count = {}  # {periph_id: int}
        self._scan_interval = scan_interval

        # Timing metrics for performance monitoring
        self._last_processing_time = 0.0
        self._last_refresh_time = 0.0
        self._last_processed_devices = 0

        # CAP-9 box metrics (Supervision tab): circular buffer of the
        # last refresh cycles (durations, per-cycle API call delta,
        # peripheral counts). The time series exists nowhere else - the
        # sensors only expose the last cycle's scalars. Purely passive
        # capture: never a dependency of the refresh flow (AD-2).
        self._metrics_history: deque = deque(maxlen=METRICS_BUFFER_SIZE)
        self._metrics_cycle_start_calls: int | None = None

        # History import timing metrics (partial refresh decomposition)
        self._last_history_time = 0.0
        self._last_history_fetch_time = 0.0
        self._last_history_import_time = 0.0
        self._last_history_periphs = 0
        self._last_history_states = 0

        # Endpoint-specific timing metrics
        self._endpoint_timings = {
            "get_periph_list": 0.0,
            "get_periph_value_list": 0.0,
            "get_periph_caract": 0.0,
            "set_periph_value": 0.0,
            "partial_refresh": 0.0,
        }
        self._endpoint_data_sizes = {
            "get_periph_list": 0,
            "get_periph_value_list": 0,
            "get_periph_caract": 0,
            "set_periph_value": 0,
            "partial_refresh": 0,
        }
        self._endpoint_call_counts = {
            "get_periph_list": 0,
            "get_periph_value_list": 0,
            "get_periph_caract": 0,
            "set_periph_value": 0,
            "partial_refresh": 0,
        }
        self._yaml_config_cache = None  # Cache for YAML configuration

        # CAP-5 backfill control state (steering of the history queue).
        # The queue itself is DERIVED from _history_progress x the drain
        # order; these sets/flags only steer the drain. ignored and paused
        # persist per config entry in .storage (BACKFILL store) so they
        # survive a reload or restart; the priority list is ephemeral.
        self._backfill_ignored: set[str] = set()
        self._backfill_paused: set[str] = set()
        self._backfill_global_paused = False
        self._backfill_priority: list[str] = []
        # Mono-importer invariant (AD-2): one history import at a time,
        # across the partial-refresh drain segment and retry_now. Busy is
        # a nominal refusal, never a wait.
        self._backfill_import_lock = asyncio.Lock()
        self._backfill_active_periph: str | None = None
        self._backfill_store: Store | None = None
        self._backfill_worker_task = None

    async def async_config_entry_first_refresh(self):
        """Perform the first data refresh and load the history progress.

        Runs the initial data refresh when the integration is first set up,
        loads historical progress data, and retrieves full device information
        from the eedomus API.
        """

        # Pre-load YAML configuration asynchronously to cache it for later synchronous access
        await self._load_yaml_config_async()

        await self._load_history_progress()

        # CAP-5: reload the persisted backfill control state (ignored /
        # paused / global pause) before any drain can run.
        await self._load_backfill_persistence()

        # AD-2: the background drain worker starts with the coordinator -
        # the refresh cycles never host the history segment again.
        self._ensure_backfill_worker()

        # Perform initial full data retrieval including peripherals list and value list
        try:
            (
                peripherals,
                peripherals_value_list,
                peripherals_caract,
            ) = await self._async_full_data_retreive()
        except Exception as err:
            _LOGGER.warning(
                "⚠️ Cannot reach the eedomus box during initialization "
                "(error: %s). Home Assistant will automatically retry "
                "in the background.",
                err,
            )
            host = (
                self.client.host
                if hasattr(self.client, "host")
                else "the configured address"
            )
            raise ConfigEntryNotReady(
                f"Unable to reach the eedomus box at {host}: {err}"
            ) from None

        # Convert the lists into dictionaries
        peripherals_dict = {str(periph["periph_id"]): periph for periph in peripherals}
        peripherals_value_dict = {
            str(item["periph_id"]): item for item in peripherals_value_list
        }
        peripherals_caract_dict = {
            str(it["periph_id"]): it for it in peripherals_caract
        }

        # Initialize the aggregated dictionary
        aggregated_data = {}

        # Aggregate the data for each peripheral
        all_periph_ids = (
            set(peripherals_dict.keys())
            | set(peripherals_value_dict.keys())
            | set(peripherals_caract_dict.keys())
        )

        # Phase 1: Build the full data set WITHOUT mapping
        # This solves the timing issue where children may not be
        # in aggregated_data yet
        for periph_id in all_periph_ids:
            aggregated_data[periph_id] = {}

            # Add peripherals_dict data (if present)
            if periph_id in peripherals_dict:
                aggregated_data[periph_id].update(peripherals_dict[periph_id])

            # Add peripherals_value_dict data (if present)
            if periph_id in peripherals_value_dict:
                aggregated_data[periph_id].update(peripherals_value_dict[periph_id])

            # Add peripherals_caract_dict data (if present)
            if periph_id in peripherals_caract_dict:
                aggregated_data[periph_id].update(peripherals_caract_dict[periph_id])

        # Phase 2: Detect parent-child relations to resolve circular dependencies
        # This gives a complete view of the relations before applying the mapping
        parent_child_relations = {}
        for periph_id, device_data in aggregated_data.items():
            parent_id = device_data.get("parent_periph_id")
            if parent_id:
                if parent_id not in parent_child_relations:
                    parent_child_relations[parent_id] = []
                parent_child_relations[parent_id].append(periph_id)

        # Phase 3: Apply the mapping with explicit dependency handling
        # Now that all relations are established, the mapping can be applied reliably
        for periph_id, device_data in aggregated_data.items():
            # Pass the full parent-child relations to the mapping to avoid timing issues
            eedomus_mapping = map_device_to_ha_entity(
                device_data,
                aggregated_data,
                coordinator=self,
                parent_child_relations=parent_child_relations,
            )
            aggregated_data[periph_id].update(eedomus_mapping)

        # Size logs
        _LOGGER.info(
            "Initial data load summary - peripherals: %d, value_list: %d, caract: %d, total: %d",
            len(peripherals_dict),
            len(peripherals_value_dict),
            len(peripherals_caract_dict),
            len(aggregated_data),
        )

        # Initialize attributes
        self._all_peripherals = aggregated_data
        self._dynamic_peripherals = {}
        self._backfill_eligible_peripherals = {}
        self._full_refresh_needed = False

        # Process the peripherals
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

            if self._is_backfill_eligible(periph_data):
                self._backfill_eligible_peripherals[periph_id] = periph_data

        _LOGGER.info(
            "📊 Device processing summary: %d total peripherals, %d dynamic, "
            "%d backfill-eligible, %d skipped, %d processed",
            len(aggregated_data),
            dynamic,
            len(self._backfill_eligible_peripherals),
            skipped,
            len(aggregated_data),
        )

        # Log final timing summary for initial refresh (consistent with other refresh types)
        endpoint_details = []
        for endpoint, timing in self._endpoint_timings.items():
            if timing > 0:
                endpoint_details.append(f"{endpoint}: {timing:.3f}s")
        endpoint_log = (
            ", ".join(endpoint_details) if endpoint_details else "no endpoints"
        )
        total_time = sum(self._endpoint_timings.values())
        _LOGGER.info(
            "🔄 INITIAL REFRESH: %d total, %.3fs total (Endpoints: %s)",
            len(aggregated_data),
            total_time,
            endpoint_log,
        )

        # Display enhanced mapping table only on initial startup (not on subsequent refreshes)
        if not hasattr(self, "_mapping_table_displayed"):
            # Count device types for summary
            device_types = {}
            rgbw_lamps = 0
            rgbw_children = 0

            for periph_id in aggregated_data.keys():
                periph_data = aggregated_data[periph_id]
                ha_entity = periph_data.get("ha_entity", "?")
                ha_subtype = periph_data.get("ha_subtype", "?")
                device_type = f"{ha_entity}:{ha_subtype}"

                # Count device types
                device_types[device_type] = device_types.get(device_type, 0) + 1

                # Count RGBW devices
                if ha_entity == "light" and ha_subtype == "rgbw":
                    rgbw_lamps += 1
                elif (
                    periph_data.get("parent_periph_id")
                    and aggregated_data.get(periph_data["parent_periph_id"], {}).get(
                        "ha_subtype"
                    )
                    == "rgbw"
                ):
                    rgbw_children += 1

            # Display summary at INFO level (always visible)
            _LOGGER.info(
                "🗺️ Device Mapping Summary: %d total devices, %d unique types",
                len(aggregated_data),
                len(device_types),
            )
            if rgbw_lamps > 0:
                _LOGGER.info(
                    "🎨 RGBW Devices: %d lamps with %d brightness channels",
                    rgbw_lamps,
                    rgbw_children,
                )

            # Display enhanced mapping table at INFO level for complete visibility
            _LOGGER.info("🗺️ Enhanced Device Mapping Table:")
            _LOGGER.info("=" * 150)
            _LOGGER.info(
                "| Periph ID   | Device Name                          "
                "| Parent ID     | Type       | Subtype         "
                "| usage_id | PRODUCT_TYPE_ID | Justification                                  |"
            )
            _LOGGER.info("=" * 150)

            for periph_id in sorted(
                aggregated_data.keys(),
                key=lambda x: aggregated_data[x].get("name", "").lower(),
            ):
                periph_data = aggregated_data[periph_id]
                parent_id = periph_data.get("parent_periph_id", "None")
                ha_entity = periph_data.get("ha_entity", "?")
                ha_subtype = periph_data.get("ha_subtype", "?")
                usage_id = periph_data.get("usage_id", "?")
                product_type_id = periph_data.get("PRODUCT_TYPE_ID", "?")
                device_name = periph_data.get("name", "?")

                # Determine justification
                is_rgbw_parent = ha_entity == "light" and ha_subtype == "rgbw"
                is_rgbw_child = (
                    parent_id != "None"
                    and aggregated_data.get(parent_id, {}).get("ha_subtype") == "rgbw"
                )

                justification = ""
                if is_rgbw_parent:
                    children = [
                        child_id
                        for child_id, child in aggregated_data.items()
                        if child.get("parent_periph_id") == periph_id
                    ]
                    justification = f"🎨 RGBW lamp detected ({len(children)} children)"
                elif is_rgbw_child:
                    justification = (
                        f"🎨 RGBW child brightness channel (parent: {parent_id})"
                    )
                else:
                    justification = f"{ha_entity}:{ha_subtype} mapping"

                # Format the table row at INFO level
                _LOGGER.info(
                    "| %-12s | %-35s | %-12s | %-10s | %-14s | %-8s | %-15s | %-45s |",
                    periph_id,
                    f"{device_name}",
                    parent_id,
                    ha_entity,
                    ha_subtype,
                    usage_id,
                    product_type_id,
                    justification,
                )

            _LOGGER.info("=" * 150)
            _LOGGER.info(f"Total devices mapped: {len(aggregated_data)}")
            _LOGGER.info(
                "⚠️  Note: This table shows all devices with complete coordinator data"
            )
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
        # 🚨 CHANGE: use time.monotonic() to compute durations precisely
        #                  (immune to system clock jumps)
        start_monotonic = time.monotonic()

        # Keep start_time (datetime): feeds _last_update_start_time and _scan_interval
        start_time = datetime.now()

        # CAP-9: baseline of the cumulative API call counters for this
        # cycle - the per-cycle metric is the delta against it (the
        # counters are never reset, only ever incremented). The read is
        # guarded like the capture itself: a metrics problem never
        # breaks the refresh.
        try:
            self._metrics_cycle_start_calls = sum(
                self._endpoint_call_counts.values()
            )
        except Exception as err:  # pragma: no cover
            self._metrics_cycle_start_calls = None
            _LOGGER.warning("Box metrics cycle baseline capture failed: %s", err)

        _LOGGER.debug("Update eedomus data")
        if (
            start_time - self._last_update_start_time
        ).total_seconds() > self._scan_interval:
            self._full_refresh_needed = True
        self._last_update_start_time = start_time

        # Reset endpoint timings and data sizes before each refresh
        self._endpoint_timings = {
            "get_periph_list": 0.0,
            "get_periph_value_list": 0.0,
            "get_periph_caract": 0.0,
            "set_periph_value": 0.0,
            "partial_refresh": 0.0,
        }
        self._endpoint_data_sizes = {
            "get_periph_list": 0,
            "get_periph_value_list": 0,
            "get_periph_caract": 0,
            "set_periph_value": 0,
            "partial_refresh": 0,
        }

        try:
            if self._full_refresh_needed:
                result = await self._async_full_refresh()

                # 🚨 CHANGE: datetime.now() replaced with time.monotonic()
                #                   to measure processing time
                processing_start = time.monotonic()

                # Handle both old and new return formats for compatibility
                if isinstance(result, tuple) and len(result) == 2:
                    aggregated_data, stats = result

                    # 🚨 CHANGE: durations computed via monotonic()
                    processing_time = time.monotonic() - processing_start
                    total_time = time.monotonic() - start_monotonic

                    # Calculate actual API time as sum of all endpoint timings
                    actual_api_time = sum(self._endpoint_timings.values())

                    # Store timing metrics for sensors
                    self._last_api_time = actual_api_time
                    self._last_processing_time = processing_time
                    self._last_refresh_time = total_time
                    self._last_processed_devices = stats["total_peripherals"]

                    # Log detailed endpoint metrics (timings + data sizes in KB)
                    endpoint_details = []
                    # 🚨 CHANGE: 'time' renamed to 'timing' to avoid
                    # shadowing the standard 'time' module
                    for endpoint, timing in self._endpoint_timings.items():
                        if timing > 0:
                            data_size = self._endpoint_data_sizes.get(endpoint, 0)
                            # Convert bytes to KB for better readability
                            data_size_kb = (
                                round(data_size / 1024, 1) if data_size > 0 else 0
                            )
                            endpoint_details.append(
                                f"{endpoint}: {timing:.3f}s ({data_size_kb} KB)"
                            )
                    endpoint_log = (
                        ", ".join(endpoint_details)
                        if endpoint_details
                        else "no endpoints"
                    )

                    _LOGGER.info(
                        "🔄 FULL REFRESH: %d total, "
                        "%d dynamic, %.3fs total "
                        "(API: %.3fs, Processing: %.3fs, Endpoints: %s)",
                        stats["total_peripherals"],
                        stats["dynamic_peripherals"],
                        total_time,
                        actual_api_time,
                        processing_time,
                        endpoint_log,
                    )
                else:
                    # Fallback for old format
                    aggregated_data = result

                    # 🚨 CHANGE: durations computed via monotonic()
                    processing_time = time.monotonic() - processing_start
                    total_time = time.monotonic() - start_monotonic

                    # Calculate actual API time as sum of all endpoint timings
                    actual_api_time = sum(self._endpoint_timings.values())

                    # Log detailed endpoint timings
                    endpoint_details = []
                    # 🚨 CHANGE: 'time' renamed to 'timing'
                    for endpoint, timing in self._endpoint_timings.items():
                        if timing > 0:
                            endpoint_details.append(f"{endpoint}: {timing:.3f}s")
                    endpoint_log = (
                        ", ".join(endpoint_details)
                        if endpoint_details
                        else "no endpoints"
                    )

                    # Store timing metrics for sensors
                    self._last_api_time = actual_api_time
                    self._last_processing_time = processing_time
                    self._last_refresh_time = total_time
                    self._last_processed_devices = (
                        len(aggregated_data) if isinstance(aggregated_data, dict) else 0
                    )

                    _LOGGER.info(
                        "🔄 FULL REFRESH: %d total, %.3fs total (API: %.3fs, Endpoints: %s)",
                        len(aggregated_data),
                        total_time,
                        actual_api_time,
                        endpoint_log,
                    )

                # CAP-9: the cycle completed - record it in the metrics
                # buffer (passive, never blocks the return path).
                self._capture_cycle_metrics(total_time, actual_api_time)
                return aggregated_data
            else:
                # 🚨 CHANGE: removed 'api_start = datetime.now()' which was dead code
                ret = await self._async_partial_refresh()

                # Calculate actual API time as sum of relevant endpoint timings for partial refresh
                # 🚨 CHANGE: 'partial_refresh' added
                #                   to the accounted endpoints list, previously ignored
                # 🚨 CHANGE: 'time' renamed to 'timing' in the loop
                actual_api_time = sum(
                    timing
                    for endpoint, timing in self._endpoint_timings.items()
                    if endpoint
                    in ["get_periph_caract", "set_periph_value", "partial_refresh"]
                )

                # 🚨 CHANGE: removed the bogus processing_time computation
                # (it measured nothing). Fixed to 0.0: the processing is
                # already included in the _async_partial_refresh() wait
                processing_time = 0.0
                total_time = time.monotonic() - start_monotonic

                # Store timing metrics for sensors
                self._last_api_time = actual_api_time
                self._last_processing_time = processing_time
                self._last_refresh_time = total_time
                # For partial refresh, processed devices is the number of dynamic peripherals
                self._last_processed_devices = (
                    len(self._dynamic_peripherals)
                    if hasattr(self, "_dynamic_peripherals")
                    else 0
                )

                # Log detailed endpoint metrics for partial refresh (timings + data sizes)
                endpoint_details = []
                # 🚨 CHANGE: 'time' renamed to 'timing'
                for endpoint, timing in self._endpoint_timings.items():
                    if timing > 0:
                        data_size = self._endpoint_data_sizes.get(endpoint, 0)
                        endpoint_details.append(
                            f"{endpoint}: {timing:.3f}s ({data_size} items)"
                        )
                endpoint_log = (
                    ", ".join(endpoint_details) if endpoint_details else "no endpoints"
                )

                # Count dynamic peripherals using the same logic as full refresh for consistency
                partial_dynamic_count = sum(
                    1
                    for periph_data in self._dynamic_peripherals.values()
                    if self._is_dynamic_peripheral(periph_data)
                )
                # Residual local processing time (loop updates, error sensors),
                # computed for the log only: history is measured separately in
                # _async_partial_refresh, the rest is time not spent in API/history.
                history_time = getattr(self, "_last_history_time", 0.0)
                processing_time_log = max(
                    total_time - actual_api_time - history_time, 0.0
                )
                _LOGGER.info(
                    "🔄 PARTIAL REFRESH: %d dynamic, %.3fs total "
                    "(API: %.3fs, History: %.3fs [%d periphs, %d states], "
                    "Processing: %.3fs, Endpoints: %s)",
                    partial_dynamic_count,
                    total_time,
                    actual_api_time,
                    history_time,
                    self._last_history_periphs,
                    self._last_history_states,
                    processing_time_log,
                    endpoint_log,
                )
                # CAP-9: the cycle completed - record it in the metrics
                # buffer (passive, never blocks the return path).
                self._capture_cycle_metrics(total_time, actual_api_time)
                return ret

        except Exception as err:
            # 🚨 CHANGE: use monotonic() for the exact time elapsed before the error
            elapsed = time.monotonic() - start_monotonic

            # Handle timeout specifically - don't raise UpdateFailed for timeouts
            if "Request timed out" in str(err):
                _LOGGER.warning(
                    "⏳ Timeout occurred after %.3f seconds - using last known good data (size: %d)",
                    elapsed,
                    len(self.data) if hasattr(self, "data") and self.data else 0,
                )
                # Return last known good data if available
                if hasattr(self, "data") and self.data:
                    return self.data
                # If no data available, return empty success response
                return {"success": 1, "body": []}
            else:
                _LOGGER.exception(
                    "Error updating eedomus after %.3f seconds data: %s", elapsed, err
                )
                # Return last known good data if available
                # if hasattr(self, "data") and self.data:
                #    return self.data
                raise UpdateFailed(f"Error updating data: {err}") from err

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
            _LOGGER.error(
                "❌ This is a critical error - YAML configuration could not be loaded"
            )
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
        _LOGGER.error(
            "❌ This indicates get_yaml_config_sync() was called before initialization completed"
        )
        raise Exception(
            "YAML configuration not loaded - this is a bug in the initialization sequence"
        )

    async def _async_full_data_retreive(self):
        """Retrieve full data including peripherals list, value list, and characteristics."""
        from datetime import datetime

        # Track timing and data size for each endpoint
        start_time = datetime.now()
        peripherals_response = await self.client.get_periph_list()
        self._endpoint_timings["get_periph_list"] = (
            datetime.now() - start_time
        ).total_seconds()
        # Store data size in bytes (raw response size from client)
        self._endpoint_data_sizes["get_periph_list"] = peripherals_response.get(
            "_raw_data_size_bytes", 0
        )
        self._endpoint_call_counts["get_periph_list"] += 1

        start_time = datetime.now()
        peripherals_value_list_response = await self.client.get_periph_value_list("all")
        self._endpoint_timings["get_periph_value_list"] = (
            datetime.now() - start_time
        ).total_seconds()
        # Store data size in bytes (raw response size from client)
        self._endpoint_data_sizes["get_periph_value_list"] = (
            peripherals_value_list_response.get("_raw_data_size_bytes", 0)
        )
        self._endpoint_call_counts["get_periph_value_list"] += 1

        start_time = datetime.now()
        peripherals_caract_response = await self.client.get_periph_caract("all", True)
        self._endpoint_timings["get_periph_caract"] = (
            datetime.now() - start_time
        ).total_seconds()
        # Store data size in bytes (raw response size from client)
        self._endpoint_data_sizes["get_periph_caract"] = (
            peripherals_caract_response.get("_raw_data_size_bytes", 0)
        )
        self._endpoint_call_counts["get_periph_caract"] += 1

        _LOGGER.debug(
            "📊 Endpoint metrics - "
            "get_periph_list: %.3fs (%.1f KB), "
            "get_periph_value_list: %.3fs (%.1f KB), "
            "get_periph_caract: %.3fs (%.1f KB)",
            self._endpoint_timings["get_periph_list"],
            self._endpoint_data_sizes["get_periph_list"] / 1024,
            self._endpoint_timings["get_periph_value_list"],
            self._endpoint_data_sizes["get_periph_value_list"] / 1024,
            self._endpoint_timings["get_periph_caract"],
            self._endpoint_data_sizes["get_periph_caract"] / 1024,
        )
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

    """
    async def _async_full_refresh_data_retreive(self):
        " ""Retrieve only characteristics data for full refresh."" "
        peripherals_caract_response = await self.client.get_periph_caract("all", True)
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
        peripherals_caract = peripherals_caract_response.get("body", [])
        if not isinstance(peripherals_caract, list):
            _LOGGER.error("Invalid peripherals list: %s", peripherals_caract)
            peripherals_caract = []
        _LOGGER.debug(
            "Found %d peripherals characteristics in total", len(peripherals_caract)
        )
        return peripherals_caract

    """

    async def _async_full_refresh(self):
        """Perform a complete refresh of all peripherals."""
        _LOGGER.debug("Performing full data refresh from eedomus API")

        # Data retrieval - CORRECTED: now calls full data retrieve with all endpoints
        peripherals_caract = await self._async_full_data_retreive()

        # SAFE: Ensure peripherals_caract contains dictionaries with periph_id
        # URGENT FIX FOR CRITICAL BUG - 2026-02-23 16:50
        # Handle both flat and nested list structures
        peripherals_caract_dict = {}
        nested_structure_count = 0

        for it in peripherals_caract:
            if isinstance(it, dict) and "periph_id" in it:
                # Normal case: flat list of dicts
                peripherals_caract_dict[str(it["periph_id"])] = it
            elif isinstance(it, list):
                # Nested case: list of lists - flatten it
                nested_structure_count += 1
                for sub_item in it:
                    if isinstance(sub_item, dict) and "periph_id" in sub_item:
                        peripherals_caract_dict[str(sub_item["periph_id"])] = sub_item
                    else:
                        _LOGGER.error(
                            "❌ Invalid sub-item in nested structure: %s (type: %s)",
                            sub_item,
                            type(sub_item),
                        )
            else:
                _LOGGER.error(
                    "❌ CRITICAL BUG FIXED: Invalid peripheral data format: %s (type: %s)",
                    it,
                    type(it),
                )

        # Log nested structure count once instead of multiple times
        if nested_structure_count > 0:
            _LOGGER.debug(
                "🔍 Found %d nested structure(s) in peripherals_caract, flattened successfully",
                nested_structure_count,
            )

        # Initialize the aggregated dictionary
        aggregated_data = self.data

        # Aggregate the data for each peripheral
        all_periph_ids = set(peripherals_caract_dict.keys())

        for periph_id in all_periph_ids:
            if periph_id not in aggregated_data:
                _LOGGER.warning(
                    "This periph_id is unknown %d, please do a reload", periph_id
                )
                aggregated_data[periph_id] = {}

            # Add peripherals_caract_dict data (if present)
            if periph_id in peripherals_caract_dict:
                aggregated_data[periph_id].update(peripherals_caract_dict[periph_id])

        # Size logs
        _LOGGER.debug(
            "Data refresh summary - caract: %d, total: %d",
            len(peripherals_caract_dict),
            len(aggregated_data),
        )

        # Initialize attributes
        self._all_peripherals = aggregated_data
        self._dynamic_peripherals = {}
        self._backfill_eligible_peripherals = {}
        self._full_refresh_needed = False

        # Process the peripherals
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

            if self._is_backfill_eligible(periph_data):
                self._backfill_eligible_peripherals[periph_id] = periph_data

        _LOGGER.info(
            "📊 Device processing summary: %d total peripherals, %d dynamic, "
            "%d backfill-eligible, %d skipped, %d processed",
            len(aggregated_data),
            dynamic,
            len(self._backfill_eligible_peripherals),
            skipped,
            len(aggregated_data),
        )

        # Mapping table only displayed on initial startup, not on subsequent refreshes
        # This reduces log volume while maintaining useful startup information
        self.data = aggregated_data
        return aggregated_data

    async def _async_partial_refresh(self):
        """Perform a partial refresh of dynamic peripherals only.

        Updates only devices marked as dynamic (lights, switches, sensors that change frequently).
        More efficient than full refresh as it targets only devices that need frequent updates.
        """
        # AD-2 (story 1.4): the history drain lives in the background
        # worker; the refresh cycle only refreshes the dynamic periphs.
        peripherals_for_history = []
        for periph_id in self._dynamic_peripherals:
            peripherals_for_history.append(periph_id)

        _LOGGER.debug(
            "Performing partial refresh for %d dynamic peripherals",
            len(self._dynamic_peripherals),
        )

        # Start API timing
        api_start_time = datetime.now()

        # Reset history metrics for this cycle so early returns below do not
        # leak stale values from a previous cycle into the refresh log
        self._last_history_time = 0.0
        self._last_history_fetch_time = 0.0
        self._last_history_import_time = 0.0
        self._last_history_periphs = 0
        self._last_history_states = 0

        # Skip API call if no dynamic peripherals to refresh
        if not self._dynamic_peripherals:
            _LOGGER.warning(
                "No dynamic peripherals to refresh, skipping partial refresh"
            )
            # Return current data to preserve state instead of empty dict
            if hasattr(self, "data") and self.data:
                _LOGGER.info(
                    "Returning current data to preserve state during partial refresh"
                )
                return self.data
            else:
                _LOGGER.error("No data available to return during partial refresh")
                return {"success": 1, "body": []}

        concat_text_periph_id = ",".join(peripherals_for_history)
        try:
            # Track timing and data size for get_periph_caract (partial refresh)
            api_start_time = datetime.now()
            peripherals_caract = await self.client.get_periph_caract(
                concat_text_periph_id
            )
            self._endpoint_timings["get_periph_caract"] = (
                datetime.now() - api_start_time
            ).total_seconds()
            # Store data size in bytes (raw response size from client)
            self._endpoint_data_sizes["get_periph_caract"] = peripherals_caract.get(
                "_raw_data_size_bytes", 0
            )
            self._endpoint_call_counts["get_periph_caract"] += 1

            _LOGGER.debug(
                "📊 Partial refresh metrics - get_periph_caract: %.3fs (%d bytes)",
                self._endpoint_timings["get_periph_caract"],
                self._endpoint_data_sizes["get_periph_caract"],
            )
        except Exception as e:
            _LOGGER.warning(
                "Failed to partial refresh peripheral %s: %s", concat_text_periph_id, e
            )

        if not isinstance(peripherals_caract, dict):
            _LOGGER.warning("Failed to partial refresh %s", concat_text_periph_id)
            raise

        # Ensure peripherals_caract.get("body") is a list before iterating
        peripherals_body = peripherals_caract.get("body")
        if not isinstance(peripherals_body, list):
            _LOGGER.error(
                "peripherals_caract body is not a list: %s", type(peripherals_body)
            )
            if peripherals_body is None:
                _LOGGER.error(
                    "peripherals_caract body is None, API may have returned empty response"
                )
            # Return current data to preserve state instead of None
            if hasattr(self, "data") and self.data:
                _LOGGER.info(
                    "Returning current data to preserve state during partial refresh"
                )
                return self.data
            else:
                _LOGGER.error("No data available to return during partial refresh")
                return {"success": 1, "body": []}

        # End API timing, start processing timing
        api_time = (datetime.now() - api_start_time).total_seconds()
        processing_start_time = datetime.now()

        processed_devices = 0
        # History import metrics for this cycle (exposed in the refresh log)
        history_time = 0.0
        history_fetch_time = 0.0
        history_import_time = 0.0
        history_periphs = 0
        history_states = 0
        for periph_data in peripherals_body:
            periph_id = periph_data.get("periph_id")
            # Add peripherals_caract_dict data (if present)
            if self.data and periph_id in self.data:
                self.data[periph_id].update(periph_data)
                processed_devices += 1
            else:
                _LOGGER.warning(
                    "Cannot update peripheral data: data not available for %s",
                    periph_id,
                )

        # AD-2 (story 1.4): the history drain moved OUT of the refresh
        # cycle - the dedicated background worker (_async_backfill_worker)
        # owns it. The refresh cycle reports zero history metrics and
        # stays ~1 s even mid-backfill.

        # End processing timing
        processing_time = (datetime.now() - processing_start_time).total_seconds()

        # Store history timing metrics for the refresh log
        self._last_history_time = history_time
        self._last_history_fetch_time = history_fetch_time
        self._last_history_import_time = history_import_time
        self._last_history_periphs = history_periphs
        self._last_history_states = history_states
        if history_periphs:
            _LOGGER.debug(
                "History metrics: %.3fs for %d peripherals, %d states "
                "(fetch: %.3fs, import: %.3fs)",
                history_time,
                history_periphs,
                history_states,
                history_fetch_time,
                history_import_time,
            )

        # Store timing metrics for sensors
        self._last_api_time = api_time
        self._last_processing_time = processing_time
        self._last_refresh_time = api_time + processing_time
        self._last_processed_devices = processed_devices

        return self.data

    def _is_backfill_eligible(self, periph):
        """Determine if a peripheral is eligible for history backfill.

        AD-3: only peripherals mapped as a `sensor` entity with a
        numerically resolvable value (AD-6) produce statistics.
        Discrete states (light/switch/binary_sensor/cover/climate/
        select) are never backfilled; the "on time" need is served
        live through HA history_stats.
        """
        if not isinstance(periph, dict) or periph.get("ha_entity") != "sensor":
            return False
        # Numeric by declared type
        if periph.get("value_type") in ("float", "int", "integer"):
            return True
        # List-type peripherals: eligible when the merged value_list
        # carries at least one numeric value (AD-6 label resolution).
        for item in periph.get("values") or []:
            if isinstance(item, dict):
                try:
                    float(item.get("value"))
                    return True
                except (ValueError, TypeError):
                    continue
        return False

    def _is_dynamic_peripheral(self, periph):
        """Determine if a peripheral needs regular updates."""
        ha_entity = periph.get("ha_entity")
        entity_specifics = periph.get("entity_specifics", {})

        dynamic_types = [
            "light",
            "switch",
            "binary_sensor",
            "number",
            "cover",
            "climate",
            "select",
        ]

        if ha_entity in dynamic_types:
            _LOGGER.debug(
                "Peripheral is dynamic ! %s (%s)",
                periph.get("name"),
                periph.get("periph_id"),
            )
            return True

        # Check if it's a sensor with dynamic value mapping
        if (
            ha_entity == "sensor"
            and entity_specifics.get("value_mapping") == "dynamic_from_values"
        ):
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

    def _parse_box_system_value(self, value) -> float | None:
        """Tolerantly parse a box system periph value (CAP-9).

        The box reports its CPU and free storage as ordinary periphs;
        an unparseable state is a None sample, never an exception.
        """
        try:
            return round(float(value), 2)
        except (ValueError, TypeError):
            return None

    def _sample_box_system_periphs(self) -> tuple[float | None, float | None]:
        """Sample the box's own system periphs (usage 23, CAP-9).

        The eedomus box exposes its CPU and free storage as regular
        periphs (usage 23) — no scraping, the ordinary cached data is
        the source. A box without them samples (None, None) and the
        panel hides the system card.
        """
        cpu = None
        free_space_kb = None
        for periph in (self.data or {}).values():
            if not isinstance(periph, dict) or periph.get("usage_id") != "23":
                continue
            name = str(periph.get("name") or "")
            if "CPU" in name and cpu is None:
                cpu = self._parse_box_system_value(periph.get("last_value"))
            elif "Espace libre" in name and free_space_kb is None:
                free_space_kb = self._parse_box_system_value(
                    periph.get("last_value")
                )
        return cpu, free_space_kb

    def _count_active_periphs_last_hour(self) -> int:
        """Count periphs whose value changed within the last hour.

        Read from the cached last_value_change (naive local text); an
        unparseable or missing date never counts and never raises.
        """
        cutoff = datetime.now() - timedelta(hours=1)
        active = 0
        for periph in (self.data or {}).values():
            if not isinstance(periph, dict):
                continue
            changed = periph.get("last_value_change")
            if not isinstance(changed, str) or not changed:
                continue
            try:
                moment = datetime.strptime(changed[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if moment >= cutoff:
                active += 1
        return active

    def _count_periphs_by_category(self) -> dict[str, int]:
        """Count peripherals per mapped entity type (CAP-9).

        Unmapped periphs are counted under "unmapped" so the chip row
        accounts for the whole box.
        """
        counts: dict[str, int] = {}
        for periph in (self.data or {}).values():
            if not isinstance(periph, dict):
                continue
            ha_entity = periph.get("ha_entity") or "unmapped"
            counts[ha_entity] = counts.get(ha_entity, 0) + 1
        return counts

    def _capture_cycle_metrics(self, refresh_time: float, api_time: float) -> None:
        """Record one refresh cycle into the circular metrics buffer.

        Purely passive (CAP-9, AD-2): any failure is logged as a warning
        and swallowed - the refresh flow never depends on the metrics.
        The cycle carries the total and API durations, the API call
        delta against the cycle baseline (the cumulative endpoint
        counters are never reset, only incremented), the total and
        dynamic peripheral counts, and the box's own system samples
        (CPU / free space, usage 23 — None when the box has no such
        periph). Only the success paths call this - a timed-out cycle
        is not a completed cycle and records nothing.
        """
        try:
            baseline = self._metrics_cycle_start_calls
            current = sum(self._endpoint_call_counts.values())
            if baseline is None or current < baseline:
                # No usable baseline (guarded read failed, or the
                # counters moved below it): record no call count at
                # all - never the unbounded cumulative total.
                api_calls = 0
            else:
                api_calls = current - baseline
            cpu, free_space_kb = self._sample_box_system_periphs()
            self._metrics_history.append(
                {
                    "ts": dt_util.utcnow().isoformat(),
                    "refresh_time": round(float(refresh_time), 3),
                    "api_time": round(float(api_time), 3),
                    "api_calls": api_calls,
                    "periphs_total": len(self._all_peripherals or {}),
                    "periphs_dynamic": len(self._dynamic_peripherals or {}),
                    "cpu": cpu,
                    "free_space_kb": free_space_kb,
                }
            )
        except Exception as err:
            _LOGGER.warning("Failed to capture the box metrics cycle: %s", err)

    def get_box_metrics(self) -> dict[str, Any]:
        """Return the buffered refresh cycles of this box (CAP-9).

        Feeds eedomus/get_box_metrics (Supervision tab): the time series
        lives nowhere else - the timing sensors only expose the last
        cycle's scalars, and every value the panel's cards render comes
        from the cycle records themselves, so the payload stops there.
        The snapshot fields (activity gauge and category counts) come
        from the same cache - one visit, one payload, no subscription.
        One box = one coordinator: entry_id and display name ride along
        so the panel can section multi-box setups. The websocket handler
        runs the payload through _json_safe.
        """
        return {
            "entry_id": self._backfill_entry_id(),
            "name": self._box_display_name(),
            "cycles": list(self._metrics_history),
            "active_periphs_last_hour": self._count_active_periphs_last_hour(),
            "periphs_by_category": self._count_periphs_by_category(),
        }

    def _box_display_name(self) -> str | None:
        """Resolve a human-readable box name (best effort, CAP-9).

        The config entry title first (the user-named box), then the
        client api_host (the configured box address); None when
        neither resolves - the panel then falls back to the entry_id.
        """
        for candidate in (
            getattr(self, "config_entry", None),
            getattr(self.client, "config_entry", None),
        ):
            title = getattr(candidate, "title", None)
            if isinstance(title, str) and title:
                return title
        for host_attr in ("api_host", "host"):
            host = getattr(self.client, host_attr, None)
            if isinstance(host, str) and host:
                return host
        return None

    """
    async def request_full_refresh(self):
        " ""Request a full refresh of all peripherals."" "
        _LOGGER.debug("Requesting full data refresh")
        self._full_refresh_needed = True
        await self.async_request_refresh()

    """

    def _history_enabled(self) -> bool:
        """Whether the history option is on (options > data > default)."""
        return bool(
            _get_config_value(self.client.config_entry, CONF_ENABLE_HISTORY, False)
        )

    def _ensure_backfill_worker(self):
        """Start the AD-2 background drain worker (idempotent).

        A MagicMock hass in tests absorbs the call; in HA the task is
        tracked for the unload shutdown. The worker owns the whole
        history drain - the refresh cycles never touch it again.
        """
        if self._backfill_worker_task is not None and not (
            getattr(self._backfill_worker_task, "done", lambda: True)()
        ):
            return
        create = getattr(self.hass, "async_create_task", None)
        if create is None:
            return
        self._backfill_worker_task = create(self._async_backfill_worker())

    async def async_shutdown_backfill(self):
        """Unload = await + flush (AD-2): cancel the worker, wait for it,
        flush the persisted progress to .storage."""
        task = self._backfill_worker_task
        self._backfill_worker_task = None
        if task is not None:
            cancel = getattr(task, "cancel", None)
            if callable(cancel):
                cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        await self._save_backfill_persistence()

    async def _async_backfill_worker(self):
        """AD-2: the history drain as a dedicated background task.

        One pass every BACKFILL_WORKER_INTERVAL seconds; each pass
        drains at most history_peripherals_per_scan peripherals under
        the mono-importer lock. A global pause skips the pass without
        consuming the quota; any pass failure is logged and the worker
        keeps running - the backfill never takes the integration down.
        """
        while True:
            await asyncio.sleep(BACKFILL_WORKER_INTERVAL)
            try:
                await self._backfill_drain_pass()
            except asyncio.CancelledError:
                raise
            except Exception as err:
                _LOGGER.warning("Backfill worker pass failed: %s", err)

    async def _backfill_drain_pass(self):
        """One drain pass (CAP-5 queue, AD-2 cadence).

        Same contract as the old in-cycle segment: priority jumps
        consumed at the head, the active marker covers the fetch, the
        quota counts periphs (a no-data fetch consumed its slot), the
        mono-importer lock serializes with retry_now.
        """
        if not self._history_enabled():
            return
        if self._backfill_global_paused:
            return
        if self._backfill_import_lock.locked():
            return
        quota = int(
            _get_config_value(
                self.client.config_entry,
                CONF_HISTORY_PERIPHERALS_PER_SCAN,
                DEFAULT_HISTORY_PERIPHERALS_PER_SCAN,
            )
            or 0
        )
        if quota <= 0:
            return
        history_queue = self._backfill_queue_ids()
        if not history_queue:
            return
        async with self._backfill_import_lock:
            for periph_id in history_queue:
                if quota <= 0:
                    break
                _LOGGER.debug("Worker retrieving history for %s", periph_id)
                if periph_id in self._backfill_priority:
                    self._backfill_priority.remove(periph_id)
                self._backfill_active_periph = periph_id
                try:
                    chunk = await self.async_fetch_history_chunk(periph_id)
                    if chunk:
                        await self.async_import_history_chunk(periph_id, chunk)
                finally:
                    self._backfill_active_periph = None
                quota -= 1

    async def _load_history_progress(self):
        """One-time migration: read progress from the legacy helper states.

        Story 1.4: the progress itself now lives in .storage (the
        backfill document, keyed "<entry_id>_<periph_id>"). The old
        eedomus.history_progress_* helper states are read once, when the
        stored document carries no progress yet; afterwards the states
        are never written again and die at the next restart.
        """
        _LOGGER.debug("Checking legacy history progress states")

        try:
            if progress := await self.hass.async_add_executor_job(
                lambda: self.hass.states.async_all(f"{DOMAIN}.history_progress_*")
            ):
                for state in progress:
                    periph_id = state.entity_id.split("_")[-1]
                    try:
                        last_timestamp = int(float(state.state))
                    except (ValueError, TypeError):
                        continue
                    self._history_progress[periph_id] = {
                        "last_timestamp": last_timestamp,
                        "completed": state.attributes.get("completed", False),
                    }
                    _LOGGER.debug(
                        "Migrated legacy progress for %s: %s",
                        periph_id,
                        self._history_progress[periph_id],
                    )
        except Exception as e:
            _LOGGER.warning(
                "Warning loading legacy history progress "
                "(this is normal if no history data exists): %s",
                e,
            )

    async def _save_history_progress(self):
        """Persist the history progress into the backfill .storage doc.

        Story 1.4: no state-machine writes - the entries are keyed
        "<entry_id>_<periph_id>" in the document's progress map
        (spec-eedomus-history constraint), and the real History Progress
        entities (bug 109) read the in-memory dict the same way.
        """
        await self._save_backfill_persistence()

    # ------------------------------------------------------------------
    # CAP-5: backfill queue control API (steering of the history queue)
    # ------------------------------------------------------------------

    def _backfill_queue_ids(self, for_drain: bool = True) -> list[str]:
        """Derive the ordered backfill queue (CAP-5).

        The queue is never stored: it is _history_progress (non completed
        peripherals) projected onto the natural drain order
        (_backfill_eligible_peripherals — AD-3: sensor entities with a
        numerically resolvable value, discrete states excluded). The
        priority list jumps its entries to the head; ignored periphs
        are out of the queue entirely. The drain view also drops
        paused periphs, while the state view keeps them (the panel
        must render them as paused, position included).
        """
        pending: list[str] = []
        for periph_id in self._backfill_eligible_peripherals:
            if periph_id in self._backfill_ignored:
                continue
            if for_drain and periph_id in self._backfill_paused:
                continue
            if self._history_progress.get(periph_id, {}).get("completed"):
                continue
            pending.append(periph_id)
        priority = [p for p in self._backfill_priority if p in pending]
        if not priority:
            return pending
        priority_set = set(priority)
        return priority + [p for p in pending if p not in priority_set]

    def get_backfill_state(self) -> dict[str, Any]:
        """Return the derived backfill queue state (CAP-5).

        One row per pending peripheral (periph_id, name, entry_id,
        status, 1-based position, error_message, retry_after, attempts),
        the ignored periphs listed separately, and the global engine
        state (global_paused, engine_active). Datetimes are
        timezone-aware; the websocket handler runs the payload through
        _json_safe.
        """
        now = dt_util.utcnow().timestamp()
        entry_id = self._backfill_entry_id()
        queue: list[dict[str, Any]] = []
        for position, periph_id in enumerate(
            self._backfill_queue_ids(for_drain=False), start=1
        ):
            retry_info = self._retry_queue.get(periph_id)
            has_error = isinstance(retry_info, dict)
            in_error = has_error and now < retry_info.get("retry_after", 0)
            # Status precedence: prioritized > in_progress > error >
            # paused > pending (CAP-5 I/O matrix).
            if periph_id in self._backfill_priority:
                status = "priority"
            elif periph_id == self._backfill_active_periph:
                status = "in_progress"
            elif in_error:
                status = "error"
            elif periph_id in self._backfill_paused:
                status = "paused"
            else:
                status = "pending"
            # The failure history stays on the row after the retry window
            # elapses (the status degrades to pending): the panel needs
            # the reason exactly when the periph becomes actionable
            # again.
            retry_after = retry_info.get("retry_after") if has_error else None
            if retry_after is not None:
                retry_after = dt_util.as_local(dt_util.utc_from_timestamp(retry_after))
            progress = self._history_progress.get(periph_id, {})
            oldest = progress.get("oldest_timestamp")
            if oldest is not None:
                oldest = dt_util.as_local(dt_util.utc_from_timestamp(oldest))
            queue.append(
                {
                    "periph_id": periph_id,
                    "name": (self.data or {}).get(periph_id, {}).get("name"),
                    "entry_id": entry_id,
                    "status": status,
                    "position": position,
                    "error_message": (
                        retry_info.get("error_message") if has_error else None
                    ),
                    "retry_after": retry_after,
                    "attempts": retry_info.get("attempts") if has_error else None,
                    # CAP-5 progress fields (story 1.4): retrieved points
                    # (real), total (ESTIMATED when estimated is True),
                    # oldest timestamp retrieved, retention start.
                    "retrieved_points": progress.get("retrieved_points", 0),
                    "total_points": progress.get("total_points"),
                    "estimated": progress.get("estimated", False),
                    "oldest_timestamp": oldest,
                    "retention_start": progress.get("retention_start"),
                }
            )
        ignored = [
            {
                "periph_id": periph_id,
                "name": (self.data or {}).get(periph_id, {}).get("name"),
                "entry_id": entry_id,
            }
            for periph_id in sorted(self._backfill_ignored)
        ]
        return {
            "queue": queue,
            "ignored": ignored,
            "global_paused": self._backfill_global_paused,
            "engine_active": (
                self._backfill_active_periph is not None
                or self._backfill_import_lock.locked()
            ),
        }

    def _backfill_row(self, periph_id: str) -> dict[str, Any] | None:
        """Return the periph's derived queue row, None when not queued."""
        for row in self.get_backfill_state()["queue"]:
            if row["periph_id"] == periph_id:
                return row
        return None

    def _backfill_entry_id(self) -> str | None:
        """Resolve the config entry id backing this coordinator.

        The config_entry attribute may live on the coordinator (HA
        DataUpdateCoordinator) or on the client (fallback for stripped
        down instances); None disables the persistence.
        """
        for candidate in (
            getattr(self, "config_entry", None),
            getattr(self.client, "config_entry", None),
        ):
            entry_id = getattr(candidate, "entry_id", None)
            if entry_id:
                return str(entry_id)
        return None

    def _get_backfill_store(self) -> Store | None:
        """Get the per-config-entry backfill store (lazy).

        Key f"{DOMAIN}.backfill_{entry_id}" - the first .storage surface
        of the backfill; the PROGRESS itself stays in hass.states.
        """
        if self._backfill_store is None:
            entry_id = self._backfill_entry_id()
            if not entry_id:
                return None
            self._backfill_store = Store(
                self.hass,
                BACKFILL_CONFIG_SCHEMA_VERSION,
                f"{DOMAIN}.backfill_{entry_id}",
            )
        return self._backfill_store

    async def _load_backfill_persistence(self) -> None:
        """Load the backfill control state from .storage (CAP-5).

        Calqued on the mapping store: a stored document without
        config_schema_version is the birth version (stamped, never
        migrated); a stored version below the current one runs the
        ordered migrations. An empty or missing store leaves the
        in-memory sets empty and the global pause off.
        """
        store = self._get_backfill_store()
        if store is None:
            return
        try:
            data = await store.async_load() or {}
            version = data.get("config_schema_version")
            if version is not None and version > BACKFILL_CONFIG_SCHEMA_VERSION:
                # A document written by a newer integration must not be
                # loaded unvalidated: start from an empty control state.
                _LOGGER.warning(
                    "Backfill control state schema v%s is newer than the "
                    "supported v%s - starting from an empty control state",
                    version,
                    BACKFILL_CONFIG_SCHEMA_VERSION,
                )
                self._backfill_ignored = set()
                self._backfill_paused = set()
                self._backfill_global_paused = False
                return
            if data and version is None:
                # Birth version: stamp it, nothing to migrate.
                data = {**data, "config_schema_version": BACKFILL_CONFIG_SCHEMA_VERSION}
                await store.async_save(data)
            elif version is not None and version < BACKFILL_CONFIG_SCHEMA_VERSION:
                migrated = dict(data)
                for target in sorted(_BACKFILL_MIGRATIONS):
                    if version < target <= BACKFILL_CONFIG_SCHEMA_VERSION:
                        migrated = _BACKFILL_MIGRATIONS[target](migrated)
                        version = target
                await store.async_save(migrated)
                data = migrated
            self._backfill_ignored = set(data.get("ignored") or [])
            self._backfill_paused = set(data.get("paused") or [])
            self._backfill_global_paused = bool(data.get("global_paused", False))
            # v2 (story 1.4): the per-periph progress + retry queue ride
            # in the same document. Stored progress wins; an empty
            # stored map keeps whatever the one-time legacy-state
            # migration read (it gets persisted right after).
            stored_progress = data.get("progress") or {}
            if stored_progress:
                prefix = f"{self._backfill_entry_id()}_"
                self._history_progress = {
                    key.removeprefix(prefix): dict(value)
                    for key, value in stored_progress.items()
                }
            elif self._history_progress:
                _LOGGER.info(
                    "Migrating %d legacy history progress entries "
                    "from the state machine to .storage",
                    len(self._history_progress),
                )
                await self._save_backfill_persistence()
            stored_retry = data.get("retry") or {}
            if isinstance(stored_retry, dict):
                self._retry_queue = {
                    key: dict(value) for key, value in stored_retry.items()
                }
        except Exception as e:
            # A broken store never blocks the coordinator: the control
            # state starts empty (worst case, periphs are re-ignored).
            _LOGGER.warning("Failed to load the backfill control state: %s", e)

    async def _save_backfill_persistence(self) -> None:
        """Persist the backfill document to .storage (CAP-5 + story 1.4).

        One document per config entry: the control state (ignored /
        paused / global pause) and, since v2, the per-periph history
        progress (keyed "<entry_id>_<periph_id>") and the retry queue.
        """
        store = self._get_backfill_store()
        if store is None:
            return
        try:
            prefix = f"{self._backfill_entry_id()}_"
            progress_doc = {
                f"{prefix}{periph_id}": dict(progress)
                for periph_id, progress in self._history_progress.items()
            }
            retry_doc = {
                periph_id: dict(retry)
                for periph_id, retry in self._retry_queue.items()
            }
            await store.async_save(
                {
                    "ignored": sorted(self._backfill_ignored),
                    "paused": sorted(self._backfill_paused),
                    "global_paused": self._backfill_global_paused,
                    "progress": progress_doc,
                    "retry": retry_doc,
                    "config_schema_version": BACKFILL_CONFIG_SCHEMA_VERSION,
                }
            )
        except Exception as e:
            _LOGGER.warning("Failed to persist the backfill state: %s", e)

    async def async_backfill_retry_now(self, periph_id: str) -> dict[str, Any]:
        """Retry a peripheral in error immediately, off-schedule (CAP-5).

        The retry queue entry is purged and fetch+import run at once under
        the mono-importer lock. A busy lock is a nominal refusal (no
        waiting); an unknown, completed, ignored or paused periph is
        refused as invalid_format. The result carries the periph's FRESH
        status after the retry: a re-failed fetch reports status "error"
        with its new error_message/retry_after instead of masquerading
        as a productive retry.

        Returns:
            A nominal result dict (periph_id, imported, fresh status).
        """
        if periph_id not in (self.data or {}):
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID, f"Unknown peripheral {periph_id}"
            )
        if periph_id not in self._backfill_eligible_peripherals:
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID,
                f"Peripheral {periph_id} is not eligible for history "
                "backfill (AD-3: numeric sensors only)",
            )
        if self._history_progress.get(periph_id, {}).get("completed"):
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID,
                f"History already fully imported for {periph_id}",
            )
        if periph_id in self._backfill_ignored:
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID, f"Peripheral {periph_id} is ignored"
            )
        if periph_id in self._backfill_paused:
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID, f"Peripheral {periph_id} is paused"
            )
        if self._backfill_import_lock.locked():
            raise EedomusBackfillError(
                BACKFILL_ERROR_BUSY, "A history import is already in progress"
            )
        async with self._backfill_import_lock:
            # Off-schedule retry: the retry window no longer applies.
            self._retry_queue.pop(periph_id, None)
            # The active marker covers the fetch too (a long fetch is
            # an in-progress import from the panel's point of view).
            self._backfill_active_periph = periph_id
            try:
                chunk = await self.async_fetch_history_chunk(periph_id)
                imported = 0
                if chunk:
                    imported = await self.async_import_history_chunk(periph_id, chunk)
            finally:
                self._backfill_active_periph = None
        # Outcome honesty: derive the fresh status. A re-failed fetch put
        # the periph back in the retry queue - report it instead of a
        # bare imported=0 that reads like a productive retry.
        row = self._backfill_row(periph_id)
        if row is not None:
            status = row["status"]
        elif self._history_progress.get(periph_id, {}).get("completed"):
            # The retry closed the periph: it left the queue completed.
            status = "completed"
        else:
            status = "pending"
        result: dict[str, Any] = {
            "success": True,
            "periph_id": periph_id,
            "imported": imported,
            "status": status,
        }
        if status == "error":
            result["error_message"] = row["error_message"]
            result["retry_after"] = row["retry_after"]
        return result

    async def async_backfill_prioritize(self, periph_id: str) -> dict[str, Any]:
        """Move a peripheral to the head of the queue (CAP-5).

        The priority list is consumed by the next drain, before the
        natural order; it is ephemeral (never persisted). Completed and
        ignored periphs are refused - a priority entry for them would
        never drain and linger forever. Paused periphs stay
        prioritizable: a pause is temporary, the jump outlives it.
        """
        if periph_id not in (self.data or {}):
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID, f"Unknown peripheral {periph_id}"
            )
        if periph_id not in self._backfill_eligible_peripherals:
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID,
                f"Peripheral {periph_id} is not eligible for history "
                "backfill (AD-3: numeric sensors only)",
            )
        if self._history_progress.get(periph_id, {}).get("completed"):
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID,
                f"History already fully imported for {periph_id}",
            )
        if periph_id in self._backfill_ignored:
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID, f"Peripheral {periph_id} is ignored"
            )
        if periph_id not in self._backfill_priority:
            self._backfill_priority.append(periph_id)
        return {"success": True, "periph_id": periph_id, "prioritized": True}

    async def async_backfill_reset_progress(self, periph_id: str) -> dict[str, Any]:
        """Clear one periph's persisted progress marker (CAP-5, 5th action).

        The marker only: the imported statistics are NEVER deleted (the
        re-import is an idempotent upsert, CAP-3). The periph re-enters
        the queue at zero - the test protocol's reset step (spec
        decision 2026-10-08). Ignored periphs are refused (reactivate
        first); unknown and ineligible periphs are refused as
        invalid_format. A paused periph stays paused - a pause is
        temporary and outlives the reset.
        """
        if periph_id not in (self.data or {}):
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID, f"Unknown peripheral {periph_id}"
            )
        if periph_id not in self._backfill_eligible_peripherals:
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID,
                f"Peripheral {periph_id} is not eligible for history "
                "backfill (AD-3: numeric sensors only)",
            )
        if periph_id in self._backfill_ignored:
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID, f"Peripheral {periph_id} is ignored"
            )
        self._history_progress.pop(periph_id, None)
        self._retry_queue.pop(periph_id, None)
        self._error_count.pop(periph_id, None)
        await self._save_backfill_persistence()
        row = self._backfill_row(periph_id)
        return {
            "success": True,
            "periph_id": periph_id,
            "reset": True,
            "status": row["status"] if row is not None else "pending",
            "state": self.get_backfill_state(),
        }

    async def async_backfill_set_paused(
        self,
        periph_id: str | None = None,
        global_pause: bool = False,
        paused: bool = True,
    ) -> dict[str, Any]:
        """Pause or resume one peripheral, or the global engine (CAP-5).

        The pause only steers the drain (the periph stays in the queue
        with a paused status; the global pause skips the whole history
        segment). Both states persist in .storage and survive a
        re-instantiation; resuming restores the drain untouched.
        """
        if global_pause:
            self._backfill_global_paused = bool(paused)
            await self._save_backfill_persistence()
            return {"success": True, "global_paused": self._backfill_global_paused}
        if periph_id is None:
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID, "periph_id or global is required"
            )
        if periph_id not in (self.data or {}):
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID, f"Unknown peripheral {periph_id}"
            )
        if paused:
            self._backfill_paused.add(periph_id)
        else:
            self._backfill_paused.discard(periph_id)
        await self._save_backfill_persistence()
        return {"success": True, "periph_id": periph_id, "paused": bool(paused)}

    async def async_backfill_set_ignored(
        self, periph_id: str, ignored: bool = True
    ) -> dict[str, Any]:
        """Ignore (or re-activate) a peripheral in the queue (CAP-5).

        Ignoring is not destructive: the periph quits the queue but its
        history progress is kept, so ignored=False re-activates it where
        it was. The state persists in .storage across restarts.
        """
        if periph_id not in (self.data or {}):
            raise EedomusBackfillError(
                BACKFILL_ERROR_INVALID, f"Unknown peripheral {periph_id}"
            )
        if ignored:
            self._backfill_ignored.add(periph_id)
            # Out of the queue: its priority jump, if any, is void.
            if periph_id in self._backfill_priority:
                self._backfill_priority.remove(periph_id)
        else:
            self._backfill_ignored.discard(periph_id)
        await self._save_backfill_persistence()
        return {"success": True, "periph_id": periph_id, "ignored": bool(ignored)}

    def _validate_history_data(self, chunk: list) -> bool:
        """Validate the received history data."""
        if not isinstance(chunk, list):
            return False

        for entry in chunk:
            if not isinstance(entry, dict):
                return False
            if "timestamp" not in entry or "value" not in entry:
                return False
            # Check that the timestamp is valid
            try:
                datetime.fromisoformat(entry["timestamp"])
            except ValueError:
                return False

        return True

    def _handle_fetch_error(self, periph_id, error_message):
        """Handle history retrieval errors."""
        now = datetime.now().timestamp()

        # Initialize on the first error
        if periph_id not in self._error_count:
            self._error_count[periph_id] = 0

        self._error_count[periph_id] += 1

        # On the first error, pause for the configured duration
        if self._error_count[periph_id] == 1:
            # Get the retry duration from the configuration
            retry_delay_hours = self.config_entry.options.get(
                CONF_HISTORY_RETRY_DELAY, DEFAULT_HISTORY_RETRY_DELAY
            )
            retry_delay = retry_delay_hours * 3600
            retry_after = now + retry_delay
            self._retry_queue[periph_id] = {
                "error_time": now,
                "retry_after": retry_after,
                "error_message": error_message,
                "attempts": 1,
            }
            _LOGGER.error(
                f"❌ Error retrieving history for {periph_id}: {error_message}"
            )
            _LOGGER.error(f"   Retry in {retry_delay_hours} hours")
        else:
            # Update the error counter
            if periph_id in self._retry_queue:
                self._retry_queue[periph_id]["attempts"] += 1

    def _estimate_total_points(self, periph_data: dict) -> tuple[int | None, str | None]:
        """CAP-5: estimate the total history points (marked ESTIMATED).

        Window = now - creation_date (the periph's data availability),
        density = 1/POLLING (the periph's declared polling seconds) -
        both from the cached caract payload. Missing or unparseable
        inputs give (None, None): the UI then shows what it has.
        """
        try:
            created = datetime.strptime(
                str(periph_data.get("creation_date")), "%Y-%m-%d %H:%M:%S"
            )
            polling = int(periph_data.get("POLLING"))
            if polling <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return None, None
        retention_start = periph_data.get("creation_date")
        total = int((datetime.now() - created).total_seconds() / polling)
        return max(total, 0), retention_start

    def _value_list_fingerprint(self, periph_data: dict) -> str | None:
        """AD-6bis: freeze the value_list at the fetch of the chunk.

        A stable JSON dump of the merged values list; None for periphs
        without one (nothing to freeze, nothing to invalidate).
        """
        values = periph_data.get("values")
        if not values:
            return None
        try:
            return json.dumps(values, sort_keys=True, default=str)
        except (TypeError, ValueError):
            return None

    async def async_fetch_history_chunk(self, periph_id: str) -> list:
        """Fetch a chunk of 10,000 history data points."""
        # Check whether the peripheral is in the retry queue
        if periph_id in self._retry_queue:
            retry_info = self._retry_queue[periph_id]
            if datetime.now().timestamp() < retry_info["retry_after"]:
                _LOGGER.debug(
                    f"Skipping {periph_id} - in retry queue until {retry_info['retry_after']}"
                )
                return []

        if periph_id not in self._history_progress:
            periph_data = (self.data or {}).get(periph_id, {})
            total_points, retention_start = self._estimate_total_points(
                periph_data
            )
            self._history_progress[periph_id] = {
                "last_timestamp": 0,
                "completed": False,
                # CAP-5 progress fields (story 1.4)
                "retrieved_points": 0,
                "total_points": total_points,
                "estimated": total_points is not None,
                "oldest_timestamp": None,
                "retention_start": retention_start,
                # AD-6bis: the value_list frozen at the first fetch
                "value_list_fingerprint": self._value_list_fingerprint(
                    periph_data
                ),
            }

        progress = self._history_progress[periph_id]

        # AD-6bis: a value_list variation invalidates the periph's
        # progress - the imported statistics would silently change
        # meaning. The periph re-enters the queue at zero.
        current_fingerprint = self._value_list_fingerprint(
            (self.data or {}).get(periph_id, {})
        )
        frozen = progress.get("value_list_fingerprint")
        if (
            frozen is not None
            and current_fingerprint is not None
            and frozen != current_fingerprint
        ):
            _LOGGER.warning(
                "value_list changed for %s: history progress invalidated",
                periph_id,
            )
            self._history_progress[periph_id] = {
                "last_timestamp": 0,
                "completed": False,
                "retrieved_points": 0,
                "total_points": progress.get("total_points"),
                "estimated": progress.get("estimated", False),
                "oldest_timestamp": None,
                "retention_start": progress.get("retention_start"),
                "value_list_fingerprint": current_fingerprint,
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

            # Validate the received data
            if not self._validate_history_data(chunk):
                _LOGGER.error(f"❌ Invalid history data for {periph_id}")
                self._handle_fetch_error(periph_id, "Invalid data format")
                return []

            # Historical data points are imported via the Statistics API
            # (async_import_history_chunk). Replaying them as states
            # flooded the recorder with backdated writes that never
            # committed ("database is locked").
            timestamps = [
                int(datetime.fromisoformat(entry["timestamp"]).timestamp())
                for entry in chunk
            ]
            # Bug 1.10 — dead-window completion: the eedomus cloud
            # returns the newest 10,000 points whatever the window, so
            # a periph that reached the present gets the SAME full
            # chunk every pass (max frozen at the cloud's latest
            # point) and would loop forever on the len < 10000 test
            # alone. A max that no longer advances past the previous
            # last_timestamp means the walk holds the newest window
            # the cloud has: the periph is done.
            stale_window = (
                progress["last_timestamp"] > 0
                and max(timestamps) <= progress["last_timestamp"]
            )
            if len(chunk) < 10000 or stale_window:
                progress["completed"] = True
                _LOGGER.info(
                    "History fully fetched for %s (%s) (received %d entries%s)",
                    periph_id,
                    (
                        self.data[periph_id]["name"]
                        if periph_id in self.data
                        else "Unknown"
                    ),
                    len(chunk),
                    ", dead window" if stale_window else "",
                )
            progress["last_timestamp"] = max(timestamps)
            # CAP-5 (story 1.4): the cumulative point count and the
            # oldest timestamp retrieved so far.
            progress["retrieved_points"] = (
                progress.get("retrieved_points", 0) + len(chunk)
            )
            oldest = min(timestamps)
            if progress.get("oldest_timestamp") is None or (
                oldest < progress["oldest_timestamp"]
            ):
                progress["oldest_timestamp"] = oldest
            _LOGGER.debug(
                "Updated last_timestamp for %s to %s",
                periph_id,
                progress["last_timestamp"],
            )

            await self._save_history_progress()
            return chunk

        except Exception as e:
            _LOGGER.error(
                f"❌ Error retrieving history for {periph_id}: {e}"
            )
            self._handle_fetch_error(periph_id, str(e))
            return []

    async def async_import_history_chunk(
        self, periph_id: str, chunk: list, main_entity_id: str = None
    ) -> int:
        """Import historical data via the recorder Statistics API.

        A failed statistics import is logged as a warning and skipped:
        backdated data points must never be written to the state machine,
        as replaying them floods the recorder with writes that never
        commit ("database is locked").

        Returns:
            The number of hourly statistics actually imported (0 when
            skipped or on failure).
        """
        if not chunk:
            _LOGGER.debug("No history data to import for %s", periph_id)
            return 0

        periph_data = self.data.get(periph_id, {})
        periph_name = periph_data.get("name", f"Device {periph_id}")
        # Prefer the explicitly provided entity, then the peripheral's real
        # registered entity (exact registry match only, AD-8bis). The ghost
        # sensor.eedomus_<periph_id> fallback is gone: a statistics target
        # that is not a real entity would create orphan long-term statistics.
        entity_id = main_entity_id or self._resolve_main_entity_id(
            periph_id, allow_suffixed=False
        )
        if not entity_id:
            # Bug 1.11: a resolution miss means the fetched chunk has no
            # importable target. A couple of misses are tolerated
            # (registry timing at startup); a persistent miss removes
            # the periph from the queue — the fetch would otherwise
            # burn every chunk for nothing, losing the points silently.
            misses = self._import_miss_count.get(periph_id, 0) + 1
            self._import_miss_count[periph_id] = misses
            if misses >= 3:
                self._history_progress.pop(periph_id, None)
                self._import_miss_count.pop(periph_id, None)
                await self._save_history_progress()
                _LOGGER.warning(
                    "Removing %s (%s) from the history queue: no exact "
                    "entity match in the entity registry after %d "
                    "attempts (fix the mapping, then reset its progress)",
                    periph_id,
                    periph_name,
                    misses,
                )
            else:
                _LOGGER.warning(
                    "Skipping history import for %s: no exact entity "
                    "match in the entity registry",
                    periph_id,
                )
            return 0

        # A resolved target resets the miss streak
        self._import_miss_count.pop(periph_id, None)

        _LOGGER.info("Importing historical data using Statistics API for %s", entity_id)

        try:
            imported = await self._import_via_statistics(
                entity_id, chunk, periph_name, periph_id
            )
            _LOGGER.info(
                "Successfully imported %d historical statistics for %s",
                imported,
                entity_id,
            )
            return imported

        except Exception as err:
            # Skip, never fall back to writing historical states
            _LOGGER.warning(
                "Statistics import failed for %s: skipping %d history points: %s",
                entity_id,
                len(chunk),
                err,
            )
            return 0

    def _resolve_main_entity_id(
        self, periph_id: str, allow_suffixed: bool = True
    ) -> str | None:
        """Resolve the peripheral's real HA entity_id via the entity registry.

        Eedomus entities use the unique_id "<entry_id>_<periph_id>"
        (see EedomusEntity). Some variants add a suffix
        (e.g. "_select"); the main entity is the exact match.
        Statistics targets require an exact match (AD-8bis):
        their resolution passes allow_suffixed=False.

        Args:
            periph_id: The peripheral identifier.
            allow_suffixed: Allow falling back to a suffixed variant
                (panel behavior); False = exact match only
                (statistics target).

        Returns:
            The registered entity_id, or None if not found.
        """
        try:
            from homeassistant.helpers import entity_registry as er

            registry = er.async_get(self.hass)
        except Exception as err:
            _LOGGER.debug("Entity registry unavailable: %s", err)
            return None
        prefix = get_entry_prefix(self)
        base_unique_id = f"{prefix}_{periph_id}"
        suffixed_fallback = None
        for entry in registry.entities.values():
            if entry.platform != DOMAIN or not entry.unique_id:
                continue
            if entry.unique_id == base_unique_id:
                return entry.entity_id
            if (
                allow_suffixed
                and entry.unique_id.startswith(f"{base_unique_id}_")
                and suffixed_fallback is None
            ):
                suffixed_fallback = entry.entity_id
        return suffixed_fallback

    def _resolve_history_value(self, periph_id: str, value) -> float | None:
        """Convert a history value to a float.

        The periph.history API returns the label (e.g. 'Confort') for
        List-type peripherals. The corresponding numeric value is
        available in self.data[periph_id]["values"] (periph.value_list
        API, merged at coordinator initialization).

        Returns:
            The numeric value, or None if the value cannot be converted.
        """
        try:
            return float(value)
        except (ValueError, TypeError):
            pass
        values_list = (self.data.get(periph_id) or {}).get("values") or []
        for item in values_list:
            if isinstance(item, dict) and item.get("description") == value:
                try:
                    return float(item["value"])
                except (ValueError, TypeError):
                    return None
        return None

    async def _import_via_statistics(
        self, entity_id: str, chunk: list, periph_name: str, periph_id: str
    ) -> int:
        """Import historical data via recorder.statistics.async_import_statistics.

        AD-1: the official Python API replaces the recorder.import_statistics
        service (Spook). AD-11: only hours strictly before the sensor's first
        native statistic are written; the recorder compiler owns the rest.

        Returns:
            The number of hourly statistics actually imported (0 when
            skipped).
        """
        try:
            # Prepare statistics data in the format expected by
            # async_import_statistics: metadata (statistic_id / source /
            # mean_type / unit_of_measurement) + stats [{start, mean, ...}].
            # HA long-term statistics are hourly: start must be from the top
            # of the hour, so the raw data points are aggregated per hour.
            hourly_values: dict[datetime, list[float]] = {}
            last_state: dict[datetime, float] = {}
            last_ts: dict[datetime, datetime] = {}
            skipped_points = 0
            first_skip_reason: str | None = None
            for entry in chunk:
                try:
                    # HA statistics require timezone-aware start datetimes;
                    # eedomus history dates are naive local time
                    timestamp = dt_util.as_local(
                        datetime.fromisoformat(entry["timestamp"])
                    )
                    state_value = self._resolve_history_value(periph_id, entry["value"])
                    if state_value is None:
                        raise ValueError(
                            f"could not convert to float: {entry['value']!r} "
                            f"(periph {periph_id})"
                        )

                    hour = timestamp.replace(minute=0, second=0, microsecond=0)
                    hourly_values.setdefault(hour, []).append(state_value)
                    # "state" is the most recent value within the hour
                    if hour not in last_ts or timestamp >= last_ts[hour]:
                        last_ts[hour] = timestamp
                        last_state[hour] = state_value
                except (ValueError, TypeError) as e:
                    # Per-point detail stays debug: a fully
                    # unresolvable periph (e.g. a box color preset
                    # mapped as sensor) would flood the log with one
                    # warning per history point; the chunk-level
                    # aggregate below carries the diagnosis.
                    _LOGGER.debug("Skipping invalid data point: %s", e)
                    skipped_points += 1
                    if first_skip_reason is None:
                        first_skip_reason = str(e)
                    continue

            if skipped_points:
                _LOGGER.warning(
                    "Skipped %d of %d history points for %s (periph %s): "
                    "%s",
                    skipped_points,
                    len(chunk),
                    entity_id,
                    periph_id,
                    first_skip_reason,
                )

            statistics_data = []
            for hour in sorted(hourly_values):
                values = hourly_values[hour]
                statistics_data.append(
                    {
                        "start": hour,
                        "mean": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                        "state": last_state.get(hour, values[-1]),
                    }
                )

            if not statistics_data:
                _LOGGER.warning("No valid statistics data to import for %s", entity_id)
                return 0

            # AD-1: import through the official recorder Python API,
            # never the recorder.import_statistics service (Spook)
            from homeassistant.components.recorder import (
                get_instance as get_recorder_instance,
                statistics as recorder_statistics,
            )
            from homeassistant.components.recorder.models import StatisticMeanType

            # The unit comes from the entity's live state: the API derives
            # unit_class from unit_of_measurement (mean_type and the unit
            # become required metadata from HA 2026.11) and raises for
            # unsupported units. Without a live state the metadata would be
            # invalid: skip the import.
            state = self.hass.states.get(entity_id)
            if state is None:
                _LOGGER.warning(
                    "Skipping statistics import for %s: no live state to "
                    "read unit_of_measurement from",
                    entity_id,
                )
                return 0
            unit = state.attributes.get("unit_of_measurement")

            # unit_class derived through the recorder's own unit map
            # (bug 1.8: the missing key deprecates from HA 2026.11).
            # unit_conversion.get_unit_converter does not exist in HA
            # 2026.9 — the AttributeError aborted every import, so the
            # lookup goes through STATISTIC_UNIT_TO_UNIT_CONVERTER, the
            # same table the recorder itself resolves converters from.
            # A unit without a converter keeps unit_class None — the key
            # stays present, only its absence deprecates.
            converter = (
                recorder_statistics.STATISTIC_UNIT_TO_UNIT_CONVERTER.get(unit)
            )
            unit_class = getattr(converter, "UNIT_CLASS", None)

            # AD-11: the recorder compiler owns every hour from the sensor's
            # first native statistic onward (the upsert would overwrite its
            # means); the backfill writes strictly earlier hours only.
            # statistics_during_period is a blocking database call: it must
            # run on the recorder's dedicated database executor, not the
            # generic hass.async_add_executor_job (HA 2026+ reports that as
            # "accesses the database without the database executor").
            native_stats = await get_recorder_instance(
                self.hass
            ).async_add_executor_job(
                recorder_statistics.statistics_during_period,
                self.hass,
                datetime(1970, 1, 1, tzinfo=dt_util.UTC),
                dt_util.utcnow(),
                {entity_id},
                "hour",
                None,
                {"state"},
            )
            native_rows = (native_stats or {}).get(entity_id) or []
            if native_rows:
                # Rows are not guaranteed ascending: take the earliest.
                # statistics_during_period returns "start" as a float
                # epoch timestamp (StatisticsRow), not a datetime.
                first_native_start = dt_util.utc_from_timestamp(
                    min(row["start"] for row in native_rows)
                )
                backfilled = [
                    stat
                    for stat in statistics_data
                    if stat["start"] < first_native_start
                ]
                if not backfilled:
                    _LOGGER.info(
                        "Nothing to import for %s: all %d hours at or after "
                        "the first native statistic (AD-11)",
                        entity_id,
                        len(statistics_data),
                    )
                    return 0
                statistics_data = backfilled

            metadata = {
                "statistic_id": entity_id,
                # "recorder" is required by async_import_statistics
                "source": "recorder",
                "name": periph_name,
                "mean_type": StatisticMeanType.ARITHMETIC,
                "has_sum": False,
                "unit_of_measurement": unit,
                # bug 1.8: unit_class is required metadata from HA
                # 2026.11 — derived from the unit (None without a
                # converter, the key itself must be present).
                "unit_class": unit_class,
            }

            _LOGGER.info(
                "Importing %d hourly statistics for %s via async_import_statistics",
                len(statistics_data),
                entity_id,
            )
            # async_import_statistics is a synchronous @callback
            recorder_statistics.async_import_statistics(
                self.hass, metadata, statistics_data
            )

            return len(statistics_data)

        except Exception as e:
            # The caller (async_import_history_chunk) owns the single
            # user-facing warning; these are diagnostic details only
            _LOGGER.debug("Failed to import statistics for %s: %s", entity_id, e)
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
        _LOGGER.debug(
            "📋 Original set_value call: %s (%s) = %s",
            self.data[periph_id]["name"],
            periph_id,
            original_value,
        )

        # try:
        ret = await self.client.set_periph_value(periph_id, value)

        # Log API response details
        _LOGGER.debug(
            "📋 API response for %s (%s): success=%s, error_code=%s",
            self.data[periph_id]["name"],
            periph_id,
            ret.get("success"),
            ret.get("error_code"),
        )

        # Only retry if enabled and we get error_code 6 (value refused)
        if enable_retry and ret.get("success") == 0 and ret.get("error_code") == "6":
            # Try PHP fallback first if enabled
            if php_fallback_enabled:
                _LOGGER.info(
                    "🔄 Trying PHP fallback for %s (%s) with original value: %s",
                    self.data[periph_id]["name"],
                    periph_id,
                    value,
                )
                fallback_result = await self.client.php_fallback_set_value(
                    periph_id, value
                )
                if fallback_result.get("success") == 1:
                    _LOGGER.info(
                        "✅ PHP fallback succeeded for %s (%s) - original value %s preserved",
                        self.data[periph_id]["name"],
                        periph_id,
                        value,
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
                        modified_value,
                    )
                    _LOGGER.warning(
                        "🔄 Retry enabled - trying next best value (%s => %s) for %s (%s)",
                        original_value,
                        modified_value,
                        self.data[periph_id]["name"],
                        periph_id,
                    )
                    await self.client.set_periph_value(periph_id, modified_value)
                    # Return success response when next best value is used
                    return {
                        "success": 1,
                        "fallback_used": True,
                        "value_used": modified_value,
                        "original_value": original_value,
                    }
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
        elif ret.get("success") == 0:
            _LOGGER.error(
                "❌ Set value failed for %s (%s): %s - retry disabled or not applicable",
                self.data[periph_id]["name"],
                periph_id,
                ret.get("error", "Unknown error"),
            )
            _LOGGER.error(
                "💡 Check the documentation for value constraints and "
                "consider enabling 'Set Value Retry' in advanced options"
            )
            _LOGGER.error(
                "📖 Documentation: https://github.com/Dan4Jer/hass-eedomus#value-constraints"
            )
        else:
            _LOGGER.info(
                "✅ Set value successful for %s (%s) - value %s applied without modification",
                self.data[periph_id]["name"],
                periph_id,
                value,
            )

            # Immediately update local state to reflect the change
            # This ensures UI updates instantly without waiting for coordinator refresh
            self.data[periph_id]["last_value"] = value
            # Notify entities so the new state is rendered immediately
            self.async_update_listeners()
            return {"success": 1, "value_used": value, "original_value": value}

    def next_best_value(self, periph_id: str, value: str):
        values_list = self.data.get(periph_id, {}).get("values", [])
        available_entries = []
        for item in values_list:
            try:
                available_entries.append((int(item["value"]), item))
            except (ValueError, KeyError):
                continue
        if not values_list:
            raise ValueError(f"No value available for peripheral {periph_id}")

        try:
            target_value = int(value)
        except ValueError:
            raise ValueError(f"The target value '{value}' is not a valid number.")
        if not available_entries:
            raise ValueError(
                f"No valid numeric value found for peripheral {periph_id}"
            )

        return min(available_entries, key=lambda x: abs(x[0] - target_value))[1]
