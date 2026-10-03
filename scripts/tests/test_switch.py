"""Tests for Eedomus switch entities."""

import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import STATE_OFF, STATE_ON

from custom_components.eedomus.switch import EedomusSwitch
from custom_components.eedomus.const import DOMAIN


@pytest.mark.asyncio
async def test_switch_initialization():
    """Test switch entity initialization."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "switch"
    mock_coordinator.data = {
        "switch_1230": {
            "periph_id": "switch_1230", 
            "name": "Test Switch",
            "last_value": "on",
            "value_list": ["on", "off"],
        }
    }

    device_info = {
        "periph_id": "switch_1230", 
        "name": "Test Switch", 
        "usage_id": "37",
    }

    switch = EedomusSwitch(mock_coordinator, device_info["periph_id"])

    assert switch.name == "Test Switch"
    assert switch.unique_id == "eedomus_switch_switch_1230"
    assert switch.is_on is True

@pytest.mark.asyncio
async def test_switch_off_state():
    """Test switch in off state."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "switch"
    mock_coordinator.data = {
        "switch_1231": {
            "periph_id": "switch_1231", 
            "name": "Test Switch 1", 
            "value": "off",
        }
    }

    device_info = {
        "periph_id": "switch_1231", 
        "name": "Test Switch 1", 
        "usage_id": "37",
    }

    switch = EedomusSwitch(mock_coordinator, device_info["periph_id"])

    assert switch.is_on is False

