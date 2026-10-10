"""Unit tests for the box-origin log tag (ticket 113).

The shared logging module tags every line emitted inside a box log
context with ` [box: <name>]`, without rewriting logger names (caplog
tests pin `custom_components.eedomus.<module>`) and without touching
records emitted outside any box context.
"""

import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.eedomus.coordinator import EedomusDataUpdateCoordinator
from custom_components.eedomus.log import (
    _BoxTagFilter,
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
    assert "Refresh complete (165 peripherals) [box: Salon]" in caplog.text, caplog.text


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
    """Repeated factory calls attach exactly one box tag filter."""
    logger_name = "custom_components.eedomus.log_test_idempotent"
    get_logger(logger_name)
    get_logger(logger_name)
    logger = get_logger(logger_name)
    attached = [flt for flt in logger.filters if isinstance(flt, _BoxTagFilter)]
    assert len(attached) == 1


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


def test_sweep_guard_no_logger_built_outside_the_factory():
    """No real module builds a logger outside the factory.

    Any logging.getLogger( occurrence in custom_components/eedomus/*.py
    (stale *.backup* files are never swept) bypasses the box tag
    filter - under any variable name or literal logger name. log.py
    is the only module allowed to touch the logging API.
    """
    package_dir = Path(__file__).resolve().parents[2] / "custom_components" / "eedomus"
    offenders = []
    for path in sorted(package_dir.glob("*.py")):
        if "backup" in path.name or path.name == "log.py":
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if "logging.getLogger(" in line:
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, "Loggers built outside the get_logger factory:\n" + "\n".join(
        offenders
    )


@pytest.mark.asyncio
async def test_domain_service_two_boxes_distinguished_by_tag(caplog):
    """Matrix row 'Domain service, 2 boxes': each box's lines carry that
    box's tag, never the other's - even with concurrent service runs."""
    from custom_components.eedomus import services
    from custom_components.eedomus.const import COORDINATOR, DOMAIN

    registered = {}
    hass = MagicMock()
    hass.services.has_service.return_value = False
    hass.services.async_register.side_effect = (
        lambda domain, name, handler: registered.__setitem__(name, handler)
    )

    def make_coordinator(title: str):
        coord = MagicMock()
        coord.config_entry = SimpleNamespace(
            title=title, entry_id=title.lower(), data={}
        )

        async def refresh() -> None:
            logger = get_logger("custom_components.eedomus.coordinator")
            logger.info("Refresh cycle start (%s)", title)
            await asyncio.sleep(0)
            logger.info("Refresh complete (%s)", title)

        coord.async_request_refresh = refresh
        return coord

    coord_salon = make_coordinator("Salon")
    coord_cave = make_coordinator("Cave")
    hass.data = {
        DOMAIN: {
            "entry_salon": {COORDINATOR: coord_salon},
            "entry_cave": {COORDINATOR: coord_cave},
        }
    }

    await services.async_setup_services(hass, coord_salon)
    handler = registered["refresh"]
    assert handler is not None, "refresh service handler not registered"

    caplog.set_level(logging.INFO, logger="custom_components.eedomus.coordinator")
    call = SimpleNamespace(data={})
    # Two concurrent service runs interleave both boxes' turns; the
    # ContextVar must stay per-task and per-box throughout.
    await asyncio.gather(handler(call), handler(call))

    text = caplog.text
    assert "Refresh cycle start (Salon) [box: Salon]" in text
    assert "Refresh complete (Salon) [box: Salon]" in text
    assert "Refresh cycle start (Cave) [box: Cave]" in text
    assert "Refresh complete (Cave) [box: Cave]" in text
    assert "(Salon) [box: Cave]" not in text
    assert "(Cave) [box: Salon]" not in text
    for record in caplog.records:
        message = record.getMessage()
        if "Refresh cycle" in message or "Refresh complete" in message:
            assert "[box: " in message, message
            if "Salon" in message:
                assert message.endswith("[box: Salon]"), message
            else:
                assert message.endswith("[box: Cave]"), message


def _make_webhook_hass(entry_id: str = "entry-1", title: str = "Salon"):
    """Build the hass side a webhook request resolves against."""
    from custom_components.eedomus.const import COORDINATOR, DOMAIN

    hass = MagicMock()
    entry = SimpleNamespace(entry_id=entry_id, title=title, data={})
    hass.config_entries.async_entries.return_value = [entry]
    hass.config_entries.async_reload = AsyncMock()

    coordinator = MagicMock()

    async def full_refresh() -> None:
        get_logger("custom_components.eedomus.coordinator").info("Full refresh done")

    async def partial_refresh() -> None:
        get_logger("custom_components.eedomus.coordinator").info("Partial refresh done")

    coordinator._async_full_refresh = full_refresh
    coordinator._async_partial_refresh = partial_refresh
    hass.data = {DOMAIN: {entry_id: {COORDINATOR: coordinator}}}
    return hass


def _make_webhook_request(hass, payload, remote: str = "1.2.3.4"):
    request = MagicMock()
    request.remote = remote
    request.app = {"hass": hass}
    request.json = AsyncMock(return_value=payload)
    return request


@pytest.mark.asyncio
async def test_webhook_unauthorized_ip_returns_403_tagged(caplog):
    """A request from an IP outside the allowlist gets a 403, tagged."""
    from custom_components.eedomus.webhook import EedomusWebhookView

    view = EedomusWebhookView("entry-1", allowed_ips=["9.9.9.9"])
    request = _make_webhook_request(_make_webhook_hass(), {"action": "refresh"})
    caplog.set_level(logging.WARNING, logger="custom_components.eedomus.webhook")
    response = await view.post(request)
    assert response.status == 403
    assert response.text == "Unauthorized"
    assert "Unauthorized IP: 1.2.3.4 [box: Salon]" in caplog.text


@pytest.mark.asyncio
async def test_webhook_unrecognized_action_returns_400(caplog):
    """An unknown action gets a clean 400, not a coordinator crash."""
    from custom_components.eedomus.webhook import EedomusWebhookView

    view = EedomusWebhookView("entry-1", allowed_ips=["1.2.3.4"])
    request = _make_webhook_request(_make_webhook_hass(), {"action": "bogus"})
    response = await view.post(request)
    assert response.status == 400
    assert response.text == "Unrecognized action"


@pytest.mark.asyncio
async def test_webhook_non_dict_body_returns_400(caplog):
    """A JSON body that is not an object gets a clean 400, not a 500."""
    from custom_components.eedomus.webhook import EedomusWebhookView

    view = EedomusWebhookView("entry-1", allowed_ips=["1.2.3.4"])
    for payload in ([1, 2], "refresh", 42):
        request = _make_webhook_request(_make_webhook_hass(), payload)
        response = await view.post(request)
        assert response.status == 400, payload
        assert response.text == "Unrecognized action", payload


@pytest.mark.asyncio
async def test_webhook_refresh_returns_ok_tagged(caplog):
    """The refresh action drives the coordinator and logs its tag."""
    from custom_components.eedomus.webhook import EedomusWebhookView

    view = EedomusWebhookView("entry-1", allowed_ips=["1.2.3.4"])
    hass = _make_webhook_hass()
    request = _make_webhook_request(hass, {"action": "refresh"})
    caplog.set_level(logging.INFO, logger="custom_components.eedomus.coordinator")
    response = await view.post(request)
    assert response.status == 200
    assert response.text == "OK"
    assert "Full refresh done [box: Salon]" in caplog.text


@pytest.mark.asyncio
async def test_webhook_reload_returns_ok_tagged(caplog):
    """The reload action reloads the entry and logs its tag."""
    from custom_components.eedomus.webhook import EedomusWebhookView

    view = EedomusWebhookView("entry-1", allowed_ips=["1.2.3.4"])
    hass = _make_webhook_hass()
    request = _make_webhook_request(hass, {"action": "reload"})
    caplog.set_level(logging.INFO, logger="custom_components.eedomus.webhook")
    response = await view.post(request)
    assert response.status == 200
    assert response.text == "OK"
    hass.config_entries.async_reload.assert_awaited_once_with("entry-1")
    assert "Eedomus integration reloaded successfully [box: Salon]" in caplog.text
