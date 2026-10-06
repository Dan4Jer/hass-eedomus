"""Tests unitaires pour les services de l'intégration eedomus."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant, ServiceCall

from custom_components.eedomus.const import DOMAIN
from custom_components.eedomus.services import async_setup_services


@pytest.fixture
def mock_hass():
    """Fixture pour simuler l'instance Home Assistant."""
    hass = MagicMock()
    # On mock explicitement la structure attendue
    hass.services = MagicMock()
    # CORRECTION : On utilise MagicMock au lieu de AsyncMock
    hass.services.async_register = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    hass.config_entries.async_reload = AsyncMock()
    return hass


@pytest.fixture
def mock_coordinator():
    """Fixture pour simuler le DataUpdateCoordinator."""
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "test_entry_id"
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_set_periph_value = AsyncMock()
    # Périphériques simulés en cache
    coordinator.data = {
        "100": {"name": "Test Device 1", "ha_entity": "light"},
        "200": {"name": "Test Thermostat", "ha_entity": "climate"},
    }
    return coordinator


@pytest.fixture
async def registered_services(mock_hass, mock_coordinator):
    """Fixture qui initialise les services et capture leurs callbacks pour les tester isolément."""

    # Dictionnaire pour stocker les fonctions de callback (les "handle_*")
    services = {}

    def mock_register(domain, service, handler):
        services[service] = handler

    mock_hass.services.async_register.side_effect = mock_register

    await async_setup_services(mock_hass, mock_coordinator)
    return services


# --- Tests: Setup Général ---


async def test_async_setup_services_registration(mock_hass, mock_coordinator):
    """Vérifie que tous les services sont bien enregistrés."""
    await async_setup_services(mock_hass, mock_coordinator)

    assert mock_hass.services.async_register.call_count == 6
    registered = [
        call.args[1] for call in mock_hass.services.async_register.call_args_list
    ]
    assert "refresh" in registered
    assert "set_value" in registered
    assert "reload" in registered
    assert "set_climate_temperature" in registered
    assert "cleanup_unused_entities" in registered
    assert "cleanup_unused_devices" in registered


# --- Tests: Service 'refresh' ---


async def test_handle_refresh_success(registered_services, mock_coordinator):
    """Vérifie que le service refresh appelle bien le coordinateur."""
    call = ServiceCall(DOMAIN, "refresh", {})
    await registered_services["refresh"](call)

    mock_coordinator.async_request_refresh.assert_called_once()


async def test_handle_refresh_no_coordinator(mock_hass):
    """Vérifie le comportement si aucun coordinateur n'est fourni."""
    services = {}
    mock_hass.services.async_register.side_effect = lambda d, s, h: services.update(
        {s: h}
    )
    await async_setup_services(mock_hass, None)

    # Ne doit pas planter
    call = ServiceCall(DOMAIN, "refresh", {})
    await services["refresh"](call)


async def test_handle_refresh_exception(registered_services, mock_coordinator):
    """Vérifie la remontée d'erreur si la mise à jour échoue."""
    mock_coordinator.async_request_refresh.side_effect = Exception("Crash")
    call = ServiceCall(DOMAIN, "refresh", {})

    with pytest.raises(Exception, match="Crash"):
        await registered_services["refresh"](call)


# --- Tests: Service 'set_value' ---


async def test_handle_set_value_missing_params(registered_services):
    """Vérifie la validation des paramètres manquants pour set_value."""
    call_missing_value = ServiceCall(DOMAIN, "set_value", {"device_id": "100"})
    with pytest.raises(ValueError, match="device_id and value are required"):
        await registered_services["set_value"](call_missing_value)


async def test_handle_set_value_success(registered_services, mock_coordinator):
    """Vérifie l'application d'une valeur et le rechargement (success = 1)."""
    mock_coordinator.async_set_periph_value.return_value = {"success": 1}
    call = ServiceCall(
        None, DOMAIN, "set_value", data={"device_id": "100", "value": "on"}
    )

    await registered_services["set_value"](call)

    mock_coordinator.async_set_periph_value.assert_called_once_with("100", "on")
    mock_coordinator.async_request_refresh.assert_called_once()


async def test_handle_set_value_api_error(registered_services, mock_coordinator):
    """Vérifie l'erreur quand l'API eedomus renvoie une erreur (success != 1)."""
    mock_coordinator.async_set_periph_value.return_value = {
        "success": 0,
        "error": "Invalid value",
    }
    call = ServiceCall(
        None, DOMAIN, "set_value", data={"device_id": "100", "value": "bad"}
    )

    with pytest.raises(ValueError, match="Failed to set value: Invalid value"):
        await registered_services["set_value"](call)


# --- Tests: Service 'reload' ---


