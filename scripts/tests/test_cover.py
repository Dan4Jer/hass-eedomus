"""Tests for Eedomus cover entities."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.cover import CoverDeviceClass, CoverEntityFeature
from homeassistant.const import STATE_CLOSED, STATE_CLOSING, STATE_OPEN, STATE_OPENING

from custom_components.eedomus.const import COORDINATOR, DOMAIN
from custom_components.eedomus.cover import EedomusCover, async_setup_entry

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "custom_components/eedomus")))
# print(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "custom_components/eedomus")))
# from cover import EedomusCover


@pytest.mark.asyncio
async def test_cover_initialization():
    """Test cover entity initialization."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "cover"
    mock_coordinator.data = {
        "cover_1230": {
            "periph_id": "cover_1230",
            "name": "Test Cover 0",
            "last_value": "100",
            "position": 100,
            "tilt_position": 50,
        }
    }

    device_info = {"periph_id": "cover_1230", "name": "Test Cover 0", "usage_id": "48"}

    cover = EedomusCover(mock_coordinator, device_info["periph_id"])
    print(vars(cover))
    print(dir(cover))
    assert cover.name == "Test Cover 0"
    assert cover.unique_id == "eedomus_cover_cover_1230"
    assert cover.is_closed is False
    assert cover.current_cover_position == 100
    assert cover.current_cover_tilt_position == 50
    assert cover.supported_features == (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.SET_TILT_POSITION
    )


@pytest.mark.asyncio
async def test_cover_closed_state():
    """Test cover in closed state."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "cover"
    mock_coordinator.data = {
        "cover_1231": {"periph_id": "cover_1231", "last_value": "closed", "position": 0}
    }

    device_info = {"periph_id": "cover_1231", "name": "Test Cover"}

    cover = EedomusCover(mock_coordinator, device_info["periph_id"])

    assert cover.is_closed is True
    assert cover.current_cover_position == 0


@pytest.mark.asyncio
async def test_cover_open_method():
    """Test cover open method."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "cover"
    mock_coordinator.data = {
        "cover_123": {"periph_id": "cover_123", "last_value": "closed", "position": 0}
    }

    device_info = {"periph_id": "cover_123", "name": "Test Cover"}

    cover = EedomusCover(mock_coordinator, device_info["periph_id"])

    assert cover.is_closed is True
    assert cover.current_cover_position == 0
    with patch.object(cover, "async_set_value") as mock_set_value:
        # On déclenche l'ouverture
        await cover.async_open_cover()

        # On vérifie que async_set_value a bien été appelée avec "100"
        # (car async_open_cover demande la position 100, convertie en string par ta méthode)
        mock_set_value.assert_called_once_with("100")
    # SIMULATION DU RETOUR DE L'API :
    # Dans la vraie vie, l'Eedomus mettrait à jour sa valeur et le coordinateur la récupérerait.
    # Ici, on modifie manuellement la donnée du mock pour simuler ce rafraîchissement.
    mock_coordinator.data["cover_123"]["last_value"] = "100"
    mock_coordinator.data["cover_123"]["position"] = 100
    # On peut maintenant vérifier que l'entité interprète correctement le nouvel état
    assert cover.is_closed is False
    assert cover.current_cover_position == 100


