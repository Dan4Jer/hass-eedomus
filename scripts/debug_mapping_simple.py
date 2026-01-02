#!/usr/bin/env python3
"""
Programme de test et debug simplifié pour la fonction map_device_to_ha_entity.
Ce programme permet de tester le mapping des périphériques eedomus vers les entités Home Assistant
sans dépendre des modules Home Assistant.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Ajouter le chemin du projet pour les imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'custom_components/eedomus')))

# Importer uniquement les modules nécessaires
from devices_class_mapping import DEVICES_CLASS_MAPPING, USAGE_ID_MAPPING

# Configuration du logger
logger = logging.getLogger(__name__)


# Réimplémentation simplifiée de la fonction map_device_to_ha_entity
def map_device_to_ha_entity(device_data, default_ha_entity: str = "sensor"):
    """Mappe un périphérique eedomus vers une entité Home Assistant."""
    logger.debug(
        "Starting mapping for %s (%s)", device_data["name"], device_data["periph_id"]
    )

    supported_classes = (
        device_data.get("SUPPORTED_CLASSES", "").split(",")
        if isinstance(device_data.get("SUPPORTED_CLASSES"), str)
        else []
    )
    generic = device_data.get("GENERIC", "")
    product_type_id = device_data.get("PRODUCT_TYPE_ID", "")
    specific = device_data.get("SPECIFIC", "")

    # Vérifier d'abord si c'est un capteur de fumée (basé uniquement sur usage_id)
    if device_data.get("usage_id") == "27":
        mapping = {
            "ha_entity": "binary_sensor",
            "ha_subtype": "smoke",
            "justification": f"Smoke detector: usage_id=27",
        }
        logger.info(
            "Smoke sensor mapping for %s (%s): %s",
            device_data["name"],
            device_data["periph_id"],
            mapping,
        )
        return mapping

    # Vérifier si c'est un périphérique de messages (basé sur le nom)
    device_name_lower = device_data["name"].lower()
    if "message" in device_name_lower and "box" in device_name_lower:
        mapping = {
            "ha_entity": "sensor",
            "ha_subtype": "text",
            "justification": f"Message box detected in name: '{device_data['name']}'",
        }
        logger.info(
            "📝 Text sensor mapping for %s (%s): %s",
            device_data["name"],
            device_data["periph_id"],
            mapping,
        )
        return mapping

    # Vérifier si c'est un indicateur CPU (basé uniquement sur usage_id)
    if device_data.get("usage_id") == "23":
        mapping = {
            "ha_entity": "sensor",
            "ha_subtype": "cpu_usage",
            "justification": f"CPU usage monitor: usage_id=23",
        }
        logger.info(
            "CPU usage sensor mapping for %s (%s): %s",
            device_data["name"],
            device_data["periph_id"],
            mapping,
        )
        return mapping

    # Vérifier d'abord si c'est un périphérique virtuel (PRODUCT_TYPE_ID=999)
    if product_type_id == "999":
        mapping = {
            "ha_entity": "select",
            "ha_subtype": "virtual",
            "justification": f"PRODUCT_TYPE_ID=999: Périphérique virtuel eedomus pour scène",
        }
        logger.debug(
            "Virtual device mapping for %s (%s): %s",
            device_data["name"],
            device_data["periph_id"],
            mapping,
        )
        return mapping

    # Vérifier les PRODUCT_TYPE_ID spécifiques qui doivent être prioritaires
    if product_type_id == "770":  # Volets Fibaro
        mapping = {
            "ha_entity": "cover",
            "ha_subtype": "shutter",
            "justification": f"PRODUCT_TYPE_ID=770: Volet Fibaro (prioritaire sur usage_id)",
        }
        logger.debug(
            "Fibaro shutter mapping for %s (%s): %s",
            device_data["name"],
            device_data["periph_id"],
            mapping,
        )
        return mapping

    if product_type_id == "4" and device_data.get("usage_id") in [
        "38",
        "19",
        "20",
    ]:  # Chauffages fil pilote
        mapping = {
            "ha_entity": "climate",
            "ha_subtype": "fil_pilote",
            "justification": f"PRODUCT_TYPE_ID=4 avec usage_id={device_data.get('usage_id')}: Chauffage fil pilote (prioritaire)",
        }
        logger.debug(
            "Fil pilote climate mapping for %s (%s): %s",
            device_data["name"],
            device_data["periph_id"],
            mapping,
        )
        return mapping

    # Vérifier les exceptions basées sur usage_id avant le mapping par classe
    # Cas spécial: usage_id=37 (motion) doit être binary_sensor même avec classe 32
    if device_data.get("usage_id") == "37":
        mapping = {
            "ha_entity": "binary_sensor",
            "ha_subtype": "motion",
            "justification": f"usage_id=37: Capteur de mouvement (prioritaire sur classe Z-Wave)",
        }
        logger.info(
            "🚶 Motion sensor mapping for %s (%s): %s",
            device_data["name"],
            device_data["periph_id"],
            mapping,
        )
        return mapping

    zwave_class = None
    for cls in supported_classes:
        cls_num = cls.split(":")[0]  # Extraire le numéro de classe (ex: "38:3" → "38")
        if (
            cls_num in DEVICES_CLASS_MAPPING
            and DEVICES_CLASS_MAPPING[cls_num]["ha_entity"] is not None
        ):
            # Vérifier si GENERIC est compatible
            if (
                not DEVICES_CLASS_MAPPING[cls_num]["GENERIC"]
                or generic in DEVICES_CLASS_MAPPING[cls_num]["GENERIC"]
            ):
                zwave_class = cls_num
                break

    # 2. Appliquer le mapping initial (basé sur SUPPORTED_CLASSES, GENERIC, et PRODUCT_TYPE_ID)
    if zwave_class:
        # Vérifier si PRODUCT_TYPE_ID est défini dans DEVICES_CLASS_MAPPING
        if product_type_id and product_type_id in DEVICES_CLASS_MAPPING[
            zwave_class
        ].get("PRODUCT_TYPE_ID", {}):
            product_mapping = DEVICES_CLASS_MAPPING[zwave_class]["PRODUCT_TYPE_ID"][
                product_type_id
            ]
            mapping = {
                "ha_entity": product_mapping["ha_entity"],
                "ha_subtype": product_mapping.get("ha_subtype"),
                "justification": f"Classe {zwave_class} + PRODUCT_TYPE_ID={product_type_id}: {product_mapping['justification']}",
            }
        else:
            # Utiliser le mapping par défaut
            mapping = {
                "ha_entity": DEVICES_CLASS_MAPPING[zwave_class]["ha_entity"],
                "ha_subtype": DEVICES_CLASS_MAPPING[zwave_class].get("ha_subtype"),
                "justification": f"Classe {zwave_class} + GENERIC={generic}: {DEVICES_CLASS_MAPPING[zwave_class]['justification']}",
            }

        # Vérifier les exceptions basées sur SPECIFIC uniquement (pas de mapping basé sur le nom)
        for exception in DEVICES_CLASS_MAPPING[zwave_class].get("exceptions", []):
            condition = exception["condition"]
            if "SPECIFIC=6" in condition and specific == "6":
                mapping = exception
                mapping["justification"] = (
                    f"Exception: {condition} for {device_data['periph_id']}"
                )
                break
                # Note: Nous ne faisons PAS de mapping basé sur le nom des périphériques
                # Les exceptions basées sur le nom ont été supprimées pour une approche plus robuste

    else:
        mapping = USAGE_ID_MAPPING.get(device_data["usage_id"])

    if mapping is None:
        mapping = {
            "ha_entity": default_ha_entity,
            "ha_subtype": "unknown",
            "justification": "Unknown",
        }
        logger.warning(
            "No mapping found for %s (%s) trying %s... data=%s",
            device_data["name"],
            device_data["periph_id"],
            mapping,
            device_data,
        )

    logger.debug(
        "Mapping for %s (%s) trying mapping=%s",
        device_data["name"],
        device_data["periph_id"],
        mapping,
    )
    return mapping


class MappingTestResult:
    """Classe pour stocker les résultats des tests de mapping."""
    
    def __init__(self):
        self.success_count = 0
        self.failure_count = 0
        self.warning_count = 0
        self.results = []
        self.mapping_stats = {}
    
    def add_success(self, device_name, device_id, mapping_result):
        """Ajouter un résultat de mapping réussi."""
        self.success_count += 1
        self.results.append({
            'status': 'success',
            'device_name': device_name,
            'device_id': device_id,
            'mapping': mapping_result
        })
        
        # Mettre à jour les statistiques
        ha_entity = mapping_result.get('ha_entity', 'unknown')
        self.mapping_stats[ha_entity] = self.mapping_stats.get(ha_entity, 0) + 1
    
    def add_failure(self, device_name, device_id, error, device_data=None):
        """Ajouter un résultat de mapping échoué."""
        self.failure_count += 1
        self.results.append({
            'status': 'failure',
            'device_name': device_name,
            'device_id': device_id,
            'error': str(error),
            'device_data': device_data
        })
    
    def add_warning(self, device_name, device_id, warning, mapping_result):
        """Ajouter un avertissement de mapping."""
        self.warning_count += 1
        self.results.append({
            'status': 'warning',
            'device_name': device_name,
            'device_id': device_id,
            'warning': warning,
            'mapping': mapping_result
        })
    
    def print_summary(self):
        """Afficher un résumé des résultats des tests."""
        total = self.success_count + self.failure_count + self.warning_count
        
        print(f"\n{'='*80}")
        print(f"📊 RÉSULTATS DES TESTS DE MAPPING")
        print(f"{'='*80}")
        print(f"Total des périphériques testés: {total}")
        print(f"✅ Succès: {self.success_count}")
        print(f"⚠️  Avertissements: {self.warning_count}")
        print(f"❌ Échecs: {self.failure_count}")
        
        if self.success_count > 0:
            print(f"\n📈 Statistiques par type d'entité:")
            for entity_type, count in sorted(self.mapping_stats.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / self.success_count) * 100
                print(f"  • {entity_type}: {count} ({percentage:.1f}%)")
        
        print(f"{'='*80}")
    
    def print_detailed_results(self, show_success=True, show_warnings=True, show_failures=True):
        """Afficher les résultats détaillés."""
        print(f"\n🔍 RÉSULTATS DÉTAILLÉS")
        print(f"{'='*80}")
        
        if show_success and self.success_count > 0:
            print(f"\n✅ MAPPINGS RÉUSSIS ({self.success_count}):")
            for result in [r for r in self.results if r['status'] == 'success']:
                print(f"  • {result['device_name']} ({result['device_id']}): {result['mapping']['ha_entity']}/{result['mapping']['ha_subtype']}")
                print(f"    Justification: {result['mapping']['justification']}")
        
        if show_warnings and self.warning_count > 0:
            print(f"\n⚠️  AVERTISSEMENTS ({self.warning_count}):")
            for result in [r for r in self.results if r['status'] == 'warning']:
                print(f"  • {result['device_name']} ({result['device_id']}):")
                print(f"    Warning: {result['warning']}")
                print(f"    Mapping: {result['mapping']['ha_entity']}/{result['mapping']['ha_subtype']}")
        
        if show_failures and self.failure_count > 0:
            print(f"\n❌ ÉCHECS DE MAPPING ({self.failure_count}):")
            for result in [r for r in self.results if r['status'] == 'failure']:
                print(f"  • {result['device_name']} ({result['device_id']}):")
                print(f"    Error: {result['error']}")
                if result.get('device_data'):
                    print(f"    Device data: {json.dumps(result['device_data'], indent=6)}")


def load_test_data_from_file(filename: str) -> List[Dict[str, Any]]:
    """Charger les données de test depuis un fichier JSON."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Vérifier si c'est une liste ou un dictionnaire
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Si c'est un dictionnaire, extraire les valeurs
            return list(data.values())
        else:
            logger.warning(f"Format de données non reconnu dans {filename}")
            return []
            
    except FileNotFoundError:
        logger.error(f"Fichier {filename} non trouvé")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Erreur de décodage JSON dans {filename}: {e}")
        return []
    except Exception as e:
        logger.error(f"Erreur lors du chargement de {filename}: {e}")
        return []


