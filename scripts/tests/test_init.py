"""Tests de custom_components.eedomus.__init__."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryNotReady
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eedomus import (
    async_migrate_entry,
    async_remove_entry,
    async_setup_entry,
    async_unload_entry,
    async_update_listener,
    get_clean_box_name,
)
from custom_components.eedomus.const import (
    CONF_API_HOST,
    CONF_API_PROXY_DISABLE_SECURITY,
    CONF_API_SECRET,
    CONF_API_USER,
    CONF_ENABLE_API_EEDOMUS,
    CONF_ENABLE_API_PROXY,
    CONF_ENABLE_HISTORY,
    CONF_ENABLE_WEBHOOK,
    CONF_REMOVE_ENTITIES,
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


@pytest.fixture
def mock_http(hass):
    """Simule le serveur HTTP Home Assistant pour les tests de setup."""
    hass.http = MagicMock()
    hass.http.register_view = MagicMock()
    return hass.http


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


@pytest.mark.asyncio
async def test_setup_entry_runs_migration(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION - 1,
        data={
            CONF_API_HOST: "192.168.1.50",
        },
        options={},
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.eedomus.async_migrate_entry",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_migrate,
        patch.object(
            hass.config_entries,
            "async_reload",
            new_callable=AsyncMock,
        ) as mock_reload,
    ):
        result = await async_setup_entry(hass, entry)

        await hass.async_block_till_done()

    assert result is False

    mock_migrate.assert_awaited_once_with(
        hass,
        entry,
    )

    mock_reload.assert_awaited_once_with(
        entry.entry_id,
    )


@pytest.mark.asyncio
async def test_setup_entry_migration_failure(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION - 1,
        data={
            CONF_API_HOST: "192.168.1.50",
        },
        options={},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.eedomus.async_migrate_entry",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Migration test failure"),
    ) as mock_migrate:
        result = await async_setup_entry(
            hass,
            entry,
        )

    assert result is False

    mock_migrate.assert_awaited_once_with(
        hass,
        entry,
    )


@pytest.mark.asyncio
async def test_setup_entry_repairs_missing_unique_id(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_ENABLE_API_EEDOMUS: False,
            CONF_ENABLE_API_PROXY: True,
        },
        options={},
        unique_id=None,
    )

    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.eedomus.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True
    assert entry.unique_id == "eedomus_192.168.1.50"


@pytest.mark.asyncio
async def test_setup_entry_modernizes_legacy_keys(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            "api_eedomus": False,
            "api_proxy": True,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.eedomus.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True

    assert "api_eedomus" not in entry.data
    assert "api_proxy" not in entry.data

    assert entry.data[CONF_ENABLE_API_EEDOMUS] is False
    assert entry.data[CONF_ENABLE_API_PROXY] is True


@pytest.mark.asyncio
async def test_setup_entry_modernizes_legacy_option_keys(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_ENABLE_API_EEDOMUS: False,
            CONF_ENABLE_API_PROXY: True,
        },
        options={
            "api_eedomus": False,
            "api_proxy": True,
        },
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.eedomus.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True

    assert "api_eedomus" not in entry.options
    assert "api_proxy" not in entry.options

    assert entry.options[CONF_ENABLE_API_EEDOMUS] is False
    assert entry.options[CONF_ENABLE_API_PROXY] is True


@pytest.mark.asyncio
async def test_setup_entry_syncs_connection_options_to_data(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_API_USER: "old_user",
            CONF_API_SECRET: "old_secret",
            CONF_ENABLE_API_EEDOMUS: False,
            CONF_ENABLE_API_PROXY: True,
        },
        options={
            CONF_API_HOST: "192.168.1.60",
            CONF_API_USER: "new_user",
            CONF_API_SECRET: "new_secret",
        },
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.eedomus.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True

    assert entry.data[CONF_API_HOST] == "192.168.1.60"
    assert entry.data[CONF_API_USER] == "new_user"
    assert entry.data[CONF_API_SECRET] == "new_secret"


@pytest.mark.asyncio
async def test_setup_entry_client_creation_failure(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_API_USER: "user",
            CONF_API_SECRET: "secret",
            CONF_ENABLE_API_EEDOMUS: True,
            CONF_ENABLE_API_PROXY: False,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.eedomus.EedomusClient",
        side_effect=RuntimeError("client creation failed"),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is False


@pytest.mark.asyncio
async def test_setup_entry_initial_refresh_failure(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_API_USER: "user",
            CONF_API_SECRET: "secret",
            CONF_ENABLE_API_EEDOMUS: True,
            CONF_ENABLE_API_PROXY: False,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock(
        side_effect=RuntimeError("refresh failed")
    )
    coordinator.config_entry = entry

    with (
        patch(
            "custom_components.eedomus.EedomusClient",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.eedomus.EedomusDataUpdateCoordinator",
            return_value=coordinator,
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is False


@pytest.mark.asyncio
async def test_setup_entry_initial_refresh_not_ready(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_API_USER: "user",
            CONF_API_SECRET: "secret",
            CONF_ENABLE_API_EEDOMUS: True,
            CONF_ENABLE_API_PROXY: False,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock(
        side_effect=ConfigEntryNotReady
    )
    coordinator.config_entry = entry

    with (
        patch(
            "custom_components.eedomus.EedomusClient",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.eedomus.EedomusDataUpdateCoordinator",
            return_value=coordinator,
        ),
    ):
        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_setup_entry_api_mode_success(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_API_USER: "user",
            CONF_API_SECRET: "secret",
            CONF_ENABLE_API_EEDOMUS: True,
            CONF_ENABLE_API_PROXY: False,
            CONF_ENABLE_HISTORY: False,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    client = MagicMock()

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.config_entry = entry

    with (
        patch(
            "custom_components.eedomus.EedomusClient",
            return_value=client,
        ),
        patch(
            "custom_components.eedomus.EedomusDataUpdateCoordinator",
            return_value=coordinator,
        ),
        patch(
            "custom_components.eedomus.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.mapping_registry.print_mapping_table",
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True
    coordinator.async_config_entry_first_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_entry_history_enabled_from_options(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_API_USER: "user",
            CONF_API_SECRET: "secret",
            CONF_ENABLE_API_EEDOMUS: True,
            CONF_ENABLE_API_PROXY: False,
            CONF_ENABLE_HISTORY: False,
        },
        options={
            CONF_ENABLE_HISTORY: True,
        },
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.config_entry = entry

    with (
        patch(
            "custom_components.eedomus.EedomusClient",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.eedomus.EedomusDataUpdateCoordinator",
            return_value=coordinator,
        ),
        patch(
            "custom_components.eedomus.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.history_sensor.async_setup_history_sensors",
            new_callable=AsyncMock,
        ) as mock_history,
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.mapping_registry.print_mapping_table",
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True
    mock_history.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_entry_history_data_true_options_false(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_API_USER: "user",
            CONF_API_SECRET: "secret",
            CONF_ENABLE_API_EEDOMUS: True,
            CONF_ENABLE_API_PROXY: False,
            CONF_ENABLE_HISTORY: True,
        },
        options={
            CONF_ENABLE_HISTORY: False,
        },
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.config_entry = entry

    with (
        patch(
            "custom_components.eedomus.EedomusClient",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.eedomus.EedomusDataUpdateCoordinator",
            return_value=coordinator,
        ),
        patch(
            "custom_components.eedomus.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.history_sensor.async_setup_history_sensors",
            new_callable=AsyncMock,
        ) as mock_history,
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.mapping_registry.print_mapping_table",
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True
    mock_history.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_migrate_entry_from_version_1(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={
            CONF_API_HOST: "192.168.1.50",
        },
        options={},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.eedomus.os.path.exists",
        return_value=False,
    ):
        result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.version == CONFIG_VERSION

    assert CONF_ENABLE_HISTORY in entry.options
    assert CONF_REMOVE_ENTITIES in entry.options
    assert CONF_ENABLE_API_PROXY in entry.options
    assert CONF_API_PROXY_DISABLE_SECURITY in entry.options


@pytest.mark.asyncio
async def test_async_migrate_entry_from_version_2(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            CONF_API_HOST: "192.168.1.50",
        },
        options={},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.eedomus.os.path.exists",
        return_value=False,
    ):
        result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.version == CONFIG_VERSION

    assert CONF_ENABLE_API_PROXY in entry.options
    assert CONF_API_PROXY_DISABLE_SECURITY in entry.options


@pytest.mark.asyncio
async def test_async_remove_entry_removes_own_entities(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_REMOVE_ENTITIES: True,
        },
    )
    entry.add_to_hass(hass)

    entity_registry = MagicMock()

    own_entity = MagicMock()
    own_entity.platform = DOMAIN
    own_entity.config_entry_id = entry.entry_id
    own_entity.entity_id = "sensor.eedomus_own"

    other_entry_entity = MagicMock()
    other_entry_entity.platform = DOMAIN
    other_entry_entity.config_entry_id = "other_entry"
    other_entry_entity.entity_id = "sensor.eedomus_other"

    unrelated_entity = MagicMock()
    unrelated_entity.platform = "mqtt"
    unrelated_entity.config_entry_id = entry.entry_id
    unrelated_entity.entity_id = "sensor.mqtt_test"

    entity_registry.entities.values.return_value = [
        own_entity,
        other_entry_entity,
        unrelated_entity,
    ]

    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        return_value=entity_registry,
    ):
        await async_remove_entry(hass, entry)

    entity_registry.async_remove.assert_called_once_with("sensor.eedomus_own")


@pytest.mark.asyncio
async def test_async_remove_entry_keeps_entities_when_disabled(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={},
        options={
            CONF_REMOVE_ENTITIES: False,
        },
    )
    entry.add_to_hass(hass)

    entity_registry = MagicMock()

    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        return_value=entity_registry,
    ) as mock_get:
        await async_remove_entry(hass, entry)

    mock_get.assert_not_called()
    entity_registry.async_remove.assert_not_called()


@pytest.mark.asyncio
async def test_setup_entry_main_device_creation_failure(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_API_USER: "user",
            CONF_API_SECRET: "secret",
            CONF_ENABLE_API_EEDOMUS: True,
            CONF_ENABLE_API_PROXY: False,
            CONF_ENABLE_HISTORY: False,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.config_entry = entry

    with (
        patch(
            "custom_components.eedomus.EedomusClient",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.eedomus.EedomusDataUpdateCoordinator",
            return_value=coordinator,
        ),
        patch(
            "homeassistant.helpers.device_registry.async_get",
            side_effect=RuntimeError("device registry failure"),
        ),
        patch(
            "custom_components.eedomus.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True


@pytest.mark.asyncio
async def test_setup_entry_mapping_table_failure(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_API_USER: "user",
            CONF_API_SECRET: "secret",
            CONF_ENABLE_API_EEDOMUS: True,
            CONF_ENABLE_API_PROXY: False,
            CONF_ENABLE_HISTORY: False,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.config_entry = entry

    with (
        patch(
            "custom_components.eedomus.EedomusClient",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.eedomus.EedomusDataUpdateCoordinator",
            return_value=coordinator,
        ),
        patch(
            "custom_components.eedomus.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.mapping_registry.print_mapping_table",
            side_effect=RuntimeError("mapping table failure"),
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True


@pytest.mark.asyncio
async def test_setup_entry_api_services_failure(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_API_USER: "user",
            CONF_API_SECRET: "secret",
            CONF_ENABLE_API_EEDOMUS: True,
            CONF_ENABLE_API_PROXY: False,
            CONF_ENABLE_HISTORY: False,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.config_entry = entry

    with (
        patch(
            "custom_components.eedomus.EedomusClient",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.eedomus.EedomusDataUpdateCoordinator",
            return_value=coordinator,
        ),
        patch(
            "custom_components.eedomus.async_setup_services",
            new_callable=AsyncMock,
            side_effect=RuntimeError("services failure"),
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True


@pytest.mark.asyncio
async def test_setup_entry_history_setup_failure(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_API_USER: "user",
            CONF_API_SECRET: "secret",
            CONF_ENABLE_API_EEDOMUS: True,
            CONF_ENABLE_API_PROXY: False,
            CONF_ENABLE_HISTORY: True,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.config_entry = entry

    with (
        patch(
            "custom_components.eedomus.EedomusClient",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.eedomus.EedomusDataUpdateCoordinator",
            return_value=coordinator,
        ),
        patch(
            "custom_components.eedomus.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.history_sensor.async_setup_history_sensors",
            new_callable=AsyncMock,
            side_effect=RuntimeError("history failure"),
        ),
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.mapping_registry.print_mapping_table",
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True


@pytest.mark.asyncio
async def test_setup_entry_proxy_security_disabled_webhook_disabled(
    hass,
    mock_http,
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_ENABLE_API_EEDOMUS: False,
            CONF_ENABLE_API_PROXY: True,
            CONF_ENABLE_WEBHOOK: False,
            CONF_API_PROXY_DISABLE_SECURITY: True,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.eedomus.async_setup_services",
        new_callable=AsyncMock,
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True

    # Proxy seulement : une seule vue doit être enregistrée.
    assert mock_http.register_view.call_count == 1


@pytest.mark.asyncio
async def test_async_migrate_entry_backs_up_mapping_file(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        data={},
        options={},
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.eedomus.os.path.exists",
            return_value=True,
        ),
        patch.object(
            hass,
            "async_add_executor_job",
            new_callable=AsyncMock,
        ) as mock_executor,
    ):
        result = await async_migrate_entry(hass, entry)

    assert result is True
    assert entry.version == CONFIG_VERSION
    mock_executor.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_entry_history_enabled_from_data_only(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_API_USER: "user",
            CONF_API_SECRET: "secret",
            CONF_ENABLE_API_EEDOMUS: True,
            CONF_ENABLE_API_PROXY: False,
            CONF_ENABLE_HISTORY: True,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.config_entry = entry

    with (
        patch(
            "custom_components.eedomus.EedomusClient",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.eedomus.EedomusDataUpdateCoordinator",
            return_value=coordinator,
        ),
        patch(
            "custom_components.eedomus.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.history_sensor.async_setup_history_sensors",
            new_callable=AsyncMock,
        ) as mock_history,
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.mapping_registry.print_mapping_table",
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True
    mock_history.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_entry_history_disabled_from_data_only(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_API_USER: "user",
            CONF_API_SECRET: "secret",
            CONF_ENABLE_API_EEDOMUS: True,
            CONF_ENABLE_API_PROXY: False,
            CONF_ENABLE_HISTORY: False,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    coordinator.config_entry = entry

    with (
        patch(
            "custom_components.eedomus.EedomusClient",
            return_value=MagicMock(),
        ),
        patch(
            "custom_components.eedomus.EedomusDataUpdateCoordinator",
            return_value=coordinator,
        ),
        patch(
            "custom_components.eedomus.async_setup_services",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.history_sensor.async_setup_history_sensors",
            new_callable=AsyncMock,
        ) as mock_history,
        patch.object(
            hass.config_entries,
            "async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.mapping_registry.print_mapping_table",
        ),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True
    mock_history.assert_not_awaited()


@pytest.mark.asyncio
async def test_setup_entry_no_mode_enabled(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_ENABLE_API_EEDOMUS: False,
            CONF_ENABLE_API_PROXY: False,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    result = await async_setup_entry(hass, entry)

    assert result is False


@pytest.mark.asyncio
async def test_setup_entry_proxy_services_failure(hass, mock_http):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        data={
            CONF_API_HOST: "192.168.1.50",
            CONF_ENABLE_API_EEDOMUS: False,
            CONF_ENABLE_API_PROXY: True,
        },
        options={},
        unique_id="eedomus_192.168.1.50",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.eedomus.async_setup_services",
        new_callable=AsyncMock,
        side_effect=RuntimeError("proxy services failure"),
    ):
        result = await async_setup_entry(hass, entry)

    assert result is True


def test_get_clean_box_name_split_failure():
    class BrokenSplitStr(str):
        def split(self, *args, **kwargs):
            raise RuntimeError("split failure")

    entry = MagicMock()
    entry.data = {"host": BrokenSplitStr("Eedomus (192.168.1.50)")}
    entry.title = "Eedomus"

    result = get_clean_box_name(entry)

    assert result == "Box eedomus (Eedomus (192.168.1.50))"