async def test_handle_reload_success(registered_services, mock_hass, mock_coordinator):
    """Vérifie le rechargement de l'entrée de configuration."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_id"
    mock_hass.config_entries.async_entries.return_value = [mock_entry]
    mock_hass.config_entries.async_reload = AsyncMock()

    call = ServiceCall(DOMAIN, "reload", {})
    await registered_services["reload"](call)

    mock_hass.config_entries.async_reload.assert_called_once_with("test_entry_id")


async def test_handle_reload_not_found(registered_services, mock_hass):
    """Vérifie l'erreur si l'entrée de configuration est introuvable."""
    mock_hass.config_entries.async_entries.return_value = []

    call = ServiceCall(DOMAIN, "reload", {})
    with pytest.raises(ValueError, match="Config entry not found"):
        await registered_services["reload"](call)


# --- Tests: Service 'set_climate_temperature' ---


async def test_set_climate_temperature_validation(registered_services):
    """Vérifie la validation de base (types, limites, id)."""
    # Manquant
    with pytest.raises(ValueError, match="device_id is required"):
        await registered_services["set_climate_temperature"](
            ServiceCall(None, DOMAIN, "test", data={"temperature": 20})
        )
    with pytest.raises(ValueError, match="temperature is required"):
        await registered_services["set_climate_temperature"](
            ServiceCall(None, DOMAIN, "test", data={"device_id": "200"})
        )

    # Hors limites
    with pytest.raises(
        ValueError, match="Temperature must be between 7.0°C and 30.0°C"
    ):
        await registered_services["set_climate_temperature"](
            ServiceCall(
                None, DOMAIN, "test", data={"device_id": "200", "temperature": "5.0"}
            )
        )
    with pytest.raises(
        ValueError, match="Temperature must be between 7.0°C and 30.0°C"
    ):
        await registered_services["set_climate_temperature"](
            ServiceCall(
                None, DOMAIN, "test", data={"device_id": "200", "temperature": 32}
            )
        )

    # Type invalide
    with pytest.raises(ValueError, match="Temperature must be a valid number"):
        await registered_services["set_climate_temperature"](
            ServiceCall(
                None, DOMAIN, "test", data={"device_id": "200", "temperature": "abc"}
            )
        )


async def test_set_climate_temperature_wrong_entity(registered_services):
    """Vérifie qu'on empêche la mise à jour si ce n'est pas un climate."""
    call = ServiceCall(
        None,
        DOMAIN,
        "set_climate_temperature",
        data={"device_id": "100", "temperature": 20},
    )
    with pytest.raises(ValueError, match="Device 100 is not a climate entity"):
        await registered_services["set_climate_temperature"](call)


async def test_set_climate_temperature_success(
    registered_services, mock_hass, mock_coordinator
):
    """Vérifie la mise à jour du thermostat (arrondi, appel HA, refresh)."""
    mock_climate = MagicMock()
    mock_climate._periph_id = "200"
    mock_climate.async_set_temperature = AsyncMock()

    # Injonction de l'entité mock dans les données HA
    mock_hass.data[DOMAIN] = {"test_entry_id": {"entities": [mock_climate]}}

    # Température à arrondir: 21.2 doit devenir 21.0, 21.3 -> 21.5
    call = ServiceCall(
        None,
        DOMAIN,
        "set_climate_temperature",
        data={"device_id": "200", "temperature": "21.3"},
    )
    result = await registered_services["set_climate_temperature"](call)

    mock_climate.async_set_temperature.assert_called_once_with(temperature=21.5)
    mock_coordinator.async_request_refresh.assert_called_once()
    assert result["success"] is True
    assert result["temperature"] == 21.5


# --- Tests: Service 'cleanup_unused_entities' ---


async def test_cleanup_unused_entities(
    registered_services, mock_hass, mock_coordinator
):
    """Vérifie le balayage du registre d'entités et les bonnes règles de suppression."""
    mock_er = MagicMock()
    mock_dr = MagicMock()

    # Simulation d'un appareil valide dans le registre des appareils rattaché à l'entrée de configuration
    mock_device = MagicMock()
    mock_device.id = "test_device_id"
    mock_device.config_entries = {"test_entry_id"}
    mock_device.identifiers = {
        (DOMAIN, "100"),
        (DOMAIN, "box1_100"),
        (DOMAIN, "eedomus_box1_100"),
    }
    mock_dr.async_get_device.return_value = mock_device
    mock_dr.devices = {"test_device_id": mock_device}

    # Création des différentes entités testées avec leur config_entry_id et device_id pour l'entité valide
    ent_valid = MagicMock(
        platform="eedomus",
        disabled=False,
        unique_id="eedomus_box1_100",
        entity_id="light.valid",
        config_entry_id="test_entry_id",
        device_id="test_device_id",
    )
    ent_disabled = MagicMock(
        platform="eedomus",
        disabled=True,
        unique_id="eedomus_box1_101",
        entity_id="light.disabled",
        config_entry_id="test_entry_id",
        device_id=None,
    )
    ent_deprecated = MagicMock(
        platform="eedomus",
        disabled=False,
        unique_id="eedomus_box1_102_deprecated",
        entity_id="light.deprecated",
        config_entry_id="test_entry_id",
        device_id=None,
    )
    ent_orphaned = MagicMock(
        platform="eedomus",
        disabled=False,
        unique_id="eedomus_box1_999",
        entity_id="light.orphaned",
        config_entry_id="test_entry_id",
        device_id=None,
    )  # 999 pas dans coordinator
    ent_no_unique = MagicMock(
        platform="eedomus",
        disabled=False,
        unique_id=None,
        entity_id="light.no_unique",
        config_entry_id="test_entry_id",
        device_id=None,
    )
    ent_other = MagicMock(
        platform="other_platform",
        entity_id="light.other",
        config_entry_id="other_entry_id",
        device_id=None,
    )

    mock_er.entities = {
        "light.valid": ent_valid,
        "light.disabled": ent_disabled,
        "light.deprecated": ent_deprecated,
        "light.orphaned": ent_orphaned,
        "light.no_unique": ent_no_unique,
        "light.other": ent_other,
    }

    # Simulation des données du coordinateur sous forme de liste standard (gérée nativement dans services.py)
    mock_coordinator.last_update_success = True
    mock_coordinator.data = [
        {
            "id": "100",
            "periph_id": "100",
            "periph_id_int": 100,
            "unique_id": "eedomus_box1_100",
            "name": "Valid Light",
        }
    ]

    # Simulation d'une entrée de configuration active
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_id"
    mock_hass.config_entries.async_entries.return_value = [mock_entry]

    # Objet mock supportant l'accès par attribut (.coordinator) et par dictionnaire (["coordinator"])
    class EntryDataMock(MagicMock):
        @property
        def coordinator(self):
            return mock_coordinator

        def __getitem__(self, key):
            if key == "coordinator":
                return mock_coordinator
            return super().__getitem__(key)

    mock_hass.data[DOMAIN] = {
        "test_entry_id": EntryDataMock(),
    }

    with patch(
        "homeassistant.helpers.entity_registry.async_get", return_value=mock_er
    ), patch("homeassistant.helpers.device_registry.async_get", return_value=mock_dr):
        call = ServiceCall(None, DOMAIN, "cleanup_unused_entities", {})
        result = await registered_services["cleanup_unused_entities"](call)

    # 5 entités eedomus considérées, 4 retirées (toutes sauf ent_valid)

    assert result["success"] is True
    assert result["entities_analyzed"] == 6
    assert result["entities_considered"] == 5
    assert result["entities_removed"] == 4

    # Vérifie que les bonnes entités ont été supprimées
    mock_er.async_remove.assert_any_call("light.disabled")
    mock_er.async_remove.assert_any_call("light.deprecated")
    mock_er.async_remove.assert_any_call("light.orphaned")
    mock_er.async_remove.assert_any_call("light.no_unique")


