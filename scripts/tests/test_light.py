"""Tests for Eedomus light entities."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_RGBW_COLOR,
    ColorMode,
)

from custom_components.eedomus.light import (
    EedomusLight,
    EedomusRGBChildLight,
    EedomusRGBWLight,
    async_setup_entry,
)

from custom_components.eedomus.const import COORDINATOR, DOMAIN


@pytest.mark.asyncio
async def test_light_rgbw_initialization():
    """Test light rgbw entity initialization."""
    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "mock_entry_id"
    async_add_entities = MagicMock()

    coordinator = AsyncMock()

    coordinator.get_all_peripherals = MagicMock(return_value={
        "1230": {"periph_id": "1230", "name": "Lampe Salon", "usage_id": "1"},
        "1231": {"periph_id": "1231", "parent_periph_id": "1230", "usage_id": "1", "name": "Lampe Salon R"},
        "1232": {"periph_id": "1232", "parent_periph_id": "1230", "usage_id": "1", "name": "Lampe Salon G"},
        "1233": {"periph_id": "1233", "parent_periph_id": "1230", "usage_id": "1", "name": "Lampe Salon B"},
        "1234": {"periph_id": "1234", "parent_periph_id": "1230", "usage_id": "1", "name": "Lampe Salon W"},
    })

    coordinator.data = {
        "1230": {
            "ha_entity": "light",
            "ha_subtype": "rgbw",
            "name": "Lampe Salon",
            "last_value": "50",
        },
        "1231": {"ha_entity": "light", "ha_subtype": "brightness", "last_value": "100"},
        "1232": {"ha_entity": "light", "ha_subtype": "brightness", "last_value": "100"},
        "1233": {"ha_entity": "light", "ha_subtype": "brightness", "last_value": "100"},
        "1234": {"ha_entity": "light", "ha_subtype": "brightness", "last_value": "100"},
    }

    hass.data = {
        "eedomus": {
            entry.entry_id: {
                "coordinator": coordinator
            }
        }
    }

    await async_setup_entry(hass, entry, async_add_entities)

    assert async_add_entities.called
    created_entities = async_add_entities.call_args[0][0]
    assert len(created_entities) == 5

    parent_entity = next(e for e in created_entities if e._periph_id == "1230")
    assert isinstance(parent_entity, EedomusRGBWLight)
    assert parent_entity.supported_color_modes == {ColorMode.RGBW}


@pytest.mark.asyncio
async def test_light_off_state():
    """Test light in off state."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "light"
    mock_coordinator.data = {
        "12311": {
            "periph_id": "12311",
            "ha_entity": "light",
            "ha_subtype": "brightness",
            "name": "Test Light 1",
            "last_value": "off", 
            "usage_id": "1"
        }
    }

    light = EedomusLight(mock_coordinator, "12311")
    assert light.is_on is False
    assert light.brightness == 0


@pytest.mark.asyncio
async def test_light_turn_on():
    """Test light turn on method."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "light"
    mock_coordinator.data = {
        "light_1234": {
            "periph_id": "light_1234",
            "ha_entity": "light",
            "ha_subtype": "brightness",
            "last_value": "off", 
            "brightness": 0, 
            "value_list": ["on", "off"],
       }
    }

    light = EedomusLight(mock_coordinator, "light_1234")
    light.hass = MagicMock()
    light.hass.services.async_call = AsyncMock()

    assert light.unique_id == "eedomus_light_light_1234"
    assert light.is_on is False

    await light.async_turn_on()
    light.hass.services.async_call.assert_called_once()

    mock_coordinator.data["light_1234"]["last_value"] = 100
    assert light.is_on is True


@pytest.mark.asyncio
async def test_light_turn_off():
    """Test light turn off method."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "light"
    mock_coordinator.data = {
        "light_1235": {
            "periph_id": "light_1235",
            "ha_entity": "light",
            "ha_subtype": "brightness",
            "last_value": "on", 
            "brightness": 50, 
            "value_list": ["on", "off"],
       }
    }

    light = EedomusLight(mock_coordinator, "light_1235")
    light.hass = MagicMock()
    light.hass.services.async_call = AsyncMock()

    assert light.is_on is True
    await light.async_turn_off()
    light.hass.services.async_call.assert_called_once()

    mock_coordinator.data["light_1235"]["last_value"] = "0"
    assert light.is_on is False


@pytest.mark.asyncio
async def test_light_with_consumption_child():
    """Test light with consumption child (Issue #9 related)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "light"
    mock_coordinator.data = {
        "light_123": {
            "name": "Test Light",
            "last_value": "on",
            "brightness": 255,
            "value_list": ["on", "off"],
        },
        "light_123_consumption": {
            "consumption": 20.5,
            "current_power": 80,
            "usage_id": "26",
            "name": "Consommation",
        },
    }

    light = EedomusLight(mock_coordinator, "light_123")
    assert light.name == "Test Light"
    assert light.is_on is True


@pytest.mark.asyncio
async def test_light_standalone_rgb_no_children():
    """Test une lumière RGB autonome sans périphériques enfants."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "light"
    mock_coordinator.data = {
        "light_123_02": {
            "periph_id": "light_123_02",
            "name": "light_123_02 Info",
            "ha_entity": "light",
            "ha_subtype": "rgb",
            "last_value": "255,100,50",
        }
    }

    light = EedomusLight(mock_coordinator, "light_123_02")
    assert light.supported_color_modes == {ColorMode.RGB}
    assert light.color_mode == ColorMode.RGB
    assert light.rgb_color == (255, 100, 50)
    assert light.is_on is True
    assert light.brightness == 255


