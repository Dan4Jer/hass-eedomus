"""Base entity for eedomus integration."""

from __future__ import annotations
from datetime import datetime

import logging

from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_PERIPH_ID, DOMAIN, EEDOMUS_TO_HA_ATTR_MAPPING
from .devices_class_mapping import DEVICES_CLASS_MAPPING, USAGE_ID_MAPPING, ADVANCED_MAPPING_RULES

_LOGGER = logging.getLogger(__name__)


# Timestamp formatting utilities

def _format_timestamp_value(timestamp_value: str) -> str:
    """Format various timestamp values from eedomus into ISO 8601 format.
    
    Handles multiple timestamp formats:
    - Unix timestamp (seconds since epoch)
    - Datetime string (e.g., "2026-01-10 16:21:14")
    - Invalid datetime (e.g., "0000-00-00 00:00:00")
    
    Args:
        timestamp_value: The raw timestamp value from eedomus
        
    Returns:
        str: ISO 8601 formatted timestamp or None if invalid
    """
    if not timestamp_value or timestamp_value == "None":
        return None
        
    try:
        # Handle Unix timestamp format (seconds since epoch)
        if isinstance(timestamp_value, (int, float)) or (isinstance(timestamp_value, str) and timestamp_value.isdigit()):
            timestamp = int(timestamp_value)
            dt = datetime.fromtimestamp(timestamp)
            return dt.isoformat()
            
        # Handle datetime string format (e.g., "2026-01-10 16:21:14")
        if isinstance(timestamp_value, str):
            timestamp_str = timestamp_value.strip()
            
            # Skip invalid datetime strings
            if timestamp_str == "0000-00-00 00:00:00":
                return None
                
            # Try common datetime formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
                    
    except (ValueError, TypeError, OverflowError) as e:
        _LOGGER.debug(
            "Failed to parse timestamp value '%s': %s",
            timestamp_value,
            e
        )
        return None
    
    return None


def _format_eedomus_timestamps(periph_data: dict) -> dict:
    """Format all eedomus timestamp fields into standardized ISO 8601 format.
    
    Processes common eedomus timestamp fields and creates standardized
    Home Assistant timestamp attributes.
    
    Args:
        periph_data: The peripheral data from eedomus
        
    Returns:
        dict: Dictionary with formatted timestamp attributes
    """
    timestamps = {}
    
    # Map eedomus timestamp fields to HA attribute names
    timestamp_mapping = {
        "last_value_change": ["last_changed", "last_reported"],  # Both attributes get same value
        "creation_date": ["created"],                           # Single attribute
    }
    
    for eedomus_field, ha_attributes in timestamp_mapping.items():
        if eedomus_field in periph_data:
            formatted_timestamp = _format_timestamp_value(periph_data[eedomus_field])
            if formatted_timestamp:
                for ha_attr in ha_attributes:
                    timestamps[ha_attr] = formatted_timestamp
    
    return timestamps


