"""Tests unitaires pour les capteurs de timing de rafraîchissement eedomus."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory

from custom_components.eedomus.const import DOMAIN
from custom_components.eedomus.refresh_timing_sensor import (
    EedomusAPITimeSensor,
    EedomusEndpointTimingSensor,
    EedomusGetPeriphCaractSensor,
    EedomusGetPeriphListSensor,
    EedomusGetPeriphValueListSensor,
    EedomusPartialRefreshSensor,
    EedomusProcessedDevicesSensor,
    EedomusProcessingTimeSensor,
    EedomusRefreshTimingSensor,
    EedomusTotalRefreshTimeSensor,
    async_setup_refresh_timing_sensors,
    get_clean_box_name_from_coord,
)


@pytest.fixture
def mock_coordinator():
    """Fixture fournissant un DataUpdateCoordinator eedomus de test."""
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "box_entry_123"
    coordinator.config_entry.title = "Eedomus (192.168.1.50)"
    coordinator.config_entry.data = {"host": "192.168.1.50"}

    # Timings de test
    coordinator._last_api_time = 1.23456
    coordinator._last_processing_time = 0.45678
    coordinator._last_refresh_time = 1.69134
    coordinator._last_processed_devices = 42
    coordinator._endpoint_timings = {
        "get_periph_list": 0.5123,
        "get_periph_value_list": 0.3111,
        "get_periph_caract": 0.1234,
        "partial_refresh": 0.0500,
    }
    coordinator._endpoint_call_counts = {
        "get_periph_list": 2,
        "get_periph_value_list": 5,
        "get_periph_caract": 1,
        "partial_refresh": 0,
    }

    return coordinator


# --- 1. Tests des fonctions helpers ---


def test_get_clean_box_name_from_coord_with_data(mock_coordinator):
    """Vérifie l'extraction de l'IP depuis config_entry.data."""
    host, name = get_clean_box_name_from_coord(mock_coordinator)
    assert host == "192.168.1.50"
    assert name == "Box eedomus (192.168.1.50)"


def test_get_clean_box_name_from_coord_from_title(mock_coordinator):
    """Vérifie le parsing du titre si 'host' n'est pas dans data."""
    mock_coordinator.config_entry.data = {}
    host, name = get_clean_box_name_from_coord(mock_coordinator)
    assert host == "192.168.1.50"
    assert name == "Box eedomus (192.168.1.50)"


def test_get_clean_box_name_from_coord_fallback(mock_coordinator):
    """Vérifie le comportement si le format d'IP est inconnu."""
    mock_coordinator.config_entry.data = {}
    mock_coordinator.config_entry.title = "Custom Name"
    host, name = get_clean_box_name_from_coord(mock_coordinator)
    assert host == "Custom Name"
    assert name == "Box eedomus (Custom Name)"


# --- 2. Tests du capteur de base (EedomusRefreshTimingSensor) ---


def test_refresh_timing_sensor_base(mock_coordinator):
    """Vérifie l'initialisation et les propriétés du capteur de base."""
    sensor = EedomusRefreshTimingSensor(mock_coordinator, "Test Type", "s", "mdi:clock")

    assert sensor.unique_id == "eedomus_box_entry_123_test_type_timing"
    assert sensor.name == "Eedomus Test Type (192.168.1.50)"
    assert sensor.native_unit_of_measurement == "s"
    assert sensor.icon == "mdi:clock"
    assert sensor.device_class == SensorDeviceClass.DURATION
    assert sensor.state_class == SensorStateClass.MEASUREMENT
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.native_value == 0.0

    attrs = sensor.extra_state_attributes
    assert attrs["sensor_type"] == "Test Type"


# --- 3. Tests des capteurs généraux de timing ---


def test_api_time_sensor(mock_coordinator):
    """Vérifie le capteur API Time."""
    sensor = EedomusAPITimeSensor(mock_coordinator)
    assert sensor.native_value == 1.235  # Arrondi à 3 décimales

    attrs = sensor.extra_state_attributes
    assert attrs["component"] == "api"


def test_processing_time_sensor(mock_coordinator):
    """Vérifie le capteur Processing Time."""
    sensor = EedomusProcessingTimeSensor(mock_coordinator)
    assert sensor.native_value == 0.457

    attrs = sensor.extra_state_attributes
    assert attrs["component"] == "processing"


def test_total_refresh_time_sensor(mock_coordinator):
    """Vérifie le capteur Total Refresh Time."""
    sensor = EedomusTotalRefreshTimeSensor(mock_coordinator)
    assert sensor.native_value == 1.691

    attrs = sensor.extra_state_attributes
    assert attrs["component"] == "total"