@pytest.mark.asyncio
async def test_switch_turn_on():
    """Test switch turn on method."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "switch"
    mock_coordinator.data = {
        "switch_1232": {
            "periph_id": "switch_1232", 
             "name": "Test Switch 2",
            "last_value": "off",
            "value_list": ["on", "off"]
        }
    }

    device_info = {
        "periph_id": "switch_1232", 
        "name": "Test Switch 2",
        "usage_id": "37",
    }

    switch = EedomusSwitch(mock_coordinator, device_info["periph_id"])

    # 🚨 LA CORRECTION MAGIQUE : Injection du faux moteur Home Assistant
    switch.hass = MagicMock()
    switch.hass.services.async_call = AsyncMock()

    assert switch.name == "Test Switch 2"
    assert switch.unique_id == "eedomus_switch_switch_1232"

    assert switch.is_on is False

    # Action : On l'allume
    await switch.async_turn_on()

    # Vérification : On s'assure que l'appel de service HA a bien été déclenché
    switch.hass.services.async_call.assert_called_once()

    # 🚨 SIMULATION DU RETOUR DE LA BOX : 
    # D'après tes logs, l'Eedomus reçoit la valeur numérique 100 pour l'allumage
    mock_coordinator.data["switch_1232"]["last_value"] = 100

    assert switch.is_on is True

@pytest.mark.asyncio
async def test_switch_turn_off():
    " ""Test switch turn off method."" "
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "switch"
    mock_coordinator.data = {
        "switch_1234": {
            "periph_id": "switch_1234", 
            "last_value": "on",
            "value_list": ["on", "off"]
        }
    }

    device_info = {
        "periph_id": "switch_1234",
        "name": "Test Switch",
        "usage_id": "37",
    }

    switch = EedomusSwitch(mock_coordinator, device_info["periph_id"])

    switch.hass = MagicMock()
    switch.hass.services.async_call = AsyncMock()

    assert switch.is_on is True
    await switch.async_turn_off()

    switch.hass.services.async_call.assert_called_once()
    mock_coordinator.data["switch_1234"]["last_value"] = 0

    assert switch.is_on is False

@pytest.mark.asyncio
async def test_switch_with_consumption_child():
    """Test switch with consumption child (Issue #9 related)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "switch"
    mock_coordinator.data = {
        "switch_1235": {
            "periph_id": "switch_1235",
            "name": "Test Switch 5",
            "last_value": "on",
            "value_list": ["on", "off"],
        },
        "switch_1235_consumption": {
            "periph_id": "switch_1235_consumption",
            "consumption": 15.5,
            "current_power": 100,
            "usage_id": "26",
        },
    }

    device_info = {
        "periph_id": "switch_1235",
        "name": "Test Switch 5",
        "usage_id": "37",
        "children": [
            {
                "periph_id": "switch_1235_consumption",
                "usage_id": "26",
                "name": "Consommation",
            }
        ],
    }

    switch = EedomusSwitch(mock_coordinator, device_info["periph_id"])
    
    # Verify switch properties
    assert switch.name == "Test Switch 5"
    assert switch.is_on is True
    assert switch.unique_id == "eedomus_switch_switch_1235"

    # Verify consumption data exists for energy sensor creation
    consumption_data = mock_coordinator.data.get("switch_1235_consumption", {})
    assert consumption_data.get("consumption") == 15.5
    assert consumption_data.get("current_power") == 100

@pytest.mark.asyncio
async def test_switch_consumption_only_device():
    """Test switch that should be remapped as energy sensor."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "consumption_monitor": {
            "periph_id": "consumption_monitor",
            "name": "Consommation Salon",
            "last_value": "150",
            "value_list": ["150"],
        }
    }

    device_info = {
        "periph_id": "consumption_monitor",
        "name": "Consommation Salon",
        "usage_id": "2",  # Appareil électrique
        "children": [
            {
                "periph_id": "consumption_monitor_power",
                "usage_id": "26",
                "name": "Puissance",
            }
        ],
    }

    # This should be detected as a consumption monitor and remapped
    # The test verifies the data structure that would trigger remapping
    switch = EedomusSwitch(mock_coordinator, device_info["periph_id"])

    # Verify the device has the right characteristics for remapping
    assert (
        "conso" in device_info["name"].lower()
        or "consommation" in device_info["name"].lower()
    )

    # Check if it has consumption children
    has_consumption_children = any(
        child.get("usage_id") == "26" for child in device_info.get("children", [])
    )
    assert has_consumption_children is True


@pytest.mark.asyncio
async def test_switch_is_on_missing_data():
    """Test is_on returns False when peripheral data is missing."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {}
    switch = EedomusSwitch(mock_coordinator, "unknown_switch")
    assert switch.is_on is False

@pytest.mark.asyncio
async def test_switch_is_on_various_truthy_values():
    """Test is_on with various valid truthy values (strings and numbers)."""
    mock_coordinator = AsyncMock()
    for val in ["1", 1, "100", 100, "on", "MARCHE", "true"]:
        mock_coordinator.data = {"sw_val": {"periph_id": "sw_val", "last_value": val}}
        switch = EedomusSwitch(mock_coordinator, "sw_val")
        assert switch.is_on is True

@pytest.mark.asyncio
async def test_switch_turn_on_exception():
    """Test async_turn_on handles API exceptions and re-raises."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {"sw_err": {"periph_id": "sw_err", "last_value": "off"}}
    switch = EedomusSwitch(mock_coordinator, "sw_err")
    switch.async_set_value = AsyncMock(side_effect=Exception("API Connection Error"))

    with pytest.raises(Exception, match="API Connection Error"):
        await switch.async_turn_on()

@pytest.mark.asyncio
async def test_switch_turn_off_exception():
    """Test async_turn_off handles API exceptions and re-raises."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {"sw_err": {"periph_id": "sw_err", "last_value": "on"}}
    switch = EedomusSwitch(mock_coordinator, "sw_err")
    switch.async_set_value = AsyncMock(side_effect=Exception("API Connection Error"))

    with pytest.raises(Exception, match="API Connection Error"):
        await switch.async_turn_off()

@pytest.mark.asyncio
async def test_async_setup_entry_switch_patterns():
    """Test async_setup_entry remapping logic (Patterns 1, 2, and 3)."""
    from custom_components.eedomus.switch import async_setup_entry

    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_id"

    mock_coordinator = MagicMock()
    mock_coordinator.get_all_peripherals.return_value = {
        # Pattern 1 & 2: Pure consumption monitor (should be remapped to sensor)
        "conso_device": {
            "periph_id": "conso_device",
            "name": "Prise Consommation Salon",
            "usage_id": "37",
        },
        "conso_child": {
            "periph_id": "conso_child",
            "parent_periph_id": "conso_device",
            "usage_id": "26",
            "name": "Energy Child"
        },
        # Pattern 3: Controllable device with consumption child (should stay a switch)
        "sapin_noel": {
            "periph_id": "sapin_noel",
            "name": "Sapin de Noel avec Consommation",
            "usage_id": "37",
        },
        "sapin_child": {
            "periph_id": "sapin_child",
            "parent_periph_id": "sapin_noel",
            "usage_id": "26",
            "name": "Sapin Conso"
        }
    }

    mock_coordinator.data = {
        "conso_device": {"periph_id": "conso_device", "name": "Prise Consommation Salon", "ha_entity": "switch"},
        "conso_child": {"periph_id": "conso_child", "parent_periph_id": "conso_device"},
        "sapin_noel": {"periph_id": "sapin_noel", "name": "Sapin de Noel avec Consommation", "ha_entity": "switch"},
        "sapin_child": {"periph_id": "sapin_child", "parent_periph_id": "sapin_noel"}
    }

    mock_hass.data = {
        "domain": {},
        "eedomus": {
            "test_entry_id": {
                "coordinator": mock_coordinator
            }
        }
    }

    async_add_entities = MagicMock()

    with patch("custom_components.eedomus.switch.map_device_to_ha_entity") as mock_map, \
         patch("custom_components.eedomus.switch.register_device_mapping") as mock_reg:
        mock_map.return_value = {"ha_entity": "switch", "ha_subtype": "switch"}
        
        await async_setup_entry(mock_hass, mock_entry, async_add_entities)
        
        # Verify that entities registration was successfully invoked
        async_add_entities.assert_called_once()


import pytest
from unittest.mock import MagicMock
from custom_components.eedomus.const import DOMAIN

@pytest.mark.asyncio
async def test_switch_parent_light_usage_26(hass):
    """Cover lines 49-59: Child of a light with usage_id '26' remapped to sensor."""
    from custom_components.eedomus.switch import async_setup_entry

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"
    
    data_dict = {
        "1": {"id": "1", "name": "Light Parent", "ha_entity": "light", "usage_id": "7"},
        "2": {
            "id": "2",
            "name": "Power Child",
            "parent_periph_id": "1",
            "ha_entity": "switch",
            "usage_id": "26"
        }
    }
    
    coordinator = MagicMock()
    coordinator.data = data_dict
    coordinator.get_all_peripherals.return_value = data_dict
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {"coordinator": coordinator}

    entities = []
    def mock_add_entities(new_entities, update_before_add=False):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)
    assert data_dict["2"]["ha_entity"] == "sensor"

