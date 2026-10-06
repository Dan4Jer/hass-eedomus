"""Tests unitaires dédiés pour le module text_sensor.py."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.eedomus.const import COORDINATOR, DOMAIN
from custom_components.eedomus.text_sensor import EedomusTextSensor, async_setup_entry


@pytest.mark.asyncio
async def test_text_sensor_dynamic_mapping():
    """Test que le capteur textuel mappe correctement les valeurs brutes vers les descriptions."""
    mock_coordinator = AsyncMock()
    mock_coordinator.config_entry.entry_id = "box_123"
    mock_coordinator.data = {
        "text_periph": {
            "periph_id": "text_periph",
            "name": "Mode Chauffage",
            "last_value": "1",
            "entity_specifics": {"value_mapping": "dynamic_from_values"},
            "values": [
                {"value": "0", "description": "Éteint"},
                {"value": "1", "description": "Confort"},
                {"value": "2", "description": "Eco"},
            ],
        }
    }

    sensor = EedomusTextSensor(mock_coordinator, "text_periph")

    # Vérification que le device_class est bien "enum" pour les capteurs textuels
    assert sensor.device_class == "enum"

    # Vérification de la conversion dynamique de la valeur
    assert sensor.native_value == "Confort"

    # Test d'une valeur absente du dictionnaire de correspondance (fallback "Unknown")
    mock_coordinator.data["text_periph"]["last_value"] = "99"
    assert sensor.native_value == "Unknown (99)"


@pytest.mark.asyncio
async def test_text_sensor_extra_attributes_and_icons():
    """Test des attributs additionnels et de la gestion des icônes dynamiques[cite: 2]."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "text_periph": {
            "periph_id": "text_periph",
            "name": "Alarme",
            "last_value": "armed",
            "entity_specifics": {
                "value_mapping": "dynamic_from_values",
                "value_icons": {
                    "armed": "mdi:shield-lock",
                    "disarmed": "mdi:shield-outline",
                },
            },
            "values": [
                {"value": "armed", "description": "Armée"},
                {"value": "disarmed", "description": "Désarmée"},
            ],
        }
    }

    sensor = EedomusTextSensor(mock_coordinator, "text_periph")

    # Vérification de l'attribution de l'icône dynamique selon la valeur courante[cite: 2]
    assert sensor.icon == "mdi:shield-lock"

    # Vérification des attributs d'état enrichis[cite: 2]
    attrs = sensor.extra_state_attributes
    assert attrs is not None
    assert attrs["current_raw_value"] == "armed"
    assert attrs["available_values"] == {"armed": "Armée", "disarmed": "Désarmée"}


@pytest.mark.asyncio
async def test_text_sensor_non_dynamic_fallback():
    """Test du comportement lorsque le capteur textuel n'utilise pas le mapping dynamique[cite: 2]."""
    mock_coordinator = AsyncMock()
    mock_coordinator.data = {
        "text_periph": {
            "periph_id": "text_periph",
            "name": "Message Libre",
            "last_value": "Texte brut direct",
            "entity_specifics": {},  # Pas de mapping dynamique
        }
    }

    sensor = EedomusTextSensor(mock_coordinator, "text_periph")

    # Doit retourner la valeur brute directement sans transformation[cite: 2]
    assert sensor.native_value == "Texte brut direct"
    assert sensor.extra_state_attributes is None


@pytest.mark.asyncio
async def test_text_sensor_async_setup_entry():
    """Test de l'enregistrement de l'entrée de la plateforme text_sensor (async_setup_entry)."""
    hass = MagicMock()
    config_entry = MagicMock()
    config_entry.entry_id = "box_123"

    mock_coordinator = MagicMock()
    mock_coordinator.get_all_peripherals.return_value = {
        "text_periph": {
            "periph_id": "text_periph",
            "name": "Capteur Texte",
            "ha_entity": "sensor",
            "ha_subtype": "text",
            "entity_specifics": {"value_mapping": "dynamic_from_values"},
        }
    }

    hass.data = {DOMAIN: {"box_123": {COORDINATOR: mock_coordinator}}}

    added_entities = []

    # ✅ CORRECTION : Une fonction classique (synchrone) car async_add_entities n'est pas awaité
    def mock_add_entities(entities):
        added_entities.extend(entities)

    result = await async_setup_entry(hass, config_entry, mock_add_entities)

    assert result is True
    assert len(added_entities) == 1
    assert isinstance(added_entities[0], EedomusTextSensor)


