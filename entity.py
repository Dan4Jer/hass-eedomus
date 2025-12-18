"""Base entity for eedomus integration."""
from __future__ import annotations

import logging
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, ATTR_PERIPH_ID
from .devices_class_mapping import DEVICES_CLASS_MAPPING, USAGE_ID_MAPPING

_LOGGER = logging.getLogger(__name__)

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
        _LOGGER.debug("Initializing entity for %s (%s)", self._attr_name, self._periph_id)
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

            if "history" in periph_data:
                attrs["history"] = periph_data["history"]

            if "value_list" in periph_data:
                attrs["value_list"] = periph_data["value_list"]

            if "room_name" in periph_data:
                attrs["room"] = periph_data["room_name"]

            if "value_type" in periph_data:
                attrs["type"] = periph_data["value_type"]

            attrs["eedomus_id"] = self._periph_id

##Bug:cover with a false temperature sensor.
#if  periph_data["value_type"] == 'float' and periph_data["current_value"] == "":
#    periph_data["current_value"] = 0
#if  periph_data["value_type"] == ' ' and periph_data["current_value"] == "":
#    periph_data["current_value"] = 0
                
            if not "room" in attrs and "room_name" in periph_data:
                attrs["room"] = periph_data["room_name"]

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
        _LOGGER.debug("Update for %s (%s) type=%s client=%s", self._attr_name, self._periph_id, type(self), type(self._client))
        try:
            caract_value = self._client.get_periph_caract(self._periph_id)
            if isinstance(caract_value, dict):
                self.coordinator.data[self._periph_id].update(caract_value)
#                for att in ["last_value", "last_value_change", "last_value_text", "battery"]:
#                    self.coordinator.data[self._periph_id][attr] = caract_value["body"].get(attr)
        except Exception as e:
            if self.available:  # Read current state, no need to prefix with _attr_
                _LOGGER.warning("Update failed for %s (%s) : %s", self._attr_name, self._periph_id, e)
                self._attr_available = False  # Set property value
                return

        self._attr_available = True
        # We don't need to check if device available here
        self._attr_native_value = self.coordinator.data[self._periph_id]["last_value"]

    async def async_update(self) -> None:
        """Update entity state."""
        _LOGGER.debug("Async Update for %s (%s) type=%s client=%s", self._attr_name, self._periph_id, type(self), type(self._client))
        try:
            caract_value = await self._client.get_periph_caract(self._periph_id)
            if isinstance(caract_value, dict):
                self.coordinator.data[self._periph_id].update(caract_value)
#                for att in ["last_value", "last_value_change", "last_value_text", "battery"]:
#                    self.coordinator.data[self._periph_id][attr] = caract_value["body"].get(attr)
        except Exception as e:
            if self.available:  # Read current state, no need to prefix with _attr_
                _LOGGER.warning("Update failed for %s (%s) : %s", self._attr_name, self._periph_id, e)
                self._attr_available = False  # Set property value
                return

        self._attr_available = True
        # We don't need to check if device available here
        self._attr_native_value = self.coordinator.data[self._periph_id]["last_value"]

        