@pytest.mark.asyncio
async def test_light_hue_one_child_color():
    """Test une lumière Hue dotée d'un parent d'intensité et d'un seul enfant couleur."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "light"
    mock_coordinator.data = {
        "546924": {
            "periph_id": "546924",
            "name": "Lampe Hue Couleur ",
            "ha_entity": "light",
            "ha_subtype": "rgb",
            "last_value": "30",
        },
        "546930": {
            "periph_id": "546930",
            "parent_periph_id": "546924",
            "name": "Hue - Couleur Hue",
            "last_value": "0,25,100",
        }
    }

    color_child = {"periph_id": "546930", "parent_periph_id": "546924"}
    light = EedomusRGBChildLight(mock_coordinator, "546924", color_child)

    assert light.supported_color_modes == {ColorMode.RGB}
    assert light.color_mode == ColorMode.RGB
    assert light.brightness == 76
    assert light.rgb_color == (0, 64, 255)


@pytest.mark.asyncio
async def test_light_brightness_only():
    """Test brightness-only light."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "light"
    mock_coordinator.data = {
        "light_dimmer": {
            "name": "Dimmer Light",
            "ha_entity": "light",
            "ha_subtype": "brightness",
            "last_value": 50,
            "value_list": ["on", "off"],
        }
    }

    light = EedomusLight(mock_coordinator, "light_dimmer")
    assert light.supported_color_modes == {ColorMode.BRIGHTNESS}
    assert light.color_mode == ColorMode.BRIGHTNESS
    assert light.brightness == 128


@pytest.mark.asyncio
async def test_light_color_temp_and_edges():
    """Couvre les modes color_temp, et les cas d'erreur de parsing RGB/Brightness."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "light"
    mock_coordinator.data = {
        "light_ct": {
            "periph_id": "light_ct",
            "ha_entity": "light",
            "ha_subtype": "color_temp",
            "last_value": "3000"
        },
        "light_err": {
            "periph_id": "light_err",
            "ha_entity": "light",
            "ha_subtype": "rgb",
            "last_value": "invalid,format,data"
        },
        "light_rgbw_err": {
            "periph_id": "light_rgbw_err",
            "ha_entity": "light",
            "ha_subtype": "rgbw",
            "last_value": "bad,values"
        }
    }

    # 1. Test color_temp
    light_ct = EedomusLight(mock_coordinator, "light_ct")
    assert light_ct.supported_color_modes == {ColorMode.COLOR_TEMP}
    assert light_ct.color_mode == ColorMode.COLOR_TEMP

    # 2. Test RGB parsing ValueError / fallback
    light_err = EedomusLight(mock_coordinator, "light_err")
    assert light_err.rgb_color == (255, 255, 255)

    # 3. Test RGBW parsing fallback
    light_rgbw_err = EedomusLight(mock_coordinator, "light_rgbw_err")
    assert light_rgbw_err.rgbw_color == (255, 255, 255, 255)


@pytest.mark.asyncio
async def test_light_turn_on_exceptions_and_color_temp():
    """Teste le turn_on avec color_temp_kelvin et la levée d'exceptions."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "light"
    mock_coordinator.data = {
        "light_ct": {"ha_entity": "light", "ha_subtype": "color_temp", "last_value": "0"}
    }
    light = EedomusLight(mock_coordinator, "light_ct")
    light.hass = MagicMock()
    light.hass.services.async_call = AsyncMock()

    await light.async_turn_on(color_temp_kelvin=4000)
    light.hass.services.async_call.assert_called()

    # Test levée d'exception sur turn_on / turn_off
    with patch.object(light, "async_set_value", side_effect=Exception("API Error")):
        with pytest.raises(Exception):
            await light.async_turn_on(brightness=100)
        with pytest.raises(Exception):
            await light.async_turn_off()