def create_sample_test_data() -> List[Dict[str, Any]]:
    """Créer des données de test échantillon pour le mapping."""
    return [
        # Cas 1: Périphérique virtuel (PRODUCT_TYPE_ID=999)
        {
            "periph_id": "virtual_1",
            "name": "Scène Salon",
            "PRODUCT_TYPE_ID": "999",
            "usage_id": "1",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "SPECIFIC": ""
        },
        
        # Cas 2: Volet Fibaro (PRODUCT_TYPE_ID=770)
        {
            "periph_id": "shutter_1",
            "name": "Volet Salon",
            "PRODUCT_TYPE_ID": "770",
            "usage_id": "48",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "SPECIFIC": ""
        },
        
        # Cas 3: Chauffage fil pilote
        {
            "periph_id": "heating_1",
            "name": "Chauffage Salon",
            "PRODUCT_TYPE_ID": "4",
            "usage_id": "38",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "SPECIFIC": ""
        },
        
        # Cas 4: Capteur de mouvement (usage_id=37)
        {
            "periph_id": "motion_1",
            "name": "Détecteur Mouvement Salon",
            "usage_id": "37",
            "SUPPORTED_CLASSES": "32:1",
            "GENERIC": "SWITCH_MULTILEVEL",
            "SPECIFIC": ""
        },
        
        # Cas 5: Capteur de fumée (usage_id=27)
        {
            "periph_id": "smoke_1",
            "name": "Détecteur Fumée Cuisine",
            "usage_id": "27",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "SPECIFIC": ""
        },
        
        # Cas 6: Capteur CPU (usage_id=23)
        {
            "periph_id": "cpu_1",
            "name": "Monitoring CPU",
            "usage_id": "23",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "SPECIFIC": ""
        },
        
        # Cas 7: Message box (détection par nom)
        {
            "periph_id": "msg_1",
            "name": "Message Box Entrée",
            "usage_id": "1",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "SPECIFIC": ""
        },
        
        # Cas 8: Périphérique inconnu (devrait utiliser le mapping par défaut)
        {
            "periph_id": "unknown_1",
            "name": "Périphérique Inconnu",
            "usage_id": "999",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "SPECIFIC": ""
        },
        
        # Cas 9: Capteur de consommation (usage_id=26)
        {
            "periph_id": "energy_1",
            "name": "Consommation Salon",
            "usage_id": "26",
            "SUPPORTED_CLASSES": "",
            "GENERIC": "",
            "SPECIFIC": ""
        },
        
        # Cas 10: Lumière RGBW
        {
            "periph_id": "light_1",
            "name": "Lumière RGBW Salon",
            "usage_id": "1",
            "SUPPORTED_CLASSES": "96:3",
            "GENERIC": "SWITCH_MULTILEVEL",
            "SPECIFIC": ""
        }
    ]


