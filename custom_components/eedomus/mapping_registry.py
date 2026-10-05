"""Global mapping registry management."""

from __future__ import annotations
import logging

_LOGGER = logging.getLogger(__name__)

# Global list to store all the mappings
_MAPPING_REGISTRY = []


def register_device_mapping(
    mapping: dict, periph_name: str, periph_id: str, device_data: dict = None
) -> None:
    """Register a mapping in the global registry."""
    parent_periph_id = device_data.get("parent_periph_id") if device_data else None
    _MAPPING_REGISTRY.append(
        {
            "periph_id": periph_id,
            "periph_name": periph_name,
            "parent_periph_id": parent_periph_id,
            "ha_entity": mapping["ha_entity"],
            "ha_subtype": mapping["ha_subtype"],
            "justification": mapping.get("justification", "No justification provided"),
        }
    )
    _LOGGER.debug(
        "✅ Device mapped: %s (%s) → %s:%s",
        periph_name,
        periph_id,
        mapping["ha_entity"],
        mapping["ha_subtype"],
    )


def clear_mapping_registry() -> None:
    """Reset the mapping registry."""
    _MAPPING_REGISTRY.clear()


def get_mapping_registry() -> list:
    """Return the mapping registry."""
    return _MAPPING_REGISTRY.copy()


def print_mapping_table() -> None:
    """Print a summary table of all the mappings.

    The full table is at DEBUG: one line per peripheral floods the
    logs at boot ("logging too frequently"). Only the count stays
    at INFO.
    """
    if not _MAPPING_REGISTRY:
        _LOGGER.warning("⚠️  Mapping registry is empty - no devices were mapped!")
        return

    _LOGGER.info(
        "Eedomus mapping table: %d devices (detail at debug level)",
        len(_MAPPING_REGISTRY),
    )

    _LOGGER.debug("\n" + "=" * 120)
    _LOGGER.debug(
        "| %-15s | %-30s | %-15s | %-10s | %-15s | %-50s |",
        "Periph ID",
        "Device Name",
        "Parent ID",
        "Type",
        "Subtype",
        "Justification",
    )
    _LOGGER.debug("=" * 120)

    for mapping in _MAPPING_REGISTRY:
        _LOGGER.debug(
            "| %-15s | %-30s | %-15s | %-10s | %-15s | %-50s |",
            mapping["periph_id"],
            mapping["periph_name"][:29],
            mapping.get("parent_periph_id", "") or "-",
            mapping["ha_entity"],
            mapping["ha_subtype"],
            mapping["justification"][:49],
        )

    _LOGGER.debug("=" * 120 + "\n")
    _LOGGER.debug("Total devices mapped: %d", len(_MAPPING_REGISTRY))


def print_mapping_summary() -> None:
    """Print a condensed mapping summary."""
    if not _MAPPING_REGISTRY:
        _LOGGER.warning("⚠️  Mapping registry is empty - no devices were mapped!")
        return

    # Count by type for the condensed summary
    entity_counts = {}
    for mapping in _MAPPING_REGISTRY:
        entity_type = f"{mapping['ha_entity']}:{mapping['ha_subtype']}"
        entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

    # Build a condensed one-line summary
    type_summary = ", ".join(
        f"{count} {entity_type}"
        for entity_type, count in sorted(
            entity_counts.items(), key=lambda x: x[1], reverse=True
        )
    )
    _LOGGER.info(
        "ℹ️  Eedomus mapping: %d devices (%s) from %d API devices",
        len(_MAPPING_REGISTRY),
        type_summary,
        len(set(m["periph_id"] for m in _MAPPING_REGISTRY)),
    )

    # Details at DEBUG for those who need them
    _LOGGER.debug(
        "Total unique periph_ids: %d",
        len(set(m["periph_id"] for m in _MAPPING_REGISTRY)),
    )
    _LOGGER.debug("Breakdown by type:")
    for entity_type, count in sorted(
        entity_counts.items(), key=lambda x: x[1], reverse=True
    ):
        _LOGGER.debug("  %s: %d", entity_type, count)
