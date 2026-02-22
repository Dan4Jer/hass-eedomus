"""Switch entity for eedomus integration."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, COORDINATOR
from .entity import EedomusEntity, map_device_to_ha_entity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    switches = []

    all_peripherals = coordinator.get_all_peripherals()
    parent_to_children = {}
    for periph_id, periph in all_peripherals.items():
        if periph.get("parent_periph_id"):
            parent_id = periph["parent_periph_id"]
            if parent_id not in parent_to_children:
                parent_to_children[parent_id] = []
            parent_to_children[parent_id].append(periph)
            if not "ha_entity" in coordinator.data[periph_id]:
                eedomus_mapping = map_device_to_ha_entity(periph, coordinator.data)
                coordinator.data[periph_id].update(eedomus_mapping)
                # S'assurer que le mapping est enregistré dans le registre global
                from .entity import _register_device_mapping
                _register_device_mapping(eedomus_mapping, periph["name"], periph_id, periph)
    for periph_id, periph in all_peripherals.items():
        ha_entity = None
        if "ha_entity" in coordinator.data[periph_id]:
            ha_entity = coordinator.data[periph_id]["ha_entity"]

        parent_id = periph.get("parent_periph_id", None)
        if parent_id and coordinator.data[parent_id]["ha_entity"] == "light":
            # les enfants sont gérés par le parent... est-ce une bonne idée ?
            eedomus_mapping = None
            if periph.get("usage_id") == "26":
                eedomus_mapping = {
                    "ha_entity": "sensor",
                    "ha_subtype": None,
                    "justification": "Parent is a switch - sensor - Consometre",
                }
            if not eedomus_mapping is None:
                coordinator.data[periph_id].update(eedomus_mapping)
                # Log pour confirmer que le device a été mappé
                _LOGGER.debug("✅ Device mapped: %s (%s) → %s:%s", 
                            periph["name"], periph_id, eedomus_mapping["ha_entity"], eedomus_mapping["ha_subtype"])

    for periph_id, periph in all_peripherals.items():
        ha_entity = None
        if "ha_entity" in coordinator.data[periph_id]:
            ha_entity = coordinator.data[periph_id]["ha_entity"]

        if ha_entity is None or not ha_entity == "switch":
            continue

        # Check if this switch should actually be a sensor (consumption monitoring)
        # Look for patterns that indicate this is a consumption sensor, not a real switch
        should_be_sensor = False

        # Pattern 1: Has ONLY children with usage_id=26 (energy meters) and no control capability
        # This indicates it's a pure consumption monitor, not a controllable device with consumption monitoring
        if periph_id in parent_to_children:
            has_only_consumption_children = True
            has_control_children = False

            for child in parent_to_children[periph_id]:
                if child.get("usage_id") == "26":  # Consomètre
                    # Check if this is a pure consumption device by looking at the device name and type
                    continue
                elif child.get("usage_id") in [
                    "1",
                    "2",
                    "4",
                    "52",
                ]:  # Control-capable children
                    has_control_children = True
                    break

            # Only remap as sensor if it has consumption children AND no control children
            # AND the device name suggests it's a consumption monitor
            if has_only_consumption_children and not has_control_children:
                # Additional check: if the device name contains consumption-related terms
                device_name_lower = periph.get("name", "").lower()
                consumption_keywords = [
                    "consommation",
                    "conso",
                    "compteur",
                    "meter",
                    "energy",
                ]
                if any(
                    keyword in device_name_lower for keyword in consumption_keywords
                ):
                    should_be_sensor = True

        # Pattern 2: Name contains "consommation" (French for consumption) but not other device types
        device_name_lower = periph.get("name", "").lower()
        if "consommation" in device_name_lower:
            # Don't remap if it's clearly a controllable device
            device_keywords = [
                "decoration",
                "lampe",
                "light",
                "prise",
                "switch",
                "interrupteur",
                "appliance",
                "noel",
                "sapin",
            ]
            if not any(keyword in device_name_lower for keyword in device_keywords):
                should_be_sensor = True

        # Pattern 3: Specific device types that should remain switches even with consumption children
        # These are devices that are primarily controllable but also have energy monitoring
        device_name_lower = periph.get("name", "").lower()
        controllable_device_keywords = [
            "decoration",
            "anti-moustique",
            "sapin",
            "noel",
            "guirlande",
            "appliance",
            "appareil",
            "prise",
            "module",
            "relay",
        ]
        if any(
            keyword in device_name_lower for keyword in controllable_device_keywords
        ):
            should_be_sensor = False  # Force this to remain a switch
            _LOGGER.debug(
                "Keeping '%s' (%s) as switch - identified as controllable device with consumption monitoring",
                periph["name"],
                periph_id,
            )

        if should_be_sensor:
            _LOGGER.debug(
                "Remapping switch '%s' (%s) as sensor - detected as consumption monitor",
                periph["name"],
                periph_id,
            )
            # Update the mapping to sensor
            coordinator.data[periph_id].update(
                {
                    "ha_entity": "sensor",
                    "ha_subtype": "energy",
                    "justification": "Detected as consumption monitor based on name pattern and children",
                }
            )
            continue  # Skip creating switch entity, will be handled by sensor setup

        _LOGGER.debug(
            "Go for a switch !!! %s (%s) mapping=%s",
            periph["name"],
            periph_id,
            ha_entity,
        )

        switches.append(EedomusSwitch(coordinator, periph_id))

    async_add_entities(switches, True)


class EedomusSwitch(EedomusEntity, SwitchEntity):
    """Representation of an eedomus switch."""

    def __init__(self, coordinator, periph_id):
        """Initialize the switch."""
        super().__init__(coordinator, periph_id)
        _LOGGER.debug("Initializing switch entity for periph_id=%s", periph_id)

    @property
    def is_on(self):
        """Return true if the switch is on."""
        periph_data = self._get_periph_data()
        if periph_data is None:
            _LOGGER.warning(f"Cannot get switch state: peripheral data not found for {self._periph_id}")
            return False
            
        value = periph_data.get("last_value")
        _LOGGER.debug(
            "Switch %s is_on: %s name=%s",
            self._periph_id,
            periph_data.get("last_value"),
            periph_data.get("name"),
        )
        return value == "100"

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        _LOGGER.debug("Turning on switch %s", self._periph_id)
        try:
            # Use entity method to turn on switch (includes fallback, retry, and state update)
            response = await self.async_set_value("100")
        except Exception as e:
            _LOGGER.error("Failed to turn on switch %s: %s", self._periph_id, e)
            raise

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        _LOGGER.debug("Turning off switch %s", self._periph_id)
        try:
            # Use entity method to turn off switch (includes fallback, retry, and state update)
            response = await self.async_set_value("0")

        except Exception as e:
            _LOGGER.error("Failed to turn off switch %s: %s", self._periph_id, e)
            raise