# ============


from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eedomus.const import COORDINATOR, DOMAIN
from custom_components.eedomus.text_sensor import EedomusTextSensor, async_setup_entry


async def test_text_sensor_setup_missing_coordinator(hass: HomeAssistant):
    """Vérifie que la configuration échoue si le coordinateur est absent."""
    entry = MockConfigEntry(domain=DOMAIN, data={"api_host": "192.168.1.50"})
    entry.add_to_hass(hass)

    async_add_entities = MagicMock()
    assert await async_setup_entry(hass, entry, async_add_entities) is False


async def test_text_sensor_setup_no_entities(hass: HomeAssistant):
    """Vérifie le comportement si aucun périphérique textuel n'est trouvé."""
    coordinator = MagicMock()
    coordinator.get_all_peripherals.return_value = {}

    entry = MockConfigEntry(domain=DOMAIN, data={"api_host": "192.168.1.50"})
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {COORDINATOR: coordinator}

    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_not_called()


async def test_text_sensor_setup_with_dynamic_mapping(hass: HomeAssistant):
    """Vérifie qu'un capteur texte avec mapping dynamique est correctement ajouté."""
    coordinator = MagicMock()
    coordinator.get_all_peripherals.return_value = {
        "123": {
            "ha_entity": "sensor",
            "ha_subtype": "text",
            "entity_specifics": {"value_mapping": "dynamic_from_values"},
            "name": "Test Sensor",
        }
    }
    entry = MockConfigEntry(domain=DOMAIN, data={"api_host": "192.168.1.50"})
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {COORDINATOR: coordinator}

    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_called_once()


async def test_text_sensor_native_value_and_attributes(hass: HomeAssistant):
    """Vérifie les différentes valeurs et attributs du capteur texte."""
    coordinator = MagicMock()
    sensor = EedomusTextSensor(coordinator, "123")

    # 1. Données absentes (None)
    sensor._get_periph_data = MagicMock(return_value=None)
    assert sensor.native_value is None
    assert sensor.extra_state_attributes is None

    # 2. Valeur avec mapping dynamique valide
    sensor._get_periph_data = MagicMock(
        return_value={
            "last_value": "1",
            "values": [{"value": "1", "description": "Active"}],
        }
    )
    sensor._dynamic_value_mapping = True
    assert sensor.native_value == "Active"

    attrs = sensor.extra_state_attributes
    assert attrs["current_raw_value"] == "1"
    assert attrs["available_values"]["1"] == "Active"

    # 3. Exception dans le mapping dynamique (ex: values non itérable)
    sensor._get_periph_data = MagicMock(
        return_value={"last_value": "1", "values": "invalid_structure"}
    )
    assert "Error" in str(sensor.native_value)

    # 4. Mode sans mapping dynamique (retourne last_value_text ou last_value)
    sensor._dynamic_value_mapping = False
    sensor._get_periph_data = MagicMock(
        return_value={"last_value": "raw_val", "last_value_text": "text_val"}
    )
    assert sensor.native_value == "text_val"


async def test_text_sensor_icon_and_device_class(hass: HomeAssistant):
    """Vérifie la gestion des icônes et de la classe de l'appareil."""
    coordinator = MagicMock()
    sensor = EedomusTextSensor(coordinator, "123")

    # Données absentes -> icon None
    sensor._get_periph_data = MagicMock(return_value=None)
    assert sensor.icon is None

    # Icône de type /img/mdm/
    sensor._get_periph_data = MagicMock(return_value={"icon": "/img/mdm/test.png"})
    assert sensor.icon == "mdi:calendar-text"

    # Fallback icône par défaut (dictionnaire non vide)
    sensor._get_periph_data = MagicMock(return_value={"entity_specifics": {}})
    assert sensor.icon == "mdi:text"

    # Device class
    assert sensor.device_class == "enum"


