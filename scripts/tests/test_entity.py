"""Tests unitaires pour la classe EedomusEntity et la logique de mapping."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.eedomus.const import DOMAIN
from custom_components.eedomus.entity import (
    DEVICE_MAPPINGS,
    INTEGRATION_VERSION,
    EedomusEntity,
    _create_mapping,
    map_device_to_ha_entity,
)


@pytest.fixture
def mock_coordinator():
    """Fixture pour simuler le DataUpdateCoordinator eedomus."""
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "box_12345"
    coordinator.data = {
        "1001": {
            "periph_id": "1001",
            "name": "Capteur Température",
            "usage_id": "1",
            "usage_name": "Température",
        },
        "1002": {
            "periph_id": "1002",
            "name": "Switch Canapé",
            "parent_periph_id": "1001",
            "usage_name": "Prise",
        },
    }
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


@pytest.fixture
def mock_hass():
    """Fixture pour simuler l'instance Home Assistant."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    return hass


# --- 1. Tests de l'initialisation du module ---


def test_version_loading():
    """Vérifie que la version est correctement initialisée."""
    assert isinstance(INTEGRATION_VERSION, str)


def test_device_mappings_initialization():
    """Vérifie que la structure globale DEVICE_MAPPINGS est bien initialisée."""
    assert DEVICE_MAPPINGS is not None
    assert isinstance(DEVICE_MAPPINGS, dict)


# --- 2. Tests de la classe EedomusEntity ---


def test_eedomus_entity_init_success(mock_coordinator):
    """Vérifie l'initialisation d'une entité valide."""
    entity = EedomusEntity(mock_coordinator, "1001")

    assert entity._periph_id == "1001"
    assert entity.name == "Capteur Température"
    assert entity.unique_id == "eedomus_box_12345_1001"
    assert entity._parent_id is None


def test_eedomus_entity_init_fallback(mock_coordinator):
    """Vérifie le comportement de secours lorsqu'un périphérique n'est pas trouvé."""
    entity = EedomusEntity(mock_coordinator, "9999")

    assert entity._periph_id == "9999"
    assert entity.name == "Unknown Device (9999)"
    assert entity.unique_id == "eedomus_box_12345_9999"
    assert entity._parent_id is None


def test_eedomus_entity_get_periph_data(mock_coordinator):
    """Vérifie la récupération des données du périphérique."""
    entity = EedomusEntity(mock_coordinator, "1001")
    data = entity._get_periph_data()
    assert data["name"] == "Capteur Température"

    # Test quand le coordinator n'a pas de données
    mock_coordinator.data = None
    assert entity._get_periph_data() is None


def test_eedomus_entity_device_info_standalone(mock_coordinator):
    """Vérifie la génération de device_info pour un appareil principal."""
    mock_coordinator.hub_device_id = "eedomus_box_box_12345"
    entity = EedomusEntity(mock_coordinator, "1001")
    info = entity.device_info

    assert info["identifiers"] == {(DOMAIN, "1001")}
    assert info["name"] == "Capteur Température"
    assert info["manufacturer"] == "Eedomus"
    assert info["via_device_id"] == "eedomus_box_box_12345"


def test_eedomus_entity_device_info_child(mock_coordinator):
    """Vérifie la génération de device_info pour un appareil enfant."""
    mock_coordinator.hub_device_id = "eedomus_box_box_12345"
    entity = EedomusEntity(mock_coordinator, "1002")
    info = entity.device_info

    # Doit pointer vers l'identifiant du parent
    assert info["identifiers"] == {(DOMAIN, "1001")}
    assert info["name"] == "Capteur Température"
    assert info["via_device_id"] == "eedomus_box_box_12345"


def test_eedomus_entity_device_info_missing_data(mock_coordinator):
    """Vérifie device_info quand le périphérique n'existe pas dans le coordinator."""
    entity = EedomusEntity(mock_coordinator, "9999")
    info = entity.device_info

    assert info["identifiers"] == {(DOMAIN, "9999")}
    assert info["name"] == "Unknown Device (9999)"


@pytest.mark.asyncio
async def test_eedomus_entity_async_update(mock_coordinator):
    """Vérifie l'appel du rafraîchissement asynchrone."""
    entity = EedomusEntity(mock_coordinator, "1001")
    await entity.async_update()
    mock_coordinator.async_request_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_eedomus_entity_async_added_to_hass(mock_coordinator):
    """Vérifie l'enregistrement dans Home Assistant lors de l'ajout."""
    entity = EedomusEntity(mock_coordinator, "1001")
    entity.async_schedule_update_ha_state = MagicMock()

    with patch(
        "homeassistant.helpers.update_coordinator.CoordinatorEntity.async_added_to_hass",
        AsyncMock(),
    ):
        await entity.async_added_to_hass()
        entity.async_schedule_update_ha_state.assert_called_once()


@pytest.mark.asyncio
async def test_eedomus_entity_async_set_value_success(mock_coordinator, mock_hass):
    """Vérifie le succès d'un changement de valeur via le service."""
    entity = EedomusEntity(mock_coordinator, "1001")
    entity.hass = mock_hass

    await entity.async_set_value("100")

    mock_hass.services.async_call.assert_called_once_with(
        DOMAIN,
        "set_value",
        {"device_id": "1001", "value": "100"},
        blocking=True,
        return_response=False,
    )


