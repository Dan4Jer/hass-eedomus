"""Tests for Eedomus binary sensor entities."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from custom_components.eedomus.binary_sensor import (
    EedomusBinarySensor,
    async_setup_entry,
)
from custom_components.eedomus.const import COORDINATOR, DOMAIN


@pytest.mark.asyncio
async def test_binary_sensor_is_on_numeric():
    """Test is_on evaluation with numeric values ('100', 1, '0', None)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.get_yaml_config_sync = MagicMock(return_value={})
    mock_coordinator.data = {
        "sensor_on_100": {
            "periph_id": "sensor_on_100",
            "name": "Motion Sensor",
            "last_value": "100",
        },
        "sensor_on_1": {
            "periph_id": "sensor_on_1",
            "name": "Door Sensor",
            "last_value": 1,
        },
        "sensor_off_0": {
            "periph_id": "sensor_off_0",
            "name": "Window Sensor",
            "last_value": "0",
        },
        "sensor_none": {
            "periph_id": "sensor_none",
            "name": "Unknown Sensor",
            "last_value": None,
        },
    }

    sensor_on_100 = EedomusBinarySensor(mock_coordinator, "sensor_on_100")
    sensor_on_1 = EedomusBinarySensor(mock_coordinator, "sensor_on_1")
    sensor_off_0 = EedomusBinarySensor(mock_coordinator, "sensor_off_0")
    sensor_none = EedomusBinarySensor(mock_coordinator, "sensor_none")

    assert sensor_on_100.is_on is True
    assert sensor_on_1.is_on is True
    assert sensor_off_0.is_on is False
    assert sensor_none.is_on is None


@pytest.mark.asyncio
async def test_binary_sensor_is_on_string():
    """Test is_on evaluation with text values ('open', 'ouvert', 'marche', etc.)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.get_yaml_config_sync = MagicMock(return_value={})
    mock_coordinator.data = {
        "sensor_open": {
            "periph_id": "sensor_open",
            "name": "Porte",
            "last_value": "ouvert",
        },
        "sensor_marche": {
            "periph_id": "sensor_marche",
            "name": "Interrupteur",
            "last_value": "marche",
        },
        "sensor_closed": {
            "periph_id": "sensor_closed",
            "name": "Fenêtre",
            "last_value": "fermé",
        },
    }

    sensor_open = EedomusBinarySensor(mock_coordinator, "sensor_open")
    sensor_marche = EedomusBinarySensor(mock_coordinator, "sensor_marche")
    sensor_closed = EedomusBinarySensor(mock_coordinator, "sensor_closed")

    assert sensor_open.is_on is True
    assert sensor_marche.is_on is True
    assert sensor_closed.is_on is False


@pytest.mark.asyncio
async def test_binary_sensor_device_class_resolution():
    """Test device_class resolution priority (ha_subtype -> usage_name -> type)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.get_yaml_config_sync = MagicMock(return_value={})
    mock_coordinator.data = {
        "sensor_subtype": {
            "periph_id": "sensor_subtype",
            "name": "Sensor 1",
            "ha_subtype": "smoke",
        },
        "sensor_usage_door": {
            "periph_id": "sensor_usage_door",
            "name": "Sensor 2",
            "usage_name": "Capteur Porte Entrée",
        },
        "sensor_usage_motion": {
            "periph_id": "sensor_usage_motion",
            "name": "Sensor 3",
            "usage_name": "Détecteur de mouvement Salon",
        },
        "sensor_usage_water": {
            "periph_id": "sensor_usage_water",
            "name": "Sensor 4",
            "usage_name": "Détecteur inondation",
        },
        "sensor_type_fallback": {
            "periph_id": "sensor_type_fallback",
            "name": "Sensor 5",
            "type": "presence",
        },
    }

    s1 = EedomusBinarySensor(mock_coordinator, "sensor_subtype")
    s2 = EedomusBinarySensor(mock_coordinator, "sensor_usage_door")
    s3 = EedomusBinarySensor(mock_coordinator, "sensor_usage_motion")
    s4 = EedomusBinarySensor(mock_coordinator, "sensor_usage_water")
    s5 = EedomusBinarySensor(mock_coordinator, "sensor_type_fallback")

    assert s1.device_class == BinarySensorDeviceClass.SMOKE
    assert s2.device_class == BinarySensorDeviceClass.DOOR
    assert s3.device_class == BinarySensorDeviceClass.MOTION
    assert s4.device_class == BinarySensorDeviceClass.MOISTURE
    assert s5.device_class == BinarySensorDeviceClass.PRESENCE