async def test_text_sensor_setup_non_dynamic_logging(hass: HomeAssistant):
    """Couvre la ligne 193 (log de debug pour un capteur texte sans mapping dynamique)."""
    coordinator = MagicMock()
    coordinator.get_all_peripherals.return_value = {
        "456": {
            "ha_entity": "sensor",
            "ha_subtype": "text",
            "entity_specifics": {"value_mapping": "standard"},
        }
    }
    entry = MockConfigEntry(domain=DOMAIN, data={"api_host": "192.168.1.50"})
    entry.add_to_hass(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {COORDINATOR: coordinator}

    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)
    async_add_entities.assert_not_called()


async def test_text_sensor_init_without_data(hass: HomeAssistant):
    """Couvre la ligne 50 (initialisation sans données ou sans mapping dynamique)."""
    coordinator = MagicMock()
    coordinator.get_all_peripherals.return_value = {}
    sensor = EedomusTextSensor(coordinator, "999")
    assert sensor._dynamic_value_mapping is False


async def test_text_sensor_native_value_no_match(hass: HomeAssistant):
    """Couvre la ligne 117 (valeur dynamique non trouvée dans la liste)."""
    coordinator = MagicMock()
    sensor = EedomusTextSensor(coordinator, "123")
    sensor._dynamic_value_mapping = True
    sensor._get_periph_data = MagicMock(
        return_value={
            "last_value": "99",
            "values": [{"value": "1", "description": "Active"}],
        }
    )
    assert sensor.native_value == "Unknown (99)"


async def test_text_sensor_icon_static_and_exception(hass: HomeAssistant):
    """Vérifie l'icône statique et la gestion des exceptions dans value_icons."""
    coordinator = MagicMock()
    sensor = EedomusTextSensor(coordinator, "123")

    # 1. Icône statique dans entity_specifics
    sensor._get_periph_data = MagicMock(
        return_value={"entity_specifics": {"icon": "mdi:custom-static"}}
    )
    assert sensor.icon == "mdi:custom-static"

    # 2. Exception dans value_icons (couvre le bloc except ValueError, TypeError)
    bad_value_icons = MagicMock()
    bad_value_icons.get.side_effect = TypeError("Simulated type error")
    sensor._get_periph_data = MagicMock(
        return_value={
            "entity_specifics": {
                "value_icons": bad_value_icons,
                "icon": "mdi:fallback-icon",
            },
            "last_value": "1",
        }
    )
    assert sensor.icon == "mdi:fallback-icon"


async def test_text_sensor_init_periph_data_none(hass: HomeAssistant):
    """Couvre la ligne 50 : __init__ lorsque _get_periph_data renvoie None."""
    coordinator = MagicMock()
    # On fait en sorte que _get_periph_data renvoie None lors de l'initialisation
    with patch(
        "custom_components.eedomus.text_sensor.EedomusTextSensor._get_periph_data",
        return_value=None,
    ):
        sensor = EedomusTextSensor(coordinator, "999")
        assert sensor._dynamic_value_mapping is False


async def test_text_sensor_native_value_dynamic_without_values_key(hass: HomeAssistant):
    """Couvre la ligne 117 : dynamic_value_mapping à True mais absence de la clé 'values'."""
    coordinator = MagicMock()
    sensor = EedomusTextSensor(coordinator, "123")
    sensor._dynamic_value_mapping = True
    # Données avec last_value mais sans la clé "values"
    sensor._get_periph_data = MagicMock(return_value={"last_value": "raw_fallback"})
    # Selon votre code, s'il n'y a pas de "values", il va chuter vers le retour standard ou last_value
    assert sensor.native_value == "raw_fallback"


async def test_text_sensor_extra_state_attributes_no_values(hass: HomeAssistant):
    """Couvre la ligne 117 : extra_state_attributes retourne None si la liste values est vide."""
    coordinator = MagicMock()
    sensor = EedomusTextSensor(coordinator, "123")
    sensor._dynamic_value_mapping = True
    sensor._get_periph_data = MagicMock(return_value={"last_value": "1", "values": []})
    assert sensor.extra_state_attributes is None