def map_device_to_ha_entity(device_data, default_ha_entity: str = "sensor"):
    """        Mappe un périphérique eedomus vers une entité Home Assistant.
    Args:
          device_data (dict): Données du périphérique.
          default_ha_entity (str): HA entity a utiliser si pas trouvé 
    Returns:
          dict: {"ha_entity": str, "ha_subtype": str, "justification": str}
    """
    _LOGGER.debug("Starting mapping for %s (%s)", device_data["name"], device_data["periph_id"])

    supported_classes = device_data.get("SUPPORTED_CLASSES", "").split(",") if isinstance(device_data.get("SUPPORTED_CLASSES"), str) else []
    generic = device_data.get("GENERIC", "")
    product_type_id = device_data.get("PRODUCT_TYPE_ID", "")
    specific = device_data.get("SPECIFIC", "")

    # Vérifier d'abord si c'est un périphérique virtuel (PRODUCT_TYPE_ID=999)
    if product_type_id == "999":
        mapping = {
            "ha_entity": "scene",
            "ha_subtype": "virtual",
            "justification": f"PRODUCT_TYPE_ID=999: Périphérique virtuel eedomus pour scène"
        }
        _LOGGER.debug("Virtual device mapping for %s (%s): %s", device_data["name"], device_data["periph_id"], mapping)
        return mapping

    # Vérifier les PRODUCT_TYPE_ID spécifiques qui doivent être prioritaires
    if product_type_id == "770":  # Volets Fibaro
        mapping = {
            "ha_entity": "cover",
            "ha_subtype": "shutter",
            "justification": f"PRODUCT_TYPE_ID=770: Volet Fibaro (prioritaire sur usage_id)"
        }
        _LOGGER.debug("Fibaro shutter mapping for %s (%s): %s", device_data["name"], device_data["periph_id"], mapping)
        return mapping

    if product_type_id == "4" and device_data.get("usage_id") in ["38", "19", "20"]:  # Chauffages fil pilote
        mapping = {
            "ha_entity": "climate",
            "ha_subtype": "fil_pilote",
            "justification": f"PRODUCT_TYPE_ID=4 avec usage_id={device_data.get('usage_id')}: Chauffage fil pilote (prioritaire)"
        }
        _LOGGER.debug("Fil pilote climate mapping for %s (%s): %s", device_data["name"], device_data["periph_id"], mapping)
        return mapping

    zwave_class = None
    for cls in supported_classes:
        cls_num = cls.split(":")[0]  # Extraire le numéro de classe (ex: "38:3" → "38")
        if cls_num in DEVICES_CLASS_MAPPING and DEVICES_CLASS_MAPPING[cls_num]["ha_entity"] is not None:
            # Vérifier si GENERIC est compatible
            if not DEVICES_CLASS_MAPPING[cls_num]["GENERIC"] or generic in DEVICES_CLASS_MAPPING[cls_num]["GENERIC"]:
                zwave_class = cls_num
                break

    # 2. Appliquer le mapping initial (basé sur SUPPORTED_CLASSES, GENERIC, et PRODUCT_TYPE_ID)
    if zwave_class:
        # Vérifier si PRODUCT_TYPE_ID est défini dans DEVICES_CLASS_MAPPING
        if product_type_id and product_type_id in DEVICES_CLASS_MAPPING[zwave_class].get("PRODUCT_TYPE_ID", {}):
            product_mapping = DEVICES_CLASS_MAPPING[zwave_class]["PRODUCT_TYPE_ID"][product_type_id]
            mapping = {
                "ha_entity": product_mapping["ha_entity"],
                "ha_subtype": product_mapping.get("ha_subtype"),
                "justification": f"Classe {zwave_class} + PRODUCT_TYPE_ID={product_type_id}: {product_mapping['justification']}",
            }
        else:
            # Utiliser le mapping par défaut
            mapping = {
                "ha_entity": DEVICES_CLASS_MAPPING[zwave_class]["ha_entity"],
                "ha_subtype": DEVICES_CLASS_MAPPING[zwave_class].get("ha_subtype"),
                "justification": f"Classe {zwave_class} + GENERIC={generic}: {DEVICES_CLASS_MAPPING[zwave_class]['justification']}",
            }
        
        # Vérifier les exceptions basées sur SPECIFIC et le nom
        for exception in DEVICES_CLASS_MAPPING[zwave_class].get("exceptions", []):
            condition = exception["condition"]
            if "SPECIFIC=6" in condition and specific == "6":
                mapping = exception
                mapping["justification"] = f"Exception: {condition} for {device_data['name']}"
                break
            if "name contains 'Volet'" in condition and "Volet" in device_data.get("name", ""):
                mapping = exception
                mapping["justification"] = f"Exception: {condition} for {device_data['name']}"
                break
            if "name contains 'Shutter'" in condition and "Shutter" in device_data.get("name", ""):
                mapping = exception
                mapping["justification"] = f"Exception: {condition} for {device_data['name']}"
                break
            if "name contient 'Consigne'" in condition and "Consigne" in device_data.get("name", ""):
                mapping = exception
                mapping["justification"] = f"Exception: {condition} for {device_data['name']}"
                break

    else:
        mapping = USAGE_ID_MAPPING.get(device_data["usage_id"])

    if mapping is None:
        mapping = {"ha_entity": default_ha_entity, "ha_subtype": "unknown", "justification": "Unknown"}
        _LOGGER.warning("No mapping found for %s (%s) trying %s... data=%s", device_data["name"], device_data["periph_id"], mapping, device_data)

    _LOGGER.debug("Mapping for %s (%s) trying mapping=%s", device_data["name"], device_data["periph_id"], mapping)
    return mapping
