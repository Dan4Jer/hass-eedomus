"""Tests unitaires pour le moteur de règles de mapping eedomus."""

import logging

import pytest

from custom_components.eedomus.mapping_rules import evaluate_conditions


@pytest.fixture
def sample_devices():
    """Fixture fournissant un jeu de données de périphériques."""
    return {
        "100": {"usage_id": 1, "name": "Box Parent", "PRODUCT_TYPE_ID": 10},
        "101": {
            "usage_id": 2,
            "name": "Capteur Température Salon",
            "parent_periph_id": "100",
            "PRODUCT_TYPE_ID": 11,
        },
        "102": {
            "usage_id": 3,
            "name": "Capteur Humidité Salon",
            "parent_periph_id": "100",
            "PRODUCT_TYPE_ID": 12,
        },
        "200": {"usage_id": 1, "name": "Autre Parent"},
        "201": {
            "usage_id": 2,
            "name": "Détecteur Mouvement",
            "parent_periph_id": "200",
        },
    }


# --- 1. Condition : usage_id ---


def test_condition_usage_id_success():
    """Vérifie le succès de la condition usage_id."""
    conditions = [{"usage_id": 1}]
    device = {"usage_id": 1}
    assert evaluate_conditions(conditions, device, {}, "100", "rule_test") is True


def test_condition_usage_id_failure():
    """Vérifie l'échec de la condition usage_id."""
    conditions = [{"usage_id": 1}]
    device = {"usage_id": 2}
    assert evaluate_conditions(conditions, device, {}, "100", "rule_test") is False


# --- 2. Condition : min_children ---


def test_condition_min_children_no_all_devices():
    """Vérifie l'échec si all_devices est vide."""
    conditions = [{"min_children": 1}]
    assert evaluate_conditions(conditions, {}, {}, "100", "rule_test") is False


def test_condition_min_children_with_relations(sample_devices):
    """Vérifie min_children en utilisant parent_child_relations."""
    conditions = [{"min_children": 2}]
    relations = {"100": ["101", "102"]}

    # Succès
    assert (
        evaluate_conditions(
            conditions,
            {},
            sample_devices,
            "100",
            "rule_test",
            parent_child_relations=relations,
        )
        is True
    )

    # Échec (attendu 3, trouvé 2)
    conditions_fail = [{"min_children": 3}]
    assert (
        evaluate_conditions(
            conditions_fail,
            {},
            sample_devices,
            "100",
            "rule_test",
            parent_child_relations=relations,
        )
        is False
    )


def test_condition_min_children_fallback(sample_devices):
    """Vérifie min_children via le fallback all_devices."""
    conditions = [{"min_children": 2}]
    assert (
        evaluate_conditions(conditions, {}, sample_devices, "100", "rule_test") is True
    )

    conditions_fail = [{"min_children": 3}]
    assert (
        evaluate_conditions(conditions_fail, {}, sample_devices, "100", "rule_test")
        is False
    )


# --- 3. Condition : child_usage_id ---


def test_condition_child_usage_id(sample_devices):
    """Vérifie la détection d'un enfant par son usage_id."""
    conditions = [{"child_usage_id": 2}]

    # Succès : l'appareil 100 a l'enfant 101 avec usage_id 2
    assert (
        evaluate_conditions(conditions, {}, sample_devices, "100", "rule_test") is True
    )

    # Échec : pas d'enfant avec usage_id 99
    conditions_fail = [{"child_usage_id": 99}]
    assert (
        evaluate_conditions(conditions_fail, {}, sample_devices, "100", "rule_test")
        is False
    )

    # Échec si all_devices est vide
    assert evaluate_conditions(conditions, {}, {}, "100", "rule_test") is False


# --- 4. Condition : PRODUCT_TYPE_ID ---


def test_condition_product_type_id():
    """Vérifie la correspondance de PRODUCT_TYPE_ID."""
    conditions = [{"PRODUCT_TYPE_ID": 10}]
    assert (
        evaluate_conditions(conditions, {"PRODUCT_TYPE_ID": 10}, {}, "100", "rule_test")
        is True
    )
    assert (
        evaluate_conditions(conditions, {"PRODUCT_TYPE_ID": 20}, {}, "100", "rule_test")
        is False
    )


# --- 5. Condition : has_parent ---


def test_condition_has_parent():
    """Vérifie la présence d'un parent."""
    conditions = [{"has_parent": True}]
    assert (
        evaluate_conditions(
            conditions, {"parent_periph_id": "100"}, {}, "101", "rule_test"
        )
        is True
    )
    assert evaluate_conditions(conditions, {}, {}, "100", "rule_test") is False


# --- 6. Condition : parent_usage_id ---


def test_condition_parent_usage_id(sample_devices):
    """Vérifie l'usage_id du parent."""
    conditions = [{"parent_usage_id": 1}]
    device = sample_devices["101"]  # parent_periph_id = "100" (usage_id = 1)

    assert (
        evaluate_conditions(conditions, device, sample_devices, "101", "rule_test")
        is True
    )

    # Échec si le parent n'a pas le bon usage_id
    conditions_fail = [{"parent_usage_id": 99}]
    assert (
        evaluate_conditions(conditions_fail, device, sample_devices, "101", "rule_test")
        is False
    )

    # Échec si le périphérique n'a pas de parent
    assert (
        evaluate_conditions(
            conditions, {"usage_id": 1}, sample_devices, "100", "rule_test"
        )
        is False
    )