# --- Tests: Service 'cleanup_unused_devices' ---


async def test_cleanup_unused_devices(registered_services):
    """Vérifie le balayage du registre d'appareils et la suppression ciblée."""
    mock_dr = MagicMock()
    mock_er = MagicMock()

    # Appareils
    dev_valid = MagicMock(
        id="dev1", name="Valid", disabled_by=None, identifiers={("eedomus", "100")}
    )
    dev_disabled = MagicMock(
        id="dev2", name="Disabled", disabled_by="user", identifiers={("eedomus", "101")}
    )
    dev_no_entity = MagicMock(
        id="dev3", name="NoEntity", disabled_by=None, identifiers={("eedomus", "102")}
    )
    dev_other = MagicMock(
        id="dev4", name="Other", disabled_by=None, identifiers={("other", "103")}
    )

    mock_dr.devices = {
        "dev1": dev_valid,
        "dev2": dev_disabled,
        "dev3": dev_no_entity,
        "dev4": dev_other,
    }

    # Seul dev1 possède une entité liée
    mock_er.entities = {
        "ent1": MagicMock(device_id="dev1"),
        "ent_other": MagicMock(device_id="dev4"),
    }

    with patch(
        "homeassistant.helpers.device_registry.async_get", return_value=mock_dr
    ), patch("homeassistant.helpers.entity_registry.async_get", return_value=mock_er):
        call = ServiceCall(DOMAIN, "cleanup_unused_devices", {})
        result = await registered_services["cleanup_unused_devices"](call)

    assert result["success"] is True
    assert result["devices_considered"] == 3  # dev1, dev2, dev3
    assert result["devices_removed"] == 2  # dev2, dev3

    mock_dr.async_remove_device.assert_any_call("dev2")
    mock_dr.async_remove_device.assert_any_call("dev3")
