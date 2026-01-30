"""Gestion du registre de mapping global."""

from __future__ import annotations
import logging

_LOGGER = logging.getLogger(__name__)

# Liste globale pour stocker tous les mappings
_MAPPING_REGISTRY = []


def register_device_mapping(mapping: dict, periph_name: str, periph_id: str, device_data: dict = None) -> None:
    """Enregistre un mapping dans le registre global."""
    parent_periph_id = device_data.get("parent_periph_id") if device_data else None
    _MAPPING_REGISTRY.append({
        "periph_id": periph_id,
        "periph_name": periph_name,
        "parent_periph_id": parent_periph_id,
        "ha_entity": mapping["ha_entity"],
        "ha_subtype": mapping["ha_subtype"],
        "justification": mapping.get("justification", "No justification provided")
    })
    _LOGGER.debug("✅ Device mapped: %s (%s) → %s:%s", periph_name, periph_id, mapping["ha_entity"], mapping["ha_subtype"])


def clear_mapping_registry() -> None:
    """Réinitialise le registre de mapping."""
    _MAPPING_REGISTRY.clear()


def get_mapping_registry() -> list:
    """Retourne le registre de mapping."""
    return _MAPPING_REGISTRY.copy()


def print_mapping_table() -> None:
    """Affiche un tableau récapitulatif de tous les mappings."""
    if not _MAPPING_REGISTRY:
        _LOGGER.warning("⚠️  Mapping registry is empty - no devices were mapped!")
        return

    _LOGGER.info("\n" + "="*120)
    _LOGGER.info("| %-15s | %-30s | %-15s | %-10s | %-15s | %-50s |",
                 "Periph ID", "Device Name", "Parent ID", "Type", "Subtype", "Justification")
    _LOGGER.info("="*120)

    for mapping in _MAPPING_REGISTRY:
        _LOGGER.info("| %-15s | %-30s | %-15s | %-10s | %-15s | %-50s |",
                     mapping["periph_id"],
                     mapping["periph_name"][:29],
                     mapping.get("parent_periph_id", "") or "-",
                     mapping["ha_entity"],
                     mapping["ha_subtype"],
                     mapping["justification"][:49])

    _LOGGER.info("="*120 + "\n")
    _LOGGER.info("Total devices mapped: %d", len(_MAPPING_REGISTRY))
    _LOGGER.info("⚠️  Note: This table shows only devices that went through map_device_to_ha_entity()")
    _LOGGER.info("\n")


def print_mapping_summary() -> None:
    """Affiche un résumé des mappings et vérifie si tous les devices sont mappés."""
    if not _MAPPING_REGISTRY:
        _LOGGER.warning("⚠️  Mapping registry is empty - no devices were mapped!")
        return

    _LOGGER.info("\n" + "="*120)
    _LOGGER.info("MAPPING SUMMARY")
    _LOGGER.info("="*120)
    _LOGGER.info("Total devices mapped: %d", len(_MAPPING_REGISTRY))
    _LOGGER.info("Total unique periph_ids: %d", len(set(m["periph_id"] for m in _MAPPING_REGISTRY)))
    
    # Compter par type
    entity_counts = {}
    for mapping in _MAPPING_REGISTRY:
        entity_type = f"{mapping['ha_entity']}:{mapping['ha_subtype']}"
        entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1
    
    _LOGGER.info("\nBreakdown by type:")
    for entity_type, count in sorted(entity_counts.items(), key=lambda x: x[1], reverse=True):
        _LOGGER.info("  %s: %d", entity_type, count)
    
    _LOGGER.info("="*120 + "\n")
