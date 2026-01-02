#!/usr/bin/env python3
"""
Programme de test et debug spécifique pour la discussion #8.
Ce programme teste les problèmes de mapping mentionnés dans la discussion GitHub #8.
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


class Discussion8TestResult:
    """Classe pour stocker les résultats des tests spécifiques à la discussion #8."""
    
    def __init__(self):
        self.success_count = 0
        self.failure_count = 0
        self.warning_count = 0
        self.problematic_count = 0
        self.results = []
        self.mapping_stats = {}
        self.problematic_devices = []
    
    def add_success(self, device_data, mapping_result):
        """Ajouter un résultat de mapping réussi."""
        self.success_count += 1
        self.results.append({
            'status': 'success',
            'device_data': device_data,
            'mapping': mapping_result
        })
        
        # Mettre à jour les statistiques
        ha_entity = mapping_result.get('ha_entity', 'unknown')
        self.mapping_stats[ha_entity] = self.mapping_stats.get(ha_entity, 0) + 1
    
    def add_failure(self, device_data, error):
        """Ajouter un résultat de mapping échoué."""
        self.failure_count += 1
        self.problematic_count += 1
        self.problematic_devices.append(device_data['periph_id'])
        self.results.append({
            'status': 'failure',
            'device_data': device_data,
            'error': str(error)
        })
    
    def add_warning(self, device_data, warning, mapping_result):
        """Ajouter un avertissement de mapping."""
        self.warning_count += 1
        self.results.append({
            'status': 'warning',
            'device_data': device_data,
            'warning': warning,
            'mapping': mapping_result
        })
    
    def add_problematic(self, device_data, issue, mapping_result):
        """Ajouter un périphérique problématique spécifique à la discussion #8."""
        self.problematic_count += 1
        self.problematic_devices.append(device_data['periph_id'])
        self.results.append({
            'status': 'problematic',
            'device_data': device_data,
            'issue': issue,
            'mapping': mapping_result
        })
    
    def print_summary(self):
        """Afficher un résumé des résultats des tests."""
        total = self.success_count + self.failure_count + self.warning_count + self.problematic_count
        
        print(f"\n{'='*80}")
        print(f"📊 RÉSULTATS DES TESTS - DISCUSSION #8")
        print(f"{'='*80}")
        print(f"Total des périphériques testés: {total}")
        print(f"✅ Succès: {self.success_count}")
        print(f"⚠️  Avertissements: {self.warning_count}")
        print(f"❌ Échecs: {self.failure_count}")
        print(f"🔴 Problématiques (Discussion #8): {self.problematic_count}")
        
        if self.success_count > 0:
            print(f"\n📈 Statistiques par type d'entité:")
            for entity_type, count in sorted(self.mapping_stats.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / self.success_count) * 100
                print(f"  • {entity_type}: {count} ({percentage:.1f}%)")
        
        if self.problematic_count > 0:
            print(f"\n🔴 Périphériques problématiques identifiés:")
            for device_id in self.problematic_devices:
                print(f"  • {device_id}")
        
        print(f"{'='*80}")
    
    def print_detailed_results(self):
        """Afficher les résultats détaillés."""
        print(f"\n🔍 RÉSULTATS DÉTAILLÉS - DISCUSSION #8")
        print(f"{'='*80}")
        
        if self.success_count > 0:
            print(f"\n✅ MAPPINGS RÉUSSIS ({self.success_count}):")
            for result in [r for r in self.results if r['status'] == 'success']:
                device_data = result['device_data']
                mapping = result['mapping']
                print(f"  • {device_data['name']} ({device_data['periph_id']}):")
                print(f"    Entité: {mapping['ha_entity']}/{mapping['ha_subtype']}")
                print(f"    Justification: {mapping['justification']}")
                if 'description' in device_data:
                    print(f"    Description: {device_data['description']}")
        
        if self.warning_count > 0:
            print(f"\n⚠️  AVERTISSEMENTS ({self.warning_count}):")
            for result in [r for r in self.results if r['status'] == 'warning']:
                device_data = result['device_data']
                mapping = result['mapping']
                print(f"  • {device_data['name']} ({device_data['periph_id']}):")
                print(f"    Warning: {result['warning']}")
                print(f"    Mapping: {mapping['ha_entity']}/{mapping['ha_subtype']}")
        
        if self.failure_count > 0:
            print(f"\n❌ ÉCHECS DE MAPPING ({self.failure_count}):")
            for result in [r for r in self.results if r['status'] == 'failure']:
                device_data = result['device_data']
                print(f"  • {device_data['name']} ({device_data['periph_id']}):")
                print(f"    Error: {result['error']}")
        
        if self.problematic_count > 0:
            print(f"\n🔴 PÉRIPHÉRIQUES PROBLÉMATIQUES ({self.problematic_count}):")
            for result in [r for r in self.results if r['status'] == 'problematic']:
                device_data = result['device_data']
                mapping = result['mapping']
                print(f"  • {device_data['name']} ({device_data['periph_id']}):")
                print(f"    Issue: {result['issue']}")
                print(f"    Mapping: {mapping['ha_entity']}/{mapping['ha_subtype']}")
                print(f"    Justification: {mapping['justification']}")
                if 'description' in device_data:
                    print(f"    Description: {device_data['description']}")