class EedomusEntity(CoordinatorEntity):
    """Base class for eedomus entities."""

    def __init__(self, coordinator, periph_id: str):
        """Initialize the entity."""
        super().__init__(coordinator)
        self._periph_id = periph_id
        self._parent_id = self.coordinator.data[periph_id].get("parent_periph_id", None)
        if self.coordinator.client:
            self._client = self.coordinator.client
        if self._parent_id is None:
            self._attr_unique_id = f"{periph_id}"
        else:
            self._attr_unique_id = f"{self._parent_id}_{periph_id}"
        if self.coordinator.data[periph_id]["name"]:
            self._attr_name = self.coordinator.data[periph_id]["name"]
        _LOGGER.debug(
            "Initializing entity for %s (%s)", self._attr_name, self._periph_id
        )
        self._attr_available = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        periph_info = self.coordinator.data[self._periph_id]
        return DeviceInfo(
            identifiers={(DOMAIN, str(self._periph_id))},
            name=periph_info.get("name"),
            manufacturer="eedomus",
            model=periph_info.get("model"),
        )

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {}
        if self.coordinator.data.get(self._periph_id):
            periph_data = self.coordinator.data[self._periph_id]
            attrs[ATTR_PERIPH_ID] = self._periph_id

            # Map standard eedomus attributes
            for eedomus_key, ha_key in EEDOMUS_TO_HA_ATTR_MAPPING.items():
                if eedomus_key in periph_data:
                    attrs[ha_key] = periph_data[eedomus_key]
            
            # Format all timestamp fields using the centralized utility
            timestamp_attrs = _format_eedomus_timestamps(periph_data)
            attrs.update(timestamp_attrs)
            
            # Add current timestamp for last_updated (when HA last updated this entity)
            attrs["last_updated"] = datetime.now().isoformat()
            
            # Ensure usage_id is always included in attributes
            if "usage_id" in periph_data:
                attrs["usage_id"] = periph_data["usage_id"]
            
        return attrs

    @property
    def available(self):
        """Return the periph ID."""
        return self._attr_available

    @property
    def periph_id(self):
        """Return the periph ID."""
        return self._periph_id

    def update(self) -> None:
        """Update entity state."""
        _LOGGER.warning(
            "Update for %s (%s) type=%s client=%s",
            self._attr_name,
            self._periph_id,
            type(self),
            type(self._client),
        )
        try:
            caract_value = self._client.get_periph_caract(self._periph_id)
            if isinstance(caract_value, dict):
                body = caract_value.get("body")
                if body is not None:
                    self.coordinator.data[self._periph_id].update(body)
                else:
                    _LOGGER.warning(
                        "No body found in API response for %s (%s)",
                        self._attr_name,
                        self._periph_id,
                    )
        except Exception as e:
            if self.available:  # Read current state, no need to prefix with _attr_
                _LOGGER.warning(
                    "Update failed for %s (%s) : %s",
                    self._attr_name,
                    self._periph_id,
                    e,
                )
                self._attr_available = False  # Set property value
                return

        self._attr_available = True
        # We don't need to check if device available here
        if "last_value" in self.coordinator.data[self._periph_id]:
            self._attr_native_value = self.coordinator.data[self._periph_id]["last_value"]
        else:
            _LOGGER.warning(
                "No last_value found in data for %s (%s)",
                self._attr_name,
                self._periph_id,
            )
            self._attr_available = False

    async def async_update(self) -> None:
        """Update entity state."""
        _LOGGER.warn(
            "Async Update for %s (%s) type=%s client=%s",
            self._attr_name,
            self._periph_id,
            type(self),
            type(self._client),
        )
        try:
            caract_value = await self._client.get_periph_caract(self._periph_id)
            if isinstance(caract_value, dict):
                body = caract_value.get("body")
                if body is not None:
                    self.coordinator.data[self._periph_id].update(body)
                else:
                    _LOGGER.warning(
                        "No body found in API response for %s (%s)",
                        self._attr_name,
                        self._periph_id,
                    )
        except Exception as e:
            if self.available:  # Read current state, no need to prefix with _attr_
                _LOGGER.warning(
                    "Update failed for %s (%s) : %s",
                    self._attr_name,
                    self._periph_id,
                    e,
                )
                self._attr_available = False  # Set property value
                return

        self._attr_available = True
        # We don't need to check if device available here
        self._attr_native_value = self.coordinator.data[self._periph_id]["last_value"]
        self.coordinator.data[self._periph_id]["last_updated"] = datetime.now().isoformat()

    async def async_set_value(self, value: str):
        """Set device value with full eedomus logic including fallback and retry.
        
        This method centralizes all value-setting logic including:
        - PHP fallback for rejected values
        - Next best value selection
        - Immediate state updates
        - Coordinator refresh
        
        Args:
            value: The value to set (e.g., "100", "0", "50")
            
        Returns:
            dict: API response from eedomus
            
        Raises:
            Exception: If the value cannot be set after all retry attempts
        """
        _LOGGER.debug(
            "Setting value '%s' for %s (%s)",
            value,
            self._attr_name,
            self._periph_id
        )
        

        
        try:
            # Call coordinator method to set the value
            response = await self.coordinator.async_set_periph_value(
                self._periph_id, str(value)
            )
            
            # Check if we need to handle retry/fallback
            if isinstance(response, dict):
                if response.get("success") == 1:
                    # Success! Force immediate state update
                    await self.async_force_state_update(value)
                    await self.coordinator.async_request_refresh()
                    return response
                elif response.get("error_code") == "6":  # Value refused
                    _LOGGER.warning(
                        "Value '%s' refused for %s (%s), checking fallback/next best value",
                        value,
                        self._attr_name,
                        self._periph_id
                    )
                    # The coordinator already handled retry/fallback, just update state
                    await self.async_force_state_update(value)
                    await self.coordinator.async_request_refresh()
                    return response
            
            # If we get here, something went wrong
            _LOGGER.error(
                "Failed to set value '%s' for %s (%s): %s",
                value,
                self._attr_name,
                self._periph_id,
                response.get("error", "Unknown error") if isinstance(response, dict) else str(response)
            )
            raise Exception(
                f"Failed to set value: {response.get('error', 'Unknown error') if isinstance(response, dict) else str(response)}"
            )
            
        except Exception as e:
            _LOGGER.error(
                "Failed to set value for %s (%s): %s",
                self._attr_name,
                self._periph_id,
                e
            )
            raise

    async def async_force_state_update(self, new_value):
        """Force an immediate state update with the given value.
        
        This method should be called after successfully setting a device value
        to ensure the UI updates immediately without waiting for coordinator refresh.
        """
        _LOGGER.debug(
            "Forcing state update for %s (%s) to value: %s",
            self._attr_name,
            self._periph_id,
            new_value
        )
        
        # Update the coordinator's data
        self.coordinator.data[self._periph_id]["last_value"] = str(new_value)
        
        # Update last_value_change timestamp to current time
        # This is crucial for covers and other entities that track when values were last changed
        from datetime import datetime
        current_timestamp = datetime.now().isoformat()
        self.coordinator.data[self._periph_id]["last_value_change"] = current_timestamp
        _LOGGER.debug(
            "Updated last_value_change for %s (%s) to: %s",
            self._attr_name,
            self._periph_id,
            current_timestamp
        )
        
        # Force immediate state update in Home Assistant using explicit state machine
        # This ensures we control the timestamp precisely
        try:
            # Get the timestamp from last_value_change
            last_value_change = self.coordinator.data[self._periph_id].get("last_value_change")
            if last_value_change:
                # Convert ISO format timestamp to datetime object
                desired_dt = datetime.fromisoformat(last_value_change)
                desired_ts = desired_dt.timestamp()
                
                _LOGGER.debug(
                    "Setting explicit state for %s (%s) with timestamp %s",
                    self._attr_name,
                    self._periph_id,
                    desired_ts
                )
                
                # Use state machine to set state with precise timestamp
                if hasattr(self, 'hass') and hasattr(self, 'entity_id'):
                    self.hass.states.async_set(
                        self.entity_id,
                        str(self._attr_native_value) if hasattr(self, '_attr_native_value') else str(new_value),
                        self.extra_state_attributes,
                        force_update=True,
                        timestamp=desired_ts,
                    )
                else:
                    _LOGGER.warning(
                        "Cannot set explicit state - missing hass or entity_id for %s (%s)",
                        self._attr_name,
                        self._periph_id
                    )
                    # Fallback to standard method
                    self.async_write_ha_state()
            else:
                _LOGGER.warning(
                    "No last_value_change timestamp available for %s (%s)",
                    self._attr_name,
                    self._periph_id
                )
                # Fallback to standard method
                self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(
                "Failed to set explicit state for %s (%s): %s",
                self._attr_name,
                self._periph_id,
                e
            )
            # Fallback to standard method
            self.async_write_ha_state()
        
        # Schedule a regular update to ensure consistency
        self.async_schedule_update_ha_state()


