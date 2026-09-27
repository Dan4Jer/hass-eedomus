"""Unit tests for history value resolution via value_list (coordinator.py).

Regression tests for the "Skipping invalid data point: could not convert
string to float: 'Confort'" warnings: the history API returns value labels
for list-type peripherals, and the numeric value must be resolved from the
peripheral's value_list (data[periph_id]["values"], from periph.value_list).
"""

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.coordinator import EedomusDataUpdateCoordinator

pytestmark = pytest.mark.unit

PERIPH_ID = "72762"

VALUES = [
    {"value": "0", "description": "Arrêt", "icon": "off.png"},
    {"value": "100", "description": "Confort", "icon": "on.png"},
]


def make_coordinator():
    """Build a coordinator whose peripheral has a value_list."""
    coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=MagicMock())
    coordinator.data = {
        PERIPH_ID: {
            "periph_id": PERIPH_ID,
            "name": "Thermostat Salon",
            "values": VALUES,
        }
    }
    return coordinator


class TestResolveHistoryValue:
    def test_numeric_value_passes_through(self):
        coordinator = make_coordinator()
        assert coordinator._resolve_history_value(PERIPH_ID, "21.5") == 21.5
        assert coordinator._resolve_history_value(PERIPH_ID, 20) == 20.0

    def test_label_resolved_from_values_list(self):
        coordinator = make_coordinator()
        assert coordinator._resolve_history_value(PERIPH_ID, "Confort") == 100.0
        assert coordinator._resolve_history_value(PERIPH_ID, "Arrêt") == 0.0

    def test_unknown_label_returns_none(self):
        coordinator = make_coordinator()
        assert coordinator._resolve_history_value(PERIPH_ID, "Hors-Gel") is None

    def test_no_values_list_returns_none_for_label(self):
        coordinator = make_coordinator()
        coordinator.data[PERIPH_ID]["values"] = []
        assert coordinator._resolve_history_value(PERIPH_ID, "Confort") is None

    def test_unknown_periph_returns_none_for_label(self):
        coordinator = make_coordinator()
        assert coordinator._resolve_history_value("999999", "Confort") is None

    def test_non_numeric_mapped_value_returns_none(self):
        coordinator = make_coordinator()
        coordinator.data[PERIPH_ID]["values"] = [
            {"value": "abc", "description": "Confort"}
        ]
        assert coordinator._resolve_history_value(PERIPH_ID, "Confort") is None


@pytest.mark.asyncio
async def test_statistics_import_resolves_labels():
    """Labels are converted to their numeric value in the statistics import."""
    coordinator = make_coordinator()
    coordinator.hass.services.async_call = AsyncMock()
    chunk = [
        {"value": "Confort", "timestamp": "2026-09-27T09:00:00"},
        {"value": "20.5", "timestamp": "2026-09-27T09:30:00"},
    ]

    await coordinator._import_via_statistics(
        f"sensor.eedomus_{PERIPH_ID}", chunk, "Thermostat Salon", PERIPH_ID
    )

    coordinator.hass.services.async_call.assert_awaited_once()
    call = coordinator.hass.services.async_call.await_args
    service_data = call.kwargs["service_data"]
    # Spook's recorder.import_statistics schema: no "entity_id" field
    assert service_data["statistic_id"] == f"sensor.eedomus_{PERIPH_ID}"
    assert service_data["source"] == "recorder"
    assert service_data["name"] == "Thermostat Salon"
    assert service_data["has_mean"] is True
    assert service_data["has_sum"] is False
    statistics = service_data["stats"]
    # Both points fall in hour 09:00: they are aggregated into ONE
    # hourly statistic (mean/min/max), HA requires top-of-the-hour starts
    assert len(statistics) == 1
    assert statistics[0]["mean"] == 60.25
    assert statistics[0]["min"] == 20.5
    assert statistics[0]["max"] == 100.0
    # "state" is the most recent value within the hour
    assert statistics[0]["state"] == 20.5
    assert statistics[0]["start"].minute == 0
    # HA statistics require timezone-aware start datetimes
    assert statistics[0]["start"].tzinfo is not None
    assert "entity_id" not in statistics[0]


@pytest.mark.asyncio
async def test_statistics_import_aggregates_per_hour():
    """Points in different hours produce one statistic per hour."""
    coordinator = make_coordinator()
    coordinator.hass.services.async_call = AsyncMock()
    chunk = [
        {"value": "10", "timestamp": "2026-09-27T08:15:00"},
        {"value": "30", "timestamp": "2026-09-27T08:45:00"},
        {"value": "50", "timestamp": "2026-09-27T09:10:00"},
    ]

    await coordinator._import_via_statistics(
        f"sensor.eedomus_{PERIPH_ID}", chunk, "Thermostat Salon", PERIPH_ID
    )

    stats = coordinator.hass.services.async_call.await_args.kwargs["service_data"][
        "stats"
    ]
    assert len(stats) == 2
    assert stats[0]["start"].hour == 8
    assert stats[0]["mean"] == 20.0
    assert stats[0]["state"] == 30.0
    assert stats[1]["start"].hour == 9
    assert stats[1]["mean"] == 50.0