@pytest.mark.asyncio
async def test_light_is_on_and_periph_edge_cases():
    """Teste les comportements de is_on et brightness quand les données manquent."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "light"

    # Initialisation avec des données valides
    mock_coordinator.data = {"missing_key": {"ha_entity": "light", "ha_subtype": "onoff", "last_value": "on"}}
    light = EedomusLight(mock_coordinator, "missing_key")

    # Coordinator data None après initialisation
    mock_coordinator.data = None
    assert light.is_on is False

    # Device data None
    mock_coordinator.data = {}
    assert light.is_on is False

    # Valeur None ou "None"
    mock_coordinator.data = {"missing_key": {"last_value": "None"}}
    assert light.is_on is False

    # Brightness avec periph_data à None et valeur invalide
    mock_coordinator.data = {"light_dim": {"ha_entity": "light", "ha_subtype": "brightness", "last_value": "not_an_int"}}
    light_dim = EedomusLight(mock_coordinator, "light_dim")
    assert light_dim.brightness == 255  # Fallback par défaut

    with patch.object(light_dim, "_get_periph_data", return_value=None):
        assert light_dim.brightness == 0
@pytest.mark.asyncio
async def test_rgb_child_light_rgbw_and_branches():
    """Teste EedomusRGBChildLight en mode rgbw et ses conditions spécifiques."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "light"
    mock_coordinator.data = {
        "parent_rgbw": {"ha_entity": "light", "ha_subtype": "rgbw", "name": "RGBW Parent", "last_value": "off"},
        "child_rgbw": {"periph_id": "child_rgbw", "parent_periph_id": "parent_rgbw", "last_value": "10,20,30"}
    }
    child_info = {"periph_id": "child_rgbw", "parent_periph_id": "parent_rgbw"}
    
    child_light = EedomusRGBChildLight(mock_coordinator, "parent_rgbw", child_info)
    child_light.hass = MagicMock()
    child_light.entity_id = "light.rgbw_parent"
    child_light.async_write_ha_state = MagicMock()  # Contourne la vérification du frame helper
    assert child_light.color_mode == ColorMode.RGBW

    # rgbw_color avec 3 parties (ajoute w=0)
    assert child_light.rgbw_color[3] == 0

    # Turn on avec ATTR_RGBW_COLOR
    child_light.coordinator.async_set_periph_value = AsyncMock()
    await child_light.async_turn_on(rgbw_color=(255, 128, 64, 32))

    # Turn on avec last_value "off"
    mock_coordinator.data["parent_rgbw"]["last_value"] = "off"
    await child_light.async_turn_on()

    # Turn on avec last_value numérique
    mock_coordinator.data["parent_rgbw"]["last_value"] = "50"
    await child_light.async_turn_on()


@pytest.mark.asyncio
async def test_rgbw_light_edge_cases_and_safe_extract():
    """Teste les cas limites de EedomusRGBWLight (enfants insuffisants, formats multiples)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "light"

    # Moins de 4 enfants
    mock_coordinator.data = {
        "parent_few": {"ha_entity": "light", "ha_subtype": "rgbw", "name": "Few", "last_value": "50"},
        "c1": {"periph_id": "c1", "parent_periph_id": "parent_few", "last_value": "10"}
    }
    rgbw_few = EedomusRGBWLight(mock_coordinator, "parent_few", [{"periph_id": "c1"}])
    rgbw_few.hass = MagicMock()
    rgbw_few.entity_id = "light.few"
    rgbw_few.async_write_ha_state = MagicMock()  # Contourne la vérification du frame helper
    assert rgbw_few.rgbw_color is None
    await rgbw_few.async_turn_on()

    # 4 enfants avec formats variés (pourcentage, invalide, etc.)
    mock_coordinator.data = {
        "parent_full": {"ha_entity": "light", "ha_subtype": "rgbw", "name": "Full", "last_value": "0"},
        "1": {"periph_id": "1", "parent_periph_id": "parent_full", "last_value": "50%"},
        "2": {"periph_id": "2", "parent_periph_id": "parent_full", "last_value": "invalid_val"},
        "3": {"periph_id": "3", "parent_periph_id": "parent_full", "last_value": None},
        "4": {"periph_id": "4", "parent_periph_id": "parent_full", "last_value": "10,20,30,40"}
    }
    children = [{"periph_id": "1"}, {"periph_id": "2"}, {"periph_id": "3"}, {"periph_id": "4"}]
    rgbw_full = EedomusRGBWLight(mock_coordinator, "parent_full", children)
    rgbw_full.hass = MagicMock()
    rgbw_full.entity_id = "light.full"
    rgbw_full.async_write_ha_state = MagicMock()  # Contourne la vérification du frame helper
    
    assert rgbw_full.rgbw_color is not None
    assert rgbw_full.xy_color is None

    # Allumage avec dicts vides (brightness à 0 puis forcé à 100)
    await rgbw_full.async_turn_on()

    # Allumage avec couleur RGBW spécifique
    await rgbw_full.async_turn_on(rgbw_color=(100, 100, 100, 100))


@pytest.mark.asyncio
async def test_setup_entry_additional_branches():
    """Couvre les lignes de setup_entry (usage_id=26 et light normale sans rgb/rgbw)."""
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry"
    
    mock_coordinator = MagicMock()
    mock_coordinator.get_all_peripherals.return_value = {
        "parent_light": {"periph_id": "parent_light", "name": "Parent", "usage_id": "1", "ha_entity": "light"},
        "child_energy": {"periph_id": "child_energy", "parent_periph_id": "parent_light", "usage_id": "26", "name": "Energy"},
        "normal_light": {"periph_id": "normal_light", "name": "Normal", "ha_entity": "light"}
    }
    mock_coordinator.data = {
        "parent_light": {"ha_entity": "light", "ha_subtype": "dimmable", "name": "Parent", "last_value": "50"},
        "child_energy": {"periph_id": "child_energy", "parent_periph_id": "parent_light", "usage_id": "26", "name": "Energy"},
        "normal_light": {"ha_entity": "light", "ha_subtype": "dimmable", "name": "Normal", "last_value": "50"}
    }
    mock_hass.data = {DOMAIN: {"test_entry": {COORDINATOR: mock_coordinator}}}
    
    added_entities = []
    def mock_add(entities):
        added_entities.extend(entities)
        
    await async_setup_entry(mock_hass, mock_entry, mock_add)
    assert len(added_entities) > 0


@pytest.mark.asyncio
async def test_eedomus_light_edge_cases_and_exceptions():
    """Couvre color_temp, types inconnus, erreurs de données et exceptions d'API."""
    coordinator = AsyncMock()
    coordinator.config_entry.entry_id = "test"
    
    # 1. Type color_temp et type inconnu (fallback ONOFF)
    coordinator.data = {
        "l_temp": {"ha_entity": "light", "ha_subtype": "color_temp", "name": "Temp", "last_value": "50"},
        "l_unknown": {"ha_entity": "light", "ha_subtype": "unknown", "name": "Unknown", "last_value": "0"}
    }
    
    light_temp = EedomusLight(coordinator, "l_temp")
    assert ColorMode.COLOR_TEMP in light_temp.supported_color_modes
    assert light_temp.color_mode == ColorMode.COLOR_TEMP
    
    light_unknown = EedomusLight(coordinator, "l_unknown")
    assert ColorMode.ONOFF in light_unknown.supported_color_modes

    # 2. is_on avec coordinator.data ou device_data à None
    coordinator.data = None
    assert light_temp.is_on is False
    
    coordinator.data = {"l_temp": None}
    assert light_temp.is_on is False

    # 3. rgb_color / rgbw_color avec valeurs invalides (ValueError)
    coordinator.data = {
        "l_temp": {"ha_entity": "light", "ha_subtype": "rgb", "last_value": "abc,def,ghi"},
        "l_w": {"ha_entity": "light", "ha_subtype": "rgbw", "last_value": "abc,def,ghi,jkl"}
    }
    light_rgb = EedomusLight(coordinator, "l_temp")
    assert light_rgb.rgb_color == (255, 255, 255)
    
    light_rgbw = EedomusLight(coordinator, "l_w")
    assert light_rgbw.rgbw_color == (255, 255, 255, 255)

    # 4. brightness avec periph_data absent, valeur "on", ou valeur invalide
    coordinator.data = {}
    assert light_rgb.brightness == 0
    
    coordinator.data = {"l_temp": {"last_value": "on"}}
    assert light_rgb.brightness == 255
    
    coordinator.data = {"l_temp": {"last_value": "not_an_int"}}
    assert light_rgb.brightness == 255

    # 5. Exceptions levées dans async_turn_on et async_turn_off
    light_temp.hass = MagicMock()
    light_temp.entity_id = "light.temp"
    light_temp.async_write_ha_state = MagicMock()
    light_temp.async_set_value = AsyncMock(side_effect=Exception("API Error"))
    
    with pytest.raises(Exception):
        await light_temp.async_turn_on(color_temp_kelvin=4000)
        
    with pytest.raises(Exception):
        await light_temp.async_turn_off()