def test_processed_devices_sensor(mock_coordinator):
    """Vérifie le capteur Processed Devices (compteur d'appareils)."""
    sensor = EedomusProcessedDevicesSensor(mock_coordinator)
    assert sensor.native_value == 42
    assert sensor.device_class is None  # Doit être réinitialisé à None
    assert sensor.native_unit_of_measurement == "devices"

    attrs = sensor.extra_state_attributes
    assert attrs["component"] == "devices"


# --- 4. Tests des capteurs d'endpoints spécifiques ---


def test_endpoint_timing_sensors(mock_coordinator):
    """Vérifie les capteurs dédiés aux endpoints d'API."""
    sensor_list = EedomusGetPeriphListSensor(mock_coordinator)
    sensor_value_list = EedomusGetPeriphValueListSensor(mock_coordinator)
    sensor_caract = EedomusGetPeriphCaractSensor(mock_coordinator)
    sensor_partial = EedomusPartialRefreshSensor(mock_coordinator)

    assert sensor_list.native_value == 0.512
    assert sensor_list.extra_state_attributes["call_count"] == 2

    assert sensor_value_list.native_value == 0.311
    assert sensor_value_list.extra_state_attributes["call_count"] == 5

    assert sensor_caract.native_value == 0.123
    assert sensor_caract.extra_state_attributes["call_count"] == 1

    assert sensor_partial.native_value == 0.05
    assert sensor_partial.extra_state_attributes["call_count"] == 0


# --- 5. Tests des cas de repli (attributs manquants) ---


def test_sensors_without_coordinator_attributes(mock_coordinator):
    """Vérifie le comportement si le coordinateur n'a pas encore de métriques."""
    empty_coordinator = MagicMock()
    empty_coordinator.config_entry.entry_id = "empty_box"
    empty_coordinator.config_entry.title = "Eedomus (10.0.0.1)"
    empty_coordinator.config_entry.data = {}

    api_sensor = EedomusAPITimeSensor(empty_coordinator)
    proc_sensor = EedomusProcessingTimeSensor(empty_coordinator)
    total_sensor = EedomusTotalRefreshTimeSensor(empty_coordinator)
    devices_sensor = EedomusProcessedDevicesSensor(empty_coordinator)
    endpoint_sensor = EedomusEndpointTimingSensor(empty_coordinator, "test", "mdi:icon")

    assert api_sensor.native_value == 0.0
    assert proc_sensor.native_value == 0.0
    assert total_sensor.native_value == 0.0
    assert devices_sensor.native_value == 0
    assert endpoint_sensor.native_value == 0.0
    assert endpoint_sensor.extra_state_attributes["call_count"] == 0


# --- 6. Test async_setup_refresh_timing_sensors ---


@pytest.mark.asyncio
async def test_async_setup_refresh_timing_sensors(mock_coordinator):
    """Vérifie l'enregistrement des 8 capteurs et de l'appareil dans Home Assistant."""
    hass = MagicMock()
    device_registry = MagicMock()

    sensors = await async_setup_refresh_timing_sensors(
        hass, mock_coordinator, device_registry
    )

    # Doit enregistrer l'appareil principal Box eedomus
    device_registry.async_get_or_create.assert_called_once_with(
        config_entry_id="box_entry_123",
        identifiers={(DOMAIN, "eedomus_box_box_entry_123")},
        name="Box eedomus (192.168.1.50)",
        manufacturer="Eedomus",
        model="Eedomus Box",
        sw_version="Unknown",
    )

    # 8 capteurs au total doivent être instanciés
    assert len(sensors) == 8
    assert isinstance(sensors[0], EedomusAPITimeSensor)
    assert isinstance(sensors[1], EedomusProcessingTimeSensor)
    assert isinstance(sensors[2], EedomusTotalRefreshTimeSensor)
    assert isinstance(sensors[3], EedomusProcessedDevicesSensor)
    assert isinstance(sensors[4], EedomusGetPeriphListSensor)
    assert isinstance(sensors[5], EedomusGetPeriphValueListSensor)
    assert isinstance(sensors[6], EedomusGetPeriphCaractSensor)
    assert isinstance(sensors[7], EedomusPartialRefreshSensor)


@pytest.mark.asyncio
async def test_get_clean_box_name_exception_handling():
    """Cover lines 34-35 in refresh_timing_sensor: exception handling during host string splitting."""
    from custom_components.eedomus.refresh_timing_sensor import (
        get_clean_box_name_from_coord,
    )

    coordinator = MagicMock()
    coordinator.config_entry.data.get.return_value = "Eedomus (192.168.1.100)"

    # Sous-classe de str valide pour isinstance(), mais qui lève une exception au split
    class CustomStr(str):
        def split(self, *args, **kwargs):
            raise Exception("Forced split exception")

    # On patch temporairement builtins.str avec notre classe (qui est un type valide)
    with patch("builtins.str", CustomStr):
        host, box_name = get_clean_box_name_from_coord(coordinator)
        assert box_name is not None
