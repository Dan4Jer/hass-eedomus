"""Gestion du registre de mapping global pour l'intégration eedomus."""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Liste globale pour stocker tous les mappings
_MAPPING_REGISTRY: list[dict[str, Any]] = []


def register_device_mapping(
    mapping: dict[str, Any],
    periph_name: str,
    periph_id: str,
    device_data: dict[str, Any] | None = None,
) -> None:
    """Enregistre un mapping dans le registre global."""
    parent_periph_id = device_data.get("parent_periph_id") if device_data else None

    ha_entity = mapping.get("ha_entity", "unknown")
    ha_subtype = mapping.get("ha_subtype", "unknown")
    justification = mapping.get("justification", "No justification provided")

    _MAPPING_REGISTRY.append(
        {
            "periph_id": periph_id,
            "periph_name": periph_name,
            "parent_periph_id": parent_periph_id,
            "ha_entity": ha_entity,
            "ha_subtype": ha_subtype,
            "justification": justification,
        }
    )
    _LOGGER.debug(
        "✅ Device mapped: %s (%s) → %s:%s",
        periph_name,
        periph_id,
        ha_entity,
        ha_subtype,
    )


def clear_mapping_registry() -> None:
    """Réinitialise le registre de mapping (appelé lors du déchargement ou des tests)."""
    _MAPPING_REGISTRY.clear()


def get_mapping_registry() -> list[dict[str, Any]]:
    """Retourne une copie du registre de mapping."""
    return _MAPPING_REGISTRY.copy()


def print_mapping_table(box_name: str = "Box eedomus") -> None:
    """Affiche un tableau récapitulatif de tous les mappings dans les logs."""
    if not _MAPPING_REGISTRY:
        _LOGGER.warning(
            "⚠️  (%s) Mapping registry is empty - no devices were mapped!",
            box_name,
        )
        return

    _LOGGER.info("\n" + "=" * 120)
    _LOGGER.info(
        "| %-15s | %-30s | %-15s | %-10s | %-15s | %-50s |",
        "Periph ID",
        "Device Name",
        "Parent ID",
        "Type",
        "Subtype",
        "Justification",
    )
    _LOGGER.info("=" * 120)

    for mapping in _MAPPING_REGISTRY:
        # Formatage avec troncature propre
        name = mapping["periph_name"]
        formatted_name = f"{name[:28]}…" if len(name) > 29 else name

        justif = mapping["justification"]
        formatted_justif = f"{justif[:48]}…" if len(justif) > 49 else justif

        _LOGGER.info(
            "(%s) | %-15s | %-30s | %-15s | %-10s | %-15s | %-50s |",
            box_name,
            mapping["periph_id"],
            formatted_name,
            mapping.get("parent_periph_id") or "-",
            mapping["ha_entity"],
            mapping["ha_subtype"],
            formatted_justif,
        )

    _LOGGER.info("=" * 120 + "\n")
    _LOGGER.info("(%s) Total devices mapped: %d", box_name, len(_MAPPING_REGISTRY))
    _LOGGER.info(
        "⚠️  Note: This table shows only devices that went through map_device_to_ha_entity()"
    )
    _LOGGER.info("\n")


def print_mapping_summary(box_name: str = "Box eedomus") -> None:
    """Affiche un résumé condensé des mappings."""
    if not _MAPPING_REGISTRY:
        _LOGGER.warning(
            "⚠️  (%s) Mapping registry is empty - no devices were mapped!",
            box_name,
         )
        return

    entity_counts: dict[str, int] = {}
    for mapping in _MAPPING_REGISTRY:
        entity_type = f"{mapping['ha_entity']}:{mapping['ha_subtype']}"
        entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

    # Créer un résumé condensé sur une seule ligne
    type_summary = ", ".join(
        f"{count} {entity_type}"
        for entity_type, count in sorted(
            entity_counts.items(), key=lambda x: x[1], reverse=True
        )
    )
    _LOGGER.info(
        "ℹ️  Eedomus mapping: (%s) %d devices (%s) from %d API devices",
        box_name,
        len(_MAPPING_REGISTRY),
        type_summary,
        len({m["periph_id"] for m in _MAPPING_REGISTRY}),
    )

    # Détails en DEBUG pour ceux qui en ont besoin
    _LOGGER.debug(
        "Total unique periph_ids: (%s) %d",
        box_name,
        len({m["periph_id"] for m in _MAPPING_REGISTRY}),
    )
    _LOGGER.debug("Breakdown by type:")
    for entity_type, count in sorted(
        entity_counts.items(), key=lambda x: x[1], reverse=True
    ):
        _LOGGER.debug("  %s: %d", entity_type, count)
