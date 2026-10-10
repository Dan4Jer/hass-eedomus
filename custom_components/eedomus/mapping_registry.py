"""Global mapping registry management."""

from __future__ import annotations
from .log import get_logger

_LOGGER = get_logger(__name__)

# Global list to store all the mappings
_MAPPING_REGISTRY = []


def register_device_mapping(
    mapping: dict,
    periph_name: str,
    periph_id: str,
    device_data: dict = None,
    entry_id: str = None,
) -> None:
    """Register a mapping in the global registry.

    entry_id ties the registration to the config entry whose
    coordinator produced it, so prune_mapping_registry can drop the
    entries of one entry (reload, unload, removal) without touching
    the other boxes' registrations.
    """
    if entry_id is None:
        # The resurrect-bug path made visible: an untagged registration
        # can never be pruned by the entry lifecycle, so a deleted
        # mapping would keep feeding the coherence identity join.
        _LOGGER.warning(
            "Device mapping registered without entry_id (%s, periph_id=%s): "
            "it cannot be pruned by the entry lifecycle",
            periph_name,
            periph_id,
        )
    parent_periph_id = device_data.get("parent_periph_id") if device_data else None
    _MAPPING_REGISTRY.append(
        {
            "periph_id": periph_id,
            "periph_name": periph_name,
            "parent_periph_id": parent_periph_id,
            "ha_entity": mapping["ha_entity"],
            "ha_subtype": mapping["ha_subtype"],
            "justification": mapping.get("justification", "No justification provided"),
            "entry_id": entry_id,
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


def prune_mapping_registry(entry_id: str = None) -> None:
    """Drop the mappings registered by one config entry.

    The registry is append-only across reloads, so a mapping deleted
    between two setups of the same entry would otherwise survive its
    own deletion and keep feeding the coherence identity join. A
    reload prunes first, then the (re)registered mappings reflect the
    current state; other entries' registrations are untouched.
    """
    if entry_id is None:
        return
    _MAPPING_REGISTRY[:] = [
        mapping
        for mapping in _MAPPING_REGISTRY
        if mapping.get("entry_id") != entry_id
    ]


def prune_mapping_registry_objects(entries: list) -> None:
    """Drop specific registration objects from the registry.

    Identity-based, never value equality: retires one entry's previous
    registration wave after its refresh has succeeded, leaving the
    fresh wave - which may contain equal-valued entries - untouched.
    """
    stale = {id(entry) for entry in entries}
    _MAPPING_REGISTRY[:] = [
        mapping
        for mapping in _MAPPING_REGISTRY
        if id(mapping) not in stale
    ]


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
