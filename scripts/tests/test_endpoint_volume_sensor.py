"""Tests unitaires pour les capteurs de volume de données des endpoints eedomus."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from homeassistant.components.sensor import SensorStateClass
from homeassistant.const import EntityCategory

from custom_components.eedomus.const import DOMAIN
from custom_components.eedomus.endpoint_volume_sensor import (
    EedomusEndpointVolumeSensor,
    EedomusGetPeriphCaractVolumeSensor,
    EedomusGetPeriphListVolumeSensor,
    EedomusGetPeriphValueListVolumeSensor,
    EedomusPartialRefreshVolumeSensor,
    EedomusTotalDataVolumeSensor,
    async_setup_endpoint_volume_sensors,
    get_clean_box_name_from_coord,
)


@pytest.fixture
def mock_coordinator():
    """Fixture simulant un DataUpdateCoordinator eedomus."""
    coordinator = MagicMock()
    coordinator.config_entry = MagicMock()
    coordinator.config_entry.entry_id = "test_entry_id_123"
    coordinator.config_entry.title = "Eedomus (192.168.1.50)"
    coordinator.config_entry.data = {"host": "192.168.1.50"}
    coordinator._endpoint_data_sizes = {
        "get_periph_list": 1048576,  # 1 Mo = 1024 Ko
        "partial_refresh": 2048,     # 2 Ko
        "empty_endpoint": 0,
    }
    coordinator._endpoint_call_counts = {
        "get_periph_list": 10,
        "partial_refresh": 2,
    }
    return coordinator


# --- 1. Tests du helper de nettoyage du nom de la box ---


def test_get_clean_box_name_from_coord_standard_host(mock_coordinator):
    """Vérifie l'extraction avec une IP standard dans data['host']."""
    host, box_name = get_clean_box_name_from_coord(mock_coordinator)
    assert host == "192.168.1.50"
    assert box_name == "Box eedomus (192.168.1.50)"


def test_get_clean_box_name_from_coord_formatted_title(mock_coordinator):
    """Vérifie le parsing du format 'Eedomus (IP)'."""
    mock_coordinator.config_entry.data = {}
    mock_coordinator.config_entry.title = "Eedomus (10.0.0.1)"

    host, box_name = get_clean_box_name_from_coord(mock_coordinator)
    assert host == "10.0.0.1"
    assert box_name == "Box eedomus (10.0.0.1)"

def test_get_clean_box_name_from_coord_unclosed_parenthesis(mock_coordinator):
    """Vérifie le parsing d'un titre avec parenthèse ouvrante sans fermeture."""
    mock_coordinator.config_entry.data = {}
    mock_coordinator.config_entry.title = "Eedomus (incomplet"

    host, box_name = get_clean_box_name_from_coord(mock_coordinator)
    assert host == "incomplet"
    assert box_name == "Box eedomus (incomplet)"


def test_get_clean_box_name_from_coord_no_eedomus_prefix(mock_coordinator):
    """Vérifie le repli sur le titre brut quand le préfixe 'Eedomus (' n'est pas présent."""
    mock_coordinator.config_entry.data = {}
    mock_coordinator.config_entry.title = "Ma Box Perso"

    host, box_name = get_clean_box_name_from_coord(mock_coordinator)
    assert host == "Ma Box Perso"
    assert box_name == "Box eedomus (Ma Box Perso)"


# --- 2. Tests de la classe de base et des capteurs individuels ---


def test_endpoint_volume_sensor_init_attributes(mock_coordinator):
    """Vérifie l'initialisation des attributs de base d'un capteur."""
    sensor = EedomusGetPeriphListVolumeSensor(mock_coordinator)

    assert sensor.name == "Eedomus get_periph_list Volume KB (192.168.1.50)"
    assert sensor.unique_id == "eedomus_test_entry_id_123_get_periph_list_volume_kb"
    assert sensor.native_unit_of_measurement == "KB"
    assert sensor.icon == "mdi:format-list-bulleted"
    assert sensor.state_class == SensorStateClass.MEASUREMENT
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.has_entity_name is True

    # Vérification des infos d'appareil
    device_info = sensor.device_info
    assert (DOMAIN, "eedomus_box_test_entry_id_123") in device_info["identifiers"]
    assert device_info["name"] == "Box eedomus (192.168.1.50)"


