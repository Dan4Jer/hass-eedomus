"""Règles de mapping avancées pour les périphériques eedomus."""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def evaluate_conditions(
    conditions: list[dict[str, Any]],
    device_data: dict[str, Any],
    all_devices: dict[str, dict[str, Any]],
    periph_id: str,
    rule_name: str,
    parent_child_relations: dict[str, list[str]] | None = None,
) -> bool:
    """Évalue une liste de conditions avec gestion optimisée des dépendances."""
    for condition in conditions:
        for cond_key, cond_value in condition.items():
            if cond_key == "usage_id":
                if device_data.get("usage_id") != cond_value:
                    return False

            elif cond_key == "min_children":
                try:
                    target_count = int(cond_value)
                except (ValueError, TypeError):
                    _LOGGER.error(
                        "Invalid min_children value '%s' in rule %s",
                        cond_value,
                        rule_name,
                    )
                    return False

                # Utiliser les relations pré-calculées si disponibles
                if parent_child_relations and periph_id in parent_child_relations:
                    # Compter directement depuis les relations sans dépendre de all_devices
                    # Cela résout le problème de timing où all_devices peut être incomplet
                    children_count = len(parent_child_relations[periph_id])
                    _LOGGER.debug(
                        "🔍 Using parent_child_relations for min_children check: %d children found for %s",
                        children_count,
                        periph_id,
                    )
                elif all_devices:
                    # Fallback si les relations pré-calculées ne sont pas transmises
                    children = [
                        child
                        for child in all_devices.values()
                        if child.get("parent_periph_id") == periph_id
                    ]
                    children_count = len(children)
                    _LOGGER.debug(
                        "🔍 Using fallback method for min_children check: %d children found for %s",
                        children_count,
                        periph_id,
                    )
                else:
                    return False

                if children_count < target_count:
                    _LOGGER.debug(
                        "🔍 min_children condition failed: %d < %d for device %s",
                        children_count,
                        target_count,
                        periph_id,
                    )
                    return False

            elif cond_key == "child_usage_id":
                if not all_devices:
                    return False

                has_matching_child = any(
                    child.get("parent_periph_id") == periph_id
                    and child.get("usage_id") == cond_value
                    for child in all_devices.values()
                )
                if not has_matching_child:
                    return False

            elif cond_key == "PRODUCT_TYPE_ID":
                if device_data.get("PRODUCT_TYPE_ID") != cond_value:
                    return False

            elif cond_key == "has_parent":
                if not device_data.get("parent_periph_id"):
                    return False

            elif cond_key == "parent_usage_id":
                parent_id = device_data.get("parent_periph_id")
                if not parent_id or not all_devices:
                    return False

                parent = all_devices.get(parent_id, {})
                if parent.get("usage_id") != cond_value:
                    return False

            elif cond_key == "parent_has_min_children":
                parent_id = device_data.get("parent_periph_id")
                if not parent_id:
                    return False

                try:
                    target_count = int(cond_value)
                except (ValueError, TypeError):
                    _LOGGER.error(
                        "Invalid parent_has_min_children value '%s' in rule %s",
                        cond_value,
                        rule_name,
                    )
                    return False

                # Utiliser les relations pré-calculées si disponibles
                if parent_child_relations and parent_id in parent_child_relations:
                    # Compter directement depuis les relations sans dépendre de all_devices
                    parent_children_count = len(parent_child_relations[parent_id])
                    _LOGGER.debug(
                        "🔍 Using parent_child_relations for parent_has_min_children check: parent %s has %d children",
                        parent_id,
                        parent_children_count,
                    )
                elif all_devices:
                    parent_children = [
                        child
                        for child in all_devices.values()
                        if child.get("parent_periph_id") == parent_id
                    ]
                    parent_children_count = len(parent_children)
                    _LOGGER.debug(
                        "🔍 Using fallback method for parent_has_min_children check: parent %s has %d children",
                        parent_id,
                        parent_children_count,
                    )
                else:
                    return False

                if parent_children_count < target_count:
                    _LOGGER.debug(
                        "🔍 parent_has_min_children condition failed: parent %s has %d < %d children",
                        parent_id,
                        parent_children_count,
                        target_count,
                    )
                    return False

            elif cond_key == "has_children_with_names":
                if not all_devices:
                    return False

                required_names = (
                    cond_value if isinstance(cond_value, list) else [cond_value]
                )
                child_names = [
                    child.get("name", "").lower()
                    for child in all_devices.values()
                    if child.get("parent_periph_id") == periph_id
                ]

                all_found = all(
                    any(
                        req_name.lower() in child_name
                        for child_name in child_names
                    )
                    for req_name in required_names
                )
                if not all_found:
                    return False

            else:
                _LOGGER.warning("Unknown condition key: %s", cond_key)
                return False

    return True