def test_specific_device_interactive():
    """Tester un périphérique spécifique de manière interactive."""
    print(f"\n🎯 TEST INTERACTIF DE MAPPING")
    print(f"{'='*80}")
    
    # Demander les informations du périphérique
    print("Entrez les informations du périphérique à tester:")
    
    device_data = {}
    device_data['periph_id'] = input("ID du périphérique (periph_id): ")
    device_data['name'] = input("Nom du périphérique: ")
    device_data['usage_id'] = input("Usage ID: ")
    device_data['PRODUCT_TYPE_ID'] = input("PRODUCT_TYPE_ID (laisser vide si inconnu): ")
    device_data['SUPPORTED_CLASSES'] = input("SUPPORTED_CLASSES (ex: '38:3,50:2'): ")
    device_data['GENERIC'] = input("GENERIC (ex: 'SWITCH_MULTILEVEL'): ")
    device_data['SPECIFIC'] = input("SPECIFIC (laisser vide si inconnu): ")
    
    # Nettoyer les champs vides
    for key in list(device_data.keys()):
        if not device_data[key]:
            device_data[key] = ""
    
    # Tester le mapping
    try:
        mapping_result = map_device_to_ha_entity(device_data)
        
        print(f"\n✅ Résultat du mapping:")
        print(f"  Entité HA: {mapping_result['ha_entity']}")
        print(f"  Sous-type: {mapping_result['ha_subtype']}")
        print(f"  Justification: {mapping_result['justification']}")
        
        # Afficher les détails de debug
        print(f"\n🔍 Détails du périphérique:")
        for key, value in device_data.items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"\n❌ Le mapping a échoué: {e}")
        print(f"\n🔍 Détails du périphérique:")
        for key, value in device_data.items():
            print(f"  {key}: {value}")


