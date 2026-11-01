"""Unit tests for the cleanup_unused_entities service (issue #136).

The service was dead (ImportError on a function that no longer exists)
behind a latent trap: a mono-box lookup that would have flagged every
entity orphan at once. These tests pin the repaired behavior: multi-box
id union, remap-aware domain criterion, the mass-deletion guard, and
the longest-digit heuristic for extracting the peripheral id.
"""

import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

import custom_components.eedomus.const as const  # noqa: E402

DOMAIN = const.DOMAIN
COORDINATOR = const.COORDINATOR


def _registry(entries):
    """Build a fake entity registry. Each entry: dict of its fields."""
    reg = MagicMock()
    reg.entities = {e["entity_id"]: SimpleNamespace(**e) for e in entries}
    removed = []
    reg.async_remove = lambda entity_id: removed.append(entity_id)
    return reg, removed


def _install_entity_registry(monkeypatch, registry):
    er_mod = types.ModuleType("homeassistant.helpers.entity_registry")
    er_mod.async_get = lambda hass: registry
    monkeypatch.setattr(
        sys.modules["homeassistant.helpers"],
        "entity_registry",
        er_mod,
        raising=False,
    )


def _hass_with_coordinators(*coordinator_datas):
    """hass stub carrying one coordinator per box (multi-box)."""
    hass = MagicMock()
    domain_data = {}
    for index, data in enumerate(coordinator_datas):
        coord = MagicMock()
        coord.data = data
        domain_data[f"entry_{index}"] = {COORDINATOR: coord}
    hass.data = {DOMAIN: domain_data}
    hass.services.has_service.return_value = False
    return hass


def _entity(entity_id, unique_id, *, device_id="dev", disabled=False):
    return {
        "entity_id": entity_id,
        "unique_id": unique_id,
        "platform": "eedomus",
        "disabled": disabled,
        "device_id": device_id,
    }


async def _get_cleanup_handler(hass):
    from custom_components.eedomus import services

    registered = {}
    hass.services.async_register.side_effect = (
        lambda domain, name, handler: registered.__setitem__(name, handler)
    )
    await services.async_setup_services(hass, MagicMock())
    return registered["cleanup_unused_entities"]


async def _run(monkeypatch, entries, *coordinator_datas):
    registry, removed = _registry(entries)
    _install_entity_registry(monkeypatch, registry)
    hass = _hass_with_coordinators(*coordinator_datas)
    handler = await _get_cleanup_handler(hass)
    result = await handler(MagicMock(data={}))
    return result, removed


@pytest.mark.asyncio
async def test_provided_entity_matching_domain_is_kept(monkeypatch):
    """Provided periph + matching domain: the entity survives."""
    result, removed = await _run(
        monkeypatch,
        [_entity("switch.prog_salon", "eedomus_1234567")],
        {"1234567": {"ha_entity": "switch"}},
    )
    assert result["success"] is True
    assert result["entities_identified"] == 0
    assert removed == []


@pytest.mark.asyncio
async def test_remap_duplicate_is_removed(monkeypatch):
    """Old-domain twin removed when the correctly-mapped one exists."""
    result, removed = await _run(
        monkeypatch,
        [
            _entity("switch.prog_salon", "eedomus_1234567"),
            _entity("sensor.prog_salon_old", "eedomus_1234567"),
        ],
        {"1234567": {"ha_entity": "switch"}},
    )
    assert result["success"] is True
    assert result["entities_removed"] == 1
    assert removed == ["sensor.prog_salon_old"]


@pytest.mark.asyncio
async def test_domain_mismatch_without_twin_is_kept(monkeypatch):
    """Mismatched domain but no mapped twin: conservative keep."""
    result, removed = await _run(
        monkeypatch,
        [_entity("sensor.prog_salon", "eedomus_1234567")],
        {"1234567": {"ha_entity": "switch"}},
    )
    assert result["success"] is True
    assert result["entities_identified"] == 0
    assert removed == []


@pytest.mark.asyncio
async def test_unprovided_periph_is_orphaned(monkeypatch):
    """A periph no box provides is an orphan."""
    result, removed = await _run(
        monkeypatch,
        [_entity("sensor.gone", "eedomus_9999999")],
        {"1234567": {"ha_entity": "switch"}},
    )
    assert result["success"] is True
    assert removed == ["sensor.gone"]


@pytest.mark.asyncio
async def test_prefix_digit_never_orphans(monkeypatch):
    """The periph id is the LONGEST digit segment: a digit in an entry
    prefix must not flag the entity (the old code's mass-deletion
    trigger)."""
    result, removed = await _run(
        monkeypatch,
        [_entity("switch.prog_salon", "eedomus_2_1234567")],
        {"1234567": {"ha_entity": "switch"}},
    )
    assert result["success"] is True
    assert result["entities_identified"] == 0
    assert removed == []


@pytest.mark.asyncio
async def test_disabled_entity_is_removed(monkeypatch):
    """Unchanged behavior: disabled entities are cleaned."""
    result, removed = await _run(
        monkeypatch,
        [_entity("sensor.off", "eedomus_1234567", disabled=True)],
        {"1234567": {"ha_entity": "sensor"}},
    )
    assert result["success"] is True
    assert removed == ["sensor.off"]


@pytest.mark.asyncio
async def test_mass_deletion_guard_refuses(monkeypatch):
    """Over half the considered entities flagged: the run is refused
    (issue #136's trap must never fire again, even on new bugs)."""
    # 12 orphans among 12 considered entities: over half of a
    # substantial set - refused. (A handful of flagged entities is a
    # legitimate small cleanup and must go through.)
    result, removed = await _run(
        monkeypatch,
        [_entity(f"sensor.orphan_{i}", f"eedomus_{1111111 + i}") for i in range(12)],
        {"9999999": {"ha_entity": "sensor"}},
    )
    assert result["success"] is False
    assert result["entities_removed"] == 0
    assert "refused" in result["error"]
    assert removed == []


@pytest.mark.asyncio
async def test_multi_box_union_protects_both_boxes(monkeypatch):
    """A periph provided by EITHER box is never an orphan (issue #102's
    lesson applied to cleanup)."""
    result, removed = await _run(
        monkeypatch,
        [
            _entity("switch.box1_dev", "eedomus_1234567"),
            _entity("switch.box2_dev", "eedomus_7654321"),
        ],
        {"1234567": {"ha_entity": "switch"}},
        {"7654321": {"ha_entity": "switch"}},
    )
    assert result["success"] is True
    assert result["entities_identified"] == 0
    assert removed == []