@pytest.mark.asyncio
async def test_binary_sensor_extra_state_attributes():
    """Test extra_state_attributes for binary sensors."""
    mock_coordinator = AsyncMock()
    mock_coordinator.get_yaml_config_sync = MagicMock(return_value={})
    mock_coordinator.data = {
        "sensor_attrs": {
            "periph_id": "sensor_attrs",
            "name": "Sensor Attrs",
            "history": [{"val": "100", "date": "2026-01-01"}],
            "value_list": [{"value": "0", "description": "Fermé"}],
        }
    }

    sensor = EedomusBinarySensor(mock_coordinator, "sensor_attrs")
    attrs = sensor.extra_state_attributes

    assert "history" in attrs
    assert attrs["history"] == [{"val": "100", "date": "2026-01-01"}]
    assert "value_list" in attrs
    assert attrs["value_list"] == [{"value": "0", "description": "Fermé"}]


@pytest.mark.asyncio
async def test_async_setup_entry_binary_sensor():
    """Test setting up binary sensor entities from config entry."""
    mock_coordinator = AsyncMock()
    mock_coordinator.get_yaml_config_sync = MagicMock(return_value={})
    mock_coordinator.data = {
        "binary_1": {
            "periph_id": "binary_1",
            "name": "Binary 1",
            "ha_entity": "binary_sensor",
        },
        "sensor_1": {
            "periph_id": "sensor_1",
            "name": "Temperature Sensor",
            "ha_entity": "sensor",
        },
    }

    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"

    hass.data = {
        DOMAIN: {
            "test_entry": {
                COORDINATOR: mock_coordinator
            }
        }
    }

    async_add_entities = MagicMock()

    await async_setup_entry(hass, entry, async_add_entities)

    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], EedomusBinarySensor)
    assert entities[0]._periph_id == "binary_1"

@pytest.mark.asyncio
async def test_binary_sensor_missing_periph_data():
    """Cover lines 72-75 and 107: periph_data is None/missing."""
    from custom_components.eedomus.binary_sensor import EedomusBinarySensor

    coordinator = MagicMock()
    coordinator.data = {}  # Aucune donnée pour cet ID

    # Instanciation avec coordinator et periph_id uniquement
    sensor = EedomusBinarySensor(coordinator, "unknown_id")
    
    # Déclenche les lignes 72-75 (is_on / retour de None avec warning)
    assert sensor.is_on is None
    
    # Déclenche la ligne 107 (device_class avec periph_info vide)
    assert sensor.device_class is None


@pytest.mark.asyncio
async def test_binary_sensor_device_class_keywords():
    """Cover lines 120, 127, and 133: MOTION, SMOKE, and VIBRATION device classes."""
    from custom_components.eedomus.binary_sensor import EedomusBinarySensor
    from homeassistant.components.binary_sensor import BinarySensorDeviceClass

    coordinator = MagicMock()

    # 1. Test ligne 120 : Mouvement (MOTION)
    coordinator.data = {
        "p1": {"usage_name": "capteur mouvement", "last_value": "1"}
    }
    s1 = EedomusBinarySensor(coordinator, "p1")
    assert s1.device_class == BinarySensorDeviceClass.MOTION

    # 2. Test ligne 127 : Fumée
    coordinator.data = {
        "p2": {"usage_name": "détecteur fumée", "last_value": "0"}
    }
    s2 = EedomusBinarySensor(coordinator, "p2")
    assert s2.device_class == BinarySensorDeviceClass.SMOKE

    # 3. Test ligne 133 : Vibration
    coordinator.data = {
        "p3": {"usage_name": "capteur vibration", "last_value": "0"}
    }
    s3 = EedomusBinarySensor(coordinator, "p3")
    assert s3.device_class == BinarySensorDeviceClass.VIBRATION

@pytest.mark.asyncio
async def test_binary_sensor_presence_device_class():
    """Cover line 120: PRESENCE device class via 'presence' / 'présence' keyword."""
    from custom_components.eedomus.binary_sensor import EedomusBinarySensor
    from homeassistant.components.binary_sensor import BinarySensorDeviceClass

    coordinator = MagicMock()
    coordinator.data = {
        "p_presence": {"usage_name": "capteur présence", "last_value": "1"}
    }
    
    sensor = EedomusBinarySensor(coordinator, "p_presence")
    assert sensor.device_class == BinarySensorDeviceClass.PRESENCE

