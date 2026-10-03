"""Unit tests for the history import via async_import_statistics (H.1.2).

Covers the story's I/O matrix:
- exact registry resolution (AD-8bis): no ghost sensor.eedomus_<periph_id>
  target, no suffixed fallback for statistics;
- AD-11 clipping: only hours strictly before the sensor's first native
  statistic are backfilled;
- live-state unit extraction for the metadata;
- failure skips (unsupported unit, locked recorder): the chunk is skipped,
  no state is ever written.

The homeassistant.components.recorder.statistics module is a conftest stub;
these tests wire hass (states.get, async_add_executor_job) so the import
path runs end to end without an HA instance.
"""

import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.coordinator import EedomusDataUpdateCoordinator
from homeassistant.components.recorder.models import StatisticMeanType

pytestmark = pytest.mark.unit

PERIPH_ID = "72762"
ENTRY_ID = "01TEST"
ENTITY_ID = "sensor.temperature_salon"
UNIT = "°C"

CHUNK = [
    {"value": "10", "timestamp": "2026-09-27T08:15:00"},
    {"value": "30", "timestamp": "2026-09-27T08:45:00"},
]


def make_coordinator():
    """Build a coordinator with one peripheral."""
    coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=MagicMock())
    coordinator.data = {PERIPH_ID: {"periph_id": PERIPH_ID, "name": "Thermostat Salon"}}
    coordinator.config_entry = SimpleNamespace(entry_id=ENTRY_ID)
    return coordinator


def configure_statistics(coordinator, unit=UNIT):
    """Reset the recorder.statistics stubs and wire hass for the import."""
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


def fake_registry(monkeypatch, entries):
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


class TestResolveMainEntityIdStrict:
    """AD-8bis: statistics targets need an exact registry match."""

    def test_strict_mode_rejects_suffixed_fallback(self, monkeypatch):
        fake_registry(
            monkeypatch,
            [("eedomus", f"{ENTRY_ID}_{PERIPH_ID}_select", "select.mode_salon")],
        )
        coordinator = make_coordinator()
        assert (
            coordinator._resolve_main_entity_id(PERIPH_ID, allow_suffixed=False) is None
        )

    def test_strict_mode_finds_exact_match(self, monkeypatch):
        fake_registry(
            monkeypatch,
            [
                ("eedomus", f"{ENTRY_ID}_{PERIPH_ID}_select", "select.mode_salon"),
                ("eedomus", f"{ENTRY_ID}_{PERIPH_ID}", ENTITY_ID),
            ],
        )
        coordinator = make_coordinator()
        assert (
            coordinator._resolve_main_entity_id(PERIPH_ID, allow_suffixed=False)
            == ENTITY_ID
        )

    def test_default_mode_keeps_suffixed_fallback(self, monkeypatch):
        """The panel path keeps the current behavior (allow_suffixed=True)."""
        fake_registry(
            monkeypatch,
            [("eedomus", f"{ENTRY_ID}_{PERIPH_ID}_select", "select.mode_salon")],
        )
        coordinator = make_coordinator()
        assert coordinator._resolve_main_entity_id(PERIPH_ID) == "select.mode_salon"


@pytest.mark.asyncio
async def test_nominal_chunk_calls_async_import_statistics(monkeypatch):
    """Nominal chunk: API called with metadata + hourly stats, never Spook."""
    fake_registry(monkeypatch, [("eedomus", f"{ENTRY_ID}_{PERIPH_ID}", ENTITY_ID)])
    coordinator = make_coordinator()
    rec_stats = configure_statistics(coordinator)
    coordinator.hass.services.async_call = AsyncMock()

    imported = await coordinator.async_import_history_chunk(PERIPH_ID, CHUNK)

    assert imported == 1
    # Never the recorder.import_statistics service
    coordinator.hass.services.async_call.assert_not_awaited()
    rec_stats.async_import_statistics.assert_called_once()
    hass_arg, metadata, stats = rec_stats.async_import_statistics.call_args.args
    assert hass_arg is coordinator.hass
    assert metadata == {
        "statistic_id": ENTITY_ID,
        "source": "recorder",
        "name": "Thermostat Salon",
        "mean_type": StatisticMeanType.ARITHMETIC,
        "has_sum": False,
        "unit_of_measurement": UNIT,
    }
    # Both points fall in hour 08: one aggregated hourly statistic
    assert [s["start"] for s in stats] == [
        datetime(2026, 9, 27, 8, tzinfo=timezone.utc)
    ]
    assert stats[0]["mean"] == 20.0
    assert stats[0]["min"] == 10.0
    assert stats[0]["max"] == 30.0
    assert stats[0]["state"] == 30.0

    # The native-statistic lookup (AD-11) targets the real entity only
    call = rec_stats.statistics_during_period.call_args
    assert call.args[0] is coordinator.hass
    assert call.args[3] == {ENTITY_ID}
    assert call.args[4] == "hour"
    assert call.args[5] is None
    assert call.args[6] == {"state"}