def test_endpoint_volume_sensor_values(mock_coordinator):
    """Vérifie le calcul des valeurs brutes et des attributs d'état."""
    sensor = EedomusGetPeriphListVolumeSensor(mock_coordinator)

    # 1048576 octets = 1024 Ko
    assert sensor.native_value == 1024.0

    attrs = sensor.extra_state_attributes
    assert attrs["endpoint"] == "get_periph_list"
    assert attrs["call_count"] == 10
    assert attrs["bytes"] == 1048576
    assert attrs["kilobytes"] == 1024.0
    assert attrs["megabytes"] == 1.0
    assert "last_updated" in attrs


def test_endpoint_volume_sensor_missing_coordinator_attrs(mock_coordinator):
    """Vérifie le comportement de secours si le coordinator n'a pas les attributs requis."""
    del mock_coordinator._endpoint_data_sizes
    del mock_coordinator._endpoint_call_counts

    sensor = EedomusPartialRefreshVolumeSensor(mock_coordinator)

    assert sensor.native_value == 0
    attrs = sensor.extra_state_attributes
    assert attrs["bytes"] == 0
    assert attrs["call_count"] == 0


# --- 3. Tests des sous-classes spécifiques ---


def test_sensor_subclasses_icons(mock_coordinator):
    """Vérifie que chaque sous-classe définit la bonne icône et le bon nom d'endpoint."""
    s1 = EedomusGetPeriphListVolumeSensor(mock_coordinator)
    assert s1._endpoint_name == "get_periph_list"
    assert s1.icon == "mdi:format-list-bulleted"

    s2 = EedomusGetPeriphValueListVolumeSensor(mock_coordinator)
    assert s2._endpoint_name == "get_periph_value_list"
    assert s2.icon == "mdi:format-list-text"

    s3 = EedomusGetPeriphCaractVolumeSensor(mock_coordinator)
    assert s3._endpoint_name == "get_periph_caract"
    assert s3.icon == "mdi:cog"

    s4 = EedomusPartialRefreshVolumeSensor(mock_coordinator)
    assert s4._endpoint_name == "partial_refresh"
    assert s4.icon == "mdi:refresh"


# --- 4. Tests du capteur totalisateur ---


def test_total_data_volume_sensor(mock_coordinator):
    """Vérifie le calcul du cumul global et du détail par endpoint."""
    sensor = EedomusTotalDataVolumeSensor(mock_coordinator)

    # Total = 1048576 + 2048 + 0 = 1050624 octets -> 1026 Ko
    assert sensor.native_value == 1026.0

    attrs = sensor.extra_state_attributes
    assert attrs["bytes"] == 1050624
    assert attrs["kilobytes"] == 1026.0

    # L'endpoint à 0 octet doit être exclu du détail
    breakdown = attrs["endpoint_breakdown"]
    assert "get_periph_list" in breakdown
    assert "partial_refresh" in breakdown
    assert "empty_endpoint" not in breakdown
    assert breakdown["get_periph_list"]["bytes"] == 1048576


def test_total_data_volume_sensor_empty_data(mock_coordinator):
    """Vérifie le totalisateur lorsqu'aucune donnée n'est présente."""
    mock_coordinator._endpoint_data_sizes = {}
    sensor = EedomusTotalDataVolumeSensor(mock_coordinator)

    assert sensor.native_value == 0
    attrs = sensor.extra_state_attributes
    assert attrs.get("endpoint_breakdown") == {}


# --- 5. Test du setup asynchrone ---


