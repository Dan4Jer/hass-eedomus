"""Tests de custom_components.eedomus.__init__."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eedomus import (
    async_migrate_entry,
    async_unload_entry,
    async_update_listener,
    get_clean_box_name,
)
from custom_components.eedomus.const import (
    CONF_API_HOST,
    CONF_API_SECRET,
    CONF_API_USER,
    CONF_ENABLE_API_EEDOMUS,
    CONF_ENABLE_API_PROXY,
    CONF_SCAN_INTERVAL,
    CONFIG_VERSION,
    COORDINATOR,
    DOMAIN,
)

def test_get_clean_box_name_from_api_host():
    entry = MagicMock()
    entry.data = {
        "api_host": "192.168.1.50",
    }
    entry.title = "Mock Title"

    assert get_clean_box_name(entry) == "Box eedomus (192.168.1.50)"

def test_get_clean_box_name_from_host():
    entry = MagicMock()
    entry.data = {
        "host": "192.168.1.60",
        "api_host": "192.168.1.50",
    }
    entry.title = "Mock Title"

    assert get_clean_box_name(entry) == "Box eedomus (192.168.1.60)"

def test_get_clean_box_name_from_title():
    entry = MagicMock()
    entry.data = {}
    entry.title = "Eedomus (192.168.1.70)"

    assert get_clean_box_name(entry) == "Box eedomus (192.168.1.70)"

def test_get_clean_box_name_plain_title():
    entry = MagicMock()
    entry.data = {}
    entry.title = "Ma Box"

    assert get_clean_box_name(entry) == "Box eedomus (Ma Box)"

@pytest.mark.asyncio
async def test_async_update_listener_updates_scan_interval(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={CONF_API_HOST: "192.168.1.50"},
        options={CONF_SCAN_INTERVAL: 120},
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.update_interval = None

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    with patch.object(
        hass.config_entries,
        "async_reload",
        new_callable=AsyncMock,
    ) as mock_reload:

        await async_update_listener(hass, entry)
        await hass.async_block_till_done()

    assert coordinator.update_interval.total_seconds() == 120
    mock_reload.assert_awaited_once_with(entry.entry_id)

@pytest.mark.asyncio
async def test_async_update_listener_without_coordinator(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={CONF_API_HOST: "192.168.1.50"},
        options={CONF_SCAN_INTERVAL: 120},
    )
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}

    with patch.object(
        hass.config_entries,
        "async_reload",
        new_callable=AsyncMock,
    ) as mock_reload:

        await async_update_listener(hass, entry)
        await hass.async_block_till_done()

    mock_reload.assert_awaited_once_with(entry.entry_id)

@pytest.mark.asyncio
async def test_async_unload_entry_success(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={CONF_API_HOST: "192.168.1.50"},
    )
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: MagicMock(),
    }

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        result = await async_unload_entry(hass, entry)

    assert result is True
    assert entry.entry_id not in hass.data[DOMAIN]

@pytest.mark.asyncio
async def test_async_unload_entry_failure(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={CONF_API_HOST: "192.168.1.50"},
    )
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR: MagicMock(),
    }

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=False,
    ):
        result = await async_unload_entry(hass, entry)

    assert result is False
    assert entry.entry_id in hass.data[DOMAIN]

@pytest.mark.asyncio
async def test_async_unload_entry_missing_data(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={CONF_API_HOST: "192.168.1.50"},
    )
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        result = await async_unload_entry(hass, entry)

    assert result is True

@pytest.mark.asyncio
async def test_async_migrate_entry_without_mapping_file(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={"host": "192.168.1.50"},
        options={},
    )
    entry.add_to_hass(hass)

    with patch("os.path.exists", return_value=False):
        result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.version == CONFIG_VERSION

@pytest.mark.asyncio
async def test_async_migrate_entry_backup_failure(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={"host": "192.168.1.50"},
        options={},
    )
    entry.add_to_hass(hass)

    with (
        patch("os.path.exists", return_value=True),
        patch.object(
            hass,
            "async_add_executor_job",
            new_callable=AsyncMock,
            side_effect=OSError("backup impossible"),
        ),
    ):
        result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.version == CONFIG_VERSION


