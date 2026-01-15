#!/usr/bin/env python3
"""
Test spécifique pour la détection RGBW.

Ce script teste la règle de détection des lampes RGBW avec 4 enfants.
"""

import sys
import os

# Ajouter le chemin du module eedomus
sys.path.append(os.path.join(os.path.dirname(__file__), 'custom_components'))

# Importer les modules nécessaires
from eedomus.devices_class_mapping import ADVANCED_MAPPING_RULES
from eedomus.entity import map_device_to_ha_entity

def test_rgbw_detection():
    """Tester la détection RGBW avec différents scénarios."""
    print("=== Test de détection RGBW ===")
    
    # Scénario 1: Lampe RGBW avec exactement 4 enfants
    rgbw_parent = {
        "periph_id": "1077644",
        "name": "Led Meuble Salle de bain",
        "usage_id": "1",
        "SUPPORTED_CLASSES": "112,114,133,134,38,39,49,50,51,96",
        "GENERIC": "11",
        "PRODUCT_TYPE_ID": "2304"
    }
    
    # Enfants RGBW (Rouge, Vert, Bleu, Blanc)
    rgbw_children = {
        "1077645": {
            "periph_id": "1077645",
            "name": "RGBW (Rouge) Salle de bain",
            "usage_id": "1",
            "parent_periph_id": "1077644",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "PRODUCT_TYPE_ID": ""
        },
        "1077646": {
            "periph_id": "1077646",
            "name": "RGBW (Vert) Salle de bain",
            "usage_id": "1",
            "parent_periph_id": "1077644",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "PRODUCT_TYPE_ID": ""
        },
        "1077647": {
            "periph_id": "1077647",
            "name": "RGBW (Bleu) Salle de bain",
            "usage_id": "1",
            "parent_periph_id": "1077644",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "PRODUCT_TYPE_ID": ""
        },
        "1077648": {
            "periph_id": "1077648",
            "name": "RGBW (Blanc) Salle de bain",
            "usage_id": "1",
            "parent_periph_id": "1077644",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "PRODUCT_TYPE_ID": ""
        }
    }
    
    # Créer la structure complète des périphériques
    all_devices = {rgbw_parent["periph_id"]: rgbw_parent}
    all_devices.update(rgbw_children)
    
    print(f"\nTest 1: Lampe RGBW avec 4 enfants")
    print(f"Parent: {rgbw_parent['name']} ({rgbw_parent['periph_id']})")
    print(f"Enfants: {len(rgbw_children)} enfants avec usage_id=1")
    
    # Tester le mapping
    mapping = map_device_to_ha_entity(rgbw_parent, all_devices)
    print(f"Résultat: {mapping['ha_entity']}:{mapping['ha_subtype']}")
    print(f"Justification: {mapping['justification']}")
    
    # Vérifier si la règle RGBW a été appliquée
    if mapping['ha_subtype'] == 'rgbw':
        print("✅ SUCCÈS: Détection RGBW fonctionnelle !")
    else:
        print("❌ ÉCHEC: La lampe RGBW n'a pas été détectée correctement")
        print(f"Mapping obtenu: {mapping}")
    
    # Scénario 2: Lampe avec seulement 2 enfants (ne devrait pas être RGBW)
    print(f"\nTest 2: Lampe avec 2 enfants (ne devrait pas être RGBW)")
    
    limited_children = {
        "1077645": rgbw_children["1077645"],
        "1077646": rgbw_children["1077646"]
    }
    
    limited_devices = {rgbw_parent["periph_id"]: rgbw_parent}
    limited_devices.update(limited_children)
    
    mapping2 = map_device_to_ha_entity(rgbw_parent, limited_devices)
    print(f"Résultat: {mapping2['ha_entity']}:{mapping2['ha_subtype']}")
    
    if mapping2['ha_subtype'] != 'rgbw':
        print("✅ SUCCÈS: Lampe avec 2 enfants correctement identifiée comme non-RGBW")
    else:
        print("❌ ÉCHEC: Fausse détection RGBW avec seulement 2 enfants")
    
    # Scénario 3: Test de la condition de la règle
    print(f"\nTest 3: Vérification directe de la condition RGBW")
    
    rgbw_rule = ADVANCED_MAPPING_RULES["rgbw_lamp_with_children"]
    
    # Tester avec 4 enfants
    result_4 = rgbw_rule["condition"](rgbw_parent, all_devices)
    print(f"Condition avec 4 enfants: {result_4}")
    
    # Tester avec 2 enfants
    result_2 = rgbw_rule["condition"](rgbw_parent, limited_devices)
    print(f"Condition avec 2 enfants: {result_2}")
    
    # Tester avec 0 enfant
    result_0 = rgbw_rule["condition"](rgbw_parent, {rgbw_parent["periph_id"]: rgbw_parent})
    print(f"Condition avec 0 enfant: {result_0}")
    
    print(f"\n=== Résumé ===")
    print(f"La règle RGBW nécessite au moins 4 enfants avec usage_id=1")
    print(f"Cela correspond aux lampes RGBW avec canaux Rouge, Vert, Bleu, Blanc")

if __name__ == "__main__":
    test_rgbw_detection()