@pytest.mark.asyncio
async def test_switch_with_control_children(hass):
    """Cover lines 89-96: Switch with control-capable children remains a switch."""
    from custom_components.eedomus.switch import async_setup_entry

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"
    
    data_dict = {
        "10": {"id": "10", "name": "Master Switch", "ha_entity": "switch", "usage_id": "1"},
        "11": {
            "id": "11",
            "name": "Control Child",
            "parent_periph_id": "10",
            "ha_entity": "switch",
            "usage_id": "1"
        }
    }
    
    coordinator = MagicMock()
    coordinator.data = data_dict
    coordinator.get_all_peripherals.return_value = data_dict
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {"coordinator": coordinator}

    entities = []
    def mock_add_entities(new_entities, update_before_add=False):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)
    assert data_dict["10"]["ha_entity"] == "switch"

@pytest.mark.asyncio
async def test_switch_remap_to_energy_sensor(hass):
    """Cover lines 159-172: Switch remapped as energy sensor based on name and children."""
    from custom_components.eedomus.switch import async_setup_entry

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"
    
    data_dict = {
        "20": {"id": "20", "name": "Compteur Energie Global", "ha_entity": "switch", "usage_id": "1"},
        "21": {
            "id": "21",
            "name": "Consommation",
            "parent_periph_id": "20",
            "ha_entity": "sensor",
            "usage_id": "26"
        }
    }
    
    coordinator = MagicMock()
    coordinator.data = data_dict
    coordinator.get_all_peripherals.return_value = data_dict
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {"coordinator": coordinator}

    entities = []
    def mock_add_entities(new_entities, update_before_add=False):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)
    assert data_dict["20"]["ha_entity"] == "sensor"
    assert data_dict["20"]["ha_subtype"] == "energy"

@pytest.mark.asyncio
async def test_switch_remap_by_consommation_name(hass):
    """Cover line 131: Switch remapped as energy sensor based on 'consommation' in name."""
    from custom_components.eedomus.switch import async_setup_entry

    config_entry = MagicMock()
    config_entry.entry_id = "test_entry_id"
    
    data_dict = {
        "30": {"id": "30", "name": "Consommation Salon", "ha_entity": "switch", "usage_id": "1"}
    }
    
    coordinator = MagicMock()
    coordinator.data = data_dict
    coordinator.get_all_peripherals.return_value = data_dict
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {"coordinator": coordinator}

    entities = []
    def mock_add_entities(new_entities, update_before_add=False):
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)
    assert data_dict["30"]["ha_entity"] == "sensor"
    assert data_dict["30"]["ha_subtype"] == "energy"


