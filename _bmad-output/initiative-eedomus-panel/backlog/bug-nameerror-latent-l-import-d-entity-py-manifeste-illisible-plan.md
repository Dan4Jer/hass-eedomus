---
ticket: story-entity-manifest-nameerror
status: built
---

# Plan — ticket 117 (entity.py NameError on manifest-read failure)

Built 2026-10-10 inline by the orchestrator (5-line reorder, plan written post-build).

## What was built

- `entity.py`: `_LOGGER = get_logger(__name__)` moved above the manifest-read `try` — the `except` branch can now log its warning instead of raising `NameError` and killing the module import.

## Verification

- `tests/unit/test_entity_manifest_failure.py` — NEW: simulates an unreadable manifest.json on a reload, asserts `VERSION == "unknown"` at failure time, the module restores cleanly afterwards, and the warning is logged. Fails with NameError on the pre-fix code.
- `python3 -m pytest tests/unit/ -q` — 432 passed.

## Residual

None.