@pytest.mark.asyncio
async def test_statistics_import_skips_unresolvable_label(caplog):
    """A label with no value_list entry is skipped with one warning per point."""
    coordinator = make_coordinator()
    coordinator.hass.services.async_call = AsyncMock()
    chunk = [
        {"value": "Hors-Gel", "timestamp": "2026-09-27T09:00:00"},
        {"value": "Arrêt", "timestamp": "2026-09-27T09:30:00"},
    ]
    caplog.set_level(logging.WARNING, logger="custom_components.eedomus.coordinator")

    await coordinator._import_via_statistics(
        f"sensor.eedomus_{PERIPH_ID}", chunk, "Thermostat Salon", PERIPH_ID
    )

    skip_warnings = [
        record
        for record in caplog.records
        if "Skipping invalid data point" in record.message
    ]
    assert len(skip_warnings) == 1
    assert "Hors-Gel" in skip_warnings[0].getMessage()
    # The valid point is still imported
    call = coordinator.hass.services.async_call.await_args
    statistics = call.kwargs["service_data"]["stats"]
    assert len(statistics) == 1
    assert statistics[0]["mean"] == 0.0


@pytest.mark.asyncio
async def test_async_set_fallback_resolves_labels():
    """The async_set fallback converts labels to numeric states too."""
    coordinator = make_coordinator()
    coordinator.hass.services.async_call = AsyncMock(
        side_effect=Exception("service not found")
    )
    coordinator.hass.states.async_set = MagicMock()
    chunk = [
        {"value": "Confort", "timestamp": "2026-09-27T09:00:00"},
        {"value": "20.5", "timestamp": "2026-09-27T09:30:00"},
    ]

    await coordinator._fallback_import_history_chunk(PERIPH_ID, chunk)

    states_set = coordinator.hass.states.async_set.call_args_list
    assert len(states_set) == 2
    # Integer list values stay readable ("100", not "100.0")
    assert states_set[0].args[1] == "100"
    assert states_set[1].args[1] == "20.5"


def _fake_registry(monkeypatch, entries):
    """Patch the entity_registry stub with fake registry entries."""
    from homeassistant.helpers import entity_registry as er

    registry = SimpleNamespace(
        entities={
            str(i): SimpleNamespace(
                platform=platform, unique_id=unique_id, entity_id=entity_id
            )
            for i, (platform, unique_id, entity_id) in enumerate(entries)
        }
    )
    monkeypatch.setattr(er, "async_get", lambda hass: registry)


def test_resolve_main_entity_id_exact_match(monkeypatch):
    """The peripheral's main entity is found by its base unique_id."""
    _fake_registry(
        monkeypatch,
        [
            ("other", "01TEST_999", "sensor.other"),
            ("eedomus", "01TEST_72762", "sensor.temperature_salon"),
            ("eedomus", "01TEST_72762_select", "select.mode_salon"),
        ],
    )
    coordinator = make_coordinator()
    coordinator.config_entry = SimpleNamespace(entry_id="01TEST")
    assert coordinator._resolve_main_entity_id(PERIPH_ID) == "sensor.temperature_salon"


def test_resolve_main_entity_id_suffixed_fallback(monkeypatch):
    """Without an exact match, a suffixed unique_id (e.g. _select) is used."""
    _fake_registry(
        monkeypatch,
        [("eedomus", "01TEST_72762_select", "select.mode_salon")],
    )
    coordinator = make_coordinator()
    coordinator.config_entry = SimpleNamespace(entry_id="01TEST")
    assert coordinator._resolve_main_entity_id(PERIPH_ID) == "select.mode_salon"


def test_resolve_main_entity_id_no_match(monkeypatch):
    """No eedomus entry for the peripheral returns None."""
    _fake_registry(monkeypatch, [("other", "01TEST_999", "sensor.other")])
    coordinator = make_coordinator()
    coordinator.config_entry = SimpleNamespace(entry_id="01TEST")
    assert coordinator._resolve_main_entity_id(PERIPH_ID) is None


@pytest.mark.asyncio
async def test_import_targets_real_entity_when_registered(monkeypatch):
    """The Statistics import uses the peripheral's real entity_id when found."""
    _fake_registry(
        monkeypatch,
        [("eedomus", "01TEST_72762", "light.rubanled_salon_2")],
    )
    coordinator = make_coordinator()
    coordinator.config_entry = SimpleNamespace(entry_id="01TEST")
    coordinator.hass.services.async_call = AsyncMock()
    chunk = [{"value": "100", "timestamp": "2026-09-27T09:00:00"}]

    await coordinator._fallback_import_history_chunk(PERIPH_ID, chunk)

    service_data = coordinator.hass.services.async_call.await_args.kwargs[
        "service_data"
    ]
    assert service_data["statistic_id"] == "light.rubanled_salon_2"


@pytest.mark.asyncio
async def test_async_set_fallback_targets_real_entity(monkeypatch):
    """When Statistics fails, async_set also targets the real entity."""
    _fake_registry(
        monkeypatch,
        [("eedomus", "01TEST_72762", "light.rubanled_salon_2")],
    )
    coordinator = make_coordinator()
    coordinator.config_entry = SimpleNamespace(entry_id="01TEST")
    coordinator.hass.services.async_call = AsyncMock(
        side_effect=Exception("service not found")
    )
    coordinator.hass.states.async_set = MagicMock()
    chunk = [{"value": "100", "timestamp": "2026-09-27T09:00:00"}]

    await coordinator._fallback_import_history_chunk(PERIPH_ID, chunk)

    states_set = coordinator.hass.states.async_set.call_args_list
    assert len(states_set) == 1
    assert states_set[0].args[0] == "light.rubanled_salon_2"
