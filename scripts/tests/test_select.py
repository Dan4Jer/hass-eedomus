"""Tests unitaires pour les entités select d'eedomus."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant

from custom_components.eedomus.const import COORDINATOR, DOMAIN
from custom_components.eedomus.select import EedomusSelect, async_setup_entry


@pytest.fixture
def mock_coordinator():
    """Fixture pour simuler le DataUpdateCoordinator eedomus."""
    coordinator = MagicMock()
    coordinator.config_entry.entry_id = "box_12345"
    coordinator.client = MagicMock()
    
    # Données simulées
    coordinator.data = {
        "100": {
            "name": "Radiateur",
            "last_value": "1",
            "ha_entity": "select",
            "values": [
                {"value": "0", "description": "Arrêt"},
                {"value": "1", "description": "Confort"},
                {"value": "2", "description": "Eco"}
            ],
            "periph_id": "100"
        },
        "200": {
            "name": "Select Sans Valeurs",
            "last_value": "0",
            "ha_entity": "select",
            # values est manquant délibérément pour tester le warning/skip
            "periph_id": "200"
        },
        "300": {
            "name": "Périphérique Non Mappé",
            "last_value": "1",
            "values": [{"value": "1", "description": "Auto"}],
            "periph_id": "300"
            # ha_entity manquant pour forcer le passage dans map_device_to_ha_entity
        },
        "400": {
            "name": "Select Format Simple",
            "last_value": "Texte1",
            "ha_entity": "select",
            "values": ["Texte1", "Texte2"],
            "periph_id": "400"
        }
    }
    
    # Simuler get_all_peripherals
    coordinator.get_all_peripherals.return_value = {
        k: v for k, v in coordinator.data.items()
    }
    
    return coordinator


async def test_async_setup_entry(hass: HomeAssistant, mock_coordinator):
    """Teste l'initialisation des entités select (inclusions, exclusions, mapping)."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    
    hass.data = {DOMAIN: {entry.entry_id: {COORDINATOR: mock_coordinator}}}
    
    async_add_entities = MagicMock()

    # Patch pour observer la passe 1 (mapping)
    with patch("custom_components.eedomus.select.map_device_to_ha_entity") as mock_map, \
         patch("custom_components.eedomus.select.register_device_mapping") as mock_register:
        
        # Simule le mapping manquant pour le périph '300'
        mock_map.return_value = {"ha_entity": "select", "mapped": True}
        
        await async_setup_entry(hass, entry, async_add_entities)

        # Vérifie que map_device_to_ha_entity a été appelé pour '300'
        mock_map.assert_called_once()
        mock_register.assert_called_once()
        
        # Vérifie que les entités ont été ajoutées
        # Devrait ajouter '100', '400' (et '300' suite au mock). '200' est ignoré car pas de values.
        assert async_add_entities.call_count == 1
        entities_added = async_add_entities.call_args[0][0]
        
        assert len(entities_added) == 3
        for entity in entities_added:
            assert isinstance(entity, EedomusSelect)
            assert entity._periph_id in ["100", "300", "400"]


async def test_select_properties(mock_coordinator):
    """Teste les différentes propriétés de l'entité EedomusSelect."""
    select_entity = EedomusSelect(mock_coordinator, "100")

    # Vérification héritage
    assert isinstance(select_entity, SelectEntity)

    # Vérification ID Unique
    assert select_entity.unique_id == "eedomus_box_12345_100_select"
    assert select_entity.name == "Radiateur"

    # Vérification des options disponibles
    assert select_entity.options == ["Arrêt", "Confort", "Eco"]

    # Vérification de l'option actuelle (last_value "1" correspond à "Confort")
    assert select_entity.current_option == "Confort"
    
    # Vérification de la disponibilité
    assert select_entity.available is True


async def test_select_options_fallback_formats(mock_coordinator):
    """Teste les propriétés options et current_option avec des formats exotiques."""
    # Test avec un format tableau simple (string list) au lieu de dictionnaire
    select_entity_simple = EedomusSelect(mock_coordinator, "400")
    assert select_entity_simple.options == ["Texte1", "Texte2"]
    assert select_entity_simple.current_option == "Texte1"

    # Cas où last_value ne matche aucune description
    mock_coordinator.data["100"]["last_value"] = "99"
    select_entity = EedomusSelect(mock_coordinator, "100")
    assert select_entity.current_option == "99" # Fallback sur la valeur brute

    # Cas de donnée vide
    mock_coordinator.data["100"]["last_value"] = ""
    select_entity = EedomusSelect(mock_coordinator, "100")
    assert select_entity.current_option is None
    assert select_entity.available is False


async def test_select_available_no_data(mock_coordinator):
    """Teste la disponibilité quand le coordinateur n'a pas/plus de données."""
    select_entity = EedomusSelect(mock_coordinator, "100")
    mock_coordinator.data = None
    
    assert select_entity.available is False
    assert select_entity.options == []


