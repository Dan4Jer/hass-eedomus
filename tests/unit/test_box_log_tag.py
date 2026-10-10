"""Unit tests for the box-origin log tag (ticket 113).

The shared logging module tags every line emitted inside a box log
context with ` [box: <name>]`, without rewriting logger names (caplog
tests pin `custom_components.eedomus.<module>`) and without touching
records emitted outside any box context.
"""

import asyncio
import logging
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from custom_components.eedomus.coordinator import EedomusDataUpdateCoordinator
from custom_components.eedomus.log import (
    box_log_context,
    get_logger,
    resolve_box_tag,
)

pytestmark = pytest.mark.unit

TEST_LOGGER = "custom_components.eedomus.log_test"


def _emit(message: str) -> None:
    get_logger(TEST_LOGGER).info(message)


def test_tag_appended_inside_context(caplog):
    """A line emitted inside a box context ends with the box tag."""
    with caplog.at_level(logging.INFO, logger=TEST_LOGGER):
        with box_log_context("Salon"):
            _emit("Refresh complete (165 peripherals)")
    assert (
        "Refresh complete (165 peripherals) [box: Salon]" in caplog.text
    ), caplog.text


def test_untagged_outside_context(caplog):
    """A line emitted outside any box context passes through untagged."""
    with caplog.at_level(logging.INFO, logger=TEST_LOGGER):
        _emit("Startup line")
    assert "Startup line" in caplog.text
    assert "[box:" not in caplog.text


def test_tag_absent_after_context_exits(caplog):
    """The tag stops applying once the context exits."""
    with caplog.at_level(logging.INFO, logger=TEST_LOGGER):
        with box_log_context("Salon"):
            _emit("inside")
        _emit("outside")
    assert "inside [box: Salon]" in caplog.text
    assert "outside [box:" not in caplog.text


def test_inner_context_wins(caplog):
    """A nested context wins until it exits, then the outer tag resumes."""
    with caplog.at_level(logging.INFO, logger=TEST_LOGGER):
        with box_log_context("Box A"):
            _emit("outer first")
            with box_log_context("Box 2"):
                _emit("inner")
            _emit("outer second")
    assert "outer first [box: Box A]" in caplog.text
    assert "inner [box: Box 2]" in caplog.text
    assert "outer second [box: Box A]" in caplog.text


@pytest.mark.asyncio
async def test_tag_survives_await(caplog):
    """The tag propagates across await boundaries within the task."""

    async def tagged_coroutine() -> None:
        await asyncio.sleep(0)
        _emit("after await")

    with caplog.at_level(logging.INFO, logger=TEST_LOGGER):
        with box_log_context("Salon"):
            await tagged_coroutine()
    assert "after await [box: Salon]" in caplog.text


@pytest.mark.asyncio
async def test_tag_reaches_every_module_logger(caplog):
    """Any factory-built logger inside the box context is tagged."""
    other_name = "custom_components.eedomus.log_test_other"
    other = get_logger(other_name)
    with caplog.at_level(logging.INFO, logger=other_name):
        with box_log_context("Salon"):
            other.info("line from another module")
    assert "line from another module [box: Salon]" in caplog.text


def test_empty_tag_never_appends(caplog):
    """An empty box tag is treated as no tag - never ` [box: ]`."""
    with caplog.at_level(logging.INFO, logger=TEST_LOGGER):
        with box_log_context(""):
            _emit("empty context")
    assert "empty context" in caplog.text
    assert "[box:" not in caplog.text


def test_logger_name_passes_through():
    """The factory keeps the exact logger name (caplog pinning)."""
    logger = get_logger("custom_components.eedomus.coordinator")
    assert logger.name == "custom_components.eedomus.coordinator"


def test_get_logger_filter_attached_once():
    """Repeated factory calls never stack duplicate filters."""
    first = get_logger("custom_components.eedomus.log_test_idempotent")
    second = get_logger("custom_components.eedomus.log_test_idempotent")
    assert first is second


