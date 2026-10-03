"""Tests unitaires pour le chargement et la fusion des configurations YAML dans device_mapping."""

from unittest.mock import mock_open, patch
import pytest

from custom_components.eedomus.device_mapping import (
    load_and_merge_yaml_mappings,
    load_custom_yaml_mappings,
    load_yaml_file,
    merge_yaml_mappings,
)


# --- 1. Tests de chargement de fichier YAML ---

def test_load_yaml_file_success():
    """Vérifie le chargement réussi d'un fichier YAML valide."""
    fake_yaml_content = """
    usage_mappings:
      "1":
        ha_entity: "switch"
    """
    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", mock_open(read_data=fake_yaml_content)
    ):
        content = load_yaml_file("/fake/path/config.yaml")
        assert content is not None
        assert "usage_mappings" in content
        assert content["usage_mappings"]["1"]["ha_entity"] == "switch"


def test_load_yaml_file_not_found():
    """Vérifie qu'un fichier inexistant retourne None sans faire crasher l'intégration."""
    with patch("os.path.exists", return_value=False):
        content = load_yaml_file("/path/does_not_exist.yaml")
        assert content is None


# --- 2. Tests de fusion des Mappings (Merge) ---

def test_merge_yaml_mappings_with_custom_overrides():
    """Vérifie que custom_specific_device_dynamic_overrides surcharge correctement la configuration de base."""
    base_mappings = {
        "usage_mappings": {"1": {"ha_entity": "switch"}},
        "dynamic_entity_properties": {"climate": {}},
        "specific_device_dynamic_overrides": {
            "111111": {"ha_entity": "light"},
            "3463520": {"ha_entity": "switch"},  # Doit être écrasé par le custom
        },
    }

    custom_mappings = {
        "custom_specific_device_dynamic_overrides": {
            "3463520": {
                "ha_entity": "climate",
                "ha_subtype": "thermostat",
                "icon": "mdi:thermostat",
            }
        },
    }

    merged = merge_yaml_mappings(base_mappings, custom_mappings)

    # Clé finale fusionnée
    assert "specific_device_dynamic_overrides" in merged
    assert "111111" in merged["specific_device_dynamic_overrides"]
    
    # Vérification que le device 111111 conserve son état base
    assert merged["specific_device_dynamic_overrides"]["111111"]["ha_entity"] == "light"

    # Vérification que le device 3463520 a bien été surchargé par le custom
    assert merged["specific_device_dynamic_overrides"]["3463520"]["ha_entity"] == "climate"
    assert merged["specific_device_dynamic_overrides"]["3463520"]["ha_subtype"] == "thermostat"


# --- 3. Tests de chargement global ---
def test_load_and_merge_yaml_mappings():
    """Vérifie le pipeline complet de chargement et fusion."""
    mock_base = {
        "usage_id_mappings": {"1": {"ha_entity": "switch"}},
        "dynamic_entity_properties": {"switch": {}},
        "specific_device_dynamic_overrides": {},
    }
    mock_custom = {
        "custom_specific_device_dynamic_overrides": {
            "3463520": {"ha_entity": "climate"}
        }
    }

    def mock_load_yaml(filepath):
        filepath_str = str(filepath)
        if "custom_mapping.yaml" in filepath_str:
            return mock_custom
        return mock_base

    with patch("os.path.exists", return_value=True), patch(
        "custom_components.eedomus.device_mapping.load_yaml_file",
        side_effect=mock_load_yaml,
    ):
        result = load_and_merge_yaml_mappings()

        assert "usage_id_mappings" in result
        assert "specific_device_dynamic_overrides" in result
        assert (
            result["specific_device_dynamic_overrides"]["3463520"]["ha_entity"]
            == "climate"
        )