@pytest.mark.asyncio
async def test_no_exact_entity_skips_import(monkeypatch, caplog):
    """No exact registry match: skipped with a warning, nothing written.

    A suffixed variant alone must not become the statistics target
    (AD-8bis), and no ghost sensor.eedomus_<periph_id> is created. The
    backfill loss is definitive, hence a warning, not a debug log.
    """
    caplog.set_level(logging.WARNING, logger="custom_components.eedomus.coordinator")
    fake_registry(
        monkeypatch,
        [
            ("eedomus", f"{ENTRY_ID}_{PERIPH_ID}_select", "select.mode_salon"),
            ("other", f"{ENTRY_ID}_999", "sensor.other"),
        ],
    )
    coordinator = make_coordinator()
    rec_stats = configure_statistics(coordinator)

    imported = await coordinator.async_import_history_chunk(PERIPH_ID, CHUNK)

    assert imported == 0
    rec_stats.async_import_statistics.assert_not_called()
    coordinator.hass.states.async_set.assert_not_called()
    assert "no exact entity match" in caplog.text


@pytest.mark.asyncio
async def test_ad11_clips_hours_at_or_after_first_native(monkeypatch):
    """Only hours strictly before the first native statistic are imported."""
    fake_registry(monkeypatch, [("eedomus", f"{ENTRY_ID}_{PERIPH_ID}", ENTITY_ID)])
    coordinator = make_coordinator()
    rec_stats = configure_statistics(coordinator)
    first_native = datetime(2026, 9, 27, 8, tzinfo=timezone.utc)
    rec_stats.statistics_during_period.return_value = {
        ENTITY_ID: [{"start": first_native}]
    }
    chunk = [
        {"value": "5", "timestamp": "2026-09-27T07:30:00"},
        {"value": "10", "timestamp": "2026-09-27T08:15:00"},
        {"value": "30", "timestamp": "2026-09-27T08:45:00"},
    ]

    await coordinator.async_import_history_chunk(PERIPH_ID, chunk)

    _hass, _metadata, stats = rec_stats.async_import_statistics.call_args.args
    assert [s["start"] for s in stats] == [
        datetime(2026, 9, 27, 7, tzinfo=timezone.utc)
    ]


@pytest.mark.asyncio
async def test_ad11_all_hours_native_or_later_no_import(monkeypatch, caplog):
    """All hours at or after the first native statistic: nothing imported."""
    fake_registry(monkeypatch, [("eedomus", f"{ENTRY_ID}_{PERIPH_ID}", ENTITY_ID)])
    coordinator = make_coordinator()
    rec_stats = configure_statistics(coordinator)
    rec_stats.statistics_during_period.return_value = {
        ENTITY_ID: [{"start": datetime(2026, 9, 27, 7, tzinfo=timezone.utc)}]
    }
    caplog.set_level(logging.INFO, logger="custom_components.eedomus.coordinator")

    imported = await coordinator.async_import_history_chunk(PERIPH_ID, CHUNK)

    assert imported == 0
    rec_stats.async_import_statistics.assert_not_called()
    assert "AD-11" in caplog.text


@pytest.mark.asyncio
async def test_ad11_rows_not_sorted_first_native_is_earliest(monkeypatch):
    """Unsorted native rows: the clip uses the earliest start, not rows[0]."""
    fake_registry(monkeypatch, [("eedomus", f"{ENTRY_ID}_{PERIPH_ID}", ENTITY_ID)])
    coordinator = make_coordinator()
    rec_stats = configure_statistics(coordinator)
    rec_stats.statistics_during_period.return_value = {
        ENTITY_ID: [
            {"start": datetime(2026, 9, 27, 9, tzinfo=timezone.utc)},
            {"start": datetime(2026, 9, 27, 8, tzinfo=timezone.utc)},
        ]
    }
    chunk = [
        {"value": "5", "timestamp": "2026-09-27T07:30:00"},
        {"value": "10", "timestamp": "2026-09-27T08:15:00"},
    ]

    await coordinator.async_import_history_chunk(PERIPH_ID, chunk)

    _hass, _metadata, stats = rec_stats.async_import_statistics.call_args.args
    # First native statistic is 08:00, not 09:00: only the 07:00 hour passes
    assert [s["start"] for s in stats] == [
        datetime(2026, 9, 27, 7, tzinfo=timezone.utc)
    ]


