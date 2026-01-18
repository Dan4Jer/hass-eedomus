#!/usr/bin/env python3
"""
Test spécifique pour le périphérique 1269454 (Meuble a chaussure Entrée).

Ce script simule le mapping pour ce périphérique spécifique
pour comprendre pourquoi il n'est pas détecté comme RGBW.
"""

import sys
import os

# Ajouter le chemin du module eedomus
sys.path.append(os.path.join(os.path.dirname(__file__), 'custom_components'))

from device_mapping import ADVANCED_MAPPING_RULES, USAGE_ID_MAPPING
from entity import map_device_to_ha_entity

def test_1269454_mapping():
    """Tester le mapping pour le périphérique 1269454."""
    print("=== Test de mapping pour 1269454 (Meuble a chaussure Entrée) ===")
    
    # Données du périphérique parent (d'après device_table_home_assistant_base.md)
    parent_device = {
        "periph_id": "1269454",
        "name": "Meuble a chaussure Entrée",
        "usage_id": "1",
        "SUPPORTED_CLASSES": "112,114,133,134,38,39,49,50,51,96",
        "GENERIC": "11",
        "PRODUCT_TYPE_ID": "2304"
    }
    
    # Données des enfants (Rouge, Vert, Bleu, Blanc)
    children = {
        "1269455": {
            "periph_id": "1269455",
            "name": "Meuble Rouge Entrée",
            "usage_id": "1",  # Doit être "1" pour être compté comme enfant RGBW
            "parent_periph_id": "1269454",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "PRODUCT_TYPE_ID": ""
        },
        "1269456": {
            "periph_id": "1269456",
            "name": "Meuble Vert Entrée",
            "usage_id": "1",
            "parent_periph_id": "1269454",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "PRODUCT_TYPE_ID": ""
        },
        "1269457": {
            "periph_id": "1269457",
            "name": "Meuble Bleu Entrée",
            "usage_id": "1",
            "parent_periph_id": "1269454",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "PRODUCT_TYPE_ID": ""
        },
        "1269458": {
            "periph_id": "1269458",
            "name": "Meuble Blanc Entrée",
            "usage_id": "1",
            "parent_periph_id": "1269454",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "PRODUCT_TYPE_ID": ""
        }
    }
    
    # Créer la structure complète
    all_devices = {parent_device["periph_id"]: parent_device}
    all_devices.update(children)
    
    print(f"\n📋 Structure du périphérique 1269454:")
    print(f"Parent: {parent_device['name']} (usage_id={parent_device['usage_id']})")
    print(f"Enfants: {len(children)}")
    
    for child_id, child in children.items():
        print(f"  - {child['name']} ({child_id}): usage_id={child['usage_id']}")
    
    # Tester la condition RGBW directement
    rgbw_rule = ADVANCED_MAPPING_RULES["rgbw_lamp_with_children"]
    condition_result = rgbw_rule["condition"](parent_device, all_devices)
    
    print(f"\n🔍 Test de la condition RGBW:")
    print(f"Condition résultat: {condition_result}")
    
    # Compter les enfants avec usage_id=1
    rgbw_children_count = sum(
        1 for child_id, child in all_devices.items()
        if child.get("parent_periph_id") == parent_device["periph_id"] and child.get("usage_id") == "1"
    )
    
    print(f"Nombre d'enfants avec usage_id=1: {rgbw_children_count}")
    print(f"Seuil requis: >= 4")
    print(f"Condition satisfaite: {rgbw_children_count >= 4}")
    
    # Tester le mapping complet
    print(f"\n🎯 Test du mapping complet:")
    mapping = map_device_to_ha_entity(parent_device, all_devices)
    
    print(f"Résultat du mapping:")
    print(f"  Entité: {mapping['ha_entity']}")
    print(f"  Sous-type: {mapping['ha_subtype']}")
    print(f"  Justification: {mapping['justification']}")
    
    # Vérifier si c'est le résultat attendu
    if mapping['ha_subtype'] == 'rgbw':
        print(f"\n✅ SUCCÈS: Le périphérique est correctement mappé comme RGBW !")
    else:
        print(f"\n❌ PROBLÈME: Le périphérique n'est pas mappé comme RGBW")
        print(f"Attendu: light:rgbw")
        print(f"Obtenu: {mapping['ha_entity']}:{mapping['ha_subtype']}")
        
        # Diagnostic supplémentaire
        if rgbw_children_count < 4:
            print(f"\n💡 Diagnostic: Seulement {rgbw_children_count} enfants avec usage_id=1 trouvés")
            print(f"La règle RGBW nécessite au moins 4 enfants avec usage_id=1")
        else:
            print(f"\n💡 Diagnostic: La condition RGBW est satisfaite mais le mapping n'est pas appliqué")
            print(f"Cela peut indiquer un problème dans la logique de priorité")

if __name__ == "__main__":
    test_1269454_mapping()