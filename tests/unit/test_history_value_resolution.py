"""Unit tests for history value resolution via value_list (coordinator.py).

Regression tests for the "Skipping invalid data point: could not convert
string to float: 'Confort'" warnings: the history API returns value labels
for list-type peripherals, and the numeric value must be resolved from the
peripheral's value_list (data[periph_id]["values"], from periph.value_list).

The ghost sensor.eedomus_<periph_id> targets below are a deliberate bypass:
_import_via_statistics is called directly to test the hourly aggregation in
isolation. H.1.3 will purge them from the fetch path.
"""

import logging
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.recorder.models import StatisticMeanType

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


def configure_statistics_harness(coordinator, unit="°C"):
    """Wire hass and the recorder.statistics stubs for the import path."""
    from homeassistant.components.recorder import statistics as rec_stats

    rec_stats.async_import_statistics.reset_mock(side_effect=True)
    rec_stats.statistics_during_period.reset_mock(side_effect=True)
    rec_stats.statistics_during_period.return_value = {}
    coordinator.hass.states.get = MagicMock(
        return_value=SimpleNamespace(attributes={"unit_of_measurement": unit})
    )

    async def _run_in_executor(fn, *args, **kwargs):
        return fn(*args, **kwargs)

    coordinator.hass.async_add_executor_job = _run_in_executor
    return rec_stats


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
    rec_stats = configure_statistics_harness(coordinator)
    chunk = [
        {"value": "Confort", "timestamp": "2026-09-27T09:00:00"},
        {"value": "20.5", "timestamp": "2026-09-27T09:30:00"},
    ]

    await coordinator._import_via_statistics(
        f"sensor.eedomus_{PERIPH_ID}", chunk, "Thermostat Salon", PERIPH_ID
    )

    rec_stats.async_import_statistics.assert_called_once()
    _hass, metadata, statistics = rec_stats.async_import_statistics.call_args.args
    assert metadata["statistic_id"] == f"sensor.eedomus_{PERIPH_ID}"
    assert metadata["source"] == "recorder"
    assert metadata["name"] == "Thermostat Salon"
    assert metadata["mean_type"] == StatisticMeanType.ARITHMETIC
    assert metadata["has_sum"] is False
    assert metadata["unit_of_measurement"] == "°C"
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
    rec_stats = configure_statistics_harness(coordinator)
    chunk = [
        {"value": "10", "timestamp": "2026-09-27T08:15:00"},
        {"value": "30", "timestamp": "2026-09-27T08:45:00"},
        {"value": "50", "timestamp": "2026-09-27T09:10:00"},
    ]

    await coordinator._import_via_statistics(
        f"sensor.eedomus_{PERIPH_ID}", chunk, "Thermostat Salon", PERIPH_ID
    )

    _hass, _metadata, stats = rec_stats.async_import_statistics.call_args.args
    assert len(stats) == 2
    assert stats[0]["start"].hour == 8
    assert stats[0]["mean"] == 20.0
    assert stats[0]["state"] == 30.0
    assert stats[1]["start"].hour == 9
    assert stats[1]["mean"] == 50.0


@pytest.mark.asyncio
async def test_statistics_import_skips_unresolvable_label(caplog):
    """A label with no value_list entry is skipped with one aggregate
    warning per chunk; the per-point detail is debug-level."""
    coordinator = make_coordinator()
    rec_stats = configure_statistics_harness(coordinator)
    chunk = [
        {"value": "Hors-Gel", "timestamp": "2026-09-27T09:00:00"},
        {"value": "Arrêt", "timestamp": "2026-09-27T09:30:00"},
    ]
    caplog.set_level(logging.WARNING, logger="custom_components.eedomus.coordinator")

    await coordinator._import_via_statistics(
        f"sensor.eedomus_{PERIPH_ID}", chunk, "Thermostat Salon", PERIPH_ID
    )

    skip_warnings = [
        record for record in caplog.records if "history points for" in record.message
    ]
    assert len(skip_warnings) == 1
    message = skip_warnings[0].getMessage()
    assert "Skipped 1 of 2" in message
    assert "Hors-Gel" in message
    # The valid point is still imported
    _hass, _metadata, statistics = rec_stats.async_import_statistics.call_args.args
    assert len(statistics) == 1
    assert statistics[0]["mean"] == 0.0