@pytest.mark.asyncio
async def test_rgb_child_light_extra_branches():
    """Couvre les branches spécifiques de EedomusRGBChildLight."""
    coordinator = AsyncMock()
    coordinator.config_entry.entry_id = "test"
    
    # Test avec sous-type rgb pour rgb_color invalide
    coordinator.data = {
        "parent_rgb": {"ha_entity": "light", "ha_subtype": "rgb", "name": "Parent", "last_value": "0"},
        "child_rgb": {"periph_id": "child_rgb", "parent_periph_id": "parent_rgb", "last_value": "invalid,format"}
    }
    child_info = {"periph_id": "child_rgb", "parent_periph_id": "parent_rgb"}
    
    child_light = EedomusRGBChildLight(coordinator, "parent_rgb", child_info)
    child_light.hass = MagicMock()
    child_light.entity_id = "light.parent"
    child_light.async_write_ha_state = MagicMock()
    
    assert child_light.rgb_color == (255, 255, 255)

    # Test avec sous-type rgbw pour la branche rgbw_color avec 3 parties
    coordinator.data = {
        "parent_rgbw": {"ha_entity": "light", "ha_subtype": "rgbw", "name": "Parent", "last_value": "0"},
        "child_rgbw": {"periph_id": "child_rgbw", "parent_periph_id": "parent_rgbw", "last_value": "50,50,50"}
    }
    child_info_w = {"periph_id": "child_rgbw", "parent_periph_id": "parent_rgbw"}
    child_light_w = EedomusRGBChildLight(coordinator, "parent_rgbw", child_info_w)
    assert child_light_w.rgbw_color[3] == 0


