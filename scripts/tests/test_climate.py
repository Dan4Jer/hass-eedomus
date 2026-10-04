"""Tests unitaires pour le chargement et la fusion des configurations YAML dans device_mapping."""

import re

from unittest.mock import AsyncMock, MagicMock, mock_open, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

import pytest

from homeassistant.const import STATE_ON

from custom_components.eedomus.climate import (
    EedomusClimate,
    async_setup_entry,
)
from custom_components.eedomus.device_mapping import (
    load_and_merge_yaml_mappings,
    load_yaml_file,
    merge_yaml_mappings,
)


# --- 1. Tests de chargement de fichier YAML ---

def test_load_yaml_file_success():
    """Vérifie le chargement réussi d'un fichier YAML valide."""
    fake_yaml_content = """
    usage_mappings:
      "1":
        ha_entity: "switch"
    """
    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", mock_open(read_data=fake_yaml_content)
    ):
        content = load_yaml_file("/fake/path/config.yaml")
        assert content is not None
        assert "usage_mappings" in content
        assert content["usage_mappings"]["1"]["ha_entity"] == "switch"


def test_load_yaml_file_not_found():
    """Vérifie qu'un fichier inexistant retourne None sans faire crasher l'intégration."""
    with patch("os.path.exists", return_value=False):
        content = load_yaml_file("/path/does_not_exist.yaml")
        assert content is None


# --- 2. Tests de fusion des Mappings (Merge) ---

def test_merge_yaml_mappings_with_custom_overrides():
    """Vérifie que custom_specific_device_dynamic_overrides surcharge correctement la configuration de base."""
    base_mappings = {
        "usage_mappings": {"1": {"ha_entity": "switch"}},
        "dynamic_entity_properties": {"climate": {}},
        "specific_device_dynamic_overrides": {
            "111111": {"ha_entity": "light"},
            "3463520": {"ha_entity": "switch"},
        },
    }

    custom_mappings = {
        "custom_specific_device_dynamic_overrides": {
            "3463520": {
                "ha_entity": "climate",
                "ha_subtype": "thermostat",
                "icon": "mdi:thermostat",
            }
        },
    }

    merged = merge_yaml_mappings(base_mappings, custom_mappings)

    assert "specific_device_dynamic_overrides" in merged
    assert "111111" in merged["specific_device_dynamic_overrides"]
    assert (
        merged["specific_device_dynamic_overrides"]["111111"]["ha_entity"]
        == "light"
    )
    assert (
        merged["specific_device_dynamic_overrides"]["3463520"]["ha_entity"]
        == "climate"
    )
    assert (
        merged["specific_device_dynamic_overrides"]["3463520"]["ha_subtype"]
        == "thermostat"
    )


# --- 3. Tests de chargement global ---
def test_load_and_merge_yaml_mappings():
    """Vérifie le pipeline complet de chargement et fusion."""
    mock_base = {
        "usage_id_mappings": {"1": {"ha_entity": "switch"}},
        "dynamic_entity_properties": {"switch": {}},
        "specific_device_dynamic_overrides": {},
    }
    mock_custom = {
        "custom_specific_device_dynamic_overrides": {
            "3463520": {"ha_entity": "climate"}
        }
    }

    def mock_load_yaml(filepath):
        filepath_str = str(filepath)
        if "custom_mapping.yaml" in filepath_str:
            return mock_custom
        if "device_mapping.yaml" in filepath_str:
            return mock_base
        return mock_base

    with patch("os.path.exists", return_value=True), patch(
        "custom_components.eedomus.device_mapping.load_yaml_file",
        side_effect=mock_load_yaml,
    ):
        result = load_and_merge_yaml_mappings()

        assert "usage_id_mappings" in result
        assert "specific_device_dynamic_overrides" in result
        assert (
            result["specific_device_dynamic_overrides"]["3463520"]["ha_entity"]
            == "climate"
        )