@pytest.mark.asyncio
async def test_statistics_failure_never_writes_states(monkeypatch, caplog):
    """A failed statistics import is skipped; no state is ever written.

    Regression test for the recorder lock-up: replaying backdated history
    points through hass.states.async_set flooded the recorder with writes
    that never committed.
    """
    _fake_registry(
        monkeypatch,
        [("eedomus", "01TEST_72762", "sensor.temperature_salon")],
    )
    coordinator = make_coordinator()
    coordinator.config_entry = SimpleNamespace(entry_id="01TEST")
    rec_stats = configure_statistics_harness(coordinator)
    rec_stats.async_import_statistics = MagicMock(
        side_effect=Exception("database is locked")
    )
    coordinator.hass.states.async_set = MagicMock()
    caplog.set_level(logging.WARNING, logger="custom_components.eedomus.coordinator")
    chunk = [
        {"value": "Confort", "timestamp": "2026-09-27T09:00:00"},
        {"value": "20.5", "timestamp": "2026-09-27T09:30:00"},
    ]

    await coordinator.async_import_history_chunk(PERIPH_ID, chunk)

    rec_stats.async_import_statistics.assert_called_once()
    coordinator.hass.states.async_set.assert_not_called()
    skip_warnings = [
        record
        for record in caplog.records
        if "skipping" in record.getMessage() and "history points" in record.getMessage()
    ]
    assert len(skip_warnings) == 1


@pytest.mark.asyncio
async def test_fetch_history_chunk_writes_no_historical_states():
    """The fetch step must not replay history points as states.

    Regression test for the recorder lock-up: the inline async_set loop
    wrote every fetched point to sensor.eedomus_<periph_id> with a backdated
    timestamp, flooding the recorder at every boot.
    """
    coordinator = make_coordinator()
    chunk = [
        {"value": "100", "timestamp": "2026-09-27T09:00:00"},
        {"value": "100", "timestamp": "2026-09-27T09:30:00"},
    ]
    coordinator.client.get_device_history = AsyncMock(return_value=chunk)
    coordinator.hass.states.async_set = MagicMock()
    coordinator._save_history_progress = AsyncMock()

    result = await coordinator.async_fetch_history_chunk(PERIPH_ID)

    assert result == chunk
    coordinator.hass.states.async_set.assert_not_called()
    progress = coordinator._history_progress[PERIPH_ID]
    assert progress["completed"] is True
    assert progress["last_timestamp"] == int(
        datetime.fromisoformat("2026-09-27T09:30:00").timestamp()
    )


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
    rec_stats = configure_statistics_harness(coordinator)
    chunk = [{"value": "100", "timestamp": "2026-09-27T09:00:00"}]

    await coordinator.async_import_history_chunk(PERIPH_ID, chunk)

    _hass, metadata, _stats = rec_stats.async_import_statistics.call_args.args
    assert metadata["statistic_id"] == "light.rubanled_salon_2"
    # The success path must never write historical states either
    coordinator.hass.states.async_set.assert_not_called()


@pytest.mark.asyncio
async def test_statistics_failure_targets_real_entity_but_skips(monkeypatch):
    """A failing import resolves the real entity, then skips without writing."""
    _fake_registry(
        monkeypatch,
        [("eedomus", "01TEST_72762", "light.rubanled_salon_2")],
    )
    coordinator = make_coordinator()
    coordinator.config_entry = SimpleNamespace(entry_id="01TEST")
    rec_stats = configure_statistics_harness(coordinator)
    rec_stats.async_import_statistics = MagicMock(
        side_effect=Exception("database is locked")
    )
    coordinator.hass.states.async_set = MagicMock()
    chunk = [{"value": "100", "timestamp": "2026-09-27T09:00:00"}]

    await coordinator.async_import_history_chunk(PERIPH_ID, chunk)

    _hass, metadata, _stats = rec_stats.async_import_statistics.call_args.args
    assert metadata["statistic_id"] == "light.rubanled_salon_2"
    coordinator.hass.states.async_set.assert_not_called()


class TestNextBestValue:
    """next_best_value raises the plain-EN setpoint errors (ticket 3.5)."""

    def make_coordinator(self, values):
        coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=MagicMock())
        coordinator.data = {
            PERIPH_ID: {
                "periph_id": PERIPH_ID,
                "name": "Thermostat Salon",
                "values": values,
            }
        }
        return coordinator

    def test_no_value_list_raises_no_value_available(self):
        coordinator = self.make_coordinator(values=[])

        with pytest.raises(
            ValueError, match=f"No value available for peripheral {PERIPH_ID}"
        ):
            coordinator.next_best_value(PERIPH_ID, "50")

    def test_non_numeric_target_raises_not_a_valid_number(self):
        coordinator = self.make_coordinator(values=VALUES)

        with pytest.raises(
            ValueError, match="The target value 'doux' is not a valid number."
        ):
            coordinator.next_best_value(PERIPH_ID, "doux")

    def test_no_numeric_entries_raises_no_valid_numeric_value(self):
        coordinator = self.make_coordinator(
            values=[{"value": "high", "description": "Élevé"}]
        )

        with pytest.raises(
            ValueError,
            match=f"No valid numeric value found for peripheral {PERIPH_ID}",
        ):
            coordinator.next_best_value(PERIPH_ID, "50")