def load_discussion8_test_data(filename: str = 'test_data_discussion8.json') -> List[Dict[str, Any]]:
    """Charger les données de test spécifiques à la discussion #8."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Vérifier si c'est une liste
        if isinstance(data, list):
            return data
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


def analyze_mapping_issues(device_data, mapping_result):
    """Analyser les problèmes potentiels de mapping pour la discussion #8."""
    issues = []
    
    # Vérifier les cas spécifiques mentionnés dans la discussion #8
    if mapping_result.get('ha_entity') == 'unknown':
        issues.append("Mapping par défaut utilisé - ce périphérique devrait être mappé spécifiquement")
    
    if mapping_result.get('ha_entity') == 'sensor' and not mapping_result.get('ha_subtype'):
        issues.append("Capteur sans sous-type spécifique - vérification nécessaire")
    
    if device_data.get('PRODUCT_TYPE_ID') and mapping_result.get('justification', '').find('PRODUCT_TYPE_ID') == -1:
        issues.append("PRODUCT_TYPE_ID présent mais pas utilisé dans la justification")
    
    if device_data.get('usage_id') == '37' and mapping_result.get('ha_entity') != 'binary_sensor':
        issues.append("Capteur de mouvement (usage_id=37) non mappé comme binary_sensor")
    
    if device_data.get('usage_id') == '27' and mapping_result.get('ha_entity') != 'binary_sensor':
        issues.append("Détecteur de fumée (usage_id=27) non mappé comme binary_sensor")
    
    if device_data.get('PRODUCT_TYPE_ID') == '999' and mapping_result.get('ha_entity') != 'select':
        issues.append("Périphérique virtuel (PRODUCT_TYPE_ID=999) non mappé comme select")
    
    return issues


def main():
    """Fonction principale du programme de debug pour la discussion #8."""
    print("🚀 DÉMARRAGE DU PROGRAMME DE DEBUG - DISCUSSION #8")
    print("="*80)
    
    # Charger les données de test spécifiques
    print("\n1️⃣ Chargement des données de test pour la discussion #8...")
    
    test_data = load_discussion8_test_data('test_data_discussion8.json')
    
    if not test_data:
        print("   ❌ Aucun fichier test_data_discussion8.json trouvé")
        return 1
    else:
        print(f"   ✅ Chargées {len(test_data)} données de test depuis test_data_discussion8.json")
    
    # Tester le mapping pour tous les périphériques
    print(f"\n2️⃣ Test du mapping pour {len(test_data)} périphériques problématiques...")
    
    # Créer un résultat de test
    test_result = Discussion8TestResult()
    
    for device_data in test_data:
        try:
            device_name = device_data.get('name', 'Unknown')
            device_id = device_data.get('periph_id', 'unknown')
            
            logger.debug(f"Testing mapping for {device_name} ({device_id})")
            logger.debug(f"Device data: {json.dumps(device_data, indent=2)}")
            
            # Appeler la fonction de mapping
            mapping_result = map_device_to_ha_entity(device_data)
            
            logger.debug(f"Mapping result: {mapping_result}")
            
            # Analyser les problèmes spécifiques à la discussion #8
            issues = analyze_mapping_issues(device_data, mapping_result)
            
            if issues:
                for issue in issues:
                    test_result.add_problematic(device_data, issue, mapping_result)
            elif mapping_result.get('ha_entity') == 'unknown':
                test_result.add_warning(device_data, "Mapping par défaut utilisé", mapping_result)
            else:
                test_result.add_success(device_data, mapping_result)
                
        except Exception as e:
            logger.error(f"Mapping failed for {device_data.get('name', 'Unknown')}: {e}")
            test_result.add_failure(device_data, e)
    
    # Afficher les résultats
    test_result.print_summary()
    test_result.print_detailed_results()
    
    # Analyse spécifique pour la discussion #8
    print(f"\n🔬 ANALYSE SPÉCIFIQUE - DISCUSSION #8")
    print(f"{'='*80}")
    
    if test_result.problematic_count > 0:
        print(f"Problèmes identifiés qui pourraient être liés à la discussion #8:")
        
        # Compter les types de problèmes
        issue_types = {}
        for result in [r for r in test_result.results if r['status'] == 'problematic']:
            issue = result['issue']
            issue_types[issue] = issue_types.get(issue, 0) + 1
        
        print(f"\nTypes de problèmes les plus courants:")
        for issue, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {issue}: {count} fois")
        
        print(f"\n💡 Recommandations pour la discussion #8:")
        print(f"  1. Vérifier les mappings par défaut pour les périphériques inconnus")
        print(f"  2. Examiner les cas où PRODUCT_TYPE_ID n'est pas utilisé")
        print(f"  3. Valider les mappings des capteurs de mouvement et fumée")
        print(f"  4. Ajouter des règles spécifiques pour les périphériques virtuels")
    else:
        print(f"Aucun problème spécifique à la discussion #8 n'a été identifié.")
        print(f"Tous les périphériques sont mappés correctement selon les règles actuelles.")
    
    print(f"\n🎉 PROGRAMME DE DEBUG TERMINÉ - DISCUSSION #8")
    print(f"="*80)
    
    # Retourner un code de sortie approprié
    if test_result.failure_count > 0 or test_result.problematic_count > 0:
        return 1
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())