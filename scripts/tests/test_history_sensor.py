"""Tests unitaires pour les capteurs d'historique eedomus."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.helpers.entity import DeviceInfo

from custom_components.eedomus.const import DOMAIN
from custom_components.eedomus.history_sensor import (
    EedomusGlobalHistoryProgressSensor,
    EedomusHistoryProgressSensor,
    EedomusHistorySensor,
    EedomusHistoryStatsSensor,
    async_setup_history_sensors,
)


@pytest.fixture
def mock_device_info():
    """Fixture fournissant un DeviceInfo de test."""
    return DeviceInfo(
        identifiers={(DOMAIN, "eedomus_box_12345")},
        name="Box eedomus",
    )


@pytest.fixture
def mock_coordinator():
    """Fixture simulant un DataUpdateCoordinator eedomus complet."""
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "12345"
    coordinator.data = {
        "1001": {
            "name": "Capteur Température",
            "last_value": "21.5",
            "last_changed": "2026-03-30 10:00:00",
        },
        "1002": {
            "name": "Prise Salon",
            "last_value": "1",
            "last_changed": "2026-03-30 11:00:00",
        },
    }
    coordinator._history_progress = {
        "1001": {
            "completed": True,
            "last_timestamp": 1700000000,
            "retrieved_points": 500,
            "total_points": 500,
        },
        "1002": {
            "completed": False,
            "last_timestamp": 1700000500,
            "retrieved_points": 250,
            "total_points": 1000,
        },
    }
    coordinator.async_add_listener = MagicMock()
    return coordinator


# --- 1. Tests EedomusHistorySensor ---


def test_history_sensor_init_and_properties(mock_coordinator, mock_device_info):
    """Vérifie l'initialisation et les valeurs du capteur d'historique individuel."""
    sensor = EedomusHistorySensor(
        mock_coordinator, "1001", "Capteur Température", mock_device_info
    )

    assert sensor.unique_id == "eedomus_12345_1001_history"
    assert sensor.name == "Capteur Température (History)"
    assert sensor.native_value == "21.5"

    attrs = sensor.extra_state_attributes
    assert attrs["device_id"] == "1001"
    assert attrs["last_updated"] == "2026-03-30 10:00:00"
    assert attrs["history_completed"] is True
    assert attrs["data_points_retrieved"] == 500


def test_history_sensor_fallback_when_data_missing(mock_coordinator, mock_device_info):
    """Vérifie le comportement si les données du périphérique sont introuvables."""
    mock_coordinator.data = {}
    mock_coordinator._history_progress = {}

    sensor = EedomusHistorySensor(mock_coordinator, "9999", "Inconnu", mock_device_info)

    assert sensor.native_value == "unknown"
    attrs = sensor.extra_state_attributes
    assert attrs["history_completed"] is False
    assert attrs["data_points_retrieved"] == 0


# --- 2. Tests EedomusHistoryProgressSensor ---


def test_history_progress_sensor_calculation(mock_coordinator, mock_device_info):
    """Vérifie le calcul de pourcentage de la progression par appareil."""
    sensor = EedomusHistoryProgressSensor(
        mock_coordinator, "1002", "Prise Salon", mock_device_info
    )

    # 250 / 1000 = 25%
    assert sensor.native_value == 25.0

    attrs = sensor.extra_state_attributes
    assert attrs["periph_id"] == "1002"
    assert attrs["completed"] is False


def test_history_progress_sensor_edge_cases(mock_coordinator, mock_device_info):
    """Vérifie le plafonnement à 100% et la gestion des données vides."""
    # Test plafonnement à 100%
    mock_coordinator._history_progress["1002"]["retrieved_points"] = 1500
    sensor = EedomusHistoryProgressSensor(
        mock_coordinator, "1002", "Prise Salon", mock_device_info
    )
    assert sensor.native_value == 100

    # Test total_points == 0
    mock_coordinator._history_progress["1002"]["total_points"] = 0
    assert sensor.native_value == 0


@pytest.mark.asyncio
async def test_history_progress_sensor_async_added_to_hass(
    mock_coordinator, mock_device_info
):
    """Vérifie l'enregistrement de l'écouteur d'événements lors de l'ajout à HA."""
    sensor = EedomusHistoryProgressSensor(
        mock_coordinator, "1001", "Capteur Température", mock_device_info
    )
    sensor.async_on_remove = MagicMock()

    with patch(
        "homeassistant.helpers.update_coordinator.CoordinatorEntity.async_added_to_hass",
        AsyncMock(),
    ):
        await sensor.async_added_to_hass()
        mock_coordinator.async_add_listener.assert_called_once()
        sensor.async_on_remove.assert_called_once()


# --- 3. Tests EedomusGlobalHistoryProgressSensor ---


def test_global_history_progress_sensor(mock_coordinator, mock_device_info):
    """Vérifie le pourcentage de progression globale (1 terminé sur 2 = 50%)."""
    sensor = EedomusGlobalHistoryProgressSensor(mock_coordinator, mock_device_info)

    assert sensor.unique_id == "eedomus_12345_history_progress_global"
    assert sensor.native_value == 50.0

    attrs = sensor.extra_state_attributes
    assert attrs["devices_total"] == 2
    assert attrs["devices_completed"] == 1
    assert attrs["devices_remaining"] == 1


def test_global_history_progress_sensor_empty(mock_coordinator, mock_device_info):
    """Vérifie le comportement si la structure de progression est absente ou vide."""
    delattr(mock_coordinator, "_history_progress")
    sensor = EedomusGlobalHistoryProgressSensor(mock_coordinator, mock_device_info)

    assert sensor.native_value == 0
    assert sensor.extra_state_attributes == {}


# --- 4. Tests EedomusHistoryStatsSensor ---


def test_history_stats_sensor_download_size(mock_coordinator, mock_device_info):
    """Vérifie l'estimation de la taille téléchargée en Mo."""
    sensor = EedomusHistoryStatsSensor(mock_coordinator, mock_device_info)

    # Points totaux récupérés = 500 + 250 = 750 points
    # 750 * 100 / (1024 * 1024) = 0.0715 Mo -> 0.07 Mo
    assert sensor.native_value == 0.07

    attrs = sensor.extra_state_attributes
    assert attrs["downloaded_size"] == "0.07"
    assert attrs["devices_with_history"] == 1
    assert attrs["devices_without_history"] == 1


