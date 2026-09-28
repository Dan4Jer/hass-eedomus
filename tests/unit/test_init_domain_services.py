"""Unit tests for the domain-level service wiring in __init__.py (P.1.1).

async_setup_entry must initialize ConfigManager, DataService, SchemaService
and UIService in dependency order, store them under the domain-level keys of
hass.data[DOMAIN] (not per entry), and stay idempotent across config entry
reloads so the websocket commands are only registered once.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

import custom_components.eedomus as eedomus_init
from custom_components.eedomus.const import DOMAIN

pytestmark = pytest.mark.unit


def make_hass():
    hass = MagicMock()
    hass.data = {}
    return hass


def patch_init_helpers(monkeypatch, **returns):
    """Patch the four _async_init_* helpers with AsyncMocks."""
    mocks = {}
    for name, value in returns.items():
        mock = AsyncMock(return_value=value)
        monkeypatch.setattr(eedomus_init, f"_async_init_{name}", mock)
        mocks[name] = mock
    return mocks


def make_ui_service(initialized=True):
    """Fake UIService exposing is_initialized() / async_init()."""
    ui_service = MagicMock()
    ui_service.is_initialized.return_value = initialized
    ui_service.async_init = AsyncMock()
    return ui_service


class TestAsyncSetupDomainServices:
    @pytest.mark.asyncio
    async def test_services_stored_under_domain_keys(self, monkeypatch):
        hass = make_hass()
        ui_service = make_ui_service()
        patch_init_helpers(
            monkeypatch,
            config_manager="cm_instance",
            data_service="ds_instance",
            schema_service="ss_instance",
            ui_service=ui_service,
        )

        await eedomus_init._async_setup_domain_services(hass)

        assert hass.data[DOMAIN] == {
            "config_manager": "cm_instance",
            "data_service": "ds_instance",
            "schema_service": "ss_instance",
            "ui_service": ui_service,
        }

    @pytest.mark.asyncio
    async def test_init_order_matches_dependencies(self, monkeypatch):
        """config_manager -> data_service -> schema_service -> ui_service."""
        hass = make_hass()
        order = []

        def make(name):
            async def _init(hass_arg):
                order.append(name)
                return f"{name}_instance"

            return AsyncMock(side_effect=_init)

        monkeypatch.setattr(
            eedomus_init, "_async_init_config_manager", make("config_manager")
        )
        monkeypatch.setattr(
            eedomus_init, "_async_init_data_service", make("data_service")
        )
        monkeypatch.setattr(
            eedomus_init, "_async_init_schema_service", make("schema_service")
        )
        ui_service = make_ui_service()

        async def _init_ui(hass_arg):
            order.append("ui_service")
            return ui_service

        monkeypatch.setattr(
            eedomus_init, "_async_init_ui_service", AsyncMock(side_effect=_init_ui)
        )

        await eedomus_init._async_setup_domain_services(hass)

        assert order == [
            "config_manager",
            "data_service",
            "schema_service",
            "ui_service",
        ]

    @pytest.mark.asyncio
    async def test_second_setup_is_idempotent(self, monkeypatch):
        """A reload must reuse the existing instances, not re-init them."""
        hass = make_hass()
        ui_service = make_ui_service()
        mocks = patch_init_helpers(
            monkeypatch,
            config_manager="cm_instance",
            data_service="ds_instance",
            schema_service="ss_instance",
            ui_service=ui_service,
        )

        await eedomus_init._async_setup_domain_services(hass)
        await eedomus_init._async_setup_domain_services(hass)

        for mock in mocks.values():
            mock.assert_called_once()
        assert hass.data[DOMAIN]["ui_service"] is ui_service
        # An initialized instance is not re-initialized on reload
        ui_service.async_init.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_failed_ui_service_registration_is_retried(self, monkeypatch):
        """A stored but uninitialized UIService gets async_init re-run."""
        hass = make_hass()
        patch_init_helpers(
            monkeypatch,
            config_manager="cm_instance",
            data_service="ds_instance",
            schema_service="ss_instance",
        )
        ui_service = make_ui_service(initialized=False)
        hass.data[DOMAIN] = {"ui_service": ui_service}

        await eedomus_init._async_setup_domain_services(hass)

        ui_service.async_init.assert_awaited_once()
        # The other services were still set up
        assert hass.data[DOMAIN]["config_manager"] == "cm_instance"

    @pytest.mark.asyncio
    async def test_partial_failure_does_not_block_remaining_services(self, monkeypatch):
        """One failing init is logged, the others still get set up."""
        hass = make_hass()
        ui_service = make_ui_service()
        monkeypatch.setattr(
            eedomus_init,
            "_async_init_config_manager",
            AsyncMock(side_effect=RuntimeError("boom")),
        )
        patch_init_helpers(
            monkeypatch,
            data_service="ds_instance",
            schema_service="ss_instance",
            ui_service=ui_service,
        )

        # Must not raise
        await eedomus_init._async_setup_domain_services(hass)

        assert "config_manager" not in hass.data[DOMAIN]
        assert hass.data[DOMAIN]["data_service"] == "ds_instance"
        assert hass.data[DOMAIN]["schema_service"] == "ss_instance"
        assert hass.data[DOMAIN]["ui_service"] is ui_service


class TestAsyncSetupEntryWiring:
    @pytest.mark.asyncio
    async def test_setup_entry_calls_domain_services_setup(self, monkeypatch):
        """async_setup_entry must branch the panel service family at setup."""
        hass = make_hass()
        hass.config_entries.async_forward_entry_setups = AsyncMock()
        hass.http = MagicMock()

        entry = MagicMock()
        entry.version = 4
        entry.unique_id = "eedomus_192.168.1.10"
        entry.entry_id = "test_entry"
        entry.data = {
            "api_host": "192.168.1.10",
            "api_eedomus": False,
            "enable_api_proxy": True,
        }
        entry.options = {}
        entry.update_listeners = []
        entry.add_update_listener = MagicMock(return_value=lambda: None)
        entry.async_on_unload = MagicMock()

        monkeypatch.setattr(eedomus_init, "async_setup_services", AsyncMock())
        monkeypatch.setattr(
            eedomus_init.aiohttp_client,
            "async_get_clientsession",
            MagicMock(return_value=MagicMock()),
        )
        # AD-13: setup ingests the custom mapping before anything reads it.
        # The lazy from-import resolves the attribute at call time, so the
        # patch targets the config_manager module itself.
        import custom_components.eedomus.config_manager as config_manager_module

        ingest = AsyncMock()
        monkeypatch.setattr(
            config_manager_module, "async_ingest_custom_mapping", ingest
        )
        setup_domain_services = AsyncMock()
        monkeypatch.setattr(
            eedomus_init, "_async_setup_domain_services", setup_domain_services
        )
        setup_panel = AsyncMock()
        monkeypatch.setattr(eedomus_init, "async_setup_panel", setup_panel)

        assert await eedomus_init.async_setup_entry(hass, entry) is True

        ingest.assert_awaited_once_with(hass)
        setup_domain_services.assert_awaited_once_with(hass)
        setup_panel.assert_awaited_once_with(hass)
        hass.config_entries.async_forward_entry_setups.assert_awaited_once()


class TestAsyncRemoveEntryTeardown:
    @pytest.mark.asyncio
    async def test_remove_last_entry_tears_down_panel(self, monkeypatch):
        """Removing the last entry must remove the sidebar panel."""
        hass = make_hass()
        hass.data[DOMAIN] = {"panel_registered": True}
        hass.config_entries.async_entries = MagicMock(return_value=[])
        unload_panel = AsyncMock()
        monkeypatch.setattr(eedomus_init, "async_unload_panel", unload_panel)

        entry = MagicMock()
        entry.options = {}
        await eedomus_init.async_remove_entry(hass, entry)

        unload_panel.assert_awaited_once_with(hass)

    @pytest.mark.asyncio
    async def test_remove_entry_with_sibling_keeps_panel(self, monkeypatch):
        """With another entry remaining, the panel must stay registered."""
        hass = make_hass()
        hass.data[DOMAIN] = {"panel_registered": True}
        sibling = MagicMock()
        sibling.entry_id = "sibling_entry"
        hass.config_entries.async_entries = MagicMock(return_value=[sibling])
        unload_panel = AsyncMock()
        monkeypatch.setattr(eedomus_init, "async_unload_panel", unload_panel)

        entry = MagicMock()
        entry.options = {}
        entry.entry_id = "last_entry"
        await eedomus_init.async_remove_entry(hass, entry)

        unload_panel.assert_not_awaited()