def map_device_to_ha_entity(device_data, all_devices=None, default_ha_entity: str = "sensor"):
    """Mappe un périphérique eedomus vers une entité Home Assistant.
    
    Nouvelle logique de mapping basée sur usage_id avec règles avancées.
    
    Args:
        device_data (dict): Données du périphérique.
        all_devices (dict): Tous les périphériques pour les règles avancées.
        default_ha_entity (str): HA entity à utiliser si pas trouvé.
    
    Returns:
        dict: {"ha_entity": str, "ha_subtype": str, "justification": str}
    """
    _LOGGER.debug(
        "Starting mapping for %s (%s)", device_data["name"], device_data["periph_id"]
    )

    # 1. Vérifier d'abord les règles avancées (basées sur les relations parent-enfant)
    if all_devices:
        for rule_name, rule_config in ADVANCED_MAPPING_RULES.items():
            if rule_config["condition"](device_data, all_devices):
                mapping = {
                    "ha_entity": rule_config["ha_entity"],
                    "ha_subtype": rule_config["ha_subtype"],
                    "justification": f"Advanced rule {rule_name}: {rule_config['justification']}",
                }
                _LOGGER.info(
                    "🎯 Advanced rule mapping for %s (%s): %s",
                    device_data["name"],
                    device_data["periph_id"],
                    mapping,
                )
                return mapping

    # 2. Vérifier les cas spécifiques prioritaires (basés uniquement sur usage_id)
    usage_id = device_data.get("usage_id")
    
    # Cas spécifiques qui doivent être traités en priorité
    if usage_id == "27":  # Capteur de fumée
        mapping = {
            "ha_entity": "binary_sensor",
            "ha_subtype": "smoke",
            "justification": f"Smoke detector: usage_id=27",
        }
        _LOGGER.info(
            "🔥 Smoke sensor mapping for %s (%s): %s",
            device_data["name"],
            device_data["periph_id"],
            mapping,
        )
        return mapping

    if usage_id == "23":  # Indicateur CPU
        mapping = {
            "ha_entity": "sensor",
            "ha_subtype": "cpu_usage",
            "justification": f"CPU usage monitor: usage_id=23",
        }
        _LOGGER.info(
            "💻 CPU usage sensor mapping for %s (%s): %s",
            device_data["name"],
            device_data["periph_id"],
            mapping,
        )
        return mapping

    if usage_id == "37":  # Capteur de mouvement
        mapping = {
            "ha_entity": "binary_sensor",
            "ha_subtype": "motion",
            "justification": f"usage_id=37: Capteur de mouvement (prioritaire)",
        }
        _LOGGER.info(
            "🚶 Motion sensor mapping for %s (%s): %s",
            device_data["name"],
            device_data["periph_id"],
            mapping,
        )
        return mapping

    # 3. Appliquer le mapping basé sur usage_id
    if usage_id in USAGE_ID_MAPPING:
        mapping = USAGE_ID_MAPPING[usage_id].copy()
        
        # Vérifier si des règles avancées sont définies pour ce usage_id
        if "advanced_rules" in mapping:
            for rule_name in mapping["advanced_rules"]:
                if rule_name in ADVANCED_MAPPING_RULES:
                    rule_config = ADVANCED_MAPPING_RULES[rule_name]
                    if rule_config["condition"](device_data, all_devices or {}):
                        mapping.update({
                            "ha_entity": rule_config["ha_entity"],
                            "ha_subtype": rule_config["ha_subtype"],
                            "justification": f"Advanced rule {rule_name}: {rule_config['justification']}",
                        })
                        _LOGGER.info(
                            "🎯 Advanced rule applied for %s (%s): %s",
                            device_data["name"],
                            device_data["periph_id"],
                            mapping,
                        )
                        break
        
        _LOGGER.debug(
            "Usage ID mapping for %s (%s): %s",
            device_data["name"],
            device_data["periph_id"],
            mapping,
        )
        return mapping

    # 4. Vérifier les cas spécifiques basés sur le nom (en dernier recours)
    device_name_lower = device_data["name"].lower()
    if "message" in device_name_lower and "box" in device_name_lower:
        mapping = {
            "ha_entity": "sensor",
            "ha_subtype": "text",
            "justification": f"Message box detected in name: '{device_data['name']}'",
        }
        _LOGGER.info(
            "📝 Text sensor mapping for %s (%s): %s",
            device_data["name"],
            device_data["periph_id"],
            mapping,
        )
        return mapping

    # 5. Mapping par défaut
    mapping = {
        "ha_entity": default_ha_entity,
        "ha_subtype": "unknown",
        "justification": "Unknown device type",
    }
    _LOGGER.warning(
        "❓ No mapping found for %s (%s): %s. Data: %s",
        device_data["name"],
        device_data["periph_id"],
        mapping,
        device_data,
    )
    return mapping