def test_history_stats_sensor_no_progress(mock_coordinator, mock_device_info):
    """Vérifie le retour du capteur de stats quand aucune progression n'est présente."""
    mock_coordinator._history_progress = {}
    sensor = EedomusHistoryStatsSensor(mock_coordinator, mock_device_info)

    assert sensor.native_value == 0
    assert sensor.extra_state_attributes == {}


# --- 5. Tests async_setup_history_sensors ---


@pytest.mark.asyncio
async def test_async_setup_history_sensors(mock_coordinator):
    """Vérifie l'initialisation complète et l'enregistrement dans le Device Registry."""
    hass = MagicMock()
    device_registry = MagicMock()

    sensors = await async_setup_history_sensors(hass, mock_coordinator, device_registry)

    # Déclaration du device principal eedomus box
    device_registry.async_get_or_create.assert_called_once_with(
        config_entry_id="12345",
        identifiers={(DOMAIN, "eedomus_box_12345")},
        name="Box eedomus",
        manufacturer="Eedomus",
        model="Eedomus Box",
        sw_version="Unknown",
    )

    # 2 globaux + (2 spécifiques * 2 appareils) = 6 capteurs
    assert len(sensors) == 6
    assert isinstance(sensors[0], EedomusGlobalHistoryProgressSensor)
    assert isinstance(sensors[1], EedomusHistoryStatsSensor)
    assert isinstance(sensors[2], EedomusHistorySensor)
    assert isinstance(sensors[3], EedomusHistoryProgressSensor)


@pytest.mark.asyncio
async def test_async_setup_history_sensors_no_history(mock_coordinator):
    """Vérifie la création uniquement des capteurs globaux si l'historique est vide."""
    mock_coordinator._history_progress = {}
    hass = MagicMock()
    device_registry = MagicMock()

    sensors = await async_setup_history_sensors(hass, mock_coordinator, device_registry)

    # Seuls les 2 capteurs globaux doivent être créés
    assert len(sensors) == 2


@pytest.mark.asyncio
async def test_history_sensor_missing_lines_168_and_229():
    """Target history_sensor.py missing lines 168 and 229."""
    from custom_components.eedomus.history_sensor import (
        EedomusGlobalHistoryProgressSensor,
        EedomusHistoryStatsSensor,
    )

    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "box_history_edge"
    device_info = MagicMock()

    # 1. Cible la ligne 168 : dictionnaire truthy mais de longueur 0
    class EmptyButTruthyDict(dict):
        def __bool__(self):
            return True

    coordinator._history_progress = EmptyButTruthyDict()
    global_sensor = EedomusGlobalHistoryProgressSensor(coordinator, device_info)
    val_global = global_sensor.native_value
    assert val_global == 0.0

    # 2. Cible la ligne 229 : total_points <= 0 (évite le if et retourne 0.0)
    coordinator._history_progress = {"p1": {"total_points": 0, "retrieved_points": 0}}
    stats_sensor = EedomusHistoryStatsSensor(coordinator, device_info)
    val_stats = stats_sensor.native_value
    assert val_stats == 0.0