async def test_climate_set_temperature(
    hass: HomeAssistant, aioclient_mock, enable_custom_integrations
) -> None:
    """Vérifie le changement de température de consigne sur le climate."""
    base_url = "http://192.168.1.50/api/get"

    # Mock spécifique pour periph.list (découverte initiale avec mot-clé Thermostat)
    aioclient_mock.get(
        re.compile(r"http://192\.168\.1\.50/api/get\?.*action=periph\.list.*"),
        json={
            "success": 1,
            "body": [
                {
                    "periph_id": "12345",
                    "name": "Thermostat Salon",
                    "usage_id": "15",
                    "value": "20",
                    "last_value": "20",
                }
            ],
        },
    )

    # Mock général pour toutes les autres requêtes GET (caract, value, etc.)
    aioclient_mock.get(
        re.compile(r"http://192\.168\.1\.50/api/get\?.*"),
        json={
            "success": 1,
            "body": [
                {
                    "periph_id": "12345",
                    "name": "Thermostat Salon",
                    "usage_id": "15",
                    "value": "21",
                    "last_value": "21",
                }
            ],
        },
    )

    # Mock pour les appels de modification de consigne (set)
    aioclient_mock.get(
        re.compile(r"http://192\.168\.1\.50/api/set\?.*"),
        json={"success": 1, "body": "OK"},
    )
    aioclient_mock.post(
        re.compile(r"http://192\.168\.1\.50/api/set\?.*"),
        json={"success": 1, "body": "OK"},
    )

    # Création et initialisation du composant
    config_entry = MockConfigEntry(
        domain="eedomus",
        data={"api_host": "192.168.1.50", "api_user": "user", "api_secret": "secret"},
    )
    config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Exécution du service set_temperature
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {
            "entity_id": "climate.thermostat_salon",
            "temperature": 21,
        },
        blocking=True,
    )

    # Vérifications des états
    state = hass.states.get("climate.thermostat_salon")
    assert state is not None, "L'entité climate.thermostat_salon n'a pas été créée"
    assert float(state.attributes.get("temperature")) == 21.0


async def test_climate_custom_specific_device_dynamic_overrides(
    hass: HomeAssistant, aioclient_mock, enable_custom_integrations
) -> None:
    """Vérifie la prise en compte des overrides dynamiques spécifiques pour une entité climate."""
    aioclient_mock.get(
        re.compile(r"http://192\.168\.1\.50/api/get\?.*action=periph\.list.*"),
        json={
            "success": 1,
            "body": [
                {
                    "periph_id": "3463520",
                    "name": "Thermostat Salle a manger",
                    "usage_id": "0",
                    "value": "20.5",
                    "last_value": "20.5",
                    "values": [
                        {"value": "20.0", "description": "20.0"},
                        {"value": "20.5", "description": "20.5"},
                        {"value": "21.0", "description": "21.0"},
                    ],
                }
            ],
        },
    )

    aioclient_mock.get(
        re.compile(r"http://192\.168\.1\.50/api/get\?.*"),
        json={
            "success": 1,
            "body": [
                {
                    "periph_id": "3463520",
                    "name": "Thermostat Salle a manger",
                    "usage_id": "0",
                    "value": "21.0",
                    "last_value": "21.0",
                }
            ],
        },
    )

    aioclient_mock.get(
        re.compile(r"http://192\.168\.1\.50/api/set\?.*"),
        json={"success": 1, "body": "OK"},
    )

    custom_mappings = {
        "custom_specific_device_dynamic_overrides": {
            "3463520": {
                "ha_entity": "climate",
                "ha_subtype": "thermostat",
                "device_class": "temperature",
                "temperature_step": 0.5,
                "precision": 0.5,
                "target_temp_step": 0.5,
                "unit_of_measurement": "°C",
                "icon": "mdi:thermostat",
                "is_dynamic": True,
                "justification": "Thermostat Salle a manger - consigne température",
            }
        }
    }

    with patch(
        "custom_components.eedomus.device_mapping.load_custom_yaml_mappings_async",
        return_value=custom_mappings,
    ):
        config_entry = MockConfigEntry(
            domain="eedomus",
            data={"api_host": "192.168.1.50", "api_user": "user", "api_secret": "secret"},
        )
        config_entry.add_to_hass(hass)

        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("climate.thermostat_salle_a_manger")
        assert state is not None, "L'entité climate.thermostat_salle_a_manger n'a pas été créée"
        assert state.attributes.get("target_temp_step") == 0.5

        await hass.services.async_call(
            "climate",
            "set_temperature",
            {
                "entity_id": "climate.thermostat_salle_a_manger",
                "temperature": 21.0,
            },
            blocking=True,
        )

        state = hass.states.get("climate.thermostat_salle_a_manger")
        assert float(state.attributes.get("temperature")) == 21.0