async def test_async_select_option_success(mock_coordinator):
    """Teste la sélection d'une option qui réussit."""
    mock_coordinator.client.set_periph_value = AsyncMock(return_value={"success": 1})
    mock_coordinator.async_request_refresh = AsyncMock()

    select_entity = EedomusSelect(mock_coordinator, "100")

    # On demande la description "Eco", le code doit envoyer la valeur "2" à l'API
    await select_entity.async_select_option("Eco")

    mock_coordinator.client.set_periph_value.assert_called_once_with("100", "2")
    mock_coordinator.async_request_refresh.assert_called_once()

async def test_async_select_option_raw_value(mock_coordinator):
    """Teste la sélection d'une option brute si non trouvée dans les descriptions."""
    # Mock des retours asynchrones
    mock_coordinator.client.set_periph_value = AsyncMock(return_value={"success": 1})
    mock_coordinator.async_request_refresh = AsyncMock()

    select_entity = EedomusSelect(mock_coordinator, "100")

    # On demande une option qui n'existe pas en tant que description
    await select_entity.async_select_option("ValeurBrute")

    # Il doit utiliser ce paramètre directement comme fallback
    mock_coordinator.client.set_periph_value.assert_called_once_with("100", "ValeurBrute")
    # Vérification que le rafraîchissement a bien été appelé suite au succès
    mock_coordinator.async_request_refresh.assert_called_once()

async def test_async_select_option_failure(mock_coordinator):
    """Teste l'échec de la sélection via l'API (success = 0)."""
    mock_coordinator.client.set_periph_value = AsyncMock(return_value={"success": 0, "error": "Invalid API"})
    mock_coordinator.async_request_refresh = AsyncMock()

    select_entity = EedomusSelect(mock_coordinator, "100")

    await select_entity.async_select_option("Eco")

    # La valeur est envoyée mais le refresh ne doit pas être appelé en cas d'erreur API
    mock_coordinator.client.set_periph_value.assert_called_once_with("100", "2")
    mock_coordinator.async_request_refresh.assert_not_called()


async def test_async_select_option_exception(mock_coordinator):
    """Teste la gestion d'une exception lors d'un appel réseau défaillant."""
    mock_coordinator.client.set_periph_value = AsyncMock(side_effect=Exception("Timeout réseau"))
    
    select_entity = EedomusSelect(mock_coordinator, "100")

    with pytest.raises(Exception, match="Timeout réseau"):
        await select_entity.async_select_option("Eco")


async def test_async_update(mock_coordinator):
    """Teste la mise à jour de l'entité depuis le coordinateur."""
    select_entity = EedomusSelect(mock_coordinator, "100")
    assert select_entity._attr_current_option == "1"

    # Simulation d'une mise à jour de la box
    mock_coordinator.data["100"]["last_value"] = "0"
    
    with patch("custom_components.eedomus.entity.EedomusEntity.async_update", new_callable=AsyncMock):
        await select_entity.async_update()
        
    assert select_entity._attr_current_option == "0"

@pytest.mark.asyncio
async def test_select_options_edge_cases():
    """Cover select.py lines 110 and 121-122: empty values and fallback to value when description is empty."""
    from custom_components.eedomus.select import EedomusSelect

    coordinator = MagicMock()
    device_info = MagicMock()

    # Instanciation avec les 2 arguments requis (coordinator et device_info)
    select_entity = EedomusSelect(coordinator, device_info)
    # On force l'identifiant pour qu'il corresponde à notre dictionnaire de test
    select_entity._periph_id = "12345"

    # 1. Cible la ligne 110 : values_data est une liste vide []
    coordinator.data = {
        "12345": {
            "values": []
        }
    }
    assert select_entity.options == []

    # 2. Cible les lignes 121-122 : description vide, mais value présente
    coordinator.data = {
        "12345": {
            "values": [
                {"value": "fallback_value", "description": ""}
            ]
        }
    }
    assert select_entity.options == ["fallback_value"]

@pytest.mark.asyncio
async def test_select_setup_entry_skip_non_select(hass):
    """Cover select.py line 42: skip peripherals where ha_entity is not 'select'."""
    from custom_components.eedomus.select import async_setup_entry
    from custom_components.eedomus.const import DOMAIN, COORDINATOR

    hass.data = {DOMAIN: {"test_entry": {COORDINATOR: MagicMock()}}}
    coordinator = hass.data[DOMAIN]["test_entry"][COORDINATOR]
    
    peripherals_data = {
        "periph_sensor": {
            "name": "Temperature Sensor",
            "values": [{"value": "20", "description": "20°C"}]
        },
        "periph_select": {
            "name": "My Select",
            "values": [{"value": "1", "description": "Option 1"}]
        }
    }
    
    coordinator.get_all_peripherals.return_value = peripherals_data
    
    # On ajoute bien le "name" attendu dans coordinator.data pour éviter le KeyError
    coordinator.data = {
        "periph_sensor": {"ha_entity": "sensor"},
        "periph_select": {"ha_entity": "select", "name": "My Select"}
    }
    
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    async_add_entities = MagicMock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()


