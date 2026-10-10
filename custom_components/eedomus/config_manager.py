"""Configuration Manager for Eedomus Integration with HA 2026 features."""

from typing import Dict, Any, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import (
    DOMAIN,
    YAML_MAPPING_SCHEMA,
)
from .log import get_logger

_LOGGER = get_logger(__name__)

# AD-14bis: schema version of the stored custom mapping. A document saved
# before this field existed is the birth version (1): stamped, never
# migrated. Bump this and add a migration to _MAPPING_MIGRATIONS when the
# config grammar evolves.
MAPPING_CONFIG_SCHEMA_VERSION = 1

# Ordered schema migrations: target_version -> pure transform (dict) -> dict.
# A migration for target N upgrades the stored document from N-1 to N.
# Empty until the first real grammar change; the mechanism is the deliverable.
_MAPPING_MIGRATIONS: Dict[int, Any] = {}


class EedomusConfigManager:
    """Central configuration management with HA 2026 features."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the configuration manager."""
        self.hass = hass
        # Canonical custom mapping (AD-13): current + file_fingerprint.
        # The editable YAML file is a mirror, never the source of truth.
        self.mapping_store = Store(hass, 1, f"{DOMAIN}.mapping")
        # Version archive for the panel Historique tab (CAP-5): the three
        # most recent custom mapping versions live in HA storage.
        self.versions_store = Store(hass, 1, f"{DOMAIN}.mapping_versions")
        self._initialized = False
    
    async def async_init(self) -> None:
        """Initialize the configuration manager.

        AD-13: ingest the editable mirror file against the canonical
        storage. Domain-level init (single instance), never per entry.
        """
        try:
            await self._async_ingest_custom_mapping()
            self._initialized = True
            _LOGGER.info("Eedomus ConfigManager initialized successfully")
        except Exception as e:
            _LOGGER.error(f"Failed to initialize ConfigManager: {e}")
            raise

    async def async_shutdown(self) -> None:
        """Release resources."""
        _LOGGER.debug("Eedomus ConfigManager shutdown complete")

    async def async_get_custom_mapping(self) -> Dict[str, Any]:
        """Return the canonical custom mapping (AD-13: HA storage).

        Falls back to the editable file only when the storage holds no
        canon yet (first-boot bootstrap, before the init ingestion).
        """
        data = await self.mapping_store.async_load() or {}
        current = data.get("current")
        if isinstance(current, dict):
            return current

        from .device_mapping import async_get_canonical_custom_mapping

        return await async_get_canonical_custom_mapping(self.hass)

    async def async_save_custom_mapping(
        self, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Persist the custom mapping to the canonical storage (AD-13).

        Validates against the mapping schema, archives the replaced
        current in the version store (three kept, oldest purged on the
        fourth save), stores current + the fingerprint of the dumped
        text, then rewrites the editable mirror file so a reload finds
        no difference (no double version).

        Returns:
            {"success": bool, "error": str | None, "path": str | None}
        """
        import yaml

        try:
            _validate_mapping_config(config)
        except (vol.Invalid, cv.Invalid) as e:
            _LOGGER.error("Custom mapping validation failed: %s", e)
            return {"success": False, "error": str(e), "path": None}

        from .device_mapping import get_config_dir_custom_mapping_path

        path = get_config_dir_custom_mapping_path(self.hass)

        data = await self.mapping_store.async_load() or {}
        previous = data.get("current")
        # A save that changes nothing archives nothing (history stays
        # meaningful): only a real replacement creates a version.
        if isinstance(previous, dict) and previous and previous != config:
            await self.async_archive_mapping_version(previous)

        text = yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
        await self.mapping_store.async_save(
            {
                "current": config,
                "file_fingerprint": text,
                "config_schema_version": MAPPING_CONFIG_SCHEMA_VERSION,
            }
        )
        try:
            await self._async_write_mirror(text)
        except Exception as e:
            _LOGGER.error("Failed to write the custom mapping mirror: %s", e)
            return {"success": False, "error": str(e), "path": path}

        _LOGGER.info("Custom mapping saved (storage canon + mirror %s)", path)
        return {"success": True, "error": None, "path": path}

    async def _async_ingest_custom_mapping(self) -> None:
        """AD-13: delegate to the module-level ingestion (see its docstring)."""
        await async_ingest_custom_mapping(self.hass)

    async def _async_write_mirror(self, text: str) -> None:
        """Write the editable mirror file from the canon."""
        await _write_mapping_mirror(self.hass, text)

    async def async_archive_mapping_version(
        self, config: Dict[str, Any], reason: str = "save"
    ) -> bool:
        """Archive a mapping version in HA storage (three kept).

        The fourth save purges the oldest. The panel Historique tab
        (P.1.6) reads these versions back; the reason labels the origin
        (save / ingestion / migration).
        """
        await _archive_mapping_version(self.hass, config, reason)
        return True

    async def async_get_mapping_versions(self) -> list:
        """Return the archived mapping versions, newest first."""
        data = await self.versions_store.async_load() or {}
        return list(data.get("versions") or [])


def _validate_mapping_config(config: Dict[str, Any]) -> None:
    """Validate a custom mapping document against the YAML schema."""
    YAML_MAPPING_SCHEMA(config)


async def _async_migrate_mapping_document(hass: HomeAssistant) -> None:
    """AD-14bis: run pending schema migrations on the stored mapping.

    A document without config_schema_version predates the field: it is the
    birth version (1) - stamped, never migrated. Migrations run in target
    order while the stored version is below the current one. A successful
    migration archives the pre-migration canon as a version (reason
    "migration", traceable in the Historique) and regenerates the mirror
    and fingerprint from the migrated content. A failed migration keeps the
    canon untouched with an explicit warning - never destructive.
    """
    import copy

    import yaml

    store = Store(hass, 1, f"{DOMAIN}.mapping")
    data = await store.async_load() or {}
    current = data.get("current")
    if not isinstance(current, dict):
        # No canon yet: the bootstrap handles it (seed or empty).
        return

    version = data.get("config_schema_version")
    if version is None:
        # Birth version: stamp it, nothing to migrate.
        await store.async_save(
            {**data, "config_schema_version": MAPPING_CONFIG_SCHEMA_VERSION}
        )
        return

    if version >= MAPPING_CONFIG_SCHEMA_VERSION:
        return

    migrated = copy.deepcopy(current)
    for target in sorted(_MAPPING_MIGRATIONS):
        if version < target <= MAPPING_CONFIG_SCHEMA_VERSION:
            try:
                migrated = _MAPPING_MIGRATIONS[target](migrated)
            except Exception as e:
                _LOGGER.warning(
                    "Mapping schema migration to v%d failed (%s) - the "
                    "stored canon is kept as is",
                    target,
                    e,
                )
                return
            version = target

    await _archive_mapping_version(hass, current, reason="migration")
    dumped = yaml.safe_dump(migrated, sort_keys=False, allow_unicode=True)
    await store.async_save(
        {
            "current": migrated,
            "file_fingerprint": dumped,
            "config_schema_version": version,
        }
    )
    await _write_mapping_mirror(hass, dumped)
    _LOGGER.info(
        "Mapping schema migrated to v%d (previous canon archived)", version
    )


async def _archive_mapping_version(
    hass: HomeAssistant, config: Dict[str, Any], reason: str = "save"
) -> None:
    """Archive a mapping version in HA storage (three kept, oldest purged).

    The reason labels the archive for the Historique UI: save (panel),
    ingestion (manual file edit), migration (schema upgrade).
    """
    from datetime import datetime

    store = Store(hass, 1, f"{DOMAIN}.mapping_versions")
    data = await store.async_load() or {}
    versions = list(data.get("versions") or [])
    versions.insert(
        0,
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "config": config,
            "reason": reason,
        },
    )
    await store.async_save({"versions": versions[:3]})


async def _write_mapping_mirror(hass: HomeAssistant, text: str) -> None:
    """Write the editable mirror file from the canonical text."""
    import os

    from .device_mapping import get_config_dir_custom_mapping_path

    path = get_config_dir_custom_mapping_path(hass)

    def _write() -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    await hass.async_add_executor_job(_write)


async def async_ingest_custom_mapping(hass: HomeAssistant) -> None:
    """AD-13: compare the editable file to the storage canon at load time.

    Must run before anything reads the mapping (coordinator, entities):
    called at the top of async_setup_entry and by the ConfigManager init.

    - No canon yet: the file bootstraps the initial current (config-dir
      first, integrated file as shipped seed), then the mirror is written
      so the user always owns an editable surface.
    - File missing or unreadable: the mirror is regenerated from the canon
      (self-healing surface).
    - Raw text differs from the fingerprint: ingest as a new version when
      it validates (previous current archived, cap 3); an invalid file
      never overwrites the canon - the mirror is regenerated and a
      warning names the problem.
    """
    import yaml

    from .device_mapping import (
        get_config_dir_custom_mapping_path,
        get_custom_mapping_paths,
        read_custom_mapping_file,
    )

    # AD-14bis: migrations first - the comparison below must see the
    # migrated canon and its regenerated fingerprint.
    await _async_migrate_mapping_document(hass)

    store = Store(hass, 1, f"{DOMAIN}.mapping")
    data = await store.async_load() or {}
    current = data.get("current")
    fingerprint = data.get("file_fingerprint")

    config_dir_file = get_config_dir_custom_mapping_path(hass)
    paths = [config_dir_file] + [
        p for p in get_custom_mapping_paths() if p != config_dir_file
    ]
    text, parsed = await hass.async_add_executor_job(
        read_custom_mapping_file, paths
    )

    if not isinstance(current, dict):
        # Bootstrap: the file becomes the initial canon, stamped with the
        # current schema version (a bootstrap never runs migrations).
        canon = parsed if isinstance(parsed, dict) else {}
        dumped = yaml.safe_dump(canon, sort_keys=False, allow_unicode=True)
        await store.async_save(
            {
                "current": canon,
                "file_fingerprint": dumped,
                "config_schema_version": MAPPING_CONFIG_SCHEMA_VERSION,
            }
        )
        await _write_mapping_mirror(hass, dumped)
        _LOGGER.info("Custom mapping bootstrapped from the editable file")
        return

    canon_text = fingerprint or yaml.safe_dump(
        current, sort_keys=False, allow_unicode=True
    )

    if text is None:
        await _write_mapping_mirror(hass, canon_text)
        _LOGGER.info("Custom mapping mirror missing - regenerated from the canon")
        return

    if text == fingerprint:
        return

    if not isinstance(parsed, dict):
        _LOGGER.warning(
            "Custom mapping file changed but does not parse - the "
            "storage canon is kept and the mirror regenerated"
        )
        await _write_mapping_mirror(hass, canon_text)
        return

    try:
        _validate_mapping_config(parsed)
    except (vol.Invalid, cv.Invalid) as e:
        _LOGGER.warning(
            "Custom mapping file changed but is invalid (%s) - the "
            "storage canon is kept and the mirror regenerated",
            e,
        )
        await _write_mapping_mirror(hass, canon_text)
        return

    await _archive_mapping_version(hass, current, reason="ingestion")
    # An edited file derives from the current canon: its schema version is
    # the one already stamped (never dropped, or the next boot would
    # re-stamp to the current version and silently skip migrations).
    await store.async_save(
        {
            "current": parsed,
            "file_fingerprint": text,
            "config_schema_version": data.get(
                "config_schema_version", MAPPING_CONFIG_SCHEMA_VERSION
            ),
        }
    )
    _LOGGER.info("Custom mapping file ingested as a new version")
