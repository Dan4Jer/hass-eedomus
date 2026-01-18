#!/usr/bin/env python3
"""
Test simplifié pour comprendre le problème de mapping du périphérique 1269454.

Ce script simule la logique de détection RGBW sans dépendre de l'environnement HA.
"""

def test_rgbw_condition():
    """Tester la condition RGBW pour le périphérique 1269454."""
    print("=== Analyse du problème 1269454 ===")
    
    # Simulation de la structure du périphérique 1269454
    parent_device = {
        "periph_id": "1269454",
        "name": "Meuble a chaussure Entrée",
        "usage_id": "1"
    }
    
    # Enfants attendus (Rouge, Vert, Bleu, Blanc)
    children = [
        {"periph_id": "1269455", "name": "Meuble Rouge Entrée", "usage_id": "1", "parent_periph_id": "1269454"},
        {"periph_id": "1269456", "name": "Meuble Vert Entrée", "usage_id": "1", "parent_periph_id": "1269454"},
        {"periph_id": "1269457", "name": "Meuble Bleu Entrée", "usage_id": "1", "parent_periph_id": "1269454"},
        {"periph_id": "1269458", "name": "Meuble Blanc Entrée", "usage_id": "1", "parent_periph_id": "1269454"}
    ]
    
    # Simuler la structure all_devices
    all_devices = {parent_device["periph_id"]: parent_device}
    for child in children:
        all_devices[child["periph_id"]] = child
    
    print(f"\n📋 Structure simulée:")
    print(f"Parent: {parent_device['name']} (usage_id={parent_device['usage_id']})")
    print(f"Enfants: {len(children)}")
    
    for child in children:
        print(f"  - {child['name']} ({child['periph_id']}): usage_id={child['usage_id']}")
    
    # Tester la condition RGBW (logique actuelle)
    def rgbw_condition(device_data, all_devices):
        return (
            device_data.get("usage_id") == "1" and
            sum(
                1 for child_id, child in all_devices.items()
                if child.get("parent_periph_id") == device_data.get("periph_id") and child.get("usage_id") == "1"
            ) >= 4
        )
    
    condition_result = rgbw_condition(parent_device, all_devices)
    
    # Compter les enfants avec usage_id=1
    rgbw_children_count = sum(
        1 for child_id, child in all_devices.items()
        if child.get("parent_periph_id") == parent_device["periph_id"] and child.get("usage_id") == "1"
    )
    
    print(f"\n🔍 Résultats du test:")
    print(f"Condition RGBW: {condition_result}")
    print(f"Enfants avec usage_id=1: {rgbw_children_count}")
    print(f"Seuil requis: >= 4")
    print(f"Condition satisfaite: {rgbw_children_count >= 4}")
    
    if condition_result:
        print(f"\n✅ La condition RGBW est satisfaite!")
        print(f"Le périphérique DOIT être mappé comme light:rgbw")
        
        print(f"\n💡 Problèmes possibles si ce n'est pas le cas:")
        print(f"1. Les données réelles des enfants n'ont pas usage_id=1")
        print(f"2. Le périphérique parent n'a pas usage_id=1")
        print(f"3. La structure all_devices n'est pas correctement passée")
        print(f"4. Un problème dans la logique de priorité du mapping")
        
    else:
        print(f"\n❌ La condition RGBW n'est pas satisfaite!")
        print(f"Nombre d'enfants avec usage_id=1: {rgbw_children_count}")
        
        if rgbw_children_count == 0:
            print(f"\n💡 Problème probable: Aucun enfant n'a usage_id=1")
            print(f"Vérifiez les données réelles des enfants dans l'API eedomus")
        else:
            print(f"\n💡 Problème probable: Pas assez d'enfants avec usage_id=1")
            print(f"Attendu: 4 enfants, Trouvé: {rgbw_children_count}")

def analyze_possible_issues():
    """Analyser les causes possibles du problème."""
    print(f"\n=== Causes possibles du problème ===")
    
    issues = [
        {
            "id": 1,
            "title": "Données des enfants incorrectes",
            "description": "Les enfants n'ont pas usage_id=1 dans les données réelles",
            "solution": "Vérifier les données brutes de l'API eedomus pour les enfants"
        },
        {
            "id": 2,
            "title": "Structure all_devices incomplète",
            "description": "La structure all_devices passée au mapping est incomplète",
            "solution": "Vérifier que tous les périphériques sont chargés dans le coordinator"
        },
        {
            "id": 3,
            "title": "Problème de priorité",
            "description": "Une autre règle est appliquée avant la règle RGBW",
            "solution": "Vérifier l'ordre d'application des règles dans les logs"
        },
        {
            "id": 4,
            "title": "Données API différentes",
            "description": "Les données réelles de l'API sont différentes des données attendues",
            "solution": "Capturer et analyser les données réelles de l'API pour ce périphérique"
        }
    ]
    
    for issue in issues:
        print(f"\n{issue['id']}. {issue['title']}")
        print(f"   Description: {issue['description']}")
        print(f"   Solution: {issue['solution']}")

def suggest_debugging_steps():
    """Suggérer des étapes de débogage."""
    print(f"\n=== Étapes de débogage recommandées ===")
    
    steps = [
        "1. Capturer les données réelles de l'API pour le périphérique 1269454 et ses enfants",
        "2. Vérifier les logs de Home Assistant avec le niveau DEBUG pour le coordinator",
        "3. Ajouter des logs spécifiques pour tracer le processus de mapping",
        "4. Tester avec les données réelles dans un environnement de développement",
        "5. Comparer les données attendues vs données réelles"
    ]
    
    for i, step in enumerate(steps, 1):
        print(f"{i}. {step}")

if __name__ == "__main__":
    test_rgbw_condition()
    analyze_possible_issues()
    suggest_debugging_steps()