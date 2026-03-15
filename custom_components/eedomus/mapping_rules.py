"""Règles de mapping avancées pour les devices."""

from __future__ import annotations
import logging
from typing import Dict, Any

_LOGGER = logging.getLogger(__name__)


def evaluate_advanced_rules(device_data: dict, all_devices: dict, advanced_rules_dict: dict) -> dict | None:
    """Évalue les règles avancées pour un device."""
    periph_id = device_data["periph_id"]
    periph_name = device_data["name"]

    for rule_name, rule_config in advanced_rules_dict.items():
        _LOGGER.debug("🔍 Evaluating rule '%s' for device %s (%s)", rule_name, periph_name, periph_id)

        # Évaluer les conditions
        if "condition" in rule_config:
            condition_result = rule_config["condition"](device_data, all_devices)
        elif "conditions" in rule_config:
            condition_result = evaluate_conditions(rule_config["conditions"], device_data, all_devices, periph_id, rule_name)
        else:
            _LOGGER.warning("No condition or conditions found in rule: %s", rule_name)
            condition_result = False

        _LOGGER.debug("Advanced rule '%s' for %s (%s): condition_result=%s",
                     rule_name, periph_name, periph_id, condition_result)

        if condition_result:
            return rule_config["mapping"]

    return None


def evaluate_conditions(conditions: list, device_data: dict, all_devices: dict, periph_id: str, rule_name: str, parent_child_relations=None) -> bool:
    """Évalue une liste de conditions avec gestion optimisée des dépendances."""
    condition_result = True

    for condition in conditions:
        for cond_key, cond_value in condition.items():
            if cond_key == "usage_id":
                if device_data.get("usage_id") != cond_value:
                    condition_result = False
                    break
            elif cond_key == "min_children":
                if not all_devices:
                    condition_result = False
                    break
                # Utiliser les relations pré-calculées si disponibles pour éviter les scans coûteux
                if parent_child_relations and periph_id in parent_child_relations:
                    # Compter directement depuis les relations sans dépendre de all_devices
                    # Cela résout le problème de timing où all_devices peut être incomplet
                    children_count = len(parent_child_relations[periph_id])
                    _LOGGER.debug("🔍 Using parent_child_relations for min_children check: %d children found for %s",
                                 children_count, periph_id)
                else:
                    # Fallback à l'ancienne méthode si les relations ne sont pas disponibles
                    children = [
                        child for child_id, child in all_devices.items()
                        if child.get("parent_periph_id") == periph_id
                    ]
                    children_count = len(children)
                    _LOGGER.debug("🔍 Using fallback method for min_children check: %d children found for %s",
                                 children_count, periph_id)
                
                if children_count < int(cond_value):
                    condition_result = False
                    _LOGGER.debug("🔍 min_children condition failed: %d < %s for device %s",
                                 children_count, cond_value, periph_id)
                    # Special debug for device 1269454
                    if periph_id == "1269454":
                        _LOGGER.error("❌ CRITICAL: Device 1269454 RGBW mapping failed - only %d children found (need %s)",
                                    children_count, cond_value)
                        _LOGGER.error("❌ This device should have at least 4 children for RGBW mapping")
                        _LOGGER.error("❌ Check if all children are properly loaded in eedomus API")
                    break

            elif cond_key == "child_usage_id":
                if not all_devices:
                    condition_result = False
                    break
                children = [
                    child for child_id, child in all_devices.items()
                    if child.get("parent_periph_id") == periph_id and child.get("usage_id") == cond_value
                ]
                if len(children) < 1:
                    condition_result = False
                    break
            elif cond_key == "PRODUCT_TYPE_ID":
                if device_data.get("PRODUCT_TYPE_ID") != cond_value:
                    condition_result = False
                    break
            elif cond_key == "has_parent":
                if not device_data.get("parent_periph_id"):
                    condition_result = False
                    break
            elif cond_key == "parent_usage_id":
                if not device_data.get("parent_periph_id"):
                    condition_result = False
                    break
                parent_id = device_data.get("parent_periph_id")
                parent = all_devices.get(parent_id, {})
                if parent.get("usage_id") != cond_value:
                    condition_result = False
                    break
            elif cond_key == "parent_has_min_children":
                if not device_data.get("parent_periph_id"):
                    condition_result = False
                    break
                parent_id = device_data.get("parent_periph_id")
                # Utiliser les relations pré-calculées si disponibles
                if parent_child_relations and parent_id in parent_child_relations:
                    # Compter directement depuis les relations sans dépendre de all_devices
                    parent_children_count = len(parent_child_relations[parent_id])
                    _LOGGER.debug("🔍 Using parent_child_relations for parent_has_min_children check: parent %s has %d children",
                                 parent_id, parent_children_count)
                else:
                    # Fallback à l'ancienne méthode
                    parent_children = [
                        child for child_id, child in all_devices.items()
                        if child.get("parent_periph_id") == parent_id
                    ]
                    parent_children_count = len(parent_children)
                    _LOGGER.debug("🔍 Using fallback method for parent_has_min_children check: parent %s has %d children",
                                 parent_id, parent_children_count)
                
                if parent_children_count < int(cond_value):
                    condition_result = False
                    _LOGGER.debug("🔍 parent_has_min_children condition failed: parent %s has %d < %s children",
                                 parent_id, parent_children_count, cond_value)
                    break
            elif cond_key == "has_children_with_names":
                if not all_devices:
                    condition_result = False
                    break
                # Check if device has children with specific names
                required_names = cond_value if isinstance(cond_value, list) else [cond_value]
                children = [
                    child for child_id, child in all_devices.items()
                    if child.get("parent_periph_id") == periph_id
                ]
                child_names = [child.get("name", "").lower() for child in children]
                
                # Special debug for device 1269454
                if periph_id == "1269454":
                    for required_name in required_names:
                        found = any(required_name.lower() in child_name for child_name in child_names)
                        if found:
                            matching_children = [name for name in child_names if required_name.lower() in name]

                # Check if all required names are present in children
                all_found = all(
                    any(required_name.lower() in child_name for child_name in child_names)
                    for required_name in required_names
                )
                if not all_found:
                    condition_result = False
                    break
            else:
                _LOGGER.warning("Unknown condition key: %s", cond_key)
                condition_result = False
                break
        
        if not condition_result:
            break
    
    return condition_result