@pytest.mark.asyncio
async def test_eedomus_entity_async_set_value_error(mock_coordinator, mock_hass):
    """Vérifie la capture des exceptions lors d'un appel au service set_value."""
    entity = EedomusEntity(mock_coordinator, "1001")
    entity.hass = mock_hass
    mock_hass.services.async_call.side_effect = Exception("Service error")

    res = await entity.async_set_value("100")
    assert res is None


# --- 3. Tests de la fonction map_device_to_ha_entity ---


def test_map_device_specific_cases():
    """Vérifie la priorité 2 : détection des cas critiques par usage_id (27 et 37)."""
    smoke_device = {"periph_id": "1", "name": "Détecteur Fumée", "usage_id": "27"}
    result_smoke = map_device_to_ha_entity(smoke_device)
    assert result_smoke["ha_entity"] == "binary_sensor"
    assert result_smoke["ha_subtype"] == "smoke"

    motion_device = {"periph_id": "2", "name": "Détecteur Mouvement", "usage_id": "37"}
    result_motion = map_device_to_ha_entity(motion_device)
    assert result_motion["ha_entity"] == "binary_sensor"
    assert result_motion["ha_subtype"] == "motion"


def test_map_device_specific_overrides():
    """Vérifie la priorité 2.5 : overrides spécifiques par periph_id."""
    device_data = {
        "periph_id": "periph_override_test",
        "name": "Appareil Spécial",
        "usage_id": "1",
    }
    custom_mappings = {
        "specific_device_dynamic_overrides": {
            "periph_override_test": {"ha_entity": "light", "ha_subtype": "dimmer"}
        }
    }

    with patch.dict(
        "custom_components.eedomus.entity.DEVICE_MAPPINGS", custom_mappings
    ):
        result = map_device_to_ha_entity(device_data)
        assert result["ha_entity"] == "light"
        assert result["ha_subtype"] == "dimmer"


def test_map_device_usage_id_mapping():
    """Vérifie la priorité 3 : mapping standard basé sur usage_id."""
    device_data = {"periph_id": "10", "name": "Thermostat Salon", "usage_id": "11"}
    custom_mappings = {
        "usage_id_mappings": {
            "11": {"ha_entity": "climate", "ha_subtype": "thermostat"}
        }
    }

    with patch.dict(
        "custom_components.eedomus.entity.DEVICE_MAPPINGS", custom_mappings
    ):
        result = map_device_to_ha_entity(device_data)
        assert result["ha_entity"] == "climate"
        assert result["ha_subtype"] == "thermostat"


def test_map_device_usage_id_subtype_mapping():
    """Vérifie le subtype_mapping dynamique selon les attributs du périphérique."""
    device_data = {
        "periph_id": "11",
        "name": "Variateur",
        "usage_id": "23",
        "value_type": "float",
    }
    custom_mappings = {
        "usage_id_mappings": {
            "23": {
                "ha_entity": "switch",
                "ha_subtype": "on_off",
                "subtype_mapping": [
                    {
                        "conditions": {"value_type": "float"},
                        "ha_entity": "light",
                        "ha_subtype": "dimmer",
                    }
                ],
                "default": {"ha_entity": "switch", "ha_subtype": "standard"},
            }
        }
    }

    with patch.dict(
        "custom_components.eedomus.entity.DEVICE_MAPPINGS", custom_mappings
    ):
        result = map_device_to_ha_entity(device_data)
        assert result["ha_entity"] == "light"
        assert result["ha_subtype"] == "dimmer"


def test_map_device_name_pattern_matching():
    """Vérifie la priorité 4 : détection par motifs de nom (regex)."""
    device_data = {"periph_id": "20", "name": "Lampe du salon", "usage_id": "99999"}
    custom_patterns = [
        {"pattern": r"(?i)\blampe\b", "ha_entity": "light", "ha_subtype": "binary"}
    ]
    custom_mappings = {
        "usage_id_mappings": {},
        "name_patterns": custom_patterns,
    }

    with patch.dict(
        "custom_components.eedomus.entity.DEVICE_MAPPINGS", custom_mappings, clear=True
    ):
        with patch("custom_components.eedomus.entity.NAME_PATTERNS", custom_patterns):
            result = map_device_to_ha_entity(device_data)
            assert result["ha_entity"] == "light"
            assert result["ha_subtype"] == "binary"


def test_map_device_fallback_default():
    """Vérifie la priorité 5 : fallback par défaut quand aucune règle ne correspond."""
    device_data = {"periph_id": "30", "name": "Inconnu", "usage_id": "888"}

    with patch.dict(
        "custom_components.eedomus.entity.DEVICE_MAPPINGS", {}, clear=True
    ):
        result = map_device_to_ha_entity(device_data, default_ha_entity="sensor")
        assert result["ha_entity"] == "sensor"
        assert result["ha_subtype"] == "unknown"


# --- 4. Tests de la fonction helper _create_mapping ---


def test_create_mapping_registration():
    """Vérifie la génération standardisée d'un mapping et son enregistrement."""
    raw_config = {
        "mapping": {"ha_entity": "switch", "ha_subtype": "outlet"},
        "justification": "Règle test",
    }

    with patch(
        "custom_components.eedomus.entity.register_device_mapping"
    ) as mock_register:
        res = _create_mapping(raw_config, "Prise Cuisine", "50", "Test Context")

        assert res["ha_entity"] == "switch"
        assert res["ha_subtype"] == "outlet"
        assert res["justification"] == "Règle test"
        mock_register.assert_called_once_with(res, "Prise Cuisine", "50", None)