@pytest.mark.asyncio
async def test_climate_set_hvac_mode(hass):
    """Test setting HVAC mode on climate entity."""
    mock_coordinator = MagicMock()
    mock_coordinator.get_yaml_config_sync.return_value = {}
    mock_coordinator.async_request_refresh = AsyncMock()
    mock_coordinator.async_set_periph_value = AsyncMock(return_value={"success": 1})
    mock_coordinator.data = {
        "climate_123": {
            "periph_id": "climate_123",
            "name": "Chauffage Bureau",
            "usage_id": "15",
            "last_value": "20",
            "values": [
                {"value": "1", "description": "heat"},
                {"value": "0", "description": "off"}
            ]
        }
    }
    
    entity = EedomusClimate(mock_coordinator, "climate_123")
    entity.hass = hass  # Utilisation de la fixture hass au lieu d'un MagicMock brut
    entity.entity_id = "climate.chauffage_bureau"

    # Test setting mode to heat
    await entity.async_set_hvac_mode("heat")
    mock_coordinator.async_set_periph_value.assert_called_once()

@pytest.mark.asyncio
async def test_climate_alternative_temperature_mapping(hass):
    """Test temperature setting fallback when usage_id is not 15 (using value list mapping)."""
    mock_coordinator = MagicMock()
    mock_coordinator.get_yaml_config_sync.return_value = {}
    mock_coordinator.async_set_periph_value = AsyncMock(return_value={"success": 1})
    mock_coordinator.async_request_refresh = AsyncMock()
    mock_coordinator.data = {
        "climate_alt": {
            "periph_id": "climate_alt",
            "name": "Chauffage Autre",
            "usage_id": "16",  # Autre usage que 15
            "last_value": "20",
            "values": [
                {"value": "10", "description": "Eco"},
                {"value": "20", "description": "Confort"}
            ]
        }
    }

    entity = EedomusClimate(mock_coordinator, "climate_alt")
    entity.hass = hass  # Utilisation de la fixture hass
    entity.entity_id = "climate.chauffage_autre"

    # Demander une température qui correspond à un libellé ou valeur exacte
    await entity.async_set_temperature(temperature=20)
    mock_coordinator.async_set_periph_value.assert_called_once()


@pytest.mark.asyncio
async def test_climate_set_temperature_exception():
    """Test exception handling during temperature update."""
    mock_coordinator = MagicMock()
    mock_coordinator.get_yaml_config_sync.return_value = {}
    mock_coordinator.data = {
        "climate_exc": {
            "periph_id": "climate_exc",
            "name": "Chauffage Erreur",
            "usage_id": "15",
            "last_value": "20"
        }
    }

    entity = EedomusClimate(mock_coordinator, "climate_exc")
    entity.coordinator.async_set_periph_value = AsyncMock(side_effect=Exception("API Error"))

    # Ne doit pas lever d'erreur non gérée mais logger / intercepter
    try:
        await entity.async_set_temperature(temperature=22)
    except Exception:
        pass