# --- 7. Condition : parent_has_min_children ---


def test_condition_parent_has_min_children_no_parent():
    """Vérifie l'échec si le périphérique n'a pas de parent."""
    conditions = [{"parent_has_min_children": 1}]
    assert evaluate_conditions(conditions, {}, {}, "100", "rule_test") is False


def test_condition_parent_has_min_children_with_relations(sample_devices):
    """Vérifie parent_has_min_children avec parent_child_relations."""
    conditions = [{"parent_has_min_children": 2}]
    relations = {"100": ["101", "102"]}
    device = sample_devices["101"]

    assert (
        evaluate_conditions(
            conditions,
            device,
            sample_devices,
            "101",
            "rule_test",
            parent_child_relations=relations,
        )
        is True
    )


def test_condition_parent_has_min_children_fallback(sample_devices):
    """Vérifie parent_has_min_children avec le fallback all_devices."""
    conditions = [{"parent_has_min_children": 2}]
    device = sample_devices["101"]

    assert (
        evaluate_conditions(conditions, device, sample_devices, "101", "rule_test")
        is True
    )

    conditions_fail = [{"parent_has_min_children": 5}]
    assert (
        evaluate_conditions(conditions_fail, device, sample_devices, "101", "rule_test")
        is False
    )


# --- 8. Condition : has_children_with_names ---


def test_condition_has_children_with_names(sample_devices):
    """Vérifie la recherche de noms chez les enfants (chaîne et liste)."""
    # Chaîne unique (recherche "température")
    cond_str = [{"has_children_with_names": "température"}]
    assert evaluate_conditions(cond_str, {}, sample_devices, "100", "rule_test") is True

    # Liste de chaînes (recherche "température" ET "humidité")
    cond_list = [{"has_children_with_names": ["température", "humidité"]}]
    assert (
        evaluate_conditions(cond_list, {}, sample_devices, "100", "rule_test") is True
    )

    # Échec : nom manquant
    cond_missing = [{"has_children_with_names": ["température", "pression"]}]
    assert (
        evaluate_conditions(cond_missing, {}, sample_devices, "100", "rule_test")
        is False
    )

    # Échec si all_devices est vide
    assert evaluate_conditions(cond_str, {}, {}, "100", "rule_test") is False


# --- 9. Clé inconnue et conditions multiples ---


def test_unknown_condition_key(caplog):
    """Vérifie le traitement d'une clé de condition non reconnue."""
    conditions = [{"invalid_key": "value"}]
    with caplog.at_level(logging.WARNING):
        assert evaluate_conditions(conditions, {}, {}, "100", "rule_test") is False
        assert "Unknown condition key: invalid_key" in caplog.text


def test_multiple_conditions_combination(sample_devices):
    """Vérifie la combinaison de plusieurs conditions (ET logique)."""
    conditions = [
        {"usage_id": 2},
        {"has_parent": True},
        {"PRODUCT_TYPE_ID": 11},
    ]
    device = sample_devices["101"]

    # Succès : toutes les conditions sont remplies
    assert (
        evaluate_conditions(conditions, device, sample_devices, "101", "rule_test")
        is True
    )

    # Échec : la dernière condition échoue
    conditions_fail = [
        {"usage_id": 2},
        {"has_parent": True},
        {"PRODUCT_TYPE_ID": 99},
    ]
    assert (
        evaluate_conditions(conditions_fail, device, sample_devices, "101", "rule_test")
        is False
    )


@pytest.mark.asyncio
async def test_mapping_rules_edge_cases():
    """Cover mapping_rules.py lines 29-35, 108-114, and 138 (ValueError/TypeError and fallback else)."""
    from custom_components.eedomus.mapping_rules import evaluate_conditions

    # 1. Cible les lignes 29-35 : min_children invalide (provoque une ValueError)
    device_data = {"usage_id": "1"}
    conditions_min_invalid = [{"min_children": "not_an_int"}]
    assert (
        evaluate_conditions(
            conditions=conditions_min_invalid,
            device_data=device_data,
            all_devices={},
            periph_id="periph_1",
            rule_name="Rule1",
        )
        is False
    )

    # 2. Cible les lignes 108-114 : parent_has_min_children invalide (provoque une ValueError)
    device_data_with_parent = {"parent_periph_id": "parent_123"}
    conditions_parent_min_invalid = [{"parent_has_min_children": "not_an_int"}]
    assert (
        evaluate_conditions(
            conditions=conditions_parent_min_invalid,
            device_data=device_data_with_parent,
            all_devices={},
            periph_id="periph_1",
            rule_name="Rule2",
        )
        is False
    )

    # 3. Cible la ligne 138 : parent_has_min_children valide, mais ni parent_child_relations ni all_devices ne sont valides/remplis
    conditions_parent_min_valid = [{"parent_has_min_children": 2}]
    assert (
        evaluate_conditions(
            conditions=conditions_parent_min_valid,
            device_data=device_data_with_parent,
            all_devices={},
            periph_id="periph_1",
            rule_name="Rule3",
            parent_child_relations=None,
        )
        is False
    )