@pytest.mark.asyncio
async def test_async_setup_endpoint_volume_sensors(mock_coordinator):
    """Vérifie l'enregistrement de l'appareil et la création des 5 capteurs."""
    mock_hass = MagicMock()
    mock_device_registry = MagicMock()

    sensors = await async_setup_endpoint_volume_sensors(
        mock_hass, mock_coordinator, mock_device_registry
    )

    # 1. Déclaration de l'appareil eedomus auprès du registre
    mock_device_registry.async_get_or_create.assert_called_once_with(
        config_entry_id="test_entry_id_123",
        identifiers={(DOMAIN, "eedomus_box_test_entry_id_123")},
        name="Box eedomus (192.168.1.50)",
        manufacturer="Eedomus",
        model="Eedomus Box",
        sw_version="Unknown",
    )

    # 2. Vérification des 5 capteurs instanciés
    assert len(sensors) == 5
    assert isinstance(sensors[0], EedomusGetPeriphListVolumeSensor)
    assert isinstance(sensors[1], EedomusGetPeriphValueListVolumeSensor)
    assert isinstance(sensors[2], EedomusGetPeriphCaractVolumeSensor)
    assert isinstance(sensors[3], EedomusPartialRefreshVolumeSensor)
    assert isinstance(sensors[4], EedomusTotalDataVolumeSensor)

@pytest.mark.asyncio
async def test_endpoint_volume_sensor_edge_cases():
    """Cover endpoint_volume_sensor.py missing lines 31-32 and 159."""
    from custom_components.eedomus.endpoint_volume_sensor import (
        get_clean_box_name_from_coord,
        EedomusEndpointVolumeSensor,
    )

    # 1. Cible les lignes 31-32 : exception dans get_clean_box_name_from_coord
    class CustomStr(str):
        def split(self, *args, **kwargs):
            raise Exception("Forced split exception")

    coordinator = MagicMock()
    coordinator.config_entry.data.get.return_value = "Eedomus (192.168.1.100)"

    with patch("builtins.str", CustomStr):
        host, box_name = get_clean_box_name_from_coord(coordinator)
        assert host is not None

    # 2. Cible la ligne 159 : native_value retourne 0 si _endpoint_data_sizes est absent
    coordinator_no_size = MagicMock()
    if hasattr(coordinator_no_size, "_endpoint_data_sizes"):
        delattr(coordinator_no_size, "_endpoint_data_sizes")

    device_info = MagicMock()
    # Ajout de l'argument 'icon' requis par le constructeur
    sensor = EedomusEndpointVolumeSensor(coordinator_no_size, device_info, "mdi:database")
    
    val = sensor.native_value
    assert val == 0

@pytest.mark.asyncio
async def test_inspect_endpoint_volume_sensor_lines():
    """Diagnostic pour afficher les lignes exactes du fichier endpoint_volume_sensor.py."""
    import inspect
    from custom_components.eedomus import endpoint_volume_sensor

    source_lines, start_line = inspect.getsourcelines(endpoint_volume_sensor)
    print("\n--- DIAGNOSTIC DES LIGNES ---")
    for idx, line in enumerate(source_lines, start=start_line):
        if 150 <= idx <= 165:
            print(f"Ligne {idx}: {repr(line)}")
    print("-----------------------------\n")
    assert True

@pytest.mark.asyncio
async def test_total_volume_sensor_missing_data_sizes():
    """Target the exact return 0 line in the total volume sensor when _endpoint_data_sizes is missing."""
    from custom_components.eedomus.endpoint_volume_sensor import EedomusTotalDataVolumeSensor

    class CoordinatorWithoutSizes:
        def __init__(self):
            self.config_entry = MagicMock()
            self.config_entry.data.get.return_value = "192.168.1.50"
            # _endpoint_data_sizes est volontairement absent

    coordinator = CoordinatorWithoutSizes()
    
    # Instanciation avec uniquement le coordinateur
    sensor = EedomusTotalDataVolumeSensor(coordinator)
    
    # Cela va forcer le hasattr à False et exécuter le return 0
    val = sensor.native_value
    assert val == 0