@pytest.mark.asyncio
async def test_climate_async_setup_entry_maps_and_creates_entities(hass):
    coordinator = MagicMock()

    coordinator.data = {
        "climate_1": {
            "name": "Thermostat Salon",
            "usage_id": "15",
            "last_value": "20",
        },
        "sensor_1": {
            "name": "Température",
            "usage_id": "7",
            "last_value": "19",
            "ha_entity": "sensor",
        },
    }

    coordinator.get_all_peripherals.return_value = {
        "climate_1": coordinator.data["climate_1"],
        "sensor_1": coordinator.data["sensor_1"],
    }

    hass.data.setdefault("eedomus", {})
    hass.data["eedomus"]["entry_1"] = {
        "coordinator": coordinator,
    }

    entry = MagicMock()
    entry.entry_id = "entry_1"

    async_add_entities = MagicMock()

    with (
        patch(
            "custom_components.eedomus.climate.map_device_to_ha_entity",
            return_value={
                "ha_entity": "climate",
                "ha_subtype": "thermostat",
            },
        ) as mock_mapping,
        patch(
            "custom_components.eedomus.climate.register_device_mapping",
        ) as mock_register,
    ):
        await async_setup_entry(
            hass,
            entry,
            async_add_entities,
        )

    mock_mapping.assert_called_once()
    mock_register.assert_called_once()

    assert coordinator.data["climate_1"]["ha_entity"] == "climate"

    async_add_entities.assert_called_once()

    entities, update_before_add = async_add_entities.call_args.args

    assert update_before_add is True
    assert len(entities) == 1
    assert isinstance(entities[0], EedomusClimate)
    assert entities[0]._periph_id == "climate_1"

def test_climate_yaml_linked_temperature_sensor_and_switch():
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "entry_1"

    coordinator.data = {
        "climate_1": {
            "name": "Thermostat Salon",
            "usage_id": "15",
            "last_value": "20",
        },
        "temp_1": {
            "name": "Sonde Salon",
            "usage_id": "7",
            "last_value": "19.5",
        },
        "switch_1": {
            "name": "Chauffage Salon",
            "last_value": "1",
        },
    }

    coordinator.get_all_peripherals.return_value = coordinator.data

    coordinator.get_yaml_config_sync.return_value = {
        "temperature_setpoint_mappings": {
            "climate_1": "temp_1",
        },
        "heating_switch_mappings": {
            "climate_1": "switch_1",
        },
    }

    entity = EedomusClimate(
        coordinator,
        "climate_1",
    )

    assert entity._linked_temperature_sensor == "temp_1"
    assert entity._linked_heating_switch == "switch_1"

@pytest.mark.asyncio
async def test_climate_async_added_loads_custom_links(hass):
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "entry_1"

    coordinator.data = {
        "climate_1": {
            "name": "Thermostat Salon",
            "usage_id": "15",
            "last_value": "20",
        }
    }

    coordinator.get_all_peripherals.return_value = coordinator.data
    coordinator.get_yaml_config_sync.return_value = {}

    entity = EedomusClimate(
        coordinator,
        "climate_1",
    )
    entity.hass = hass

    custom_mappings = {
        "temperature_setpoint_mappings": {
            "climate_1": "temp_1",
        },
        "heating_switch_mappings": {
            "climate_1": "switch_1",
        },
    }

    with (
        patch(
            "custom_components.eedomus.entity.EedomusEntity.async_added_to_hass",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.device_mapping.load_custom_yaml_mappings_async",
            new_callable=AsyncMock,
            return_value=custom_mappings,
        ),
    ):
        await entity.async_added_to_hass()

    assert entity._linked_temperature_sensor == "temp_1"
    assert entity._linked_heating_switch == "switch_1"

@pytest.mark.asyncio
async def test_climate_async_added_custom_mapping_failure(hass):
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "entry_1"

    coordinator.data = {
        "climate_1": {
            "name": "Thermostat Salon",
            "usage_id": "15",
            "last_value": "20",
        }
    }

    coordinator.get_all_peripherals.return_value = coordinator.data
    coordinator.get_yaml_config_sync.return_value = {}

    entity = EedomusClimate(
        coordinator,
        "climate_1",
    )
    entity.hass = hass

    with (
        patch(
            "custom_components.eedomus.entity.EedomusEntity.async_added_to_hass",
            new_callable=AsyncMock,
        ),
        patch(
            "custom_components.eedomus.device_mapping.load_custom_yaml_mappings_async",
            new_callable=AsyncMock,
            side_effect=RuntimeError("mapping failure"),
        ),
    ):
        await entity.async_added_to_hass()

    assert entity._linked_temperature_sensor is None
    assert entity._linked_heating_switch is None