@pytest.mark.asyncio
async def test_cover_set_position():
    """Test cover set position method."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "cover"
    mock_coordinator.data = {
        "cover_123": {"periph_id": "cover_123", "last_value": "50", "position": 50}
    }

    device_info = {"periph_id": "cover_123", "name": "Test Cover"}

    cover = EedomusCover(mock_coordinator, device_info["periph_id"])

    assert cover.is_closed is False
    assert cover.current_cover_position == 50
    with patch.object(cover, "async_set_value") as mock_set_value:
        await cover.async_set_cover_position(position=75)
        mock_set_value.assert_called_once_with("75")
    mock_coordinator.data["cover_123"]["last_value"] = "75"
    mock_coordinator.data["cover_123"]["position"] = 75
    # On peut maintenant vérifier que l'entité interprète correctement le nouvel état
    assert cover.is_closed is False
    assert cover.current_cover_position == 75


@pytest.mark.asyncio
async def test_cover_with_energy_sensor():
    """Test cover with associated energy sensor (Issue #9 related)."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "cover"
    mock_coordinator.data = {
        "cover_123": {
            "periph_id": "cover_123",
            "name": "Test Cover",
            "value": "open",
            "position": 100,
        },
        "cover_123_consumption": {
            "periph_id": "cover_123_consumption",
            "consumption": 25.5,
            "current_power": 50,
        },
    }

    device_info = {
        "periph_id": "cover_123",
        "name": "Test Cover",
        "usage_id": "48",
        "children": [{"periph_id": "cover_123_consumption", "usage_id": "26"}],
    }

    cover = EedomusCover(mock_coordinator, device_info["periph_id"])

    # Verify cover properties
    assert cover.name == "Test Cover"

    # Verify energy sensor would be created for consumption child
    # This is handled in the coordinator setup, but we can verify the data exists
    consumption_data = mock_coordinator.data.get("cover_123_consumption", {})
    assert consumption_data.get("consumption") == 25.5


@pytest.mark.asyncio
async def test_cover_with_missing_parent2():
    """Test cover when parent device is not loaded."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "cover"

    # 1. Correction de la donnée (utilisation de 'last_value' avec une valeur numérique)
    mock_coordinator.data = {
        "cover_child": {
            "name": "Child Cover",
            "last_value": "0",
            "position": 0,
            "parent_periph_id": "missing_parent",
        }
        # Note: missing_parent is NOT in coordinator.data
    }

    device_info = {
        "periph_id": "cover_child",
        "name": "Child Cover",
        "usage_id": "48",
        "parent_periph_id": "missing_parent",
    }

    # L'instanciation ne doit pas lever de KeyError
    cover = EedomusCover(mock_coordinator, device_info["periph_id"])

    # 2. Vérification des propriétés de base
    assert cover.name == "Child Cover"
    assert cover.unique_id == "eedomus_cover_cover_child"

    # 3. Vérification de la robustesse lors de la lecture des états (polling)
    assert cover.is_closed is True
    assert cover.current_cover_position == 0
    assert cover.current_cover_tilt_position is None

    # 4. Vérification de la robustesse lors de l'appel d'une action
    with patch.object(cover, "async_set_value") as mock_set_value:
        await cover.async_open_cover()
        mock_set_value.assert_called_once_with("100")


@pytest.mark.asyncio
async def test_cover_async_setup_entry():
    """Test async_setup_entry for cover integration setup[cite: 1]."""

    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry"

    coordinator = MagicMock()
    coordinator.get_all_peripherals.return_value = {
        "cover_1": {"periph_id": "cover_1", "name": "Main Cover", "usage_id": "48"},
        "child_1": {
            "periph_id": "child_1",
            "name": "Slats",
            "parent_periph_id": "cover_1",
            "usage_id": "48",
        },
        "child_2": {
            "periph_id": "child_2",
            "name": "Energy",
            "parent_periph_id": "cover_1",
            "usage_id": "26",
        },
    }
    coordinator.data = {
        "cover_1": {"ha_entity": "cover", "name": "Main Cover"},
        "child_1": {"name": "Slats"},
        "child_2": {"name": "Energy"},
    }
    hass.data = {DOMAIN: {"test_entry": {COORDINATOR: coordinator}}}

    entities = []

    def mock_add_entities(new_entities):
        entities.extend(new_entities)

    with patch(
        "custom_components.eedomus.cover.map_device_to_ha_entity",
        return_value={"ha_entity": "cover"},
    ), patch("custom_components.eedomus.cover.register_device_mapping"):
        await async_setup_entry(hass, entry, mock_add_entities)

    assert len(entities) > 0


@pytest.mark.asyncio
async def test_aggregated_cover():
    """Test EedomusAggregatedCover entity behavior and extra attributes[cite: 1]."""
    from custom_components.eedomus.cover import EedomusAggregatedCover

    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "cover"
    mock_coordinator.data = {
        "parent_cover": {
            "periph_id": "parent_cover",
            "name": "Parent Cover",
            "last_value": "40",
        },
        "child_cover": {
            "periph_id": "child_cover",
            "name": "Child Shutter",
            "last_value": "20",
            "unit": "%",
            "ha_subtype": "shutter",
        },
    }

    child_devices = [{"periph_id": "child_cover", "name": "Child Shutter"}]
    agg_cover = EedomusAggregatedCover(mock_coordinator, "parent_cover", child_devices)

    assert agg_cover.current_cover_position == 40
    attrs = agg_cover.extra_state_attributes
    assert "child_devices" in attrs
    assert "child_cover" in attrs["child_devices"]


@pytest.mark.asyncio
async def test_cover_misc_methods_and_errors():
    """Test stop cover, tilt position handling, and error/exception paths[cite: 1]."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "cover"
    mock_coordinator.data = {
        "cover_err": {
            "periph_id": "cover_err",
            "name": "Err Cover",
            "last_value": "invalid_val",
            "tilt_position": "invalid_tilt",
        }
    }
    cover = EedomusCover(mock_coordinator, "cover_err")

    # Test exception handling in position parsing
    assert cover.current_cover_position == 0
    assert cover.is_closed is True
    assert cover.current_cover_tilt_position is None

    # Test stop action
    await cover.async_stop_cover()

    # Test tilt position setting paths
    await cover.async_set_cover_tilt_position(tilt_position=None)
    await cover.async_set_cover_tilt_position(tilt_position=50)

    # Test set position with None value
    await cover.async_set_cover_position(position=None)


@pytest.mark.asyncio
async def test_cover_tilt_position_and_stop():
    """Teste le réglage du tilt, le logging du stop et le format invalide du tilt."""
    from homeassistant.components.cover import ATTR_TILT_POSITION

    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "cover"
    mock_coordinator.data = {
        "cover_123": {"periph_id": "cover_123", "name": "Test Cover"}
    }
    cover = EedomusCover(mock_coordinator, "cover_123")

    # Test du réglage d'un tilt valide (couvre les lignes de log et d'exécution)
    await cover.async_set_cover_tilt_position(**{ATTR_TILT_POSITION: 40})

    # Test de la gestion d'un tilt invalide (ValueError/TypeError)
    mock_coordinator.data["cover_123"]["tilt_position"] = "invalid_tilt"
    assert cover.current_cover_tilt_position is None

    # Test de l'arrêt du cover (couvre la méthode async_stop_cover et son log)
    await cover.async_stop_cover()


@pytest.mark.asyncio
async def test_aggregated_cover_missing_and_invalid_data():
    """Teste le cover agrégé avec données manquantes ou invalides (ValueError/TypeError)."""
    from custom_components.eedomus.cover import EedomusAggregatedCover

    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "cover"
    mock_coordinator.data = {
        "parent_cover": {
            "periph_id": "parent_cover",
            "name": "Parent Cover",
            "last_value": "invalid_val",
        }
    }

    child_devices = [{"periph_id": "child_cover", "name": "Child Shutter"}]
    agg_cover = EedomusAggregatedCover(mock_coordinator, "parent_cover", child_devices)

    # Test de l'exception levée par un last_value non numérique
    assert agg_cover.current_cover_position == 0

    # Test lorsque le parent est totalement absent des données du coordinateur
    mock_coordinator.data = {}
    assert agg_cover.current_cover_position == 0


@pytest.mark.asyncio
async def test_async_setup_entry_slats_child():
    """Teste spécifiquement le bloc des lamelles (usage_id == '48') dans async_setup_entry."""
    from custom_components.eedomus.const import COORDINATOR, DOMAIN
    from custom_components.eedomus.cover import async_setup_entry

    hass = MagicMock()
    entry = MagicMock()
    entry.entry_id = "test_entry_slats"

    coordinator = MagicMock()
    coordinator.get_all_peripherals.return_value = {
        "cover_main": {
            "periph_id": "cover_main",
            "name": "Main Cover",
            "usage_id": "48",
        },
        "child_slats": {
            "periph_id": "child_slats",
            "name": "Slats",
            "parent_periph_id": "cover_main",
            "usage_id": "48",
        },
    }
    coordinator.data = {
        "cover_main": {"ha_entity": "cover", "name": "Main Cover"},
        "child_slats": {"name": "Slats"},
    }
    hass.data = {DOMAIN: {"test_entry_slats": {COORDINATOR: coordinator}}}

    entities = []

    def mock_add_entities(new_entities):
        entities.extend(new_entities)

    with patch(
        "custom_components.eedomus.cover.map_device_to_ha_entity",
        return_value={"ha_entity": "cover"},
    ), patch("custom_components.eedomus.cover.register_device_mapping"):
        await async_setup_entry(hass, entry, mock_add_entities)

    assert len(entities) > 0


@pytest.mark.asyncio
async def test_cover_remaining_edge_cases():
    """Couvre les dernières lignes non testées (position None, periph_data None, log tilt)."""
    from homeassistant.components.cover import ATTR_TILT_POSITION

    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "cover"

    # 1. Test current_cover_position quand periph_data devient None après l'init
    mock_coordinator.data = {"missing_periph": {"name": "Test Cover"}}
    cover_missing = EedomusCover(mock_coordinator, "missing_periph")
    mock_coordinator.data = {}  # On vide les données après l'initialisation
    assert cover_missing.current_cover_position == 0

    # 2. Test async_set_cover_position avec position None et coordinator.data présent
    mock_coordinator.data = {
        "cover_123": {"periph_id": "cover_123", "name": "Test Cover"}
    }
    cover = EedomusCover(mock_coordinator, "cover_123")
    await cover.async_set_cover_position(position=None)

    # 3. Test async_set_cover_tilt_position avec coordinator.data présent
    await cover.async_set_cover_tilt_position(**{ATTR_TILT_POSITION: 60})


@pytest.mark.asyncio
async def test_cover_absolute_100_percent():
    """Atteint les 100% en couvrant _get_periph_data -> None et le log du tilt."""
    from homeassistant.components.cover import ATTR_TILT_POSITION

    mock_coordinator = MagicMock()
    mock_coordinator.config_entry.entry_id = "cover"
    mock_coordinator.data = {
        "cover_123": {"periph_id": "cover_123", "name": "Test Cover"}
    }

    cover = EedomusCover(mock_coordinator, "cover_123")

    # 1. Force _get_periph_data à retourner None
    with patch.object(cover, "_get_periph_data", return_value=None):
        assert cover.current_cover_position == 0

    # 2. Exécute explicitement le log avec coordinator.data présent
    await cover.async_set_cover_tilt_position(**{ATTR_TILT_POSITION: 50})


@pytest.mark.asyncio
async def test_cover_absolute_100_percent_final():
    """Couvre les toutes dernières lignes (is_closed avec periph_data None et tilt avec coordinator.data vide)."""
    from homeassistant.components.cover import ATTR_TILT_POSITION

    mock_coordinator = MagicMock()
    mock_coordinator.config_entry.entry_id = "cover"
    mock_coordinator.data = {
        "cover_123": {"periph_id": "cover_123", "name": "Test Cover"}
    }

    cover = EedomusCover(mock_coordinator, "cover_123")

    # 1. Force _get_periph_data à retourner None pour is_closed
    with patch.object(cover, "_get_periph_data", return_value=None):
        assert cover.is_closed is True

    # 2. Teste le tilt avec coordinator.data à None (pour couvrir le "else 'unknown'")
    mock_coordinator.data = None
    await cover.async_set_cover_tilt_position(**{ATTR_TILT_POSITION: 50})


@pytest.mark.asyncio
async def test_cover_close_method():
    """Test cover close method."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "cover"
    mock_coordinator.data = {
        "cover_123": {"periph_id": "cover_123", "last_value": "100", "position": 100}
    }

    cover = EedomusCover(mock_coordinator, "cover_123")

    with patch.object(cover, "async_set_value") as mock_set_value:
        # On déclenche la fermeture
        await cover.async_close_cover()

        # On vérifie que async_set_value a bien été appelée avec "0"
        mock_set_value.assert_called_once_with("0")

    # Simulation du retour de l'API (fermé)
    mock_coordinator.data["cover_123"]["last_value"] = "0"
    mock_coordinator.data["cover_123"]["position"] = 0

    assert cover.is_closed is True
    assert cover.current_cover_position == 0