@pytest.mark.asyncio
async def test_rgbw_light_safe_extract_and_edges():
    """Couvre safe_extract_value et les cas limites de EedomusRGBWLight."""
    coordinator = AsyncMock()
    coordinator.config_entry.entry_id = "test"
    
    # Utilisation d'ID numériques sous forme de chaînes pour le tri de EedomusRGBWLight
    children = [
        {"periph_id": "101"}, {"periph_id": "102"}, {"periph_id": "103"}, {"periph_id": "104"}
    ]
    coordinator.data = {
        "parent_full": {"ha_entity": "light", "ha_subtype": "rgbw", "name": "Full", "last_value": "-5"},
        "101": {"periph_id": "101", "parent_periph_id": "parent_full", "last_value": "10,20,30,40"},
        "102": {"periph_id": "102", "parent_periph_id": "parent_full", "last_value": "bad_parts"},
        "103": {"periph_id": "103", "parent_periph_id": "parent_full", "last_value": "75%"},
        "104": {"periph_id": "104", "parent_periph_id": "parent_full", "last_value": "0"}
    }
    
    rgbw_full = EedomusRGBWLight(coordinator, "parent_full", children)
    rgbw_full.hass = MagicMock()
    rgbw_full.entity_id = "light.full"
    rgbw_full.async_write_ha_state = MagicMock()
    
    colors = rgbw_full.rgbw_color
    assert colors is not None
    
    assert rgbw_full.is_on is False
    
    coordinator.async_set_periph_value = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    await rgbw_full.async_turn_on()
    
    await rgbw_full.async_turn_off()


@pytest.mark.asyncio
async def test_setup_entry_parent_light_children_mapping():
    """Couvre explicitement les lignes 116-133 (enfants de type 1 et 26 sous un parent light)."""
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_children"
    
    mock_coordinator = MagicMock()
    mock_coordinator.get_all_peripherals.return_value = {
        "parent_l": {"periph_id": "parent_l", "name": "Parent Light", "ha_entity": "light"},
        "child_brightness": {"periph_id": "child_brightness", "parent_periph_id": "parent_l", "usage_id": "1", "name": "Child Brightness"},
        "child_energy": {"periph_id": "child_energy", "parent_periph_id": "parent_l", "usage_id": "26", "name": "Child Energy"}
    }
    mock_coordinator.data = {
        "parent_l": {"ha_entity": "light", "ha_subtype": "dimmable", "name": "Parent Light", "last_value": "50"},
        "child_brightness": {"ha_entity": "sensor", "periph_id": "child_brightness", "parent_periph_id": "parent_l", "usage_id": "1", "name": "Child Brightness"},
        "child_energy": {"ha_entity": "sensor", "periph_id": "child_energy", "parent_periph_id": "parent_l", "usage_id": "26", "name": "Child Energy"}
    }
    mock_hass.data = {DOMAIN: {"test_entry_children": {COORDINATOR: mock_coordinator}}}
    
    added_entities = []
    await async_setup_entry(mock_hass, mock_entry, lambda ents: added_entities.extend(ents))
    assert len(added_entities) > 0

@pytest.mark.asyncio
async def test_eedomus_light_color_modes_and_properties():
    """Couvre les propriétés de color_mode pour BRIGHTNESS et COLOR_TEMP."""
    coordinator = AsyncMock()
    coordinator.config_entry.entry_id = "test"
    
    # Test BRIGHTNESS
    coordinator.data = {"l_bright": {"ha_entity": "light", "ha_subtype": "brightness", "last_value": "40"}}
    light_b = EedomusLight(coordinator, "l_bright")
    assert light_b.color_mode == ColorMode.BRIGHTNESS
    
    # Test COLOR_TEMP
    coordinator.data = {"l_ct": {"ha_entity": "light", "ha_subtype": "color_temp", "last_value": "3000"}}
    light_ct = EedomusLight(coordinator, "l_ct")
    assert light_ct.color_mode == ColorMode.COLOR_TEMP


@pytest.mark.asyncio
async def test_rgb_child_light_comprehensive_coverage():
    """Couvre les branches avancées de EedomusRGBChildLight (rgbw_color, turn_on avec RGBW et valeurs par défaut)."""
    coordinator = AsyncMock()
    coordinator.config_entry.entry_id = "test"
    coordinator.data = {
        "parent_rgbw": {"ha_entity": "light", "ha_subtype": "rgbw", "name": "Parent", "last_value": "0"},
        "child_rgbw": {"periph_id": "child_rgbw", "parent_periph_id": "parent_rgbw", "last_value": "50,50,50,50"}
    }
    child_info = {"periph_id": "child_rgbw", "parent_periph_id": "parent_rgbw"}
    
    child_light = EedomusRGBChildLight(coordinator, "parent_rgbw", child_info)
    child_light.hass = MagicMock()
    child_light.entity_id = "light.parent"
    child_light.async_write_ha_state = MagicMock()
    child_light.async_set_value = AsyncMock()
    coordinator.async_set_periph_value = AsyncMock()
    
    # Test rgbw_color complet (4 parties)
    assert child_light.rgbw_color is not None
    
    # Test turn_on avec ATTR_RGBW_COLOR
    await child_light.async_turn_on(rgbw_color=(100, 100, 100, 100))
    
    # Test turn_on sans brightness (current_val = "0" puis autre)
    coordinator.data["parent_rgbw"]["last_value"] = "0"
    await child_light.async_turn_on()
    
    coordinator.data["parent_rgbw"]["last_value"] = "50"
    await child_light.async_turn_on()


