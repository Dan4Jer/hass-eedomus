"""Unit test for the entity.py manifest-read failure path (ticket 117).

The module-level try/except reads manifest.json at import: when the
read fails, the except branch logs through _LOGGER. Before the fix the
assignment ran after the try, so the warning itself raised NameError
and killed the import. This test simulates the failing read on a
reload and asserts the import survives, VERSION falls back and the
warning is logged.
"""

import builtins
import importlib
import logging

import pytest

pytestmark = pytest.mark.unit


def test_manifest_read_failure_logs_instead_of_crashing(monkeypatch, caplog):
    """A failed manifest read logs a warning; the import survives."""
    import custom_components.eedomus.entity as entity_mod

    real_open = builtins.open

    def fake_open(file, *args, **kwargs):
        if str(file).endswith("manifest.json"):
            raise OSError("simulated unreadable manifest")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)
    caplog.set_level(logging.WARNING, logger="custom_components.eedomus.entity")
    version_after_failure = None
    try:
        importlib.reload(entity_mod)
        version_after_failure = entity_mod.VERSION
    finally:
        monkeypatch.undo()
        importlib.reload(entity_mod)

    assert version_after_failure == "unknown"
    assert entity_mod.VERSION != "unknown"
    assert "Failed to read version from manifest.json" in caplog.text