def main():
    """Fonction principale du programme de debug."""
    print("🚀 DÉMARRAGE DU PROGRAMME DE DEBUG DE MAPPING")
    print("="*80)
    
    # Charger les données de test
    print("\n1️⃣ Chargement des données de test...")
    
    # D'abord essayer de charger depuis un fichier test_data.json
    test_data = load_test_data_from_file('test_data.json')
    
    if not test_data:
        print("   ⚠️  Aucun fichier test_data.json trouvé, utilisation des données échantillon")
        test_data = create_sample_test_data()
    else:
        print(f"   ✅ Chargées {len(test_data)} données de test depuis test_data.json")
    
    # Tester le mapping pour tous les périphériques
    print(f"\n2️⃣ Test du mapping pour {len(test_data)} périphériques...")
    
    # Créer un résultat de test
    test_result = MappingTestResult()
    
    for device_data in test_data:
        try:
            device_name = device_data.get('name', 'Unknown')
            device_id = device_data.get('periph_id', 'unknown')
            
            logger.debug(f"Testing mapping for {device_name} ({device_id})")
            logger.debug(f"Device data: {json.dumps(device_data, indent=2)}")
            
            # Appeler la fonction de mapping
            mapping_result = map_device_to_ha_entity(device_data)
            
            logger.debug(f"Mapping result: {mapping_result}")
            
            # Vérifier si le mapping est valide
            if mapping_result.get('ha_entity') == 'unknown':
                test_result.add_warning(
                    device_name, 
                    device_id, 
                    "Mapping par défaut utilisé (unknown entity)",
                    mapping_result
                )
            else:
                test_result.add_success(device_name, device_id, mapping_result)
                
        except Exception as e:
            logger.error(f"Mapping failed for {device_data.get('name', 'Unknown')}: {e}")
            test_result.add_failure(
                device_data.get('name', 'Unknown'),
                device_data.get('periph_id', 'unknown'),
                e,
                device_data
            )
    
    # Afficher les résultats
    test_result.print_summary()
    test_result.print_detailed_results()
    
    # Analyser les motifs
    print(f"\n🔬 ANALYSE DES MOTIFS DE MAPPING")
    print(f"{'='*80}")
    
    # Analyser les mappings réussis
    successful_mappings = [r for r in test_result.results if r['status'] == 'success']
    
    if successful_mappings:
        print(f"Analyse de {len(successful_mappings)} mappings réussis...")
        
        # Compter les justifications
        justification_counts = {}
        for result in successful_mappings:
            justification = result['mapping']['justification']
            justification_counts[justification] = justification_counts.get(justification, 0) + 1
        
        print(f"\n📋 Justifications de mapping les plus courantes:")
        for justification, count in sorted(justification_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  • {justification}: {count} fois")
    
    # Analyser les échecs
    failed_mappings = [r for r in test_result.results if r['status'] == 'failure']
    
    if failed_mappings:
        print(f"\n❌ Analyse de {len(failed_mappings)} échecs de mapping...")
        
        # Compter les types d'erreurs
        error_types = {}
        for result in failed_mappings:
            error = result['error']
            error_types[error] = error_types.get(error, 0) + 1
        
        print(f"Types d'erreurs les plus courants:")
        for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  • {error}: {count} fois")
    
    # Proposer un test interactif
    print(f"\n3️⃣ TEST INTERACTIF")
    print(f"{'='*80}")
    
    while True:
        choice = input("\nSouhaitez-vous tester un périphérique spécifique ? (o/n): ").lower()
        
        if choice == 'o':
            test_specific_device_interactive()
        elif choice == 'n':
            break
        else:
            print("Réponse non reconnue, veuillez répondre par 'o' ou 'n'")
    
    print(f"\n🎉 PROGRAMME DE DEBUG TERMINÉ")
    print(f"="*80)
    
    # Retourner un code de sortie approprié
    if test_result.failure_count > 0:
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())