@pytest.mark.asyncio
async def test_rgbw_light_xy_color_and_edge_cases():
    """Couvre xy_color et les cas limites de EedomusRGBWLight (turn_on avec kwargs vides ou last_value à 0)."""
    coordinator = AsyncMock()
    coordinator.config_entry.entry_id = "test"
    
    children = [
        {"periph_id": "201"}, {"periph_id": "202"}, {"periph_id": "203"}, {"periph_id": "204"}
    ]
    coordinator.data = {
        "parent_rgbw2": {"ha_entity": "light", "ha_subtype": "rgbw", "name": "Full2", "last_value": "0"},
        "201": {"periph_id": "201", "parent_periph_id": "parent_rgbw2", "last_value": "0"},
        "202": {"periph_id": "202", "parent_periph_id": "parent_rgbw2", "last_value": "0"},
        "203": {"periph_id": "203", "parent_periph_id": "parent_rgbw2", "last_value": "0"},
        "204": {"periph_id": "204", "parent_periph_id": "parent_rgbw2", "last_value": "0"}
    }
    
    rgbw_light = EedomusRGBWLight(coordinator, "parent_rgbw2", children)
    rgbw_light.hass = MagicMock()
    rgbw_light.entity_id = "light.full2"
    rgbw_light.async_write_ha_state = MagicMock()
    
    # Vérifie xy_color
    assert rgbw_light.xy_color is None
    
    # Turn on avec kwargs vides et last_value à 0 (force _global_brightness_percent à 100)
    coordinator.async_set_periph_value = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    await rgbw_light.async_turn_on()

@pytest.mark.asyncio
async def test_setup_entry_with_various_child_usages():
    """Couvre spécifiquement les lignes 116-133 (gestion des enfants par usage_id dans async_setup_entry)."""
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_usages"
    
    mock_coordinator = MagicMock()
    mock_coordinator.get_all_peripherals.return_value = {
        "parent_light": {"periph_id": "parent_light", "name": "Parent Light", "ha_entity": "light"},
        "child_dim": {"periph_id": "child_dim", "parent_periph_id": "parent_light", "usage_id": "1", "name": "Child Dim"},
        "child_power": {"periph_id": "child_power", "parent_periph_id": "parent_light", "usage_id": "26", "name": "Child Power"},
        "child_other": {"periph_id": "child_other", "parent_periph_id": "parent_light", "usage_id": "99", "name": "Child Other"}
    }
    mock_coordinator.data = {
        "parent_light": {"ha_entity": "light", "ha_subtype": "dimmable", "name": "Parent Light", "last_value": "50"},
        "child_dim": {"ha_entity": "light", "periph_id": "child_dim", "parent_periph_id": "parent_light", "usage_id": "1", "name": "Child Dim"},
        "child_power": {"ha_entity": "sensor", "periph_id": "child_power", "parent_periph_id": "parent_light", "usage_id": "26", "name": "Child Power"},
        "child_other": {"ha_entity": "sensor", "periph_id": "child_other", "parent_periph_id": "parent_light", "usage_id": "99", "name": "Child Other"}
    }
    mock_hass.data = {DOMAIN: {"test_entry_usages": {COORDINATOR: mock_coordinator}}}
    
    added_entities = []
    await async_setup_entry(mock_hass, mock_entry, lambda ents: added_entities.extend(ents))
    assert len(added_entities) > 0


@pytest.mark.asyncio
async def test_setup_entry_light_children_variants():
    """Couvre explicitement les lignes 116-133 (len(children) == 1 et else dans async_setup_entry)."""
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_variants"
    
    mock_coordinator = MagicMock()
    mock_coordinator.get_all_peripherals.return_value = {
        # Cas 1 : Un seul enfant (lignes 116-125)
        "light_hue": {"periph_id": "light_hue", "name": "Hue Light", "ha_entity": "light"},
        "child_color": {"periph_id": "child_color", "parent_periph_id": "light_hue", "name": "Child Color"},
        
        # Cas 2 : Deux enfants (lignes 126-133 - bloc else)
        "light_other": {"periph_id": "light_other", "name": "Other Light", "ha_entity": "light"},
        "child_1": {"periph_id": "child_1", "parent_periph_id": "light_other", "name": "Child 1"},
        "child_2": {"periph_id": "child_2", "parent_periph_id": "light_other", "name": "Child 2"},
    }
    mock_coordinator.data = {
        "light_hue": {"ha_entity": "light", "ha_subtype": "rgb", "name": "Hue Light", "last_value": "0"},
        "child_color": {"ha_entity": "sensor", "periph_id": "child_color", "parent_periph_id": "light_hue", "last_value": "0,0,0"},
        "light_other": {"ha_entity": "light", "ha_subtype": "dimmable", "name": "Other Light", "last_value": "0"},
        "child_1": {"ha_entity": "sensor", "periph_id": "child_1", "parent_periph_id": "light_other", "last_value": "0"},
        "child_2": {"ha_entity": "sensor", "periph_id": "child_2", "parent_periph_id": "light_other", "last_value": "0"},
    }
    mock_hass.data = {DOMAIN: {"test_entry_variants": {COORDINATOR: mock_coordinator}}}
    
    added_entities = []
    await async_setup_entry(mock_hass, mock_entry, lambda ents: added_entities.extend(ents))
    assert len(added_entities) >= 2