@pytest.mark.asyncio
async def test_no_live_state_skips_import_with_warning(monkeypatch, caplog):
    """Without a live state the unit is unknown: skip with a named warning."""
    fake_registry(monkeypatch, [("eedomus", f"{ENTRY_ID}_{PERIPH_ID}", ENTITY_ID)])
    coordinator = make_coordinator()
    rec_stats = configure_statistics(coordinator)
    coordinator.hass.states.get = MagicMock(return_value=None)
    caplog.set_level(logging.WARNING, logger="custom_components.eedomus.coordinator")

    imported = await coordinator.async_import_history_chunk(PERIPH_ID, CHUNK)

    assert imported == 0
    rec_stats.async_import_statistics.assert_not_called()
    assert "no live state" in caplog.text
    # One named warning only, no duplicate failure warning from the caller
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1


@pytest.mark.asyncio
async def test_live_state_without_unit_imports_unit_none(monkeypatch):
    """A state without unit_of_measurement: metadata carries unit None.

    The StatisticMetaData TypedDict allows unit_of_measurement: None; the
    recorder only derives unit_class when a unit is set.
    """
    fake_registry(monkeypatch, [("eedomus", f"{ENTRY_ID}_{PERIPH_ID}", ENTITY_ID)])
    coordinator = make_coordinator()
    rec_stats = configure_statistics(coordinator)
    coordinator.hass.states.get = MagicMock(return_value=SimpleNamespace(attributes={}))

    await coordinator.async_import_history_chunk(PERIPH_ID, CHUNK)

    _hass, metadata, _stats = rec_stats.async_import_statistics.call_args.args
    assert metadata["unit_of_measurement"] is None
    assert metadata["has_sum"] is False
    assert metadata["mean_type"] == StatisticMeanType.ARITHMETIC


@pytest.mark.asyncio
async def test_main_entity_id_used_as_is(monkeypatch):
    """An explicitly provided main_entity_id is the target, resolution-free.

    Documents the side door: the registry has no exact match for the
    peripheral, yet the provided entity_id is used as-is.
    """
    fake_registry(
        monkeypatch,
        [("eedomus", f"{ENTRY_ID}_{PERIPH_ID}_select", "select.mode_salon")],
    )
    coordinator = make_coordinator()
    rec_stats = configure_statistics(coordinator)

    await coordinator.async_import_history_chunk(
        PERIPH_ID, CHUNK, main_entity_id="light.explicit_target"
    )

    _hass, metadata, _stats = rec_stats.async_import_statistics.call_args.args
    assert metadata["statistic_id"] == "light.explicit_target"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "api_error",
    [
        Exception("no unit class for unit X"),  # unsupported unit
        Exception("database is locked"),  # recorder unavailable
    ],
    ids=["unsupported-unit", "recorder-unavailable"],
)
async def test_api_error_skips_chunk(monkeypatch, caplog, api_error):
    """async_import_statistics raising skips the chunk; no state written.

    The single user-facing warning comes from async_import_history_chunk;
    import errors are not retried (only fetch errors have a retry queue).
    """
    fake_registry(monkeypatch, [("eedomus", f"{ENTRY_ID}_{PERIPH_ID}", ENTITY_ID)])
    coordinator = make_coordinator()
    rec_stats = configure_statistics(coordinator)
    rec_stats.async_import_statistics = MagicMock(side_effect=api_error)
    coordinator.hass.states.async_set = MagicMock()
    caplog.set_level(logging.WARNING, logger="custom_components.eedomus.coordinator")

    imported = await coordinator.async_import_history_chunk(PERIPH_ID, CHUNK)

    assert imported == 0
    rec_stats.async_import_statistics.assert_called_once()
    coordinator.hass.states.async_set.assert_not_called()
    skip_warnings = [
        r
        for r in caplog.records
        if "skipping" in r.getMessage() and "history points" in r.getMessage()
    ]
    assert len(skip_warnings) == 1