def test_resolve_box_tag_title_first():
    """Config entry title wins."""
    entry = SimpleNamespace(title="Salon", entry_id="abc", data={})
    assert resolve_box_tag(entry) == "Salon"


def test_resolve_box_tag_client_config_entry():
    """The tag resolves through client.config_entry when entry is None."""
    entry = SimpleNamespace(title="Cave", entry_id="abc", data={})
    client = SimpleNamespace(config_entry=entry)
    assert resolve_box_tag(None, client) == "Cave"


def test_resolve_box_tag_api_host_fallback():
    """Without a title, the configured api host is used."""
    entry = SimpleNamespace(title="", entry_id="abc", data={})
    client = SimpleNamespace(config_entry=entry, api_host="192.168.1.10")
    assert resolve_box_tag(None, client) == "192.168.1.10"
    entry_with_data = SimpleNamespace(
        title="", entry_id="abc", data={"api_host": "10.0.0.2"}
    )
    assert resolve_box_tag(entry_with_data) == "10.0.0.2"


def test_resolve_box_tag_entry_id_fallback():
    """Empty title and no api host fall back to the entry_id."""
    entry = SimpleNamespace(title="", entry_id="abc123", data={})
    assert resolve_box_tag(entry) == "abc123"


def test_resolve_box_tag_never_empty():
    """Nothing resolvable still yields a non-empty tag."""
    assert resolve_box_tag(None) == "unknown"
    assert resolve_box_tag(SimpleNamespace(title=None, data={})) == "unknown"


@pytest.mark.asyncio
async def test_coordinator_refresh_tags_log_lines(caplog):
    """A coordinator refresh logs every line with the box tag.

    Mirrors the caplog pattern of test_coordinator_partial_refresh:
    the coordinator's client carries the config entry, whose title
    becomes the tag.
    """
    from datetime import datetime
    from unittest.mock import MagicMock

    client = MagicMock()
    client.config_entry = SimpleNamespace(
        title="Salon",
        options={"history": False},
        data={},
    )
    coordinator = EedomusDataUpdateCoordinator(hass=MagicMock(), client=client)
    coordinator.data = {}
    coordinator._dynamic_peripherals = {}
    coordinator._full_refresh_needed = False
    coordinator._last_update_start_time = datetime.now()

    caplog.set_level(logging.INFO, logger="custom_components.eedomus.coordinator")
    await coordinator._async_update_data()

    eedomus_records = [
        record
        for record in caplog.records
        if record.name.startswith("custom_components.eedomus")
    ]
    assert eedomus_records, "no eedomus log line emitted by the refresh"
    for record in eedomus_records:
        assert record.getMessage().endswith(" [box: Salon]"), record.getMessage()


def test_sweep_guard_every_logger_uses_factory():
    """No real module logs through a logger that bypasses the factory.

    Walks custom_components/eedomus/*.py (stale *.backup* files are
    never swept) and asserts every _LOGGER assignment uses get_logger.
    """
    package_dir = (
        Path(__file__).resolve().parents[2] / "custom_components" / "eedomus"
    )
    offenders = []
    for path in sorted(package_dir.glob("*.py")):
        if "backup" in path.name:
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if re.match(r"^\s*_LOGGER\s*=", line) and "get_logger(" not in line:
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, "Raw logger assignments bypassing get_logger:\n" + "\n".join(
        offenders
    )


def test_sweep_guard_no_raw_get_logger_call():
    """No real module calls logging.getLogger(__name__) directly."""
    package_dir = (
        Path(__file__).resolve().parents[2] / "custom_components" / "eedomus"
    )
    offenders = []
    for path in sorted(package_dir.glob("*.py")):
        if "backup" in path.name:
            continue
        text = path.read_text()
        if "logging.getLogger(__name__)" in text:
            offenders.append(path.name)
    assert not offenders, f"Direct logging.getLogger(__name__) in: {offenders}"