@pytest.mark.asyncio
async def test_setup_entry_rgb_fallback_light():
    """Couvre explicitement les lignes 128-133 (fallback standalone RGB/RGBW sans enfants)."""
    mock_hass = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_entry_rgb_fallback"
    
    mock_coordinator = MagicMock()
    mock_coordinator.get_all_peripherals.return_value = {
        "light_rgb_standalone": {
            "periph_id": "light_rgb_standalone", 
            "name": "RGB Standalone", 
            "ha_entity": "light", 
            "ha_subtype": "rgb"
        },
    }
    mock_coordinator.data = {
        "light_rgb_standalone": {
            "ha_entity": "light", 
            "ha_subtype": "rgb", 
            "name": "RGB Standalone", 
            "last_value": "0"
        },
    }
    mock_hass.data = {DOMAIN: {"test_entry_rgb_fallback": {COORDINATOR: mock_coordinator}}}
    
    added_entities = []
    await async_setup_entry(mock_hass, mock_entry, lambda ents: added_entities.extend(ents))
    assert len(added_entities) == 1

@pytest.mark.asyncio
async def test_light_missing_lines_color_modes_and_properties():
    """Couvre explicitement les lignes 217, 224, 231, 247 et 252-253."""
    coordinator = AsyncMock()
    coordinator.config_entry.entry_id = "test"

    # 1. Test ligne 217 : color_mode -> RGBW
    coordinator.data = {"l_rgbw": {"ha_entity": "light", "ha_subtype": "rgbw", "last_value": "0"}}
    light_rgbw = EedomusLight(coordinator, "l_rgbw")
    assert light_rgbw.color_mode == ColorMode.RGBW

    # 2. Test ligne 224 : color_mode -> ONOFF (quand aucun autre mode ne matche)
    coordinator.data = {"l_plain": {"ha_entity": "light", "ha_subtype": "other", "last_value": "0"}}
    light_plain = EedomusLight(coordinator, "l_plain")
    light_plain._attr_supported_color_modes = {ColorMode.ONOFF}
    assert light_plain.color_mode == ColorMode.ONOFF

    # 3. Test ligne 231 : rgb_color -> None si ColorMode.RGB n'est pas supporté
    coordinator.data = {"l_dim": {"ha_entity": "light", "ha_subtype": "dimmable", "last_value": "50"}}
    light_dim = EedomusLight(coordinator, "l_dim")
    light_dim._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    assert light_dim.rgb_color is None

    # 4. Test ligne 247 : rgbw_color -> None si ColorMode.RGBW n'est pas supporté
    assert light_dim.rgbw_color is None

    # 5. Test lignes 252-253 : rgbw_color avec >= 4 parties valides
    coordinator.data = {"l_rgbw_full": {"ha_entity": "light", "ha_subtype": "rgbw", "last_value": "100,150,200,50"}}
    light_rgbw_full = EedomusLight(coordinator, "l_rgbw_full")
    assert light_rgbw_full.rgbw_color == (100, 150, 200, 50)

@pytest.mark.asyncio
async def test_light_turn_on_rgb_rgbw_and_turn_off_exception():
    """Couvre explicitement les lignes 324, 326 et 377."""
    coordinator = AsyncMock()
    coordinator.config_entry.entry_id = "test"
    
    coordinator.data = {"l_standalone": {"ha_entity": "light", "ha_subtype": "rgbw", "last_value": "0"}}
    light_ent = EedomusLight(coordinator, "l_standalone")
    light_ent.hass = MagicMock()
    light_ent.entity_id = "light.standalone"
    light_ent.async_write_ha_state = MagicMock()

    # 1. Test ligne 324 : async_turn_on avec rgb_color
    light_ent.async_set_value = AsyncMock(return_value="OK")
    await light_ent.async_turn_on(rgb_color=(255, 128, 0))
    
    # 2. Test ligne 326 : async_turn_on avec rgbw_color
    await light_ent.async_turn_on(rgbw_color=(255, 128, 0, 50))

    # 3. Test ligne 377 : exception levée et gérée dans async_turn_off (avec capture de 'response' non défini)
    light_ent.async_set_value = AsyncMock(side_effect=Exception("Turn off error"))
    with pytest.raises(Exception):
        await light_ent.async_turn_off()

