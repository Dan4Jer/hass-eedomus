"""Tests unitaires pour le registre de mapping eedomus."""

import logging
from unittest.mock import patch

import pytest

from custom_components.eedomus.mapping_registry import (
    _MAPPING_REGISTRY,
    clear_mapping_registry,
    get_mapping_registry,
    print_mapping_summary,
    print_mapping_table,
    register_device_mapping,
)


@pytest.fixture(autouse=True)
def reset_registry():
    """Fixture réinitialisant le registre global avant et après chaque test."""
    clear_mapping_registry()
    yield
    clear_mapping_registry()


# --- 1. Tests d'enregistrement (register_device_mapping) ---


def test_register_device_mapping_minimal():
    """Vérifie l'enregistrement d'un mapping minimal sans device_data ni justification."""
    mapping = {"ha_entity": "light", "ha_subtype": "dimmer"}

    register_device_mapping(mapping, "Lampe Salon", "1001")

    registry = get_mapping_registry()
    assert len(registry) == 1
    assert registry[0] == {
        "periph_id": "1001",
        "periph_name": "Lampe Salon",
        "parent_periph_id": None,
        "ha_entity": "light",
        "ha_subtype": "dimmer",
        "justification": "No justification provided",
    }


def test_register_device_mapping_complete():
    """Vérifie l'enregistrement complet avec device_data et justification personnalisée."""
    mapping = {
        "ha_entity": "switch",
        "ha_subtype": "outlet",
        "justification": "Détecté par usage_id 2",
    }
    device_data = {"parent_periph_id": "2000", "usage_id": "2"}

    register_device_mapping(mapping, "Prise Cuisine", "1002", device_data)

    registry = get_mapping_registry()
    assert len(registry) == 1
    assert registry[0]["parent_periph_id"] == "2000"
    assert registry[0]["justification"] == "Détecté par usage_id 2"


# --- 2. Tests de réinitialisation et de copie ---


def test_clear_mapping_registry():
    """Vérifie le vidage du registre."""
    mapping = {"ha_entity": "sensor", "ha_subtype": "temperature"}
    register_device_mapping(mapping, "Capteur", "1003")

    assert len(get_mapping_registry()) == 1
    clear_mapping_registry()
    assert len(get_mapping_registry()) == 0


def test_get_mapping_registry_returns_copy():
    """Vérifie que get_mapping_registry retourne une copie indépendante."""
    mapping = {"ha_entity": "sensor", "ha_subtype": "temperature"}
    register_device_mapping(mapping, "Capteur", "1003")

    registry_copy = get_mapping_registry()
    registry_copy.clear()  # Modification de la copie

    assert len(get_mapping_registry()) == 1  # L'original doit rester intact


# --- 3. Tests de print_mapping_table ---


def test_print_mapping_table_empty(caplog):
    """Vérifie le message d'avertissement lorsque le registre est vide."""
    with caplog.at_level(logging.WARNING):
        print_mapping_table()
        assert "Mapping registry is empty" in caplog.text


def test_print_mapping_table_populated(caplog):
    """Vérifie l'affichage du tableau avec formatage et troncature des chaînes longues."""
    mapping_short = {
        "ha_entity": "light",
        "ha_subtype": "binary",
        "justification": "Court",
    }
    mapping_long = {
        "ha_entity": "sensor",
        "ha_subtype": "humidity",
        "justification": "Une justification extrêmement longue qui dépasse la limite imposée par le formateur",
    }

    register_device_mapping(mapping_short, "Lampe", "101")
    register_device_mapping(
        mapping_long,
        "Nom de périphérique extrêmement long qui doit être tronqué",
        "102",
        {"parent_periph_id": "101"},
    )

    with caplog.at_level(logging.INFO):
        print_mapping_table()

        assert "Periph ID" in caplog.text
        assert "Total devices mapped: 2" in caplog.text
        assert "101" in caplog.text
        assert "102" in caplog.text
        # Vérification de la troncature aux 29 premiers caractères
        assert "Nom de périphérique extrêmeme" in caplog.text


# --- 4. Tests de print_mapping_summary ---


def test_print_mapping_summary_empty(caplog):
    """Vérifie le comportement de print_mapping_summary avec un registre vide."""
    with caplog.at_level(logging.WARNING):
        print_mapping_summary()
        assert "Mapping registry is empty" in caplog.text


def test_print_mapping_summary_populated(caplog):
    """Vérifie la génération du résumé condensé des mappings par types d'entités."""
    register_device_mapping(
        {"ha_entity": "light", "ha_subtype": "dimmer"}, "Lampe 1", "101"
    )
    register_device_mapping(
        {"ha_entity": "light", "ha_subtype": "dimmer"}, "Lampe 2", "102"
    )
    register_device_mapping(
        {"ha_entity": "switch", "ha_subtype": "outlet"}, "Prise 1", "103"
    )

    with caplog.at_level(logging.DEBUG):
        print_mapping_summary()

        assert "Eedomus mapping: (Box eedomus) 3 devices" in caplog.text
        assert "2 light:dimmer" in caplog.text
        assert "1 switch:outlet" in caplog.text
        assert "Total unique periph_ids: (Box eedomus) 3" in caplog.text
