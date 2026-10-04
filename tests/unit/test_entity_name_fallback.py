"""Unit tests for the translated entity name fallback (CAP-2, 3.4).

EedomusEntity must point its name at the native translation grammar
(entity.<domain>.<translation_key>.name) ONLY when the peripheral name is
absent or blank, and re-evaluate that state on every coordinator refresh
so a late-arriving real name replaces the translated fallback. A real
name (or a subclass-derived name) must never be overridden.
"""

from types import SimpleNamespace

import pytest

from custom_components.eedomus.entity import EedomusEntity

pytestmark = pytest.mark.unit


def make_coordinator(periphs=None):
    """Coordinator stub exposing .data like the real DataUpdateCoordinator."""
    return SimpleNamespace(
        data=periphs if periphs is not None else {},
        config_entry=SimpleNamespace(entry_id="entry_1"),
    )


class TestNameFallback:
    def test_named_peripheral_gets_no_translation(self):
        """A real name wins: no translation_key, has_entity_name False."""
        coordinator = make_coordinator({"100": {"name": "Salon"}})
        entity = EedomusEntity(coordinator, "100")

        assert entity._attr_name == "Salon"
        assert entity._attr_translation_key is None
        assert entity._attr_translation_placeholders is None
        assert entity._attr_has_entity_name is False

    def test_missing_name_sets_unknown_device_translation(self):
        """No name: translated fallback via the native entity grammar."""
        coordinator = make_coordinator({"100": {}})
        entity = EedomusEntity(coordinator, "100")

        assert not hasattr(entity, "_attr_name")
        assert entity._attr_translation_key == "unknown_device"
        assert entity._attr_translation_placeholders == {"periph_id": "100"}
        assert entity._attr_has_entity_name is True

    def test_blank_name_sets_unknown_device_translation(self):
        """A blank name (falsy after strip) is treated as unnamed."""
        coordinator = make_coordinator({"100": {"name": "   "}})
        entity = EedomusEntity(coordinator, "100")

        assert not hasattr(entity, "_attr_name")
        assert entity._attr_translation_key == "unknown_device"
        assert entity._attr_translation_placeholders == {"periph_id": "100"}

    def test_missing_periph_data_sets_unknown_device_translation(self):
        """No coordinator data at all: the fallback still translates."""
        coordinator = make_coordinator({})
        entity = EedomusEntity(coordinator, "100")

        assert entity._attr_translation_key == "unknown_device"
        assert entity._attr_translation_placeholders == {"periph_id": "100"}
        assert entity._parent_id is None

    def test_parent_peripheral_sets_unknown_parent_translation(self):
        """A nameless peripheral referenced as parent gets unknown_parent."""
        coordinator = make_coordinator(
            {
                "200": {},
                "100": {"parent_periph_id": "200"},
            }
        )
        entity = EedomusEntity(coordinator, "200")

        assert entity._attr_translation_key == "unknown_parent"
        assert entity._attr_translation_placeholders == {"parent_id": "200"}

    def test_late_arriving_name_replaces_the_fallback(self):
        """Coordinator refresh: the real name replaces the translation."""
        coordinator = make_coordinator({"100": {}})
        entity = EedomusEntity(coordinator, "100")
        assert entity._attr_translation_key == "unknown_device"

        coordinator.data["100"] = {"name": "Salon"}
        entity._handle_coordinator_update()

        assert entity._attr_name == "Salon"
        assert entity._attr_translation_key is None
        assert entity._attr_translation_placeholders is None
        assert entity._attr_has_entity_name is False

    def test_late_blank_name_restores_the_fallback(self):
        """Refresh to a blank name re-points the name at the translation."""
        coordinator = make_coordinator({"100": {"name": "Salon"}})
        entity = EedomusEntity(coordinator, "100")

        coordinator.data["100"] = {"name": " "}
        entity._handle_coordinator_update()

        assert not hasattr(entity, "_attr_name")
        assert entity._attr_translation_key == "unknown_device"
        assert entity._attr_translation_placeholders == {"periph_id": "100"}

    def test_subclass_derived_name_never_overridden(self):
        """A subclass name set after super().__init__ wins and is kept.

        The battery sensor derives its own name from the peripheral name;
        the fallback state must not survive next to it (has_entity_name
        would compose the device name into the friendly name).
        """
        coordinator = make_coordinator({"100": {}})
        entity = EedomusEntity(coordinator, "100")
        assert entity._attr_translation_key == "unknown_device"

        entity._attr_name = "Unknown Device Battery"
        entity._adopt_derived_name()

        coordinator.data["100"] = {"name": "Salon"}
        entity._handle_coordinator_update()

        assert entity._attr_name == "Unknown Device Battery"
        assert entity._attr_translation_key is None
        assert entity._attr_has_entity_name is False