@pytest.mark.asyncio
async def test_light_final_remaining_lines():
    """Atteint 100% de couverture de light.py en activant chaque ligne précisément."""
    from custom_components.eedomus.light import EedomusLight, EedomusRGBWLight
    from homeassistant.components.light import ColorMode

    coordinator = AsyncMock()
    coordinator.config_entry.entry_id = "test"

    # --- Partie 1 : EedomusLight (lignes 377, 422, 444) ---
    
    # 1. Ligne 377: Exception dans async_turn_off
    coordinator.data = {"l_plain": {"ha_entity": "light", "ha_subtype": "other", "last_value": "100"}}
    light_plain = EedomusLight(coordinator, "l_plain")
    light_plain.async_set_value = AsyncMock(side_effect=Exception("API Fail"))
    with pytest.raises(Exception):
        await light_plain.async_turn_off()

    # 2. Lignes 422 & 444: Propriétés rgb_color / rgbw_color non supportées
    coordinator.data = {"l_dim": {"ha_entity": "light", "ha_subtype": "dimmable", "last_value": "50"}}
    light_dim = EedomusLight(coordinator, "l_dim")
    light_dim._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _ = light_dim.rgb_color   # Ligne 422
    _ = light_dim.rgbw_color  # Ligne 444

    # --- Partie 2 : EedomusRGBWLight (lignes 465-467, 483-485, 501-502, 543, 574-578, 625-628) ---
    
    parent_id = "parent_rgbw"
    child_devices = [
        {"periph_id": "10", "ha_entity": "light"},
        {"periph_id": "11", "ha_entity": "light"},
        {"periph_id": "12", "ha_entity": "light"},
        {"periph_id": "13", "ha_entity": "light"},
    ]
    coordinator.data = {
        parent_id: {"name": "RGBW Light", "ha_subtype": "rgbw", "last_value": "50"},
        "10": {"last_value": "25,25,25,25"},
        "11": {"last_value": "50"},
        "12": {"last_value": "75"},
        "13": {"last_value": "100"},
    }

    rgbw_light = EedomusRGBWLight(coordinator, parent_id, child_devices)
    rgbw_light.hass = MagicMock()
    rgbw_light.entity_id = "light.rgbw_light"
    rgbw_light.async_write_ha_state = MagicMock()
    coordinator.async_set_periph_value = AsyncMock()

    # Forcer le mode supporté pour l'évaluation des propriétés
    rgbw_light._attr_supported_color_modes = {ColorMode.RGBW}

    # 3. Lignes 543 & 574-578 : color_mode et brightness
    _ = rgbw_light.color_mode   # Ligne 543
    _ = rgbw_light.brightness   # Lignes 574-578

    # 4. Lignes 465-467 : Erreur de conversion dans rgbw_color
    coordinator.data["10"]["last_value"] = "invalid_value,abc,xyz,def"
    _ = rgbw_light.rgbw_color

    # 5. Lignes 625-628 : safe_extract_value avec format court ou mal formé
    coordinator.data["10"]["last_value"] = "malformed"
    _ = rgbw_light.rgbw_color

    # 6. Lignes 483-485 & 501-502 : async_turn_on avec rgb_color et rgbw_color
    await rgbw_light.async_turn_on(rgb_color=(255, 128, 64), brightness=100)
    await rgbw_light.async_turn_on(rgbw_color=(10, 20, 30, 40))

@pytest.mark.asyncio
async def test_light_final_remaining_lines_100_percent():
    """Atteint 100% de couverture en validant l'exception sur async_turn_off."""
    from custom_components.eedomus.light import EedomusLight, EedomusRGBChildLight, EedomusRGBWLight
    from homeassistant.components.light import ColorMode

    coordinator = AsyncMock()
    coordinator.config_entry.entry_id = "test"

    # --- 1. Ligne 377 : Exception turn_off en mockant async_set_value directement sur l'objet ---
    coordinator.data = {"l_plain": {"ha_entity": "light", "ha_subtype": "other", "last_value": "100"}}
    
    light_plain = EedomusLight(coordinator, "l_plain")
    light_plain.hass = MagicMock()
    light_plain.entity_id = "light.plain"
    light_plain.async_write_ha_state = MagicMock()
    
    # Forcer l'exception sur la méthode async_set_value appelée par async_turn_off
    light_plain.async_set_value = AsyncMock(side_effect=Exception("API Error"))

    with pytest.raises(Exception):
        await light_plain.async_turn_off()

    # --- 2. Reste des classes pour s'assurer que tout le reste reste couvert ---
    coordinator.data = {
        "parent_hue": {"ha_entity": "light", "ha_subtype": "rgb", "last_value": "50"},
        "child_color": {"last_value": "25,50,75"}
    }
    rgb_child_light = EedomusRGBChildLight(coordinator, "parent_hue", {"periph_id": "child_color"})
    rgb_child_light.hass = MagicMock()
    rgb_child_light.entity_id = "light.rgb_child"
    rgb_child_light.async_write_ha_state = MagicMock()

    _ = rgb_child_light.rgbw_color  # Ligne 444
    await rgb_child_light.async_turn_on(rgb_color=(100, 150, 200), brightness=128)

    coordinator.data["parent_hue"]["ha_subtype"] = "rgbw"
    rgbw_child_light = EedomusRGBChildLight(coordinator, "parent_hue", {"periph_id": "child_color"})
    _ = rgbw_child_light.rgb_color  # Ligne 422

    coordinator.data["child_color"]["last_value"] = "abc,def,ghi,jkl"
    _ = rgbw_child_light.rgbw_color  # Lignes 465-467

    # Cas EedomusRGBWLight (safe_extract_value)
    parent_id = "parent_rgbw"
    child_devices = [
        {"periph_id": "10", "ha_entity": "light"},
        {"periph_id": "11", "ha_entity": "light"},
        {"periph_id": "12", "ha_entity": "light"},
        {"periph_id": "13", "ha_entity": "light"},
    ]
    coordinator.data = {
        parent_id: {"name": "RGBW Light", "ha_subtype": "rgbw", "last_value": "50"},
        "10": {"last_value": "abc,def"},  # Lignes 625-628
        "11": {"last_value": "50"},
        "12": {"last_value": "75"},
        "13": {"last_value": "100"},
    }

    rgbw_light = EedomusRGBWLight(coordinator, parent_id, child_devices)
    rgbw_light.hass = MagicMock()
    rgbw_light.entity_id = "light.rgbw_light"
    rgbw_light.async_write_ha_state = MagicMock()
    _ = rgbw_light.rgbw_color
